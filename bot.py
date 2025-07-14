import logging
from typing import Optional, Union
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from config import TELEGRAM_BOT_TOKEN, PROVIDER_TOKEN
from sheets import *
from util import (
    create_answers_format,
    make_question_handler,
    global_step_changer,
    message_replay,
    navigation,
    reset,
    first_step_handler,
    is_valid_sheet_url
)
from seance_data import *
from gpt_analysis_openrouter import *
from supabase_client import (
    supabase,
    get_row_from_psycho_by_psychoid_db,
    get_row_from_psycho_by_uid_db,
    get_row_from_patients_db,
    insert_row_to_patients_db,
    insert_row_to_psycho_db,
    get_table_linked_to_psycho,
    get_credits_of_psycho,
    decrement_credits,
)
from telegram.error import TelegramError

logging.basicConfig(filename="errors.log", level=logging.ERROR)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error("Произошла ошибка:", exc_info=context.error)

    if update and isinstance(update, Update) and update.message:
        try:
            await update.message.reply_text("🚫 Ошибка связи с сервером.")
        except TelegramError:
            pass  # если и это не сработает — не страшно


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    code: str = update.message.text.strip()
    user_id: int = update.message.from_user.id
    print("[BOT] Пользователь начал ввод кода.")

    return await first_step_handler(update, context, user_id)





async def psych_set_table_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    link: str = update.message.text.strip()
    username: Optional[str] = update.message.from_user.username
    user_id: int = update.message.from_user.id

    if not is_valid_sheet_url(link):
        await update.message.reply_text("⚠️ Это не похоже на ссылку на Google Таблицу. Вставьте корректную ссылку.")
        return global_step_changer(steps[STEP_PSYCHO_TABLE]['component'], update, context)

    try:
        row = await insert_row_to_psycho_db(user_id, {'name': username, 'table': link, 'credits': 1})
        psycho_row = await get_row_from_psycho_by_uid_db(user_id)

        if row is None:
            await update.message.reply_text('Не добавить/поменять ссылку на таблицу')
            return global_step_changer(steps[STEP_PSYCHO_TABLE]['component'], update, context)

        if psycho_row is None or 'psychologist_id' not in psycho_row:
            await update.message.reply_text('Ошибка при получении ID психолога')
            return global_step_changer(steps[STEP_PSYCHO_TABLE]['component'], update, context)

        psychologist_id: str = psycho_row['psychologist_id']
        credits: str = psycho_row['credits']
        await update.message.reply_text(f'Ваш код психолога: {psychologist_id} \n У вас {credits} кредитов')
    except Exception as e:
        logging.error(e)
        await update.message.reply_text('Ошибка базы данных')
    # Если нужен возврат шага, раскомментировать
    # return global_step_changer(steps[STEP_START]['component'], update, context)


async def get_psycho_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    code: str = update.message.text.strip()
    username: Optional[str] = update.message.from_user.username
    user_id: int = update.message.from_user.id

    row = await get_row_from_psycho_by_psychoid_db(code)

    if row is None:
        await update.message.reply_text("Код психолога не найден. Пожалуйста, введите правильный код.")
    else:
        await insert_row_to_patients_db(user_id, {"psychologist_id": code, "name": username})
        await update.message.reply_text("Код психолога принят. Теперь введите код вашей пары:",
                                        reply_markup=ReplyKeyboardRemove())
        print(f"[BOT] Код {code} принят, строка {row}")

    return global_step_changer(STEP_CODE, update, context)


