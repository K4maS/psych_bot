import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from config import TELEGRAM_BOT_TOKEN
from sheets import *
from gpt_analysis_openrouter import call_gpt, call_gpt_user, call_gpt_pair, call_gpt_to_pair, call_gpt_pair_to_psyhologist, call_gpt_single, call_gpt_to_single, call_gpt_single_to_psyhologist
from util import create_answers_format, make_question_handler, global_step_changer, message_replay, navigation
from seance_data import *
logging.basicConfig(filename="errors.log", level=logging.ERROR)

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
    questions_cut = Q_3 if device == "one" else STEP_MSG1
    message_with_answers = create_answers_format(steps, users_actions, context, Q_1, questions_cut ) + message
    
    if message == reset_action or message == back_action:
        return await navigation(message, update, context)
    
    uid_1, msg_1, uid_2, msg_2 = read_messages(row)

    if msg_1 and uid_1 and device != "one":
        is_first = False
    
   
        
    write_message(row, user_id, message_with_answers, is_first)
    
 
    uid_2 = update.message.chat.id
    msg_2 = message_with_answers
    print(f'get_message1 "uid_1 {uid_1}, msg_1 {msg_1}, uid_2 {uid_2}, msg_2 {msg_2}')
    print(f"[BOT] Сообщение записано в строку {row}")
    return await do_analysis(update, context,  device, row)



async def do_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE, device, row):
    await update.message.reply_text("Делаем анализ, подождите",  reply_markup=ReplyKeyboardRemove())
     
    try:
        uid_1, msg_1, uid_2, msg_2 = read_messages(row)

        if (msg_1 and msg_2) or  msg_1 and device == "one":
           await analysis_and_send_message_to_users(uid_1, msg_1, uid_2, msg_2, row, context, update)
        else:
            await update.message.reply_text("Ожидаем сообщение второго партнёра.", reply_markup= reply_markup_end)
    except Exception as e:
        logging.error(f"[BOT] Ошибка анализа: {e}")
        await update.message.reply_text("Произошла ошибка при анализе.", reply_markup= reply_markup_end)
    return  global_step_changer(STEP_END, update, context)

# Анализ сообщения
async def analysis_and_send_message_to_users(uid_1, msg_1, uid_2, msg_2, row, context, update):
    try:
        about_user1 = call_gpt_user(msg_1)
        write_user1_analysis(row, about_user1)
        print(f"[GPT] Анализируем пользователя: {msg_2}")
        if msg_1 and not msg_2:
            print(f"[GPT] Анализируем пользователя: {uid_1}")
            summary = call_gpt_single(msg_1)
            write_summary(row, summary)
            
            to_pair_rec = call_gpt_to_single(msg_1)
            write_recommendation(row, to_pair_rec)
            
            to_psych_rec = call_gpt_single_to_psyhologist(msg_1)
            write_recommendation_to_apsychologist(row, to_psych_rec)
        else: 
            print(f"[GPT] Анализируем пару: {uid_1} и {uid_2}")
            about_user2 = call_gpt_user(msg_2)
            write_user2_analysis(row, about_user2)
            
            summary = call_gpt_pair(msg_1, msg_2)
            write_summary(row, summary)
            
            to_pair_rec = call_gpt_to_pair(msg_1, msg_2)
            write_recommendation(row, to_pair_rec)
            
            to_psych_rec = call_gpt_pair_to_psyhologist(msg_1, msg_2)
            write_recommendation_to_apsychologist(row, to_psych_rec)
        
        if uid_1:
            await context.bot.send_message(chat_id=int(uid_1), text="✅ Анализ завершён. Психолог получил резюме.", reply_markup=reply_markup_end)
        if uid_2 and uid_2 != uid_1:
            await context.bot.send_message(chat_id=int(uid_2), text="✅ Анализ завершён. Психолог получил резюме.", reply_markup=reply_markup_end)
        print(f"[GPT] Анализ завершён и записан.")
      
    except Exception as e:
        logging.error(f"[GPT] Ошибка анализа: {e}")
        await update.message.reply_text("Произошла ошибка при анализе. Пожалуйста, попробуйте позже.", reply_markup=reply_markup_end)
        return
  
    
# Компонент после всех сообщений
async def ending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        session = user_sessions[user_id]
        message = update.message.text.strip()

        if message == reset_action:
            return await reset(update, context)
        return  global_step_changer(STEP_END, update, context)
    except Exception as e:
        logging.error(f"[BOT] Ошибка в конце сессии: {e}")
        await update.message.reply_text("Произошла ошибка в конце сессии. Пожалуйста, попробуйте еще раз.", reply_markup=reply_markup_end)
        return global_step_changer(STEP_END, update, context)

# Ресет
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        user_sessions.pop(user_id, None)
        context.user_data["users_actions"] = [None] * len(steps)
        
        await update.message.reply_text("Сессия сброшена. Введите код пары:",  reply_markup=ReplyKeyboardRemove())
        return  global_step_changer(STEP_CODE, update, context)
    except Exception as e:
        logging.error(f"[BOT] Ошибка при сбросе сессии: {e}")
        await update.message.reply_text("Произошла ошибка при сбросе сессии. Пожалуйста, попробуйте еще раз.", reply_markup=ReplyKeyboardRemove())
        return global_step_changer(STEP_CODE, update, context)

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