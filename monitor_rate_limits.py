#!/usr/bin/env python3
"""
Скрипт для мониторинга rate limits OpenAI API
"""

import time
import requests
import json
from datetime import datetime
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

class OpenAIRateLimitMonitor:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.base_url = "https://api.openai.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def check_usage(self):
        """Проверяет текущее использование API"""
        try:
            response = requests.get(
                f"{self.base_url}/usage",
                headers=self.headers
            )
            
            if response.status_code == 200:
                usage_data = response.json()
                return usage_data
            else:
                print(f"Ошибка при получении данных об использовании: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Ошибка при проверке использования: {e}")
            return None
    
    def test_api_call(self):
        """Тестирует API вызов для проверки rate limits"""
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": "gpt-4o",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 10
                }
            )
            
            # Проверяем заголовки на rate limit информацию
            rate_limit_remaining = response.headers.get('x-ratelimit-remaining-requests', 'unknown')
            rate_limit_reset = response.headers.get('x-ratelimit-reset-requests', 'unknown')
            
            print(f"Rate Limit Remaining: {rate_limit_remaining}")
            print(f"Rate Limit Reset: {rate_limit_reset}")
            
            if response.status_code == 429:
                print("⚠️  Rate limit exceeded!")
                retry_after = response.headers.get('retry-after', 'unknown')
                print(f"Retry after: {retry_after} seconds")
                return False
            elif response.status_code == 200:
                print("✅ API call successful")
                return True
            else:
                print(f"❌ API call failed with status: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error testing API call: {e}")
            return False
    
    def monitor_continuously(self, interval=60):
        """Непрерывный мониторинг с заданным интервалом"""
        print(f"🚀 Starting continuous monitoring (interval: {interval}s)")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                print(f"\n📊 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("-" * 50)
                
                # Тестируем API вызов
                success = self.test_api_call()
                
                if not success:
                    print("⏳ Waiting before next check...")
                    time.sleep(interval)
                    continue
                
                # Проверяем использование
                usage = self.check_usage()
                if usage:
                    print(f"📈 Usage data: {json.dumps(usage, indent=2)}")
                
                print(f"⏳ Next check in {interval} seconds...")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
        except Exception as e:
            print(f"❌ Monitoring error: {e}")

def main():
    monitor = OpenAIRateLimitMonitor()
    
    print("🔍 OpenAI API Rate Limit Monitor")
    print("=" * 40)
    
    # Проверяем API ключ
    if not monitor.api_key:
        print("❌ OPENAI_API_KEY not found in environment variables")
        return
    
    print("1. Test single API call")
    print("2. Check usage data")
    print("3. Start continuous monitoring")
    print("4. Exit")
    
    while True:
        try:
            choice = input("\nВыберите действие (1-4): ").strip()
            
            if choice == "1":
                monitor.test_api_call()
            elif choice == "2":
                usage = monitor.check_usage()
                if usage:
                    print(json.dumps(usage, indent=2))
            elif choice == "3":
                interval = input("Введите интервал мониторинга в секундах (по умолчанию 60): ").strip()
                try:
                    interval = int(interval) if interval else 60
                    monitor.monitor_continuously(interval)
                except ValueError:
                    print("❌ Неверный интервал, используем 60 секунд")
                    monitor.monitor_continuously()
            elif choice == "4":
                print("👋 Goodbye!")
                break
            else:
                print("❌ Неверный выбор")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 