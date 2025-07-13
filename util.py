from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes
import logging
from seance_data import (
    steps,
    Q_2,
    STEP_MSG1,
    reset_action,
    back_action,
    reply_markup_back_reset,
    user_sessions,
    STEP_CODE,
    STEP_PSYCHO_CODE,
    STEP_START
)
import re
from supabase_client import (
    supabase,
    get_row_from_patients_db,
    get_credits_of_psycho,
)


def is_valid_sheet_url(url: str) -> bool:
    return re.match(r'^https:\/\/docs\.google\.com\/spreadsheets\/d\/[a-zA-Z0-9-_]+', url) is not None


async def first_step_handler(update: object, context, user_id):
    try:
        credits = await get_credits_of_psycho(user_id)

        row: Optional[dict] = await get_row_from_patients_db(user_id)
        next_step: int = STEP_PSYCHO_CODE if row is None else STEP_CODE
        if row and credits <= 0:
            await update.message.reply_text("Недостаточно кредитов", reply_markup=ReplyKeyboardRemove())
            return reset(update, context)

        await update.message.reply_text(steps[next_step]['question'], reply_markup=ReplyKeyboardRemove())
        return global_step_changer(steps[next_step]['component'], update, context)
    except Exception as e:
        logging.error(e)
        await update.message.reply_text('Ошибка базы данных', reply_markup=ReplyKeyboardRemove())


# Ресет
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        user_sessions.pop(user_id, None)
        context.user_data["users_actions"] = [None] * len(steps)

        await update.message.reply_text(steps[STEP_START]['question'], reply_markup=ReplyKeyboardRemove())
        return await first_step_handler(update, context, user_id)

    except Exception as e:
        logging.error(f"[BOT] Ошибка при сбросе сессии: {e}")
        await update.message.reply_text("Произошла ошибка при сбросе сессии. Пожалуйста, попробуйте еще раз.",
                                        reply_markup=ReplyKeyboardRemove())
        return global_step_changer(STEP_START, update, context)


# Функция для создания формата ответов
# Используется для форматирования вопросов и ответов пользователя
def create_answers_format(steps, users_actions, context, left_cut, right_cut):
    try:
        questions = steps[left_cut: right_cut]
        users_actions = context.user_data.get("users_actions", [None] * len(steps))
        users_answers = users_actions[left_cut: right_cut]

        text = 'Вопросы заданные психологом пользователю: \n'
        for index, question in enumerate(questions):
            text += f'- {question["question"]}\n  - {users_answers[index]}\n'
        return text + '\n'
    except IndexError:
        return "Нет вопросов для отображения."


# Функция для навигации между шагами
# Используется для обработки действий пользователя, таких как переход назад или сброс сессии
async def navigation(message, update, context):
    try:
        current_step = context.user_data.get("current_step", 0)
        print(f'Вы перешли на шаг {current_step}')

        if message == reset_action:
            return await reset(update, context)
        elif message == back_action:
            if current_step <= 0:
                await update.message.reply_text("Вы находитесь на первом шаге.", reply_markup=reply_markup_back_reset)
            else:
                current_step -= 1
                context.user_data["current_step"] = current_step
                await message_replay(steps[current_step], update, context)
            return current_step
    except Exception as e:
        logging.error(f"Ошибка в навигации: {e}")
        await update.message.reply_text("Произошла ошибка при навигации. Пожалуйста, попробуйте еще раз.",
                                        reply_markup=reply_markup_back_reset)
        return None


# Функция для изменения глобального шага
# Используется для записи текущего шага в глобальную переменную
# и вывода сообщения о переходе на новый шаг
def global_step_changer(step, update, context):
    context.user_data["current_step"] = step
    print(f'Вы перешли на шаг {step}')
    return step


def get_user_id(update):
    if update.message:
        return update.message.from_user.id
    elif update.callback_query:
        return update.callback_query.from_user.id
    elif update.effective_user:
        return update.effective_user.id
    return None


# Функция для обработки вопросов и ответов
# Используется для обработки ответов на вопросы и перехода к следующему вопросу
async def question_answer_base(update, context, question_index):
    try:
        user_id = get_user_id(update)
        session = user_sessions.get(user_id)
        if session is None:
            await update.message.reply_text("Сессия не найдена. Начните сначала /start")
            return await reset(update, context)

        row = session["row"]
        device = session["device"]
        message = update.message.text.strip()

        users_actions = context.user_data.get("users_actions", [None] * len(steps))
        users_actions[question_index] = message
        context.user_data["users_actions"] = users_actions  # сохраняем

        if message == reset_action or message == back_action:
            return await navigation(message, update, context)

        if device == "one" and question_index == Q_2:
            await update.message.reply_text("Опишите ваши проблемы:")
            return global_step_changer(STEP_MSG1, update, context)

        try:
            next_question = steps[question_index + 1]
            await message_replay(next_question, update, context)

            if 'component' in next_question or len(steps) <= question_index:
                return global_step_changer(next_question['component'], update, context)

        except IndexError:
            await update.message.reply_text("Опишите ваши проблемы:")

        uid_1, msg_1, uid_2, msg_2 = read_messages(row)
        return global_step_changer(STEP_MSG1, update, context)
    except Exception as e:
        logging.error(f"Ошибка в обработке вопроса: {e}")
        await update.message.reply_text("Произошла ошибка при обработке вашего ответа. Пожалуйста, попробуйте еще раз.",
                                        reply_markup=reply_markup_back_reset)
        return None


# Вывод сообщения с вопросом и кнопками
async def message_replay(step, update, context):
    try:
        question_text = step['question']
        reply_markup = step['reply_markup'] if 'reply_markup' in step else None

        return await update.message.reply_text(question_text,
                                               reply_markup=reply_markup if reply_markup else reply_markup_back_reset)
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения: {e}")
        return None


# Функция для создания обработчика вопросов
# Используется для создания обработчиков для каждого вопроса
def make_question_handler(question_index):
    try:
        async def question_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            return await question_answer_base(update, context, question_index)

        return question_handler
    except Exception as e:
        logging.error(f"Ошибка при создании обработчика вопроса: {e}")
        return None
