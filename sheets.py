# sheet.py
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import GOOGLE_CREDENTIALS_JSON, SHEET_NAME, PROMPT_SHEET_NAME, spreadsheet_id
import logging
import re

logging.basicConfig(filename="errors.log", level=logging.ERROR)

CODE, NAME, UID_1, MESSAGE_1, USER1_ANALYSIS, UID_2, MESSAGE_2, USER2_ANALYSIS, SUMMARY, RECOMENDATION, RECOMENDATION_TO_A_PSYHOLOGIST = range(1,12)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIALS_JSON, scope)
client = gspread.authorize(creds)

def extract_spreadsheet_id(google_link: str) -> str:
    # Пример ссылки: https://docs.google.com/spreadsheets/d/1AbCdEfGhIjKlMnOpQrStUvWxYz/edit#gid=0
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", google_link)
    return match.group(1) if match else None

def get_worksheet(sheet_id, sheet_name=SHEET_NAME):
    try:
        sheet = client.open_by_key(sheet_id).worksheet(sheet_name)
        return sheet
    except Exception as e:
        logging.error(f"[GoogleSheets] Ошибка открытия листа {sheet_name}: {e}")
        raise

def get_all_codes(sheet_id):
    sheet = get_worksheet(sheet_id)
    return sheet.col_values(CODE)[1:]  # exclude header

def find_row_by_code(code, sheet_id):
    sheet = get_worksheet(sheet_id)
    codes = sheet.col_values(CODE)
    print(sheet, codes)
    try:
        row = codes.index(code) + 1
        return row
    except ValueError:
        return None

def get_prompt_from_sheet(sheet_id = spreadsheet_id):
    try:
        prompt_sheet = get_worksheet(sheet_id, PROMPT_SHEET_NAME)
        prompt = prompt_sheet.acell("A1").value
        print(f'Промпт {prompt}')
        return prompt if prompt else None
    except Exception as e:
        logging.error(f"[Prompt] Ошибка получения промпта: {e}")
        return None

def write_message(row, user_id, message, sheet_id, is_first=True):
    sheet = get_worksheet(sheet_id)
    col_uid = UID_1 if is_first else UID_2
    col_msg = MESSAGE_1 if is_first else MESSAGE_2
    try:
        print(message)
        sheet.update_cell(row, col_uid, str(user_id))
        sheet.update_cell(row, col_msg, message)

    except Exception as e:
        logging.error(f"[GoogleSheets] Ошибка записи сообщения: {e}")
        raise

def read_messages(row, sheet_id):
    sheet = get_worksheet(sheet_id)
    try:
        uid_1 = sheet.cell(row, UID_1).value
        msg_1 = sheet.cell(row, MESSAGE_1).value
        uid_2 = sheet.cell(row, UID_2).value
        msg_2 = sheet.cell(row, MESSAGE_2).value
        return uid_1, msg_1, uid_2, msg_2
    except Exception as e:
        logging.error(f"[GoogleSheets] Ошибка чтения сообщений: {e}")
        raise
    
def read_column(row, column, sheet_id):
    sheet = get_worksheet(sheet_id)
    try:
        column = sheet.cell(row, column).value
        return column
    except Exception as e:
        logging.error(f"[GoogleSheets] Ошибка чтения сообщений: {e}")
        raise
    

def write_to_cell(row, column, value, sheet_id):
    sheet = get_worksheet(sheet_id)
    try:
        sheet.update_cell(row, column, value)
    except Exception as e:
        logging.error(f"[GoogleSheets] Ошибка записи summary: {e}")
        raise

def write_summary(row, value,   sheet_id):
    """Записывает summary в указанную строку."""
    write_to_cell(row, SUMMARY, value, sheet_id)
    
def write_user1_analysis(row, value, sheet_id):
    write_to_cell(row, USER1_ANALYSIS, value, sheet_id)
    
def write_user2_analysis(row, value, sheet_id):
    """Записывает анализ пользователя 2 в указанную строку."""
    write_to_cell(row, USER2_ANALYSIS, value,  sheet_id)
    
def write_recommendation(row, value, sheet_id):
    write_to_cell(row, RECOMENDATION, value, sheet_id)
    
def write_recommendation_to_psychologist(row, value, sheet_id):
    write_to_cell(row, RECOMENDATION_TO_A_PSYHOLOGIST, value, sheet_id)