async def write_spreadsheet_id_in_context(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> Optional[str]:
    try:
        sheet_link: Optional[str] = await get_table_linked_to_psycho(user_id)
        credits: Optional[str] = await get_credits_of_psycho(user_id)
        if sheet_link is None:
            return None
        sheet_id: Optional[str] = extract_spreadsheet_id(sheet_link)
        if sheet_id:
            context.user_data["sheet_id"] = sheet_id
        return sheet_id, credits
    except Exception as e:
        logging.error(e)
        await update.message.reply_text('Ошибка базы данных')


async def get_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    code: str = update.message.text.strip()
    user_id: int = update.message.from_user.id

    await write_spreadsheet_id_in_context(user_id, context)
    sheet_id: Optional[str] = context.user_data.get("sheet_id")

    try:
        row = find_row_by_code(code, sheet_id)
    except Exception as e:
        error_text = f"⚠️ Произошла ошибка при работе с таблицей:\n{str(e)}"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=error_text)

    if row is None:
        await update.message.reply_text("Код не найден. Повторите ввод.")
        return global_step_changer(STEP_CODE, update, context)

    try:
        summary = read_column(row, SUMMARY, sheet_id)
    except Exception as e:
        error_text = f"⚠️ Произошла ошибка при работе с таблицей:\n{str(e)}"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=error_text)

    if summary:
        await update.message.reply_text("Этот код уже использован. Введите другой код.")
        return global_step_changer(STEP_CODE, update, context)

    user_sessions[user_id] = {"code": code, "row": row}
    await update.message.reply_text(steps[STEP_DEVICE]['question'], reply_markup=reply_markup)
    print(f"[BOT] Код {code} принят, строка {row}")
    return global_step_changer(STEP_DEVICE, update, context)


async def choose_device(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    choice: str = update.message.text
    user_id: int = update.message.from_user.id
    session = user_sessions[user_id]

    sheet_id: Optional[str] = context.user_data.get("sheet_id")
    row = session["row"]
    choice_lower: str = choice.lower()

    if "свои" in choice_lower:
        session["device"] = "one"
    elif "пары" in choice_lower:
        session["device"] = "two"
    elif reset_action.lower() in choice_lower:
        return await reset(update, context)
    else:
        return global_step_changer(STEP_DEVICE, update, context)

    uid_1, msg_1, uid_2, msg_2 = await read_messages_except(row, sheet_id)

    if session["device"] == "two" and msg_1 and uid_1:
        await update.message.reply_text("Ваш партнер ввел сообщение, ваша очередь:",
                                        reply_markup=reply_markup_back_reset)
        session["is_first"] = False
    else:
        session["is_first"] = True
        await update.message.reply_text("Введите ваше сообщение:", reply_markup=reply_markup_back_reset)

    await message_replay(steps[first_question], update, context)
    return global_step_changer(first_question, update, context)


async def get_message1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    user_id: int = update.message.from_user.id
    session = user_sessions[user_id]
    sheet_id: Optional[str] = context.user_data.get("sheet_id")
    row = session["row"]
    device = session["device"]

    message: str = update.message.text.strip()
    is_first: bool = True
    users_actions = context.user_data.get("users_actions", [None] * len(steps))

    questions_cut = Q_3 if device == "one" else STEP_MSG1
    message_with_answers = create_answers_format(steps, users_actions, context, Q_1, questions_cut) + message
    print(f"[BOT] Message1: {update.message.text}")

    if message == reset_action or message == back_action:
        return await navigation(message, update, context)

    uid_1, msg_1, uid_2, msg_2 = await read_messages_except(row, sheet_id)

    if msg_1 and uid_1 and device != "one":
        is_first = False
    print(f'get_message sheet id {sheet_id}')
    try:
        write_message(row, user_id, message_with_answers, sheet_id, is_first)
    except Exception as e:
        error_text = f"⚠️ Произошла ошибка при работе с таблицей:\n{str(e)}"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=error_text)

    uid_2 = update.message.chat.id
    msg_2 = message_with_answers

    print(f'get_message1 "uid_1 {uid_1}, msg_1 {msg_1}, uid_2 {uid_2}, msg_2 {msg_2}')
    print(f"[BOT] Сообщение записано в строку {row}")
    return await do_analysis(update, context, device, row)


