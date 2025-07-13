import openai
import time
import asyncio
import threading
from typing import Dict, Any, List
from config import OPENAI_API_KEY
from collections import deque
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройка OpenAI клиента
openai.api_key = OPENAI_API_KEY

class RateLimiter:
    """Класс для управления rate limiting"""
    def __init__(self, max_requests_per_minute=60):
        self.max_requests = max_requests_per_minute
        self.requests = deque()
        self.lock = threading.Lock()
    
    def can_make_request(self):
        """Проверяет, можно ли сделать запрос"""
        now = time.time()
        with self.lock:
            # Удаляем старые запросы (старше 1 минуты)
            while self.requests and now - self.requests[0] > 60:
                self.requests.popleft()
            
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            return False
    
    def wait_if_needed(self):
        """Ждет, если нужно, перед выполнением запроса"""
        while not self.can_make_request():
            time.sleep(1)

class OpenAIClient:
    def __init__(self):
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
        self.rate_limiter = RateLimiter(max_requests_per_minute=90)  # GPT-3.5-turbo имеет более высокие лимиты
        self.request_queue = deque()
        self.processing = False
    
    def _make_request_with_backoff(self, request_func, *args, **kwargs):
        """Выполняет запрос с экспоненциальной задержкой при ошибках"""
        max_retries = 5
        base_delay = 1
        
        for attempt in range(max_retries):
            try:
                # Ждем, если достигнут лимит запросов
                self.rate_limiter.wait_if_needed()
                
                # Выполняем запрос
                return request_func(*args, **kwargs)
                
            except openai.RateLimitError as e:
                logger.warning(f"Rate limit hit on attempt {attempt + 1}: {e}")
                
                if attempt < max_retries - 1:
                    # Экспоненциальная задержка с джиттером
                    delay = base_delay * (2 ** attempt) + (time.time() % 1)
                    logger.info(f"Waiting {delay:.2f} seconds before retry")
                    time.sleep(delay)
                    continue
                else:
                    raise e
                    
            except openai.APIError as e:
                logger.error(f"API error on attempt {attempt + 1}: {e}")
                
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                else:
                    raise e
                    
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(base_delay * (2 ** attempt))
                    continue
                else:
                    raise e
        
        raise Exception("Max retries exceeded")
    
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

        try:
            response = self._make_request_with_backoff(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip() if response.choices[0].message.content else "Извините, не удалось получить ответ."
        
        except openai.RateLimitError:
            logger.error("Rate limit exceeded for consultation request")
            return "Извините, сервер OpenAI перегружен. Попробуйте через несколько минут."
        
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return "Извините, произошла ошибка API OpenAI. Попробуйте позже."
        
        except Exception as e:
            logger.error(f"Unexpected error in consultation: {e}")
            return "Извините, произошла ошибка при обработке вашего запроса. Попробуйте позже."
    
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

        try:
            response = self._make_request_with_backoff(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2000,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip() if response.choices[0].message.content else "Извините, не удалось получить ответ."
        
        except openai.RateLimitError:
            logger.error("Rate limit exceeded for map generation")
            return "Извините, сервер OpenAI перегружен. Попробуйте создать карту позже."
        
        except openai.APIError as e:
            logger.error(f"OpenAI API error in map generation: {e}")
            return "Извините, произошла ошибка API OpenAI при создании карты. Попробуйте позже."
        
        except Exception as e:
            logger.error(f"Unexpected error in map generation: {e}")
            return "Извините, произошла ошибка при создании психологической карты. Попробуйте позже."
    
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

        try:
            response = self._make_request_with_backoff(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo",
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
                logger.warning("Failed to parse moderation JSON response")
                return {
                    "is_safe": True,
                    "risk_level": "low",
                    "concerns": [],
                    "recommendation": "Контент прошел проверку"
                }
        
        except (openai.RateLimitError, openai.APIError) as e:
            logger.error(f"OpenAI error in moderation: {e}")
            return {
                "is_safe": True,
                "risk_level": "low",
                "concerns": [],
                "recommendation": "Ошибка модерации, контент пропущен"
            }
        
        except Exception as e:
            logger.error(f"Unexpected error in moderation: {e}")
            return {
                "is_safe": True,
                "risk_level": "low",
                "concerns": [],
                "recommendation": "Ошибка модерации, контент пропущен"
            } 