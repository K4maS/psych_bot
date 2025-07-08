import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from config import TELEGRAM_BOT_TOKEN
from sheets import *
from gpt_analysis_openrouter import call_gpt, call_gpt_user, call_gpt_pair, call_gpt_to_pair, call_gpt_pair_to_psyhologist, call_gpt_single, call_gpt_to_single, call_gpt_single_to_psyhologist

logging.basicConfig(filename="errors.log", level=logging.ERROR)

STEP_CODE,  STEP_DEVICE,  Q_1, Q_2, Q_3, Q_4, Q_5, Q_6, Q_7, Q_8,STEP_MSG1, STEP_MSG2, STEP_END = range(13)
first_question = Q_1
user_sessions = {}  # user_id: {code, row, device, is_first}


reply_markup = ReplyKeyboardMarkup([["Проблемы пары", "Свои проблемы", "Сначала"]], resize_keyboard=True)

back_action = "Назад"
reset_action = "Сначала"


reply_markup_back_reset = ReplyKeyboardMarkup([[back_action, reset_action]], resize_keyboard=True)
reply_markup_gender = ReplyKeyboardMarkup([['Мужской', 'Женский'],[back_action, reset_action]], resize_keyboard=True)
reply_markup_end = ReplyKeyboardMarkup([[reset_action]], resize_keyboard=True)

steps = [
    {'question': 'Введите ваш код:', 'component': STEP_CODE},
    {'question': 'Подключение успешно. Укажите, какие проблемы вы собираетесь решать:', 'component': STEP_DEVICE},
    {'question': 'Ваш пол', 'reply_markup': reply_markup_gender , 'component': Q_1},
    {'question': 'Сколько Вам лет?', 'component': Q_2},
    {'question': 'Сколько вы вместе?', 'component': Q_3},
    {'question': 'Как давно у вас начались конфликты', 'component': Q_4},
    {'question': 'Женаты / замужем ли вы?', 'component': Q_5},
    {'question': 'Какими вы видите Ваши отношения в идеале?', 'component': Q_6},
    {'question': 'Что самое главное вы ожидаете от вашего партнера в отношениях с вами?', 'component': Q_7},
    {'question': 'Что не приемлемо для вас в отношениях?', 'component': Q_8},
    {'question': 'Введите ваше сообщение:', 'component': STEP_MSG1},
    {'question': 'Теперь введите сообщение партнёра 2:', 'component': STEP_MSG2},
    {'question': 'Сессия прошла успешно', 'component': STEP_END},
]


# Функция для создания формата ответов
# Используется для форматирования вопросов и ответов пользователя
def create_answers_format (steps, users_actions, context, left_cut=Q_1, right_cut=STEP_MSG1):
    questions = steps[left_cut : right_cut]
    users_actions = context.user_data.get("users_actions", [None] * len(steps))
    users_answers = users_actions[left_cut : right_cut]
    
    text = '\n\n Вопросы заданные психологом пользователю: \n'
    for index, question in enumerate(questions):
        text += f'- {question["question"]}\n  - {users_answers[index]}\n'
    return text +'\n'

# Функция для навигации между шагами
# Используется для обработки действий пользователя, таких как переход назад или сброс сессии
async def navigation(message, update, context):
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
    
# Функция для изменения глобального шага
# Используется для записи текущего шага в глобальную переменную
# и вывода сообщения о переходе на новый шаг
def global_step_changer(step, update, context):
    context.user_data["current_step"] = step
    print(f'Вы перешли на шаг {step}')
    return step 

# Функция для обработки вопросов и ответов
# Используется для обработки ответов на вопросы и перехода к следующему вопросу
async def question_answer_base(update: Update, context: ContextTypes.DEFAULT_TYPE, question_index):
    user_id = update.message.from_user.id
    session = user_sessions[user_id]
    row = session["row"]
    device = session["device"]
    message = update.message.text.strip()
    users_actions = context.user_data.get("users_actions", [None] * len(steps))
    users_actions[question_index] = message
    context.user_data["users_actions"] = users_actions  # сохраняем
    
    if device == "one" and question_index == Q_2: 
        await update.message.reply_text("Опишите ваши проблемы:")
        return  global_step_changer(STEP_MSG1, update, context)
    
    if message == reset_action or message == back_action:
       
        return await navigation(message, update, context)    

    try:
        next_question = steps[question_index + 1]
        
        await message_replay(next_question, update, context)
        
        if 'component' in next_question or len(steps) <= question_index:
            return global_step_changer(next_question['component'], update, context)
        
    except IndexError:
        await update.message.reply_text("Опишите ваши проблемы:")
    
    uid_1, msg_1, uid_2, msg_2 = read_messages(row)
    if msg_1 and uid_1 and device == "one":
        return  global_step_changer(STEP_MSG2, update, context)
    return  global_step_changer(STEP_MSG1, update, context)

