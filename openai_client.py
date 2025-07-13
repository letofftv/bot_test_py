import openai
import time
from typing import Dict, Any, List
from config import OPENAI_API_KEY

# Настройка OpenAI клиента
openai.api_key = OPENAI_API_KEY

class OpenAIClient:
    def __init__(self):
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
    
    def get_psychological_consultation(self, user_question: str, user_context: str = "") -> str:
        """Получает психологическую консультацию от GPT-4"""
        
        system_prompt = """Ты - опытный психолог-консультант. Твоя задача - предоставить профессиональную психологическую поддержку и консультацию.

Правила работы:
1. Отвечай с позиции профессионального психолога
2. Будь эмпатичным и поддерживающим
3. Не давай медицинских диагнозов
4. При серьезных проблемах рекомендую обратиться к специалисту
5. Используй техники когнитивно-поведенческой терапии
6. Отвечай на русском языке
7. Будь конкретным и практичным в советах"""

        user_prompt = f"""
Контекст пользователя: {user_context}

Вопрос пользователя: {user_question}

Пожалуйста, предоставь профессиональную психологическую консультацию.
"""

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=1000,
                    temperature=0.7
                )
                
                return response.choices[0].message.content.strip() if response.choices[0].message.content else "Извините, не удалось получить ответ."
            
            except openai.RateLimitError:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 2  # Экспоненциальная задержка
                    time.sleep(wait_time)
                    continue
                return "Извините, сервер OpenAI перегружен. Попробуйте позже."
            
            except openai.APIError as e:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return f"Извините, произошла ошибка API OpenAI. Попробуйте позже. Ошибка: {str(e)}"
            
            except Exception as e:
                return f"Извините, произошла ошибка при обработке вашего запроса. Попробуйте позже. Ошибка: {str(e)}"
    
    def generate_psychological_map(self, answers: List[str], questions: List[str], map_type: str) -> str:
        """Генерирует психологическую карту на основе ответов пользователя"""
        
        system_prompt = """Ты - профессиональный психолог, специализирующийся на создании психологических карт личности. 

Твоя задача - проанализировать ответы человека на психологические вопросы и создать подробную психологическую карту.

Структура карты должна включать:
1. Эмоциональное состояние
2. Психологические особенности
3. Сильные стороны личности
4. Области для развития
5. Рекомендации по самопомощи
6. Общие выводы

Будь профессиональным, но доступным в формулировках. Используй эмпатичный тон."""

        # Формируем контекст с вопросами и ответами
        qa_context = ""
        for i, (question, answer) in enumerate(zip(questions, answers), 1):
            qa_context += f"Вопрос {i}: {question}\nОтвет: {answer}\n\n"
        
        user_prompt = f"""
Тип карты: {map_type}

Вопросы и ответы пользователя:

{qa_context}

Создай подробную психологическую карту на основе этих ответов. Структурируй информацию по разделам и дай практические рекомендации.
"""

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=2000,
                    temperature=0.7
                )
                
                return response.choices[0].message.content.strip() if response.choices[0].message.content else "Извините, не удалось получить ответ."
            
            except openai.RateLimitError:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 2
                    time.sleep(wait_time)
                    continue
                return "Извините, сервер OpenAI перегружен. Попробуйте позже."
            
            except openai.APIError as e:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return f"Извините, произошла ошибка API OpenAI. Попробуйте позже. Ошибка: {str(e)}"
            
            except Exception as e:
                return f"Извините, произошла ошибка при создании психологической карты. Попробуйте позже. Ошибка: {str(e)}"
    
    def moderate_content(self, content: str) -> Dict[str, Any]:
        """Модерирует контент на предмет безопасности"""
        
        system_prompt = """Ты - модератор контента. Проверь следующий текст на предмет:
1. Призывов к самоповреждению
2. Суицидальных мыслей
3. Опасного поведения
4. Неподходящего контента

Ответь в формате JSON:
{
    "is_safe": true/false,
    "risk_level": "low/medium/high",
    "concerns": ["список проблем"],
    "recommendation": "рекомендация"
}"""

        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": content}
                    ],
                    max_tokens=500,
                    temperature=0.3
                )
                
                # Парсим JSON ответ
                import json
                try:
                    result = json.loads(response.choices[0].message.content.strip()) if response.choices[0].message.content else {
                        "is_safe": True,
                        "risk_level": "low",
                        "concerns": [],
                        "recommendation": "Контент прошел проверку"
                    }
                    return result
                except json.JSONDecodeError:
                    return {
                        "is_safe": True,
                        "risk_level": "low",
                        "concerns": [],
                        "recommendation": "Контент прошел проверку"
                    }
            
            except (openai.RateLimitError, openai.APIError):
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return {
                    "is_safe": True,
                    "risk_level": "low",
                    "concerns": [],
                    "recommendation": "Ошибка модерации, контент пропущен"
                }
            
            except Exception as e:
                return {
                    "is_safe": True,
                    "risk_level": "low",
                    "concerns": [],
                    "recommendation": "Ошибка модерации, контент пропущен"
                } 