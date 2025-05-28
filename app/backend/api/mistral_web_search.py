#!/usr/bin/env python3
"""
Скрипт для веб-поиска и анализа результатов с помощью Mistral AI.
Поддерживает несколько поисковых движков с механизмом резервирования.
"""

import json
import os
import random
import re
import time

from pathlib import Path

import requests

from dotenv import load_dotenv
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage

# Пробуем импортировать DuckDuckGo, но не останавливаемся если не получается
try:
    from duckduckgo_search import DDGS

    DUCKDUCKGO_AVAILABLE = True
except ImportError:
    DUCKDUCKGO_AVAILABLE = False

# Возможные User-Agent для запросов
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0",
]


def setup_environment():
    """Настройка окружения и загрузка API ключа из переменных окружения или .env файла."""
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
        print(
            "Ошибка: MISTRAL_API_KEY не найден ни в переменных окружения, ни в .env файле"
        )
        raise ValueError("MISTRAL_API_KEY is required")

    return api_key


def search_duckduckgo(query, num_results=3, retries=3, delay=2):
    """Выполняет поиск через DuckDuckGo с несколькими попытками при ошибке.

    Args:
        query: Поисковый запрос
        num_results: Количество результатов (по умолчанию: 3)
        retries: Количество попыток при ошибке
        delay: Задержка между попытками в секундах

    Returns:
        Список результатов поиска или пустой список при ошибке
    """
    if not DUCKDUCKGO_AVAILABLE:
        print("DuckDuckGo Search не установлен")
        return []

    for attempt in range(retries):
        try:
            # Случайная задержка для предотвращения блокировки
            time.sleep(random.uniform(1, delay))

            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=num_results))

            if results:
                print(
                    f"DuckDuckGo: успешно получено {len(results)} результатов"
                )
                return results
        except Exception as e:
            print(f"DuckDuckGo поиск, попытка {attempt + 1}: {e}")
            time.sleep(delay * (attempt + 1))  # Экспоненциальная задержка

    print(
        "DuckDuckGo: не удалось получить результаты после нескольких попыток"
    )
    return []


def search_google_serper(query, num_results=3):
    """Выполняет поиск через Serper.dev (API для Google поиска).

    Требует API ключа в переменной окружения SERPER_API_KEY.

    Args:
        query: Поисковый запрос
        num_results: Количество результатов

    Returns:
        Список результатов поиска или пустой список при ошибке
    """
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        print(
            "Serper API ключ не найден в переменных окружения (SERPER_API_KEY)"
        )
        return []

    try:
        url = "https://google.serper.dev/search"
        headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
        payload = {"q": query, "num": num_results}

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        results = []
        if "organic" in data:
            for item in data["organic"][:num_results]:
                results.append(
                    {
                        "title": item.get("title", ""),
                        "href": item.get("link", ""),
                        "body": item.get("snippet", ""),
                    }
                )

        print(f"Google Serper: успешно получено {len(results)} результатов")
        return results
    except Exception as e:
        print(f"Ошибка при поиске через Google Serper: {e}")
        return []


def search_wikipedia(query, num_results=3):
    """Выполняет поиск по Wikipedia.

    Args:
        query: Поисковый запрос
        num_results: Количество результатов

    Returns:
        Список результатов поиска или пустой список при ошибке
    """
    try:
        url = "https://ru.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": query,
            "srlimit": num_results,
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        results = []
        if "query" in data and "search" in data["query"]:
            for item in data["query"]["search"]:
                title = item.get("title", "")
                snippet = re.sub(
                    r"<[^>]+>", "", item.get("snippet", "")
                )  # Убираем HTML теги
                url = (
                    f"https://ru.wikipedia.org/wiki/{title.replace(' ', '_')}"
                )

                results.append({"title": title, "href": url, "body": snippet})

        print(f"Wikipedia: успешно получено {len(results)} результатов")
        return results
    except Exception as e:
        print(f"Ошибка при поиске в Wikipedia: {e}")
        return []


