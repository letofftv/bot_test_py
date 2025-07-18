import logging
import time
from collections import defaultdict
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from config import TELEGRAM_TOKEN, ADMIN_IDS
from database import Database
from local_responses import LocalResponseSystem
from psychological_maps import PSYCHOLOGICAL_MAPS

# Состояния для ConversationHandler
MENU, CONSULT, MAP_SELECT, MAP_TYPE, MAP_QUESTIONS, WAITING_MODERATION = range(6)

# Клавиатуры
main_keyboard = ReplyKeyboardMarkup([
    ["1️⃣ Получить консультацию"],
    ["2️⃣ Создать психологическую карту"]
], resize_keyboard=True)

# Клавиатура с навигацией
navigation_keyboard = ReplyKeyboardMarkup([
    ["🔙 Назад", "🏠 Главное меню"]
], resize_keyboard=True)

# Формируем клавиатуру выбора карты с навигацией
map_names = [[f"{i+1}. {m['name']}"] for i, m in enumerate(PSYCHOLOGICAL_MAPS)]
map_select_keyboard = ReplyKeyboardMarkup(map_names + [["🔙 Назад", "🏠 Главное меню"]], resize_keyboard=True)

map_type_keyboard = ReplyKeyboardMarkup([
    ["Базовая анкета (4 вопроса)"],
    ["Расширенная анкета (10 вопросов)"],
    ["🔙 Назад", "🏠 Главное меню"]
], resize_keyboard=True)

# Приветствия
MAP_RULES_TEXT = (
    "🧭 Перед тем, как начать: 3 важных правила\n"
    "Эти простые принципы помогут создать карту, которая действительно отразит тебя. Нарушение любого из них может исказить результат, и тогда ты увидишь не себя — а свою социальную маску.\n"
    "1. Пиши, как для себя — не как для других.\n"
    "Это пространство честного контакта с собой. Здесь не нужно «казаться лучше», «умнее» или «благополучнее». Никаких оценок, никакой критики. Карта — твой личный инструмент, и чем искреннее ты будешь, тем глубже и точнее она станет.\n"
    "2. Отвечай не как «правильно», а как на самом деле.\n"
    "Забудь на время, как \"принято\", \"надо\", \"ожидается\". Смотри в свой реальный опыт: что ты чувствуешь, что вызывает у тебя резонанс или отторжение. Даже если ответ «неудобный» — он, скорее всего, самый честный. Почувствуй, какие образы, воспоминания или телесные реакции приходят в ответ — именно они подскажут, что для тебя важно.\n"
    "3. Дай себе время — и пиши развернуто.\n"
    "Ответ на каждый вопрос должен быть не короче 3–4 предложений. Лучше — больше. Старайся раскрывать примеры, эмоции, образы. Если чувствуешь паузу — дыши, смотри внутрь, вспоминай. Иногда одно слово, пришедшее из глубины, важнее десятка «правильных» формулировок."
)

CONSULT_WELCOME_TEXT = (
    "Не пиши, как ты хотел(а) бы думать или как тебя учили. Пиши, как ты реально чувствуешь, как поступаешь и что у тебя происходит на самом деле. Это не тест на мораль — это зеркало, и чем оно яснее, тем точнее будет ответ."
)

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

db = Database()
ai = LocalResponseSystem()
user_last_request = defaultdict(float)
MIN_REQUEST_INTERVAL = 10

def check_user_rate_limit(user_id: int) -> bool:
    now = time.time()
    last_request = user_last_request.get(user_id, 0)
    if now - last_request < MIN_REQUEST_INTERVAL:
        return False
    user_last_request[user_id] = now
    return True

def save_navigation_state(context: ContextTypes.DEFAULT_TYPE, current_state: int, previous_state: int = None):
    """Сохраняет состояние навигации"""
    if context.user_data is None:
        context.user_data = {}
    
    # Сохраняем стек состояний
    if 'navigation_stack' not in context.user_data:
        context.user_data['navigation_stack'] = []
    
    # Добавляем текущее состояние в стек
    if previous_state is not None:
        context.user_data['navigation_stack'].append(previous_state)
    
    context.user_data['current_state'] = current_state

