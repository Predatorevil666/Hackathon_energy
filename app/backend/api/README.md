# API Утилиты

В этом модуле реализованы три основные функциональности:

1. **Проверка адреса на принадлежность к физическому лицу** (`check_address.py`)
2. **Взаимодействие с Mistral AI через API** (`mistral_api.py`)
3. **Веб-поиск с анализом результатов через Mistral AI** (`mistral_web_search.py`)

## Установка

1. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

2. Создайте файл `.env` на основе `mistral.env.example` и добавьте в него ваш API ключ Mistral:
   ```
   MISTRAL_API_KEY=your_actual_api_key_here
   ```

## Использование

### 1. Проверка адреса

```bash
python check_address.py [путь_к_json_файлу]
```

Если путь к файлу не указан, используется файл `test_address.json` по умолчанию.

### 2. Взаимодействие с Mistral AI

```bash
python mistral_api.py --prompt "Ваш запрос здесь"
```

или

```bash
python mistral_api.py --file sample_prompt.txt
```

Параметры:
- `--prompt TEXT` - Текст промпта
- `--file PATH` - Путь к файлу с промптом
- `--model NAME` - Название модели Mistral (по умолчанию: mistral-medium)

### 3. Веб-поиск через Mistral AI

```bash
python mistral_web_search.py "Ваш поисковый запрос"
```

Параметры:
- `query` - Поисковый запрос
- `--results N` - Количество результатов для анализа (по умолчанию: 3)

## Примечания

- Для работы с API Mistral необходимо зарегистрироваться на [mistral.ai](https://mistral.ai/) и получить API ключ.
- Скрипт `check_address.py` требует запущенного API вашего проекта на `localhost:8003`.
- Веб-поиск выполняется с использованием DuckDuckGo без API ключа. В реальном проекте рекомендуется использовать платные API поиска, такие как Google Custom Search API или SerpApi. 