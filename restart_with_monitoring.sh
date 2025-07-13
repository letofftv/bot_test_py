#!/bin/bash

# Скрипт для перезапуска бота с мониторингом rate limits

echo "🔄 Перезапуск бота с улучшенным rate limiting..."

# Останавливаем все экземпляры бота
echo "⏹️  Останавливаем существующие экземпляры..."
./stop_bot.sh

# Ждем немного
sleep 2

# Проверяем rate limits перед запуском
echo "🔍 Проверяем текущие rate limits OpenAI API..."
python3 monitor_rate_limits.py <<< "1" <<< "4"

# Запускаем бота
echo "🚀 Запускаем бота с улучшенным rate limiting..."
python3 run.py 