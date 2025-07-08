import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import GOOGLE_CREDENTIALS_JSON, SHEET_NAME, PROMPT_SHEET_NAME, spreadsheet_id
import logging

logging.basicConfig(filename="errors.log", level=logging.ERROR)

CODE, NAME, UID_1, MESSAGE_1, USER1_ANALYSIS, UID_2, MESSAGE_2, USER2_ANALYSIS, SUMMARY, RECOMENDATION, RECOMENDATION_TO_A_PSYHOLOGIST = range(1,12)


scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIALS_JSON, scope)
client = gspread.authorize(creds)

def get_worksheet(sheet_name=SHEET_NAME):
    try:
        sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
        return sheet
    except Exception as e:
        logging.error(f"[GoogleSheets] Ошибка открытия листа {sheet_name}: {e}")
        raise

def get_all_codes():
    sheet = get_worksheet()
    return sheet.col_values(CODE)[1:]  # exclude header

def find_row_by_code(code):
    sheet = get_worksheet()
    codes = sheet.col_values(CODE)
    try:
        row = codes.index(code) + 1
        return row
    except ValueError:
        return None

def get_prompt_from_sheet():
    try:
        prompt_sheet = get_worksheet(PROMPT_SHEET_NAME)
        prompt = prompt_sheet.acell("A1").value
        return prompt if prompt else None
    except Exception as e:
        logging.error(f"[Prompt] Ошибка получения промпта: {e}")
        return None

def write_message(row, user_id, message, is_first=True):
    sheet = get_worksheet()
    col_uid = UID_1 if is_first else UID_2
    col_msg = MESSAGE_1 if is_first else MESSAGE_2
    try:
        sheet.update_cell(row, col_uid, str(user_id))
        sheet.update_cell(row, col_msg, message)
    except Exception as e:
        logging.error(f"[GoogleSheets] Ошибка записи сообщения: {e}")
        raise

def read_messages(row):
    sheet = get_worksheet()
    try:
        uid_1 = sheet.cell(row, UID_1).value
        msg_1 = sheet.cell(row, MESSAGE_1).value
        uid_2 = sheet.cell(row, UID_2).value
        msg_2 = sheet.cell(row, MESSAGE_2).value
        return uid_1, msg_1, uid_2, msg_2
    except Exception as e:
        logging.error(f"[GoogleSheets] Ошибка чтения сообщений: {e}")
        raise
    
def read_column(row, column):
    sheet = get_worksheet()
    try:
        column = sheet.cell(row, column).value
        return column
    except Exception as e:
        logging.error(f"[GoogleSheets] Ошибка чтения сообщений: {e}")
        raise
    

def write_to_cell(row, column, value):
    sheet = get_worksheet()
    try:
        sheet.update_cell(row, column, value)
    except Exception as e:
        logging.error(f"[GoogleSheets] Ошибка записи summary: {e}")
        raise

def write_summary(row, value):
    write_to_cell(row, SUMMARY, value)
    
def write_user1_analysis(row, value):
    write_to_cell(row, USER1_ANALYSIS, value)
    
def write_user2_analysis(row, value):
    write_to_cell(row, USER2_ANALYSIS, value)
    
def write_recommendation(row, value):
    write_to_cell(row, RECOMENDATION, value)
    
def write_recommendation_to_apsychologist(row, value):
    write_to_cell(row, RECOMENDATION_TO_A_PSYHOLOGIST, value)