import httpx
import logging
from config import OPENROUTER_API_KEY
from sheets import get_prompt_from_sheet

logging.basicConfig(filename="errors.log", level=logging.ERROR)

MODELS = [
    # "openai/gpt-4o",
    # "openai/gpt-3.5-turbo",
    # "deepseek-ai/deepseek-coder",
    # "google/gemini-pro",
    "mistralai/mistral-7b-instruct",
]

API_URL = "https://openrouter.ai/api/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://yourproject.com",  # заменить при необходимости
    "X-Title": "PsychologyBot",
}

def call_gpt(sheet_id, value, extra_prefix):
    
    prompt_prefix = get_prompt_from_sheet() or (
        "Ты профессиональный психолог."
    )
     
    messages = [
        {"role": "system", "content": f"{prompt_prefix}.\n\n{extra_prefix}"},
        {"role": "user", "content": f"{value}"}
    ]

    
 
    for model in MODELS:
        try:
            response = httpx.post(API_URL, headers=HEADERS, json={
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1000,
            })

            if response.status_code == 200:
                data = response.json()
                result = data["choices"][0]["message"]["content"]
                print(f"[GPT] Использована модель: {model}")
                return result
            else:
                raise Exception(f"Код: {response.status_code} | {response.text}")

        except Exception as e:
            logging.error(f"[GPT] Ошибка с моделью {model}: {e}")
            print(f"[GPT] Ошибка модели {model}: {e}")

    return "Ошибка: ни одна модель GPT не сработала."

# Парная консультация с психологом
def call_gpt_pair(sheet_id, message_1, message_2):
    extra_prefix = "Проанализируй сообщения двух партнёров и составь краткое резюме для психолога. Не надо рекомендаций, напиши пару предложений"
    messages =  f"Партнёр 1: {message_1}\n\nПартнёр 2: {message_2}"
    return call_gpt(sheet_id, messages, extra_prefix)

def call_gpt_to_pair(sheet_id, message_1, message_2):
    extra_prefix = "Проанализируй сообщения двух партнёров и составь краткое резюме c советами для пары. Не надо описывать, просто несколько предложений с рекомендациями."
    messages =  f"Партнёр 1: {message_1}\n\nПартнёр 2: {message_2}"
    return call_gpt(sheet_id, messages, extra_prefix)

def call_gpt_pair_to_psyhologist( sheet_id, message_1, message_2):
    extra_prefix = "Проанализируй сообщения двух партнёров и составь краткое резюме с советами для психолога. Напиши только советы психологу для работы с данной парой"
    messages =  f"Партнёр 1: {message_1}\n\nПартнёр 2: {message_2}"
    return call_gpt(sheet_id, messages, extra_prefix)

def call_gpt_user(sheet_id, user_message):
    extra_prefix = "Проанализируй сообщения партнёра и составь краткое резюме для психолога. Опиши только одного пратнера, не надо описывать прару. Нам интересен только конкретный партнер"
    message = f"Партнёр: {user_message}"
    return call_gpt(sheet_id, user_message, extra_prefix)

# Личная консультация с психологом
def call_gpt_single(sheet_id, message):
    extra_prefix = "Проанализируй сообщения конкретного пользователя и составь краткое резюме для психолога. Не надо рекомендаций, напиши несколько предложений"
    messages =  f"Пользователь: {message}"
    return call_gpt(sheet_id, messages, extra_prefix)

def call_gpt_to_single(sheet_id, message):
    extra_prefix = "Проанализируй сообщения конкретного пользователя и составь краткое резюме c советами для конкретного пользователя. Не надо описывать, просто несколько предложений с рекомендациями."
    messages =  f"Пользователь: {message}"
    return call_gpt(sheet_id, messages, extra_prefix)

def call_gpt_single_to_psychologist(sheet_id, message):
    extra_prefix = "Проанализируй сообщения конкретного пользователя и составь краткое резюме с советами для психолога. Напиши только советы психологу для работы с данным поциентом"
    messages =  f"Пользователь: {message}"
    return call_gpt(sheet_id, messages, extra_prefix)
