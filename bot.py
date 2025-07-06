import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from config import TELEGRAM_BOT_TOKEN
from sheets import *
from gpt_analysis_openrouter import call_gpt

logging.basicConfig(filename="errors.log", level=logging.ERROR)

STEP_CODE, Q_1, Q_2, Q_3, Q_4, Q_5, Q_6, Q_7, STEP_DEVICE, STEP_MSG1, STEP_MSG2, STEP_END = range(12)

user_sessions = {}  # user_id: {code, row, device, is_first}

reply_markup = ReplyKeyboardMarkup([["С одного устройства", "С двух устройств", "Сначала"]], resize_keyboard=True)

back_action = "Назад"
reset_action = "Сначала"


reply_markup2 = ReplyKeyboardMarkup([[back_action, reset_action]], resize_keyboard=True)
reply_markup_end = ReplyKeyboardMarkup([[reset_action]], resize_keyboard=True)



questions = [
    {'question': 'Сколько вы вместе?', 'component': Q_1},
    {'question': 'Как давно у вас начались конфликты', 'component': Q_2},
    {'question': 'Сколько Вам лет?', 'component': Q_3},
    {'question': 'Женаты / замужем ли вы?', 'component': Q_4},
    {'question': 'Какими вы видите Ваши отношения в идеале?', 'component': Q_5},
    {'question': 'Что самое главное вы ожидаете от вашего партнера в отношениях с вами?', 'component': Q_6},
    {'question': 'Что не приемлемо для вас в отношениях?', 'component': Q_7},
    ]

users_answers = [None] *  len(questions)

def create_answers_format (questions, users_answers):
    text = '\n\n Заданные вопросы пользователю: \n'
    for index, question in enumerate(questions):
        text += f'- {question['question']}\n  - {users_answers[index]}\n'
    return text +'\n'

async def question_answer_base(update: Update, contex: ContextTypes.DEFAULT_TYPE, question_index):
    user_id = update.message.from_user.id
    session = user_sessions[user_id]
    row = session["row"]
    message = update.message.text.strip()
    users_answers[question_index] = message
    print(users_answers, question_index)
    
    

    try:
        next_question = questions[question_index + 1]['question']
        await update.message.reply_text(next_question,  reply_markup=reply_markup2)
        print(f"Задан вопрос {next_question}" )

        if 'component' in questions[question_index + 1] or len(questions) <= question_index:
            return questions[question_index + 1]['component']
        uid_1, msg_1, uid_2, msg_2 = read_messages(row)
            if msg_1 and uid_1 and session["device"] == "one":
                return  STEP_MSG2
            return  STEP_MSG1
    except IndexError:
        await update.message.reply_text("Опишите ваши проблемы:")
        
    

async def question_answer1(update: Update, contex: ContextTypes.DEFAULT_TYPE):
    users_answers = [None] *  len(questions)
    return await question_answer_base(update, contex, 0)

async def question_answer2(update: Update, contex: ContextTypes.DEFAULT_TYPE):
    return await question_answer_base(update, contex, 1)

async def question_answer3(update: Update, contex: ContextTypes.DEFAULT_TYPE):
    return await question_answer_base(update, contex, 2)

async def question_answer4(update: Update, contex: ContextTypes.DEFAULT_TYPE):
    return await question_answer_base(update, contex, 3)

async def question_answer5(update: Update, contex: ContextTypes.DEFAULT_TYPE):
    return await question_answer_base(update, contex, 4)

async def question_answer6(update: Update, contex: ContextTypes.DEFAULT_TYPE):
    return await question_answer_base(update, contex, 5)

async def question_answer7(update: Update, contex: ContextTypes.DEFAULT_TYPE):
    return await question_answer_base(update, contex, 6)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите код вашей пары:",  reply_markup=ReplyKeyboardRemove())
    print("[BOT] Пользователь начал ввод кода.")
    return STEP_CODE

async def get_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip()
    user_id = update.message.from_user.id
    row = find_row_by_code(code)

    if row is None:
        await update.message.reply_text("Код не найден. Повторите ввод.")
        return STEP_CODE

    uid_1, msg_1, uid_2, msg_2 = read_messages(row)
    if uid_1 and msg_1 and uid_2 and msg_2:
        await update.message.reply_text("Этот код уже использован. Введите другой код.")
        return STEP_CODE

    user_sessions[user_id] = {"code": code, "row": row}
    await update.message.reply_text("Подключение успешно. Укажите, с одного или с двух устройств вы пишете:", reply_markup=reply_markup)
    print(f"[BOT] Код {code} принят, строка {row}")
    return STEP_DEVICE

