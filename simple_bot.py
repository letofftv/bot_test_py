import logging
import os
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from config import TELEGRAM_TOKEN, EXTERNAL_DOMAIN

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Flask приложение
app = Flask(__name__)

# Telegram приложение
if not TELEGRAM_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")

telegram_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Привет! Я простой тестовый бот.")

# Настройка обработчиков
telegram_app.add_handler(CommandHandler("start", start))

# Webhook endpoint
@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(), telegram_app.bot)
    telegram_app.process_update(update)
    return 'OK'

# Health check endpoint
@app.route('/health', methods=['GET'])
def health():
    return 'OK'

if __name__ == '__main__':
    # Получаем порт из переменной окружения или используем 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Настраиваем webhook
    webhook_url = f"https://{EXTERNAL_DOMAIN}/webhook"
    
    logging.info(f"Bot token: {TELEGRAM_TOKEN[:10]}...")
    logging.info(f"Webhook URL: {webhook_url}")
    logging.info(f"Port: {port}")
    
    try:
        telegram_app.bot.set_webhook(url=webhook_url)
        logging.info(f"Setting webhook to: {webhook_url}")
    except Exception as e:
        logging.error(f"Error setting webhook on startup: {e}")
    
    # Запускаем Flask приложение
    logging.info(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port) 