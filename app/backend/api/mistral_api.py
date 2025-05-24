import os
import requests
import json
import argparse
from dotenv import load_dotenv

# Пытаемся загрузить .env из разных мест
# Сначала из текущей директории
load_dotenv()

# Если не нашли, пробуем корень проекта
if not os.getenv("MISTRAL_API_KEY"):
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dotenv_path = os.path.join(ROOT_DIR, '.env')
    print(f"Пытаемся загрузить .env из: {dotenv_path}")
    load_dotenv(dotenv_path=dotenv_path)

# Получаем API ключ из переменной окружения
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
if MISTRAL_API_KEY:
    print("API ключ Mistral успешно загружен")
else:
    print("ВНИМАНИЕ: API ключ Mistral не найден в .env файле")

MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"


def send_prompt_to_mistral(prompt, model="open-mistral-7b"):
    """
    Отправляет текстовый промпт к API Mistral и возвращает ответ.
    
    Args:
        prompt (str): Текстовый запрос для отправки
        model (str): Название модели Mistral AI для использования
        
    Returns:
        dict: Ответ от API Mistral
    """
    if not MISTRAL_API_KEY:
        raise ValueError(
            "MISTRAL_API_KEY не найден. Пожалуйста, установите переменную окружения."
        )
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {MISTRAL_API_KEY}"
    }
    
    data = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    try:
        print(f"Отправляем запрос с моделью: {model}")
        response = requests.post(MISTRAL_API_URL, headers=headers, json=data)
        
        if response.status_code != 200:
            print(f"Код ошибки: {response.status_code}")
            print(f"Ответ сервера: {response.text}")
            
        response.raise_for_status()  # Проверка статуса ответа
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при отправке запроса: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Ответ API: {e.response.text}")
        return None


def format_response(response):
    """
    Форматирует ответ от API для читаемого вывода.
    
    Args:
        response (dict): Ответ от API Mistral
        
    Returns:
        str: Форматированный текст ответа
    """
    if not response or "choices" not in response:
        return "Не удалось получить ответ"
    
    try:
        return response["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        return f"Ошибка при обработке ответа: {json.dumps(response, indent=2)}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Отправка промптов к Mistral AI API"
    )
    parser.add_argument(
        "--prompt", type=str, help="Текст промпта для отправки"
    )
    parser.add_argument(
        "--model", type=str, default="open-mistral-7b", 
        help="Модель Mistral AI (по умолчанию: open-mistral-7b)"
    )
    parser.add_argument(
        "--file", type=str, help="Путь к файлу с промптом"
    )
    
    args = parser.parse_args()
    
    prompt_text = ""
    if args.prompt:
        prompt_text = args.prompt
    elif args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                prompt_text = f.read()
        except Exception as e:
            print(f"Ошибка при чтении файла: {e}")
            exit(1)
    else:
        prompt_text = input("Введите ваш промпт: ")
    
    print(f"Отправляем запрос к модели {args.model}...")
    response = send_prompt_to_mistral(prompt_text, model=args.model)
    
    if response:
        formatted_response = format_response(response)
        print("\nОтвет от Mistral AI:")
        print("-" * 50)
        print(formatted_response)
        print("-" * 50)
    else:
        print("Не удалось получить ответ от API") 