#Выбро девайса
async def choose_device(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    user_id = update.message.from_user.id
    session = user_sessions[user_id]
    row = session["row"]

    if "одного" in choice:
        session["device"] = "one"
    elif "двух" in choice:
        session["device"] = "two"
    elif reset_action in choice:
        return await reset(update, context)
    else:
        return STEP_DEVICE
    uid_1, msg_1, uid_2, msg_2 = read_messages(row)

    if session["device"] == "two" and msg_1 and uid_1:
        await update.message.reply_text("Ваш партнер ввел сообщение, ваша очередь:", reply_markup=reply_markup2)
        session["is_first"] = False

    else:
        session["is_first"] = True
        # await update.message.reply_text("Введите сообщение партнёра 1:", reply_markup=ReplyKeyboardRemove())
        await update.message.reply_text("Введите сообщение партнёра 1:", reply_markup=reply_markup2)
    
    # return STEP_MSG1
    await update.message.reply_text(questions[0]['question'], reply_markup=reply_markup2)
    return Q_1

# Первое сообщение
async def get_message1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    session = user_sessions[user_id]
    row = session["row"]
    message = update.message.text.strip()
    is_first = True

    if message == reset_action:
        return await reset(update, context)
    uid_1, msg_1, uid_2, msg_2 = read_messages(row)

    if msg_1 and uid_1 and session["device"] != "one":
        is_first = False

    write_message(row, user_id, create_answers_format (questions, users_answers) + message, is_first)
    print(f"[BOT] Сообщение партнёра 1 записано в строку {row}")

    if session["device"] == "one":
        await update.message.reply_text("Теперь введите сообщение партнёра 2:")
        await update.message.reply_text(questions[0]['question'], reply_markup=reply_markup2)
        return Q_1
    else:
        if not is_first:
            await send_message_to_users(uid_1, msg_1, uid_2, msg_2, row, context, update)
        await update.message.reply_text("Сообщение принято. Ждём второго участника.")
        return STEP_END

# Второе сообщение
async def get_message2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    session = user_sessions[user_id]
    row = session["row"]
    message = update.message.text.strip()

    if message == reset_action:
        return await reset(update, context)

    write_message(row, user_id,  create_answers_format (questions, users_answers) + message, is_first=False)
    print(f"[BOT] Сообщение партнёра 2 записано в строку {row}")
    await update.message.reply_text("Делаем анализ, подождите")
    try:
        uid_1, msg_1, uid_2, msg_2 = read_messages(row)
        if msg_1 and msg_2:
           await send_message_to_users(uid_1, msg_1, uid_2, msg_2, row, context, update)
        else:
            await update.message.reply_text("Ожидаем сообщение второго партнёра.")
    except Exception as e:
        logging.error(f"[BOT] Ошибка анализа: {e}")
        await update.message.reply_text("Произошла ошибка при анализе.")
    return STEP_END

# Анализ сообщения
async def send_message_to_users(uid_1, msg_1, uid_2, msg_2, row, context, update):
    await update.message.reply_text("Делаем анализ, подождите")
    summary = call_gpt(msg_1, msg_2)
    write_summary(row, summary)
    if uid_1:
        await context.bot.send_message(chat_id=int(uid_1), text="✅ Анализ завершён. Психолог получил резюме.")
    if uid_2 and uid_2 != uid_1:
        await context.bot.send_message(chat_id=int(uid_2), text="✅ Анализ завершён. Психолог получил резюме.")
    print(f"[GPT] Анализ завершён и записан.")

# Компонент после всех сообщений
async def ending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    session = user_sessions[user_id]
    message = update.message.text.strip()

    await update.message.reply_text("Сессия прошла успешно",  reply_markup=reply_markup_end)

    if message == reset_action:
        return await reset(update, context)

    return STEP_END

# Ресет
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_sessions.pop(user_id, None)
    await update.message.reply_text("Сессия сброшена. Введите код пары:",  reply_markup=ReplyKeyboardRemove())
    return STEP_CODE

# Основная функция
def main():
    print("[СТАТУС] Бот запускается...")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            STEP_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_code)],
            STEP_DEVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_device)],
            STEP_MSG1: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_message1)],
            STEP_MSG2: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_message2)],
            STEP_END: [MessageHandler(filters.TEXT & ~filters.COMMAND, ending)],
            STEP_END: [MessageHandler(filters.TEXT & ~filters.COMMAND, ending)],
            Q_1: [MessageHandler(filters.TEXT & ~filters.COMMAND, question_answer1)],
            Q_2: [MessageHandler(filters.TEXT & ~filters.COMMAND, question_answer2)],
            Q_3: [MessageHandler(filters.TEXT & ~filters.COMMAND, question_answer3)],
            Q_4: [MessageHandler(filters.TEXT & ~filters.COMMAND, question_answer4)],
            Q_5: [MessageHandler(filters.TEXT & ~filters.COMMAND, question_answer5)],
            Q_6: [MessageHandler(filters.TEXT & ~filters.COMMAND, question_answer6)],
            Q_7: [MessageHandler(filters.TEXT & ~filters.COMMAND, question_answer7)],

        },
        fallbacks=[CommandHandler("reset", reset)]
    )

    app.add_handler(conv) 
    print("[СТАТУС] Бот успешно запущен.")
    app.run_polling()
   



if __name__ == "__main__":
    main()