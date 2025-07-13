import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
TELEGRAM_TOKEN = "7548616316:AAHppd9JUUoDHJ1bntK2OVvCno1cGq0G03U"

# OpenAI API Key
OPENAI_API_KEY = "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"

# Admin ID for moderation
ADMIN_ID = 196035876

# Domains
EXTERNAL_DOMAIN = "myslennyj-veter-letoff.amvera.io"
INTERNAL_DOMAIN = "amvera-letoff-run-myslennyj-veter"

# Database file
DATABASE_FILE = "database.json"

# Psychological map questions
BASIC_QUESTIONS = [
    "Как бы вы описали свое текущее эмоциональное состояние?",
    "Какие события в последнее время повлияли на ваше настроение?",
    "Как вы справляетесь со стрессом в повседневной жизни?",
    "Что для вас является источником радости и удовлетворения?"
]

EXTENDED_QUESTIONS = [
    "Как бы вы описали свое текущее эмоциональное состояние?",
    "Какие события в последнее время повлияли на ваше настроение?",
    "Как вы справляетесь со стрессом в повседневной жизни?",
    "Что для вас является источником радости и удовлетворения?",
    "Опишите ваши отношения с близкими людьми",
    "Какие цели вы ставите перед собой в ближайшее время?",
    "Как вы относитесь к изменениям в жизни?",
    "Что вас беспокоит больше всего в данный момент?",
    "Как вы видите свое будущее через год?",
    "Что бы вы хотели изменить в себе или своей жизни?"
] 