# Вывод сообщения с вопросом и кнопками
async def message_replay(step, update, context):
    question_text = step['question']
    reply_markup = step['reply_markup'] if 'reply_markup' in step else None

    return await update.message.reply_text(question_text,  reply_markup=reply_markup if reply_markup else reply_markup_back_reset)

# Функция для создания обработчика вопросов
# Используется для создания обработчиков для каждого вопроса
def make_question_handler(question_index):
    async def question_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await question_answer_base(update, context, question_index)
    return question_handler



# Начало сессии
# Вызывается при команде /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(steps[STEP_CODE]['question'],  reply_markup=ReplyKeyboardRemove())
    print("[BOT] Пользователь начал ввод кода.")
    return  global_step_changer(STEP_CODE, update, context)

# Получение кода
# Вызывается при вводе кода пользователем
async def get_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip()
    user_id = update.message.from_user.id
    row = find_row_by_code(code)

    if row is None:
        await update.message.reply_text("Код не найден. Повторите ввод.")
        return  global_step_changer(STEP_CODE, update, context)
 
    summary = read_column(row, SUMMARY)
    if summary:
        await update.message.reply_text("Этот код уже использован. Введите другой код.")
        return  global_step_changer(STEP_CODE, update, context)

    user_sessions[user_id] = {"code": code, "row": row}
    await update.message.reply_text(steps[STEP_DEVICE]['question'], reply_markup=reply_markup)
    print(f"[BOT] Код {code} принят, строка {row}")
    return  global_step_changer(STEP_DEVICE, update, context)

# Выбро режима сеанса  
# Вызывается при выборе устройства пользователем
async def choose_device(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    user_id = update.message.from_user.id
    session = user_sessions[user_id]
    row = session["row"]
    choice_lower = choice.lower()
    if "свои" in choice_lower:
        session["device"] = "one"
    elif "пары" in choice_lower:
        session["device"] = "two"
    elif reset_action.lower() in choice_lower:
        return await reset(update, context)
    else:
        return  global_step_changer(STEP_DEVICE, update, context)
    uid_1, msg_1, uid_2, msg_2 = read_messages(row)

    if session["device"] == "two" and msg_1 and uid_1:
        await update.message.reply_text("Ваш партнер ввел сообщение, ваша очередь:", reply_markup=reply_markup_back_reset)
        session["is_first"] = False

    else:
        session["is_first"] = True
        await update.message.reply_text("Введите ваше сообщение:", reply_markup=reply_markup_back_reset)
    await message_replay(steps[first_question], update, context)
    return  global_step_changer(first_question, update, context)    
 
# Первое сообщение
async def get_message1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    session = user_sessions[user_id]
    row = session["row"]
    device = session["device"]
    message = update.message.text.strip()
    is_first = True
    users_actions = context.user_data.get("users_actions", [None] * len(steps))
    questions_cut = STEP_MSG1
    
    if message == reset_action:
        return await reset(update, context)
    uid_1, msg_1, uid_2, msg_2 = read_messages(row)

    if msg_1 and uid_1 and device != "one":
        is_first = False
    
    if device == "one":
        questions_cut = Q_3

    write_message(row, user_id, create_answers_format(steps, users_actions, context, Q_1, questions_cut ) + message, is_first)
    print(f"[BOT] Сообщение записано в строку {row}")

    if device == "one":
        return await do_analysis(update, context, device, row)
    else:
        if not is_first:
            await analysis_and_send_message_to_users(uid_1, msg_1, uid_2, msg_2, row, context, update)
        await update.message.reply_text("Сообщение принято. Ждём второго участника.")
        return  global_step_changer(STEP_END, update, context)

# Второе сообщение
async def get_message2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    session = user_sessions[user_id]
    row = session["row"]
    message = update.message.text.strip()
    users_actions = context.user_data.get("users_actions", [None] * len(steps))
    
    if message == reset_action:
        return await reset(update, context)

    write_message(row, user_id,  create_answers_format (steps, users_actions, context) + message, is_first=False)
    print(f"[BOT] Сообщение партнёра 2 записано в строку {row}")

# Анализ сообщений
# Вызывается после получения обоих сообщений
async def do_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE, device, row):
   
    await update.message.reply_text("Делаем анализ, подождите")
    try:
        uid_1, msg_1, uid_2, msg_2 = read_messages(row)
        if (msg_1 and msg_2) or  msg_1 and device == "one":
           await analysis_and_send_message_to_users(uid_1, msg_1, uid_2, msg_2, row, context, update)
        else:
            await update.message.reply_text("Ожидаем сообщение второго партнёра.")
    except Exception as e:
        logging.error(f"[BOT] Ошибка анализа: {e}")
        await update.message.reply_text("Произошла ошибка при анализе.")
    return  global_step_changer(STEP_END, update, context)