async def do_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE, device: str, row: int) -> Optional[int]:
    await update.message.reply_text("Делаем анализ, подождите", reply_markup=ReplyKeyboardRemove())
    sheet_id: Optional[str] = context.user_data.get("sheet_id")

    uid_1, msg_1, uid_2, msg_2 = await read_messages_except(row, sheet_id)
    try:


        if (msg_1 and msg_2) or (msg_1 and device == "one"):
            await analysis_and_send_message_to_users(uid_1, msg_1, uid_2, msg_2, row, context, update)
        else:
            await update.message.reply_text("Ожидаем сообщение второго партнёра.", reply_markup=reply_markup_end)
    except Exception as e:
        logging.error(f"[BOT] Ошибка анализа: {e}")
        await update.message.reply_text("Произошла ошибка при анализе.", reply_markup=reply_markup_end)
    return global_step_changer(STEP_END, update, context)


async def  read_messages_except(row, sheet_id):
    try:
        uid_1, msg_1, uid_2, msg_2 = read_messages(row, sheet_id)
        return uid_1, msg_1, uid_2, msg_2
    except Exception as e:
        error_text = f"⚠️ Произошла ошибка при работе с таблицей:\n{str(e)}"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=error_text)

async def analysis_and_send_message_to_users(
        uid_1: Optional[int],
        msg_1: Optional[str],
        uid_2: Optional[int],
        msg_2: Optional[str],
        row: int,
        context: ContextTypes.DEFAULT_TYPE,
        update: Update,
) -> None:
    credits = await get_credits_of_psycho(uid_1)
    if credits <= 0:
        if uid_1:
            await context.bot.send_message(
                chat_id=int(uid_1),
                text="Недостаточно кредитов.",
                reply_markup=reply_markup_end,
            )
        if uid_2 and uid_2 != uid_1:
            await context.bot.send_message(
                chat_id=int(uid_2),
                text="Недостаточно кредитов.",
                reply_markup=reply_markup_end,
            )

    sheet_id: Optional[str] = context.user_data.get("sheet_id")
    try:


        about_user1 = call_gpt_user(sheet_id, msg_1)
        write_user1_analysis(row, about_user1, sheet_id)

        print(sheet_id)
        print(f"[GPT] Анализируем пользователя: {msg_2}")
        if msg_1 and not msg_2:
            print(f"[GPT] Анализируем пользователя: {uid_1}")
            summary = call_gpt_single(sheet_id, msg_1)
            write_summary(row, summary, sheet_id)

            to_pair_rec = call_gpt_to_single(sheet_id, msg_1)
            write_recommendation(row, to_pair_rec, sheet_id)

            to_psych_rec = call_gpt_single_to_psychologist(sheet_id, msg_1)
            write_recommendation_to_psychologist(row, to_psych_rec, sheet_id)
        else:
            print(f"[GPT] Анализируем пару: {uid_1} и {uid_2}")
            about_user2 = call_gpt_user(sheet_id, msg_2)
            write_user2_analysis(row, about_user2, sheet_id)

            summary = call_gpt_pair(sheet_id, msg_1, msg_2)
            write_summary(row, summary, sheet_id)

            to_pair_rec = call_gpt_to_pair(sheet_id, msg_1, msg_2)
            write_recommendation(row, to_pair_rec, sheet_id)

            to_psych_rec = call_gpt_pair_to_psyhologist(sheet_id, msg_1, msg_2)
            write_recommendation_to_psychologist(row, to_psych_rec, sheet_id)

        credits_now = await decrement_credits(uid_1)
        print(f'credits_now: {credits_now}')

        if uid_1:
            await context.bot.send_message(
                chat_id=int(uid_1),
                text="✅ Анализ завершён. Психолог получил резюме.",
                reply_markup=reply_markup_end,
            )
        if uid_2 and uid_2 != uid_1:
            await context.bot.send_message(
                chat_id=int(uid_2),
                text="✅ Анализ завершён. Психолог получил резюме.",
                reply_markup=reply_markup_end,
            )
        print(f"[GPT] Анализ завершён и записан.")

    except Exception as e:
        logging.error(f"[GPT] Ошибка анализа: {e}")
        await update.message.reply_text("Произошла ошибка при анализе.",
                                        reply_markup=reply_markup_end)
        return


