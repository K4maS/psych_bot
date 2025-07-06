# Psych Bot 🤖
Telegram-бот для психологических консультаций с интеграцией Google Sheets и OpenAI API

## 📦 Установка
1. Клонируйте репозиторий:
```bash
git clone https://github.com/K4maS/psych_bot2.git && cd psych_bot2
Установите зависимости:

bash
pip install -r requirements.txt
Создайте файл конфигурации config.py:

python
TELEGRAM_BOT_TOKEN = "ваш_токен"
SHEET_ID = "id_google_таблицы"
GOOGLE_CREDS_FILE = "credentials.json" 
OPENAI_API_KEY = "ваш_api_ключ"

🚀 Запуск
bash
python bot.py

🔧 Основные команды Git
bash
# Инициализация и подключение репозитория
git init
git remote add origin https://github.com/K4maS/psych_bot2.git

# Работа с ветками
git checkout -b feature/новая_фича
git push origin feature/новая_фича
📂 Структура проекта
text
.
├── bot.py             - Основной скрипт бота
├── config.py          - Конфигурационные параметры
├── sheets.py          - Работа с Google Sheets API
├── gpt_analysis.py    - Интеграция с OpenAI
├── requirements.txt   - Список зависимостей
└── README.md          - Документация

⚠️ Важно
• Не коммитьте файлы с ключами (config.py, credentials.json)
• Лимит запросов к Google Sheets API - 60/мин
• Логи сохраняются в errors.log

📝 Лицензия
MIT License © 2023