# Анализ сообщения
async def analysis_and_send_message_to_users(uid_1, msg_1, uid_2, msg_2, row, context, update):
    await update.message.reply_text("Делаем анализ, подождите")
  
    about_user1 = call_gpt_user(msg_1)
    write_user1_analysis(row, about_user1)
    print(f"[GPT] Анализируем пользователя: {msg_2}")
    if msg_1 and msg_2: 
        print(f"[GPT] Анализируем пару: {uid_1} и {uid_2}")
        about_user2 = call_gpt_user(msg_2)
        write_user2_analysis(row, about_user2)
        
        summary = call_gpt_pair(msg_1, msg_2)
        write_summary(row, summary)
        
        to_pair_rec = call_gpt_to_pair(msg_1, msg_2)
        write_recommendation(row, to_pair_rec)
        
        to_psych_rec = call_gpt_pair_to_psyhologist(msg_1, msg_2)
        write_recommendation_to_apsychologist(row, to_psych_rec)
    else:
        print(f"[GPT] Анализируем пользователя: {uid_1}")
        summary = call_gpt_single(msg_1)
        write_summary(row, summary)
        
        to_pair_rec = call_gpt_to_single(msg_1)
        write_recommendation(row, to_pair_rec)
        
        to_psych_rec = call_gpt_single_to_psyhologist(msg_1)
        write_recommendation_to_apsychologist(row, to_psych_rec)
  
    
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

    await update.message.reply_text(steps[STEP_END]['question'],  reply_markup=reply_markup_end)

    if message == reset_action:
        return await reset(update, context)
    return  global_step_changer(STEP_END, update, context)

# Ресет
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_sessions.pop(user_id, None)
    context.user_data["users_actions"] = [None] * len(steps)
    
    await update.message.reply_text("Сессия сброшена. Введите код пары:",  reply_markup=ReplyKeyboardRemove())
    return  global_step_changer(STEP_CODE, update, context)

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
            Q_1: [MessageHandler(filters.TEXT & ~filters.COMMAND, make_question_handler(Q_1))],
            Q_2: [MessageHandler(filters.TEXT & ~filters.COMMAND, make_question_handler(Q_2))],
            Q_3: [MessageHandler(filters.TEXT & ~filters.COMMAND, make_question_handler(Q_3))],
            Q_4: [MessageHandler(filters.TEXT & ~filters.COMMAND, make_question_handler(Q_4))],
            Q_5: [MessageHandler(filters.TEXT & ~filters.COMMAND, make_question_handler(Q_5))],
            Q_6: [MessageHandler(filters.TEXT & ~filters.COMMAND, make_question_handler(Q_6))],
            Q_7: [MessageHandler(filters.TEXT & ~filters.COMMAND, make_question_handler(Q_7))],
            Q_8: [MessageHandler(filters.TEXT & ~filters.COMMAND, make_question_handler(Q_8))],
        },
        fallbacks=[CommandHandler("reset", reset)]
    )

    app.add_handler(conv) 
    print("[СТАТУС] Бот успешно запущен.")
    app.run_polling()
   



if __name__ == "__main__":
    main()