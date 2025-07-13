import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from config import TELEGRAM_TOKEN, ADMIN_ID
from database import Database

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Инициализация
db = Database()

async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начальная команда для админа"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("У вас нет доступа к админским функциям.")
        return
    
    await update.message.reply_text(
        "Админ-панель психологического бота\n\n"
        "Доступные команды:\n"
        "/pending - Показать карты на модерации\n"
        "/approve <map_id> - Одобрить карту\n"
        "/reject <map_id> - Отклонить карту"
    )

async def show_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать карты на модерации"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("У вас нет доступа к админским функциям.")
        return
    
    pending_maps = db.get_pending_maps()
    
    if not pending_maps:
        await update.message.reply_text("Нет карт на модерации.")
        return
    
    for map_id, map_data in pending_maps.items():
        user_id = map_data['user_id']
        map_type = map_data['data']['type']
        map_text = map_data['data']['map_text'][:500] + "..." if len(map_data['data']['map_text']) > 500 else map_data['data']['map_text']
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{map_id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{map_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message_text = f"📋 Карта на модерации\n\n"
        message_text += f"ID: {map_id}\n"
        message_text += f"Пользователь: {user_id}\n"
        message_text += f"Тип: {map_type}\n\n"
        message_text += f"Содержание:\n{map_text}"
        
        await update.message.reply_text(message_text, reply_markup=reply_markup)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка callback кнопок"""
    if update.effective_user.id != ADMIN_ID:
        await update.callback_query.answer("У вас нет доступа к админским функциям.")
        return
    
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("approve_"):
        map_id = data.split("_")[1]
        await approve_map(map_id, context)
        await query.edit_message_text(f"✅ Карта {map_id} одобрена!")
    elif data.startswith("reject_"):
        map_id = data.split("_")[1]
        await reject_map(map_id, context)
        await query.edit_message_text(f"❌ Карта {map_id} отклонена!")

async def approve_map(map_id: str, context: ContextTypes.DEFAULT_TYPE):
    """Одобрить карту и отправить пользователю"""
    map_data = db.data.get("psychological_maps", {}).get(map_id)
    if not map_data:
        return
    
    db.approve_map(map_id)
    user_id = map_data['user_id']
    map_text = map_data['data']['map_text']
    
    # Отправляем карту пользователю
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ Ваша психологическая карта одобрена!\n\n{map_text}"
        )
    except Exception as e:
        logging.error(f"Error sending approved map to user {user_id}: {e}")

async def reject_map(map_id: str, context: ContextTypes.DEFAULT_TYPE):
    """Отклонить карту и уведомить пользователя"""
    map_data = db.data.get("psychological_maps", {}).get(map_id)
    if not map_data:
        return
    
    db.reject_map(map_id)
    user_id = map_data['user_id']
    
    # Уведомляем пользователя
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Ваша психологическая карта была отклонена модератором. Попробуйте создать новую карту."
        )
    except Exception as e:
        logging.error(f"Error sending rejection to user {user_id}: {e}")

def main():
    """Запуск админского бота"""
    # Проверяем наличие токена
    if not TELEGRAM_TOKEN:
        logging.error("BOT_TOKEN environment variable is not set")
        return
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("admin", admin_start))
    app.add_handler(CommandHandler("pending", show_pending))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    logging.info("Starting admin bot with polling...")
    app.run_polling(
        poll_interval=1.0,
        timeout=30,
        bootstrap_retries=5,
        read_timeout=30,
        write_timeout=30
    )

if __name__ == "__main__":
    main() 