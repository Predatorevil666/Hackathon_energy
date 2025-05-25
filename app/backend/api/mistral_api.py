#!/usr/bin/env python3
"""
Скрипт для взаимодействия с Mistral AI API.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage


def setup_environment():
    """Настройка окружения и загрузка API ключа из корневого .env файла или переменных окружения."""
    # Сначала пытаемся получить ключ напрямую из переменных окружения
    api_key = os.getenv("MISTRAL_API_KEY")
    
    # Если ключа нет в окружении, пытаемся загрузить из .env файла
    if not api_key:
        # Ищем .env файл в корневой директории проекта
        root_dir = Path(__file__).parent.parent.parent.parent
        env_path = root_dir / ".env"
        
        if env_path.exists():
            load_dotenv(env_path)
            api_key = os.getenv("MISTRAL_API_KEY")
    
    if not api_key:
        print("Ошибка: MISTRAL_API_KEY не найден ни в переменных окружения, ни в .env файле")
        raise ValueError("MISTRAL_API_KEY is required")
    
    return api_key


def query_mistral(prompt, model="mistral-large-2411"):
    """Отправка запроса к Mistral AI API.
    
    Args:
        prompt: Текст запроса
        model: Модель Mistral AI (по умолчанию: mistral-large-2411)
    
    Returns:
        Ответ от модели
    """
    api_key = setup_environment()
    
    client = MistralClient(api_key=api_key)
    
    messages = [
        ChatMessage(role="user", content=prompt)
    ]
    
    try:
        chat_response = client.chat(
            model=model,
            messages=messages,
        )
        
        return chat_response.choices[0].message.content
    except Exception as e:
        print(f"Ошибка при запросе к Mistral API: {e}")
        raise e 