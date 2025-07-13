import logging
import os
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from config import TELEGRAM_TOKEN, ADMIN_ID, BASIC_QUESTIONS, EXTENDED_QUESTIONS, INTERNAL_DOMAIN
from database import Database
from openai_client import OpenAIClient

# Состояния для ConversationHandler
MENU, CONSULT, MAP_TYPE, MAP_QUESTIONS, WAITING_MODERATION = range(5)

# Клавиатуры
main_keyboard = ReplyKeyboardMarkup([
    ["1️⃣ Получить консультацию"],
    ["2️⃣ Создать психологическую карту"]
], resize_keyboard=True)

map_type_keyboard = ReplyKeyboardMarkup([
    ["Базовая (4 вопроса)"],
    ["Расширенная (10 вопросов)"]
], resize_keyboard=True)

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Инициализация
db = Database()
ai = OpenAIClient()

# Flask приложение
app = Flask(__name__)

# Telegram приложение
if not TELEGRAM_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")

telegram_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Добро пожаловать в психологический бот!\n\nВыберите действие:",
        reply_markup=main_keyboard
    )
    db.set_user_state(update.effective_user.id, "MENU")
    return MENU

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if text.startswith("1"):
        await update.message.reply_text(
            "Пожалуйста, опишите ваш вопрос или ситуацию, с которой вы хотите обратиться к психологу.",
            reply_markup=ReplyKeyboardRemove()
        )
        db.set_user_state(user_id, "CONSULT")
        return CONSULT
    elif text.startswith("2"):
        await update.message.reply_text(
            "Выберите тип психологической карты:",
            reply_markup=map_type_keyboard
        )
        db.set_user_state(user_id, "MAP_TYPE")
        return MAP_TYPE
    else:
        await update.message.reply_text("Пожалуйста, выберите действие из меню.")
        return MENU

async def consult_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    question = update.message.text
    await update.message.reply_text("Ваш вопрос принят. Пожалуйста, подождите, идет обработка...")
    # Получаем ответ от OpenAI
    answer = await ai.get_psychological_consultation(question)
    await update.message.reply_text(answer, reply_markup=main_keyboard)
    db.set_user_state(user_id, "MENU")
    return MENU

async def map_type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    if "Базовая" in text:
        questions = BASIC_QUESTIONS
        map_type = "Базовая"
    elif "Расширенная" in text:
        questions = EXTENDED_QUESTIONS
        map_type = "Расширенная"
    else:
        await update.message.reply_text("Пожалуйста, выберите тип карты.")
        return MAP_TYPE
    context.user_data['map_questions'] = questions
    context.user_data['map_type'] = map_type
    context.user_data['map_answers'] = []
    context.user_data['current_q'] = 0
    await update.message.reply_text(f"Вам будет задано {len(questions)} вопросов. Отвечайте честно.\n\n{questions[0]}", reply_markup=ReplyKeyboardRemove())
    db.set_user_state(user_id, "MAP_QUESTIONS")
    return MAP_QUESTIONS

async def map_questions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    answer = update.message.text
    answers = context.user_data.get('map_answers', [])
    questions = context.user_data.get('map_questions', [])
    current_q = context.user_data.get('current_q', 0)
    answers.append(answer)
    context.user_data['map_answers'] = answers
    if current_q + 1 < len(questions):
        context.user_data['current_q'] = current_q + 1
        await update.message.reply_text(questions[current_q + 1])
        return MAP_QUESTIONS
    else:
        await update.message.reply_text("Спасибо за ваши ответы! Формируется психологическая карта...")
        # Генерируем карту через OpenAI
        map_text = await ai.generate_psychological_map(answers, questions, context.user_data['map_type'])
        # Сохраняем карту в БД на модерацию
        map_id = db.save_psychological_map(user_id, {
            "type": context.user_data['map_type'],
            "questions": questions,
            "answers": answers,
            "map_text": map_text
        })
        await update.message.reply_text(
            "Ваша карта отправлена на модерацию. После проверки вы получите результат.",
            reply_markup=main_keyboard
        )
        db.set_user_state(user_id, "MENU")
        # Уведомление админу
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"Новая психологическая карта на модерацию (ID: {map_id}) от пользователя {user_id}."
        )
        return MENU

async def unknown_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Пожалуйста, используйте меню для взаимодействия с ботом.")
    return MENU

# Настройка обработчиков
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler)],
        CONSULT: [MessageHandler(filters.TEXT & ~filters.COMMAND, consult_handler)],
        MAP_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, map_type_handler)],
        MAP_QUESTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, map_questions_handler)],
    },
    fallbacks=[MessageHandler(filters.ALL, unknown_handler)],
    allow_reentry=True
)

telegram_app.add_handler(conv_handler)

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
    webhook_url = f"https://{INTERNAL_DOMAIN}/webhook"
    
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