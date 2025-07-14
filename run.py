#!/usr/bin/env python3
"""
Основной файл для запуска психологического бота на хостинге
"""

import os
import sys
import logging
from bot_polling import main as run_bot

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def main():
    """Основная функция запуска"""
    # Проверяем переменные окружения
    if not os.getenv('BOT_TOKEN'):
        logging.error("BOT_TOKEN environment variable is not set")
        sys.exit(1)
    
    logging.info("Starting psychological bot...")
    
    try:
        run_bot()
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Bot crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 