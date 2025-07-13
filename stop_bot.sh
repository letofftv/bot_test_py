#!/bin/bash

# Скрипт для остановки всех экземпляров бота

echo "🛑 Остановка всех экземпляров бота..."

# Останавливаем все процессы Python с ботом
pkill -f "run.py"
pkill -f "bot_polling.py"
pkill -f "admin_polling.py"

# Ждем немного
sleep 2

# Проверяем, что процессы остановлены
if pgrep -f "run.py\|bot_polling.py\|admin_polling.py" > /dev/null; then
    echo "⚠️  Некоторые процессы все еще работают. Принудительная остановка..."
    pkill -9 -f "run.py"
    pkill -9 -f "bot_polling.py"
    pkill -9 -f "admin_polling.py"
else
    echo "✅ Все экземпляры бота остановлены"
fi

echo "🎯 Готово к запуску нового экземпляра" 