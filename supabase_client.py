from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_ANON_KEY
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
        return None
    
async def insert_row_to_base(table, data: dict):
    try:
        response = supabase.table(table).insert(data).execute()
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
    
async def get_table_linked_to_psycho(uid):
    data = await joint_table(uid)
    return  data.get("psychologist", {}).get("table")