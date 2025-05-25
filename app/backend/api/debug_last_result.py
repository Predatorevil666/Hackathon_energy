"""
Отладочный скрипт для проверки содержимого last_result
"""

import sys
import os
import json

# Добавляем текущую директорию в путь импорта
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Импортируем функцию проверки адреса
try:
    from check_address import check_address, last_result
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    sys.exit(1)

def test_address_with_debug():
    """Тестируем адрес и выводим отладочную информацию"""
    # Тестовые адреса
    test_addresses = [
        "г. Москва, ул. Ленина, д. 10, кв. 5",
        "г. Москва, Ленинский проспект, д. 15, офис 301",
        "г. Москва, Хорошевское шоссе, д. 38, промзона"
    ]
    
    for address in test_addresses:
        print(f"\n=== Проверка адреса: {address} ===")
        
        # Проверяем адрес
        address_data = {"address": address}
        is_physical = check_address(address_data)
        
        # Выводим информацию о глобальной переменной last_result
        print("\nСодержимое last_result:")
        print(json.dumps(last_result, indent=2, ensure_ascii=False))
        
        # Выводим основные поля
        print("\nОсновные поля:")
        print(f"is_physical: {is_physical}")
        print(f"is_commercial: {not is_physical}")
        print(f"probability: {last_result.get('probability', 'не указана')}")
        print(f"explanation: {last_result.get('explanation', 'не указано')}")
        print(f"normalized_address: {last_result.get('normalized_address', 'не указан')}")
        
        print("-" * 80)

if __name__ == "__main__":
    test_address_with_debug() 