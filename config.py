import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")

# Admin IDs for moderation (список)
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "196035876").split(",") if x.strip()]

# Domains
EXTERNAL_DOMAIN = "myslennyj-veter-letoff.amvera.io"
INTERNAL_DOMAIN = "amvera-letoff-run-myslennyj-veter"

# Database file
DATABASE_FILE = "database.json"

# Удаляю старые вопросы для карт 