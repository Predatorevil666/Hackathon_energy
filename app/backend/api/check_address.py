import json
import requests
import sys
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Получаем API ключ из переменной окружения
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

def load_json_data(file_path):
    """Загрузка данных из JSON файла"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка при чтении JSON файла: {e}")
        sys.exit(1)


def check_address(address_data):
    """Отправка адреса на Mistral API и проверка статуса физического лица"""
    if not MISTRAL_API_KEY:
        print("Ошибка: MISTRAL_API_KEY не найден. Установите API ключ в файле .env")
        return None
    
    # Готовим запрос к Mistral API
    address = address_data["address"]
    prompt = f"""
    Проанализируй следующий адрес: "{address}" 
    
    Определи, является ли это адресом физического лица или юридического лица (организации).
    Оцени вероятность от 0 до 1.
    
    Ответ предоставь в формате JSON:
    {{
        "is_commercial": true/false,
        "probability": 0.x,
        "explanation": "краткое объяснение"
    }}
    
    Где is_commercial - true, если это адрес организации, и false, если физического лица.
    """
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {MISTRAL_API_KEY}"
    }
    
    data = {
        "model": "open-mistral-7b",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 500
    }
    
    try:
        print("Отправляем запрос к Mistral API для анализа адреса...")
        response = requests.post(MISTRAL_API_URL, headers=headers, json=data)
        response.raise_for_status()
        
        # Обрабатываем ответ
        result = response.json()
        if "choices" in result:
            response_text = result["choices"][0]["message"]["content"]
            print("Получен ответ от Mistral API:")
            print(response_text)
            
            # Пытаемся извлечь JSON из ответа
            try:
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    result = json.loads(json_str)
                    
                    print(f"Адрес: {address}")
                    
                    if "is_commercial" in result:
                        is_physical = not result["is_commercial"]
                        status = 'Физическое лицо' if is_physical else 'Юридическое лицо'
                        print(f"Статус: {status}")
                        print(f"Вероятность: {result.get('probability', 'Не указана')}")
                        if "explanation" in result:
                            print(f"Объяснение: {result['explanation']}")
                        return is_physical
                    else:
                        print(f"Неожиданный формат ответа API: {result}")
                else:
                    print("Не удалось извлечь JSON из ответа")
            except Exception as e:
                print(f"Ошибка при обработке JSON: {e}")
        else:
            print(f"Неожиданный формат ответа API: {result}")
    except requests.exceptions.RequestException as e:
        print(f"Ошибка запроса: {e}")
    
    return None


if __name__ == "__main__":
    # Определяем директорию скрипта
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Получаем путь к файлу из аргументов или используем значение по умолчанию
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        # Используем test_address.json из директории скрипта
        json_file = os.path.join(script_dir, "test_address.json")
    
    print(f"Проверка адреса из файла: {json_file}")
    address_data = load_json_data(json_file)
    
    result = check_address(address_data)
    
    if result is not None:
        status = 'Физическое лицо' if result else 'Юридическое лицо'
        print(f"Итоговый результат: {status}")
    else:
        print("Не удалось определить статус лица")
