#!/usr/bin/env python3
import json
import requests
import sys


def load_json_data(file_path):
    """Загрузка данных из JSON файла"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка при чтении JSON файла: {e}")
        sys.exit(1)


def check_address(address_data):
    """Отправка адреса на API и проверка статуса физического лица"""
    # URL вашего локального API или внешнего сервиса
    api_url = "http://localhost:8003/api/v1/predict"

    # Преобразуем данные в формат, ожидаемый API
    payload = {
        "address": address_data["address"],
        "additional_info": address_data.get("metadata", {}),
    }

    try:
        # Отправляем POST запрос
        response = requests.post(api_url, json=payload)

        # Проверяем статус ответа
        if response.status_code == 200:
            result = response.json()
            print("Результат проверки:")
            print(f"Адрес: {address_data['address']}")

            # Проверяем ожидаемую структуру ответа
            if "is_commercial" in result:
                is_physical = not result["is_commercial"]
                print(
                    f"Статус: {'Физическое лицо' if is_physical else 'Юридическое лицо'}"
                )
                print(f"Вероятность: {result.get('probability', 'Не указана')}")
                return is_physical
            else:
                print(f"Неожиданный формат ответа API: {result}")
        else:
            print(f"Ошибка API: {response.status_code}")
            print(f"Текст ошибки: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Ошибка запроса: {e}")

    return None


if __name__ == "__main__":
    # Получаем путь к файлу из аргументов или используем значение по умолчанию
    json_file = sys.argv[1] if len(sys.argv) > 1 else "test_address.json"

    print(f"Проверка адреса из файла: {json_file}")
    address_data = load_json_data(json_file)

    result = check_address(address_data)

    if result is not None:
        print(
            f"Итоговый результат: {'Физическое лицо' if result else 'Юридическое лицо'}"
        )
    else:
        print("Не удалось определить статус лица")
