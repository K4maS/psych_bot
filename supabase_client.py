from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_ANON_KEY
from typing import Optional, Union, Dict, List
import logging


url: str = SUPABASE_URL  # ← сюда свой URL из Supabase
key: str = SUPABASE_ANON_KEY  # ← сюда свой публичный anon ключ
supabase: Client = create_client(url, key)

PSYHOLOGIST_TABLE = "psychologists"
PATIENTS_TABLE = "patients"

async def get_row_from_base(table, column, value):
    try:
        response = supabase.table(table).select("*").eq(column, value).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logging.error(f"[BOT] Ошибка при получении строки из базы: {e}")
        raise
    
async def insert_row_to_base(table, data: dict):
    try:
        response = supabase.table(table).upsert(data, on_conflict="uid").execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logging.error(f"[BOT] Ошибка при добавлении строки: {e}")
        return None
    
async def update_row_to_base(table, input_value, column, value):
    try:
        response = supabase.table(table).update(input_value).eq(column, value).execute()
        if response.data:
            return response.data[0]['row']
        return None
    except Exception as e:
        logging.error(f"[BOT] Ошибка при получении строки из базы: {e}")
        return None



async def get_row_from_patients_db(uid):
    return await get_row_from_base(PATIENTS_TABLE, "uid",  uid)

async def get_row_from_psycho_by_db(uid):
    return await get_row_from_base(PSYHOLOGIST_TABLE, "uid", uid)

async def get_row_from_psycho_by_psychoid_db(psychologist_id):
    return await get_row_from_base(PSYHOLOGIST_TABLE, "psychologist_id", psychologist_id)
async def get_row_from_psycho_by_uid_db(uid):
    return await get_row_from_base(PSYHOLOGIST_TABLE, "uid", uid)

async def insert_row_to_patients_db(uid, input_value):
    return await insert_row_to_base(PATIENTS_TABLE, {"uid": str(uid), **input_value}) 

async def insert_row_to_psycho_db(uid, input_value):
    return await insert_row_to_base(PSYHOLOGIST_TABLE, {"uid": str(uid), **input_value} )
    
async def joint_table(uid):
    response = supabase \
    .from_("patients") \
    .select("*, psychologist:psychologists(*)") \
    .eq("uid", uid) \
    .execute()
    if response.data:
        return response.data[0]
    
async def get_psycho_data(uid: int) -> Optional[str]:
    data = await joint_table(uid)
    if not data or not isinstance(data, dict):
        return None
    return data.get("psychologist", {})

async def get_table_linked_to_psycho(uid: int) -> Optional[str]:
    data = await get_psycho_data(uid)
    return data.get("table")

async def get_credits_of_psycho(uid: int) -> Optional[str]:
    data = await get_psycho_data(uid)
    return data.get("credits")


async def joint_table_upsert(uid):
    response = supabase \
        .from_("patients") \
        .upsert(data, on_conflict="uid") \
        .execute()
    if response.data:
        return response.data[0]


async def decrement_credits(uid: int) -> Optional[int]:
    try:
        # 1. Получаем пациента по uid
        patient_data = await get_row_from_patients_db(uid)
        if not patient_data:
            logging.error(f"[Credits] Пациент с uid={uid} не найден.")
            return None

        # 2. Получаем psychologist_id
        psychologist_id = patient_data.get("psychologist_id")
        if not psychologist_id:
            logging.error(f"[Credits] У пациента с uid={uid} нет psychologist_id.")
            return None

        # 3. Получаем психолога по psychologist_id
        psycho_data = await get_row_from_psycho_by_psychoid_db(psychologist_id)
        if not psycho_data:
            logging.error(f"[Credits] Психолог с id={psychologist_id} не найден.")
            return None

        # 4. Читаем текущие кредиты
        credits = psycho_data.get("credits")
        if credits is None:
            logging.error(f"[Credits] У психолога {psychologist_id} нет поля 'credits'.")
            return None

        # 5. Уменьшаем кредиты
        new_credits = int(credits) - 1
        if new_credits < 0:
            new_credits = 0  # Можно также сделать return None если хочешь блокировать

        # 6. Обновляем кредиты у психолога
        await update_row_to_base(PSYHOLOGIST_TABLE, {"credits": new_credits}, "psychologist_id", psychologist_id)

        return new_credits

    except Exception as e:
        logging.exception(f"[Credits] Ошибка при уменьшении кредитов у психолога {psychologist_id}: {e}")
        return None