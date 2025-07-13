#!/usr/bin/env python3
"""
Скрипт для проверки баланса и использования OpenAI API
"""

import requests
import json
from datetime import datetime
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

class OpenAIAccountChecker:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.base_url = "https://api.openai.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def check_usage(self):
        """Проверяет использование API"""
        try:
            response = requests.get(
                f"{self.base_url}/usage",
                headers=self.headers
            )
            
            if response.status_code == 200:
                usage_data = response.json()
                return usage_data
            else:
                print(f"❌ Ошибка при получении данных об использовании: {response.status_code}")
                print(f"Ответ: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка при проверке использования: {e}")
            return None
    
    def check_subscription(self):
        """Проверяет информацию о подписке"""
        try:
            response = requests.get(
                f"{self.base_url}/dashboard/billing/subscription",
                headers=self.headers
            )
            
            if response.status_code == 200:
                subscription_data = response.json()
                return subscription_data
            else:
                print(f"❌ Ошибка при получении данных о подписке: {response.status_code}")
                print(f"Ответ: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка при проверке подписки: {e}")
            return None
    
    def test_api_call(self):
        """Тестирует API вызов"""
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 10
                }
            )
            
            if response.status_code == 429:
                error_data = response.json()
                error_message = error_data.get('error', {}).get('message', 'Unknown error')
                error_type = error_data.get('error', {}).get('type', 'unknown')
                
                print(f"⚠️  Rate limit exceeded!")
                print(f"Тип ошибки: {error_type}")
                print(f"Сообщение: {error_message}")
                
                if "insufficient_quota" in error_message.lower():
                    print("💸 ПРОБЛЕМА: Закончились средства на аккаунте OpenAI!")
                    print("🔗 Перейдите на https://platform.openai.com/account/billing для пополнения")
                
                return False
            elif response.status_code == 200:
                print("✅ API вызов успешен")
                return True
            else:
                print(f"❌ API вызов не удался: {response.status_code}")
                print(f"Ответ: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка тестирования API: {e}")
            return False
    
    def display_account_info(self):
        """Отображает информацию об аккаунте"""
        print("🔍 Проверка аккаунта OpenAI")
        print("=" * 50)
        
        # Проверяем API ключ
        if not self.api_key:
            print("❌ OPENAI_API_KEY не найден в переменных окружения")
            return
        
        print(f"📅 Время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Тестируем API вызов
        print("🧪 Тестирование API вызова...")
        api_success = self.test_api_call()
        print()
        
        # Проверяем подписку
        print("💳 Проверка подписки...")
        subscription = self.check_subscription()
        if subscription:
            print("✅ Данные подписки получены")
            print(f"   План: {subscription.get('object', 'N/A')}")
            print(f"   Статус: {subscription.get('status', 'N/A')}")
            if 'hard_limit_usd' in subscription:
                print(f"   Лимит: ${subscription.get('hard_limit_usd', 'N/A')}")
        else:
            print("❌ Не удалось получить данные подписки")
        print()
        
        # Проверяем использование
        print("📊 Проверка использования...")
        usage = self.check_usage()
        if usage:
            print("✅ Данные использования получены")
            print(json.dumps(usage, indent=2, ensure_ascii=False))
        else:
            print("❌ Не удалось получить данные использования")
        print()
        
        # Рекомендации
        print("💡 Рекомендации:")
        if not api_success:
            print("   - Проверьте баланс на https://platform.openai.com/account/billing")
            print("   - Убедитесь, что API ключ действителен")
            print("   - Возможно, нужно пополнить счет")
        else:
            print("   - API работает корректно")
            print("   - Продолжайте использовать бота")

def main():
    checker = OpenAIAccountChecker()
    checker.display_account_info()

if __name__ == "__main__":
    main() 