async def ending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    try:
        user_id: int = update.message.from_user.id
        session = user_sessions[user_id]
        message: str = update.message.text.strip()

        if message == reset_action:
            return await reset(update, context)
        return global_step_changer(STEP_END, update, context)
    except Exception as e:
        logging.error(f"[BOT] Ошибка в конце сессии: {e}")
        await update.message.reply_text(
            "Произошла ошибка в конце сессии. Пожалуйста, попробуйте еще раз.",
            reply_markup=reply_markup_end,
        )
        return global_step_changer(STEP_END, update, context)


async def set_menu_commands(app: ApplicationBuilder) -> None:
    commands = [
        BotCommand("start", "Запустить бота"),
        BotCommand("main", "Главная"),
        BotCommand("psy", "Для психолога"),
        BotCommand("link", "Записать/перезаписать код психолога"),
        # BotCommand("pay", "Покупка кредитов"),
        BotCommand("reset", "Сбросить данные"),
        BotCommand("help", "Помощь"),
    ]
    await app.bot.set_my_commands(commands)


async def set_table_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    await update.message.reply_text(steps[STEP_PSYCHO_TABLE]['question'], reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")
    context.user_data.clear()
    return global_step_changer(STEP_PSYCHO_TABLE, update, context)

async def help (update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    text = (
        "🧠 *Психологический бот*\n\n"
        "Бот поможет вам и вашему партнёру пройти анализ и получить рекомендации от GPT на основе ваших сообщений.\n\n"
        "📌 *Доступные команды:*\n"
        "/start – начать работу с ботом\n"
        "/link – указать или изменить ссылку на таблицу психолога\n"
        "/reset – сбросить текущую сессию и начать заново\n"
        "/main – вернуться на главный шаг\n"
        "/help – показать эту справку\n"
        "/psy – показать данные психолога\n\n"
        "ℹ️ Просто следуйте инструкциям на экране. Если что-то пошло не так — используйте /reset.\n\n"
        "Если вы – психолог, сначала используйте команду /link, чтобы указать таблицу Google Sheets.\n"
        "Если вы – клиент, сначала введите код психолога, затем код вашей пары.\n\n"
        "⚠️ Все данные сохраняются в защищённой таблице Google.\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())

async def for_psychologist (update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    user_id: int = update.message.from_user.id
    psycho_row = await get_row_from_psycho_by_uid_db(user_id)
    if psycho_row is None:
        await update.message.reply_text('Это данные для аккаунтов психолога  \n\n вы можете так же создать свой аккаунт психолога: /link')
    else:
        psychologist_id: str = psycho_row['psychologist_id']
        credits: str = psycho_row['credits']
        table: str = psycho_row['table']

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(text=psychologist_id, callback_data="code_copy")]
        ])

        text = (
            "*Данные для психолога*\n\n"
            f"`{psychologist_id}` — ваш код психолога (нажмите, чтобы скопировать)\n\n"
            f"[Ссылка на таблицу]({table})\n\n"
            f"Ваши кредиты: *{credits}*\n\n"
        )

        await update.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )



async def start_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Оплатить 100₽", url=YOOMONEY_LINK)]
    ])
    await update.message.reply_text(
        "Для покупки кредитов нажмите кнопку ниже:",
        reply_markup=keyboard
    )


def main() -> None:
    print("[СТАТУС] Бот запускается...")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.post_init = set_menu_commands
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
        ],
        states={
            STEP_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, start)],
            STEP_PSYCHO_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_psycho_code)],
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
            STEP_PSYCHO_TABLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, psych_set_table_link)],
        },
        fallbacks=[CommandHandler("start", start),
                   CommandHandler("reset", reset),
                   CommandHandler("link", set_table_link),
                   CommandHandler("help", help),
                   CommandHandler("main", start),
                   CommandHandler("psy", for_psychologist),
                   # CommandHandler("pay", start_payment),
                   ],  # ←],
    )

    app.add_handler(conv)

    app.add_error_handler(error_handler)

    print("[СТАТУС] Бот успешно запущен.")
    app.run_polling()




if __name__ == "__main__":
    main()
