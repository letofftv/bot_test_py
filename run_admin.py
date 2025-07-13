#!/usr/bin/env python3
"""
Файл для запуска админской панели на хостинге
"""

import os
import sys
import logging
from admin_polling import main as run_admin

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def main():
    """Основная функция запуска админской панели"""
    # Проверяем переменные окружения
    if not os.getenv('BOT_TOKEN'):
        logging.error("BOT_TOKEN environment variable is not set")
        sys.exit(1)
    
    logging.info("Starting admin panel...")
    
    try:
        run_admin()
    except KeyboardInterrupt:
        logging.info("Admin panel stopped by user")
    except Exception as e:
        logging.error(f"Admin panel crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 