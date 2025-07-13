from openai import OpenAI
import logging
import random
from config import OPENAI_API_KEY, OPENROUTER_API_KEY
from sheets import get_prompt_from_sheet

logging.basicConfig(filename="errors.log", level=logging.ERROR)

models = [
    {"name": "openai/gpt-4o", "key": OPENROUTER_API_KEY},
    {"name": "openai/gpt-3.5-turbo", "key": OPENROUTER_API_KEY},
    {"name": "deepseek-ai/deepseek-coder", "key": OPENROUTER_API_KEY},
    {"name": "google/gemini-pro", "key": OPENROUTER_API_KEY},
    {"name": "mistralai/mistral-7b-instruct", "key": OPENROUTER_API_KEY},
]

def call_gpt(message_1, message_2):
    prompt_prefix = get_prompt_from_sheet() or "На основе сообщений проведи психологический анализ, используя доказательные подходы. Ответ выдай в виде краткого резюме."

    system_prompt = {
        "role": "system",
        "content": prompt_prefix
    }

    user_prompt = {
        "role": "user",
        "content": f"Сообщение партнёра 1:\n{message_1}\n\nСообщение партнёра 2:\n{message_2}"
    }

    for model in models:
        try:
            client = OpenAI(api_key = model["key"])
            response = client.chat.completions.create(
                model=model["name"],
                messages=[system_prompt, user_prompt],
                temperature=0.7
            )
            result = response.choices[0].message.content
            print(f"[GPT] Использована модель: {model['name']}")
            return result
        except Exception as e:
            logging.error(f"[GPT] Ошибка с моделью {model['name']}: {e}")
            print(f"[GPT] Ошибка модели {model['name']}: {e}")
            raise
    return "Ошибка: ни одна модель GPT не сработала."
