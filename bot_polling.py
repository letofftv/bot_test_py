import logging
import time
from collections import defaultdict
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from config import TELEGRAM_TOKEN, ADMIN_ID, BASIC_QUESTIONS, EXTENDED_QUESTIONS
from database import Database
from local_responses import LocalResponseSystem

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
ai = LocalResponseSystem()

# Rate limiting для пользователей
user_last_request = defaultdict(float)
MIN_REQUEST_INTERVAL = 10  # Минимальный интервал между запросами в секундах

def check_user_rate_limit(user_id: int) -> bool:
    """Проверяет, не слишком ли часто пользователь делает запросы"""
    now = time.time()
    last_request = user_last_request.get(user_id, 0)
    
    if now - last_request < MIN_REQUEST_INTERVAL:
        return False
    
    user_last_request[user_id] = now
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    if update.message and update.effective_user:
        await update.message.reply_text(
            "Добро пожаловать в психологический бот!\n\nВыберите действие:",
            reply_markup=main_keyboard
        )
        db.set_user_state(update.effective_user.id, "MENU")
    return MENU

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик главного меню"""
    if not update.message or not update.message.text or not update.effective_user:
        return MENU
    
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
    """Обработчик психологической консультации"""
    if not update.message or not update.message.text or not update.effective_user:
        return MENU
    
    user = update.effective_user
    user_id = user.id
    username = user.username or '-'
    phone = '-'
    question = update.message.text
    
    # Пересылаем админу вопрос пользователя психологу
    admin_text = (
        f"📝 <b>Вопрос психологу</b>\n"
        f"ID: <code>{user_id}</code>\n"
        f"Ник: @{username}\n"
        f"Телефон: {phone}\n"
        f"\n<b>Вопрос:</b>\n{question}"
    )
    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_text, parse_mode='HTML')
    
    # Проверяем rate limiting
    if not check_user_rate_limit(user_id):
        remaining_time = MIN_REQUEST_INTERVAL - (time.time() - user_last_request.get(user_id, 0))
        await update.message.reply_text(
            f"Пожалуйста, подождите {int(remaining_time)} секунд перед следующим запросом.",
            reply_markup=main_keyboard
        )
        db.set_user_state(user_id, "MENU")
        return MENU
    
    # Отправляем сообщение о том, что обрабатываем запрос
    processing_msg = await update.message.reply_text("Ваш вопрос принят. Пожалуйста, подождите, идет обработка...")
    
    try:
        answer = ai.get_psychological_consultation(question)
        
        # Отправляем ответ пользователю
        await update.message.reply_text(answer, reply_markup=main_keyboard)
        db.set_user_state(user_id, "MENU")
        
    except Exception as e:
        logging.error(f"Error in consult_handler: {e}")
        await update.message.reply_text(
            "Извините, произошла ошибка при обработке вашего запроса. Попробуйте позже.",
            reply_markup=main_keyboard
        )
        db.set_user_state(user_id, "MENU")
    
    return MENU

async def map_type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора типа карты"""
    if not update.message or not update.message.text or not update.effective_user:
        return MAP_TYPE
    
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
    
    # Сохраняем данные в контексте
    if context.user_data is not None:
        context.user_data['map_questions'] = questions
        context.user_data['map_type'] = map_type
        context.user_data['map_answers'] = []
        context.user_data['current_q'] = 0
    
    await update.message.reply_text(
        f"Вам будет задано {len(questions)} вопросов. Отвечайте честно.\n\n{questions[0]}", 
        reply_markup=ReplyKeyboardRemove()
    )
    db.set_user_state(user_id, "MAP_QUESTIONS")
    return MAP_QUESTIONS

async def map_questions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ответов на вопросы карты"""
    if not update.message or not update.message.text or not update.effective_user:
        return MAP_QUESTIONS
    
    user_id = update.effective_user.id
    answer = update.message.text
    
    if context.user_data is None:
        await update.message.reply_text("Ошибка: потерян контекст. Начните заново с /start")
        return MENU
    
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
        # Все вопросы отвечены, генерируем карту
        await update.message.reply_text("Спасибо за ваши ответы! Формируется психологическая карта...")
        
        try:
            map_text = ai.generate_psychological_map(answers, questions, context.user_data['map_type'])
            
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
            
            # Пересылаем админу все вопросы и ответы пользователя
            user = update.effective_user
            user_id = user.id
            username = user.username or '-'
            phone = '-'
            qa_lines = [f"<b>{i+1}. {q}</b>\n{a}" for i, (q, a) in enumerate(zip(questions, answers))]
            qa_text = '\n\n'.join(qa_lines)
            admin_text = (
                f"🗺 <b>Ответы пользователя на вопросы для генерации карты</b>\n"
                f"ID: <code>{user_id}</code>\n"
                f"Ник: @{username}\n"
                f"Телефон: {phone}\n"
                f"Тип карты: {context.user_data['map_type']}\n\n"
                f"<b>Вопросы и ответы:</b>\n{qa_text}"
            )
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_text, parse_mode='HTML')
            
        except Exception as e:
            logging.error(f"Error in map_questions_handler: {e}")
            await update.message.reply_text(
                "Извините, произошла ошибка при создании карты. Попробуйте позже.",
                reply_markup=main_keyboard
            )
            db.set_user_state(user_id, "MENU")
        
        return MENU

async def unknown_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик неизвестных команд"""
    if update.message:
        await update.message.reply_text("Пожалуйста, используйте меню для взаимодействия с ботом.")
    return MENU

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    if not update.message:
        return
    
    help_text = """
🤖 Психологический бот

Доступные команды:
/start - Начать работу с ботом
/help - Показать эту справку

Функции бота:
1️⃣ Получить консультацию - задайте вопрос психологу
2️⃣ Создать психологическую карту - пройдите опрос и получите персональную карту

Для начала работы отправьте /start
    """
    await update.message.reply_text(help_text)

def main():
    """Основная функция запуска бота"""
    # Проверяем наличие токена
    if not TELEGRAM_TOKEN:
        logging.error("BOT_TOKEN environment variable is not set")
        return
    
    # Создаем приложение
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
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
    
    # Добавляем обработчики
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))
    
    # Добавляем обработчик ошибок
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logging.error(f"Exception while handling an update: {context.error}")
    
    app.add_error_handler(error_handler)
    
    # Запускаем бота с улучшенными настройками
    logging.info("Starting bot with polling...")
    app.run_polling(
        poll_interval=1.0,
        timeout=30,
        bootstrap_retries=5,
        read_timeout=30,
        write_timeout=30,
        drop_pending_updates=True,  # Игнорируем старые сообщения
        allowed_updates=["message", "callback_query"]  # Только нужные типы обновлений
    )

if __name__ == "__main__":
    main() 