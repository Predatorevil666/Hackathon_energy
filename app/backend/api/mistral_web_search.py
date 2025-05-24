#!/usr/bin/env python3
import argparse
import requests
import time
import os
import sys
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Определяем пути
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Загружаем переменные окружения из .env файла в корне проекта
load_dotenv(dotenv_path=os.path.join(ROOT_DIR, '.env'))

# Импортируем mistral_api
try:
    import mistral_api
except ImportError:
    # Если не удается импортировать как модуль, импортируем из текущей директории
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import mistral_api


def search_web(query, num_results=5):
    """
    Выполняет поиск в Интернете по заданному запросу.
    
    Args:
        query (str): Поисковый запрос
        num_results (int): Количество результатов для возврата
        
    Returns:
        list: Список словарей с результатами поиска
    """
    # Используем бесплатный API SerpApi или подобный сервис для поиска
    # В демо-версии используем DuckDuckGo без API ключа
    search_url = f"https://html.duckduckgo.com/html/?q={query}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # Парсим результаты поиска
        search_results = soup.select('.result')
        for i, result in enumerate(search_results[:num_results]):
            title_elem = result.select_one('.result__title')
            link_elem = result.select_one('.result__url')
            snippet_elem = result.select_one('.result__snippet')
            
            title = title_elem.get_text().strip() if title_elem else "Нет заголовка"
            link = link_elem.get_text().strip() if link_elem else "Нет ссылки"
            snippet = snippet_elem.get_text().strip() if snippet_elem else "Нет описания"
            
            results.append({
                "title": title,
                "link": link,
                "snippet": snippet
            })
            
        return results
    
    except Exception as e:
        print(f"Ошибка при поиске: {e}")
        return []


def fetch_content(url):
    """
    Получает содержимое веб-страницы по URL.
    
    Args:
        url (str): URL страницы для получения
        
    Returns:
        str: Текстовое содержимое страницы
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Удаляем скрипты, стили и другие ненужные элементы
        for script in soup(["script", "style", "meta", "noscript", "iframe"]):
            script.extract()
        
        # Получаем текст страницы
        text = soup.get_text(separator=' ', strip=True)
        
        # Удаляем лишние пробелы и переносы строк
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines 
                  for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Ограничиваем длину текста
        return text[:5000]  # Ограничиваем 5000 символами
    
    except Exception as e:
        print(f"Ошибка при получении содержимого страницы {url}: {e}")
        return ""


def mistral_web_search(query, num_results=3):
    """
    Выполняет веб-поиск и использует Mistral AI для анализа результатов.
    
    Args:
        query (str): Поисковый запрос
        num_results (int): Количество результатов для анализа
        
    Returns:
        str: Ответ от Mistral AI с анализом результатов поиска
    """
    print(f"Выполняем поиск по запросу: '{query}'")
    search_results = search_web(query, num_results)
    
    if not search_results:
        return "Не удалось найти результаты по вашему запросу"
    
    # Собираем информацию из результатов поиска
    content_text = ""
    for i, result in enumerate(search_results):
        print(f"Обрабатываем результат {i+1}/{len(search_results)}: "
              f"{result['title']}")
        content_text += f"\n--- Результат {i+1} ---\n"
        content_text += f"Заголовок: {result['title']}\n"
        content_text += f"URL: {result['link']}\n"
        content_text += f"Описание: {result['snippet']}\n"
        
        # Пытаемся получить полное содержимое страницы
        try:
            if result['link'].startswith(('http://', 'https://')):
                page_content = fetch_content(result['link'])
                if page_content:
                    content_text += f"Содержимое: {page_content[:1000]}...\n"
        except Exception as e:
            print(f"Ошибка при получении содержимого: {e}")
        
        # Пауза между запросами
        time.sleep(1)
    
    # Формируем промпт для Mistral AI
    prompt = f"""
    Вот результаты поиска по запросу: "{query}"
    
    {content_text}
    
    Пожалуйста, проанализируй эту информацию и предоставь структурированный ответ
    на основе найденных данных. Объедини информацию из различных источников,
    выдели ключевые факты и предоставь полезный ответ на запрос.
    """
    
    print("Отправляем данные для анализа в Mistral AI...")
    response = mistral_api.send_prompt_to_mistral(prompt)
    
    if response and "choices" in response:
        return response["choices"][0]["message"]["content"]
    else:
        return "Не удалось получить анализ от Mistral AI"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Веб-поиск с анализом через Mistral AI"
    )
    parser.add_argument(
        "query", nargs="?", type=str, help="Поисковый запрос"
    )
    parser.add_argument(
        "--results", type=int, default=3,
        help="Количество результатов для анализа"
    )
    
    args = parser.parse_args()
    
    search_query = args.query
    if not search_query:
        search_query = input("Введите поисковый запрос: ")
    
    result = mistral_web_search(search_query, args.results)
    
    print("\nРезультат анализа от Mistral AI:")
    print("-" * 50)
    print(result)
    print("-" * 50) 