def web_search(query, num_results=3, search_engines=None):
    """Выполняет поиск через несколько поисковых систем с механизмом резервирования.

    Args:
        query: Поисковый запрос
        num_results: Количество результатов (по умолчанию: 3)
        search_engines: Список поисковых движков для использования
                      (по умолчанию все доступные)

    Returns:
        Список результатов поиска
    """
    if search_engines is None:
        # Изменен порядок поисковых движков: сначала Wikipedia, затем другие
        search_engines = ["wikipedia", "duckduckgo", "google"]

    all_results = []

    for engine in search_engines:
        if len(all_results) >= num_results:
            break

        try:
            engine_results = []
            if engine == "duckduckgo":
                engine_results = search_duckduckgo(query, num_results)
            elif engine == "google":
                engine_results = search_google_serper(query, num_results)
            elif engine == "wikipedia":
                engine_results = search_wikipedia(query, num_results)

            # Добавляем источник к результатам
            for result in engine_results:
                result["source"] = engine

            all_results.extend(engine_results)
        except Exception as e:
            print(f"Ошибка при поиске через {engine}: {e}")
            # Продолжаем поиск с другими движками
            continue

    # Возвращаем только запрошенное количество результатов
    return all_results[:num_results] if all_results else []


def analyze_with_mistral(search_results, query, model="mistral-large-2411"):
    """Анализирует результаты поиска с помощью Mistral AI.

    Args:
        search_results: Результаты поиска
        query: Поисковый запрос
        model: Модель Mistral AI (по умолчанию: mistral-large-2411)

    Returns:
        Анализ результатов поиска
    """
    if not search_results:
        return "Не удалось найти результаты по вашему запросу."

    try:
        api_key = setup_environment()
        client = MistralClient(api_key=api_key)

        # Формируем промпт с результатами поиска
        prompt = f"""
Пользователь выполнил поиск по запросу: "{query}"

Вот результаты поиска:

{json.dumps(search_results, ensure_ascii=False, indent=2)}

Пожалуйста, проанализируй эти результаты и предоставь:
1. Краткую сводку основной информации
2. Ключевые факты, найденные в результатах
3. Любые противоречия или несоответствия, если они есть
4. Рекомендации для дальнейшего изучения вопроса
"""

        messages = [ChatMessage(role="user", content=prompt)]

        try:
            chat_response = client.chat(
                model=model,
                messages=messages,
            )

            return chat_response.choices[0].message.content
        except Exception as e:
            # Более подробный вывод ошибки для отладки
            error_msg = (
                f"Ошибка при запросе к Mistral API для анализа: {str(e)}"
            )
            print(error_msg)

            # В случае проблем с API вернуть базовый ответ
            return f"Не удалось выполнить анализ с помощью AI. Найдено {len(search_results)} результатов по запросу: '{query}'."
    except Exception as e:
        print(f"Критическая ошибка при настройке Mistral API: {str(e)}")
        return "Произошла ошибка при подготовке анализа результатов."


# Тестовый код для проверки модуля веб-поиска
if __name__ == "__main__":
    import sys

    query = (
        "Солнечные батареи для частного дома"
        if len(sys.argv) < 2
        else sys.argv[1]
    )
    results = web_search(query, num_results=3)

    if results:
        print(f"\nНайдено {len(results)} результатов:")
        for i, result in enumerate(results, 1):
            print(
                f"\n{i}. {result.get('title', 'Без заголовка')} ({result.get('source', 'Неизвестный источник')})"
            )
            print(f"   URL: {result.get('href', 'Нет ссылки')}")
            print(f"   {result.get('body', 'Нет описания')[:200]}...")

        analysis = analyze_with_mistral(results, query)
        print("\nАнализ результатов:")
        print(analysis)
    else:
        print("Не удалось найти результаты по запросу")