def get_previous_state(context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает предыдущее состояние из стека"""
    if context.user_data is None or 'navigation_stack' not in context.user_data:
        return MENU
    
    navigation_stack = context.user_data.get('navigation_stack', [])
    if navigation_stack:
        return navigation_stack.pop()
    return MENU

async def handle_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> int:
    """Обрабатывает навигационные команды"""
    if not update.message or not update.effective_user:
        return MENU
    
    user_id = update.effective_user.id
    
    if text == "🔙 Назад":
        previous_state = get_previous_state(context)
        if previous_state == MENU:
            # Если мы в главном меню, остаемся там
            await update.message.reply_text(
                "Вы уже в главном меню. Выберите действие:",
                reply_markup=main_keyboard
            )
            return MENU
        else:
            # Возвращаемся к предыдущему состоянию
            return await navigate_to_state(update, context, previous_state)
    
    elif text == "🏠 Главное меню":
        # Очищаем стек навигации и возвращаемся в главное меню
        if context.user_data:
            context.user_data['navigation_stack'] = []
            context.user_data['current_state'] = MENU
        
        await update.message.reply_text(
            "Выберите действие:",
            reply_markup=main_keyboard
        )
        db.set_user_state(user_id, "MENU")
        return MENU
    
    return None  # Не навигационная команда

async def navigate_to_state(update: Update, context: ContextTypes.DEFAULT_TYPE, target_state: int) -> int:
    """Навигация к определенному состоянию"""
    if not update.message or not update.effective_user:
        return MENU
    
    user_id = update.effective_user.id
    
    if target_state == MENU:
        await update.message.reply_text(
            "Выберите действие:",
            reply_markup=main_keyboard
        )
        db.set_user_state(user_id, "MENU")
        return MENU
    
    elif target_state == MAP_SELECT:
        await update.message.reply_text(
            "Выберите одну из 15 психологических карт:",
            reply_markup=map_select_keyboard
        )
        db.set_user_state(user_id, "MAP_SELECT")
        return MAP_SELECT
    
    elif target_state == MAP_TYPE:
        selected_map = context.user_data.get('selected_map')
        if selected_map:
            await update.message.reply_text(
                f"<b>{selected_map['name']}</b>\n\n{selected_map['description']}\n\nВыберите тип анкеты:",
                reply_markup=map_type_keyboard,
                parse_mode='HTML'
            )
            db.set_user_state(user_id, "MAP_TYPE")
            return MAP_TYPE
    
    # Если не удалось определить состояние, возвращаемся в главное меню
    await update.message.reply_text(
        "Выберите действие:",
        reply_markup=main_keyboard
    )
    db.set_user_state(user_id, "MENU")
    return MENU

async def handle_non_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нетекстовые сообщения"""
    if not update.message:
        return
    
    await update.message.reply_text(
        "Пожалуйста, введите ответ текстом, чтобы я мог продолжить работу.",
        reply_markup=ReplyKeyboardRemove()
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.effective_user:
        # Очищаем навигационный стек при старте
        if context.user_data:
            context.user_data['navigation_stack'] = []
            context.user_data['current_state'] = MENU
        
        await update.message.reply_text(
            "Добро пожаловать в психологический бот!\n\nВыберите действие:",
            reply_markup=main_keyboard
        )
        db.set_user_state(update.effective_user.id, "MENU")
    return MENU

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text or not update.effective_user:
        return MENU
    
    text = update.message.text
    user_id = update.effective_user.id
    
    # Проверяем навигационные команды
    navigation_result = await handle_navigation(update, context, text)
    if navigation_result is not None:
        return navigation_result
    
    if text.startswith("1"):
        save_navigation_state(context, CONSULT, MENU)
        await update.message.reply_text(CONSULT_WELCOME_TEXT, reply_markup=navigation_keyboard)
        db.set_user_state(user_id, "CONSULT")
        return CONSULT
    elif text.startswith("2"):
        save_navigation_state(context, MAP_SELECT, MENU)
        # Сразу отправляем приветствие и меню выбора карты
        await update.message.reply_text(MAP_RULES_TEXT, reply_markup=ReplyKeyboardRemove())
        await update.message.reply_text(
            "Выберите одну из 15 психологических карт:",
            reply_markup=map_select_keyboard
        )
        db.set_user_state(user_id, "MAP_SELECT")
        return MAP_SELECT
    else:
        await update.message.reply_text("Пожалуйста, выберите действие из меню.")
        return MENU

async def consult_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text or not update.effective_user:
        return MENU
    
    text = update.message.text
    
    # Проверяем навигационные команды
    navigation_result = await handle_navigation(update, context, text)
    if navigation_result is not None:
        return navigation_result
    
    user = update.effective_user
    user_id = user.id
    username = user.username or '-'
    phone = '-'
    question = text
    admin_text = (
        f"📝 <b>Вопрос психологу</b>\n"
        f"ID: <code>{user_id}</code>\n"
        f"Ник: @{username}\n"
        f"Телефон: {phone}\n"
        f"\n<b>Вопрос:</b>\n{question}"
    )
    for admin_id in ADMIN_IDS:
        await context.bot.send_message(chat_id=admin_id, text=admin_text, parse_mode='HTML')
    if not check_user_rate_limit(user_id):
        remaining_time = MIN_REQUEST_INTERVAL - (time.time() - user_last_request.get(user_id, 0))
        await update.message.reply_text(
            f"Пожалуйста, подождите {int(remaining_time)} секунд перед следующим запросом.",
            reply_markup=main_keyboard
        )
        db.set_user_state(user_id, "MENU")
        return MENU
    processing_msg = await update.message.reply_text("Ваш вопрос принят. Пожалуйста, подождите, идет обработка...")
    try:
        answer = ai.get_psychological_consultation(question)
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

async def map_select_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text or not update.effective_user:
        return MAP_SELECT
    
    text = update.message.text
    
    # Проверяем навигационные команды
    navigation_result = await handle_navigation(update, context, text)
    if navigation_result is not None:
        return navigation_result
    
    user_id = update.effective_user.id
    try:
        idx = int(text.split('.')[0].strip()) - 1
        selected_map = PSYCHOLOGICAL_MAPS[idx]
    except Exception:
        await update.message.reply_text("Пожалуйста, выберите карту из списка.", reply_markup=map_select_keyboard)
        return MAP_SELECT
    
    context.user_data['selected_map'] = selected_map
    save_navigation_state(context, MAP_TYPE, MAP_SELECT)
    
    await update.message.reply_text(
        f"<b>{selected_map['name']}</b>\n\n{selected_map['description']}\n\nВыберите тип анкеты:",
        reply_markup=map_type_keyboard,
        parse_mode='HTML'
    )
    db.set_user_state(user_id, "MAP_TYPE")
    return MAP_TYPE

async def map_type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text or not update.effective_user:
        return MAP_TYPE
    
    text = update.message.text
    
    # Проверяем навигационные команды
    navigation_result = await handle_navigation(update, context, text)
    if navigation_result is not None:
        return navigation_result
    
    if context.user_data is None:
        await update.message.reply_text("Ошибка: потерян контекст. Начните заново с /start")
        return MENU
    
    user_id = update.effective_user.id
    selected_map = context.user_data.get('selected_map')
    if not selected_map:
        await update.message.reply_text("Ошибка: карта не выбрана. Начните заново с /start.")
        return MENU
    
    if "Базовая" in text:
        questions = selected_map['basic']
        map_type = "Базовая"
    elif "Расширенная" in text:
        questions = selected_map['extended']
        map_type = "Расширенная"
    else:
        await update.message.reply_text("Пожалуйста, выберите тип анкеты.", reply_markup=map_type_keyboard)
        return MAP_TYPE
    
    context.user_data['map_questions'] = questions
    context.user_data['map_type'] = map_type
    context.user_data['map_answers'] = []
    context.user_data['current_q'] = 0
    save_navigation_state(context, MAP_QUESTIONS, MAP_TYPE)
    
    await update.message.reply_text(
        f"Вам будет задано {len(questions)} вопросов. Отвечайте честно.\n\n{questions[0]}",
        reply_markup=navigation_keyboard
    )
    db.set_user_state(user_id, "MAP_QUESTIONS")
    return MAP_QUESTIONS

async def map_questions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text or not update.effective_user:
        return MAP_QUESTIONS
    
    text = update.message.text
    
    # Проверяем навигационные команды
    navigation_result = await handle_navigation(update, context, text)
    if navigation_result is not None:
        return navigation_result
    
    if context.user_data is None:
        await update.message.reply_text("Ошибка: потерян контекст. Начните заново с /start")
        return MENU
    
    user_id = update.effective_user.id
    answer = text
    answers = context.user_data.get('map_answers', [])
    questions = context.user_data.get('map_questions', [])
    current_q = context.user_data.get('current_q', 0)
    selected_map = context.user_data.get('selected_map')
    map_type = context.user_data.get('map_type')
    
    if not questions or not selected_map or not map_type:
        await update.message.reply_text("Ошибка: потерян контекст. Начните заново с /start")
        return MENU
    
    # Сохраняем ответ
    answers.append(answer)
    context.user_data['map_answers'] = answers
    
    if current_q + 1 < len(questions):
        context.user_data['current_q'] = current_q + 1
        next_question = questions[current_q + 1]
        await update.message.reply_text(next_question, reply_markup=navigation_keyboard)
        return MAP_QUESTIONS
    else:
        await update.message.reply_text("Спасибо за ваши ответы! Формируется психологическая карта...")
        try:
            map_text = ai.generate_psychological_map(answers, questions, map_type)
            map_id = db.save_psychological_map(user_id, {
                "type": map_type,
                "map_id": selected_map['id'],
                "map_name": selected_map['name'],
                "questions": questions,
                "answers": answers,
                "map_text": map_text
            })
            await update.message.reply_text(
                "Ваша карта отправлена на модерацию. После проверки вы получите результат.",
                reply_markup=main_keyboard
            )
            db.set_user_state(user_id, "MENU")
            user = update.effective_user
            username = user.username or '-'
            phone = '-'
            qa_lines = [f"<b>{i+1}. {q}</b>\n{a}" for i, (q, a) in enumerate(zip(questions, answers))]
            qa_text = '\n\n'.join(qa_lines)
            admin_text = (
                f"🗺 <b>Ответы пользователя на вопросы для генерации карты</b>\n"
                f"ID: <code>{user_id}</code>\n"
                f"Ник: @{username}\n"
                f"Телефон: {phone}\n"
                f"Карта: {selected_map['name']}\n"
                f"Тип анкеты: {map_type}\n\n"
                f"<b>Вопросы и ответы:</b>\n{qa_text}"
            )
            for admin_id in ADMIN_IDS:
                await context.bot.send_message(chat_id=admin_id, text=admin_text, parse_mode='HTML')
        except Exception as e:
            logging.error(f"Error in map_questions_handler: {e}")
            await update.message.reply_text(
                "Извините, произошла ошибка при создании карты. Попробуйте позже.",
                reply_markup=main_keyboard
            )
            db.set_user_state(user_id, "MENU")
        return MENU

async def unknown_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Пожалуйста, используйте меню для взаимодействия с ботом.")
    return MENU

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

Навигация:
🔙 Назад - вернуться к предыдущему шагу
🏠 Главное меню - вернуться в главное меню

Для начала работы отправьте /start
    """
    await update.message.reply_text(help_text)

def main():
    if not TELEGRAM_TOKEN:
        logging.error("BOT_TOKEN environment variable is not set")
        return
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Обработчик нетекстовых сообщений (должен быть первым!)
    non_text_handler = MessageHandler(
        filters.ALL & ~filters.TEXT & ~filters.COMMAND,
        handle_non_text_message
    )
    app.add_handler(non_text_handler)
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler)],
            CONSULT: [MessageHandler(filters.TEXT & ~filters.COMMAND, consult_handler)],
            MAP_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, map_select_handler)],
            MAP_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, map_type_handler)],
            MAP_QUESTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, map_questions_handler)],
        },
        fallbacks=[CommandHandler("help", help_command), MessageHandler(filters.COMMAND, unknown_handler)]
    )
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))
    app.run_polling()

if __name__ == "__main__":
    main() 