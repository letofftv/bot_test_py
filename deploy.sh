#!/bin/bash

# Скрипт для развертывания психологического бота на хостинге

echo "🚀 Развертывание психологического бота..."

# Проверяем наличие Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Установите Python 3.8+"
    exit 1
fi

# Проверяем переменные окружения
if [ -z "$BOT_TOKEN" ]; then
    echo "❌ BOT_TOKEN не установлен"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OPENAI_API_KEY не установлен"
    exit 1
fi

echo "✅ Переменные окружения проверены"

# Устанавливаем зависимости
echo "📦 Установка зависимостей..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Ошибка установки зависимостей"
    exit 1
fi

echo "✅ Зависимости установлены"

# Запускаем бота
echo "🤖 Запуск бота..."
python3 run.py 