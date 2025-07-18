import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")

# Admin ID for moderation
ADMIN_ID = 196035876

# Domains
EXTERNAL_DOMAIN = "myslennyj-veter-letoff.amvera.io"
INTERNAL_DOMAIN = "amvera-letoff-run-myslennyj-veter"

# Database file
DATABASE_FILE = "database.json"

# Удаляю старые вопросы для карт 