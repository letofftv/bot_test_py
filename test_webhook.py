import os
from config import EXTERNAL_DOMAIN

# Тестируем формирование webhook URL
webhook_url = f"https://{EXTERNAL_DOMAIN}/webhook"
print(f"EXTERNAL_DOMAIN: {EXTERNAL_DOMAIN}")
print(f"Webhook URL: {webhook_url}")

# Проверяем переменные окружения
print(f"BOT_TOKEN: {os.getenv('BOT_TOKEN', 'NOT_SET')[:10]}...")
print(f"OPENAI_API_KEY: {os.getenv('OPENAI_API_KEY', 'NOT_SET')[:10]}...") 