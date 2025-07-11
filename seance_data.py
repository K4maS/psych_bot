from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove

STEP_CODE, STEP_DEVICE,  Q_1, Q_2, Q_3, Q_4, Q_5, Q_6, Q_7, Q_8,STEP_MSG1, STEP_END, STEP_PSYCHO_CODE, STEP_PSYCHO_TABLE = range(14)
first_question = Q_1
user_sessions = {}  # user_id: {code, row, device, is_first}

back_action = "Назад"
reset_action = "Сначала"

reply_markup = ReplyKeyboardMarkup([["Проблемы пары", "Свои проблемы", "Сначала"]], resize_keyboard=True)
reply_markup_back_reset = ReplyKeyboardMarkup([[back_action, reset_action]], resize_keyboard=True)
reply_markup_gender = ReplyKeyboardMarkup([['Мужской', 'Женский'],[back_action, reset_action]], resize_keyboard=True)
reply_markup_to_main = ReplyKeyboardMarkup([[reset_action]], resize_keyboard=True)
reply_markup_menu = ReplyKeyboardMarkup([['Для психолога', 'Сменить код психолога']], resize_keyboard=True)
reply_markup_end = ReplyKeyboardMarkup([[reset_action]], resize_keyboard=True)
reply_markup_yes_or_no = ReplyKeyboardMarkup([['Да', 'Нет'],[back_action, reset_action]], resize_keyboard=True)


steps = [
    {'question': 'Введите ваш код:', 'reply_markup': reply_markup_menu,  'component': STEP_CODE},
    {'question': 'Подключение успешно. Укажите, какие проблемы вы собираетесь решать:',  'reply_markup': reply_markup , 'component': STEP_DEVICE},
    {'question': 'Ваш пол', 'reply_markup': reply_markup_gender , 'component': Q_1},
    {'question': 'Сколько Вам лет?', 'component': Q_2},
    {'question': 'Сколько вы вместе?', 'component': Q_3},
    {'question': 'Как давно у вас начались конфликты', 'component': Q_4},
    {'question': 'Женаты / замужем ли вы?', 'reply_markup': reply_markup_yes_or_no , 'component': Q_5},
    {'question': 'Какими вы видите Ваши отношения в идеале?', 'component': Q_6},
    {'question': 'Что самое главное вы ожидаете от вашего партнера в отношениях с вами?', 'component': Q_7},
    {'question': 'Что не приемлемо для вас в отношениях?', 'component': Q_8},
    {'question': 'Введите ваше сообщение:', 'component': STEP_MSG1},
    {'question': 'Сессия прошла успешно', 'component': STEP_END},
    {'question': 'Введите код психолога:', 'reply_markup': ReplyKeyboardRemove(),  'component': STEP_PSYCHO_CODE},
    {'question': 'Введите код психолога:', 'reply_markup': reply_markup_to_main,  'component': STEP_PSYCHO_TABLE},
]
