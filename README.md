# Hackathon Energy

Проект для прогнозирования коммерческих потребителей энергии. Позволяет определять, является ли потребитель коммерческим на основе данных о потреблении энергии.

## 📋 Описание проекта

Система включает в себя:
- REST API на FastAPI для выполнения предсказаний в реальном времени
- Скрипт для пакетного предсказания (batch processing)
- DAG для Apache Airflow для автоматизации регулярных предсказаний
- Интеграцию с S3/MinIO для хранения ML-моделей
- MLflow для отслеживания экспериментов

## 🛠 Технологический стек

- **Backend**: Python, FastAPI
- **ML**: scikit-learn, pandas
- **Хранение**: MinIO/S3
- **Оркестрация**: Apache Airflow
- **CI/CD**: GitHub Actions
- **Контейнеризация**: Docker, Docker Compose

## 🚀 Быстрый старт

### Предварительные требования

- Python 3.12+
- Docker и Docker Compose
- Git

### Установка и запуск

1. Клонировать репозиторий:
   ```bash
   git clone https://github.com/yourusername/hackathon_energy.git
   cd hackathon_energy
   ```

2. Создать и активировать виртуальное окружение:
   ```bash
   python -m venv venv
   source venv/bin/activate  # На Windows: venv\Scripts\activate
   ```

3. Установить зависимости:
   ```bash
   pip install -r app/backend/requirements.txt
   ```

4. Настроить переменные окружения:
   ```bash
   cp env.example .env
   # Отредактировать .env файл при необходимости
   ```

5. Запустить с помощью Docker Compose:
   ```bash
   docker-compose up -d
   ```

### Docker Compose сервисы

Проект разворачивается с помощью Docker Compose и включает следующие сервисы:

| Сервис | Описание | Порт |
|--------|----------|------|
| backend | FastAPI приложение | 8003 |
| postgres | База данных PostgreSQL | 5432 |
| minio | Объектное хранилище S3-compatible | 9000 (API), 9001 (Web UI) |
| mlflow | Система отслеживания ML-экспериментов | 5000 |
| airflow-webserver | Веб-интерфейс Airflow | 8080 |
| airflow-scheduler | Планировщик задач Airflow | - |

### Использование API

API будет доступен по адресу http://localhost:8003

Документация Swagger доступна по адресу http://localhost:8003/docs

**Пример запроса для предсказания:**
```bash
curl -X POST "http://localhost:8003/predict" \
  -H "Content-Type: application/json" \
  -d '[{
    "accountId": 123,
    "roomsCount": 4,
    "residentsCount": 2,
    "buildingType": "apartment",
    "consumption": {
      "1": 150.0, "2": 140.0, "3": 160.0, "4": 165.0,
      "5": 170.0, "6": 190.0, "7": 200.0, "8": 210.0,
      "9": 180.0, "10": 170.0, "11": 160.0, "12": 155.0
    }
  }]'
```

### Пакетное предсказание

Для выполнения предсказаний над большим набором данных:

```bash
python batch_predict.py \
  --input data/input.csv \
  --output results/predictions.csv \
  --endpoint-url http://localhost:9000 \
  --aws-access-key-id minio \
  --aws-secret-access-key minio123
```

## 📊 Структура базы данных

### Таблица Contacts
Таблица `contacts` хранит контактные данные, собранные с помощью OSINT.

| Поле       | Тип           | Описание                               |
|------------|---------------|----------------------------------------|
| id         | SERIAL        | Первичный ключ                         |
| account_id | INTEGER       | ID аккаунта потребителя энергии        |
| phone      | VARCHAR(20)   | Номер телефона                         |
| email      | VARCHAR(255)  | Электронная почта                      |
| url1       | VARCHAR(512)  | Основной URL контакта                  |
| url2       | VARCHAR(512)  | Дополнительный URL контакта            |
| comment    | TEXT          | Комментарий или дополнительная информация |
| created_at | TIMESTAMP     | Дата и время создания записи           |
| updated_at | TIMESTAMP     | Дата и время последнего обновления     |

#### Индексы
- `idx_contacts_account_id` - для быстрого поиска по account_id
- `idx_contacts_phone` - для поиска по телефону
- `idx_contacts_email` - для поиска по email

## 🐳 Docker

### Особенности Docker-конфигурации

- **Многоэтапная сборка**: Оптимизирует размер образов и повышает безопасность
- **Непривилегированный пользователь**: Контейнеры запускаются от имени `appuser` для безопасности
- **Монтирование логов**: Логи сохраняются в директории `logs` на хосте
- **Entrypoint**: Обеспечивает корректную настройку прав доступа для логов

### Полезные команды Docker

```bash
# Запуск сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f backend

# Доступ к контейнеру под пользователем appuser
docker-compose exec backend bash

# Доступ к контейнеру под root для администрирования
docker-compose exec -u root backend bash

# Применение SQL-скриптов к базе данных
docker-compose exec postgres psql -U postgres -d energy_db -f /docker-entrypoint-initdb.d/create_contacts_table.sql
```

## 📥 Загрузка данных

### Загрузка контактных данных из OSINT

Для загрузки контактных данных используйте скрипт `load_contacts.py`:

```bash
python app/backend/load_contacts.py --input path/to/osint_results.json
```

#### Поддерживаемые форматы
- JSON: содержит массив объектов с полями account_id, phone, email и т.д.
- CSV: содержит колонки account_id, phone, email и т.д.

#### Обработка дубликатов
Скрипт автоматически обрабатывает дубликаты, обновляя существующие записи новыми данными.

## 📊 Airflow DAGs

В проекте настроены DAG для Apache Airflow, автоматизирующие регулярные задачи.

### Расположение компонентов Airflow

Airflow интегрирован в проект через Docker Compose и имеет следующую структуру:

- DAG-файлы: `app/backend/airflow/dags/`
- Логи: `app/backend/airflow/logs/`
- Плагины: `app/backend/airflow/plugins/`
- Конфигурация: `app/backend/airflow/config/`

Веб-интерфейс Airflow доступен по адресу http://localhost:8080 (логин/пароль: admin/admin)

### Monthly Batch Prediction DAG

DAG `monthly_batch_predict` выполняет ежемесячное предсказание коммерческих потребителей энергии.

#### Расписание
- Запускается в полночь первого числа каждого месяца
- Cron-выражение: `0 0 1 * *`

#### Параметры
DAG использует следующие переменные Airflow:

| Переменная | Описание | Значение по умолчанию |
|------------|----------|----------------------|
| `project_root` | Путь к корневой директории проекта | - |
| `input_data_path` | Путь к входному файлу с данными | `/data/energy_consumption.csv` |
| `admin_email` | Email для уведомлений | `admin@example.com` |
| `minio_endpoint` | URL-адрес MinIO/S3 | `http://minio:9000` |
| `minio_access_key` | Ключ доступа MinIO/S3 | `minio` |
| `minio_secret_key` | Секретный ключ MinIO/S3 | `minio123` |
| `minio_bucket` | Имя бакета в MinIO/S3 | `models` |
| `model_key` | Ключ модели в MinIO/S3 | `model.pkl` |

#### Структура DAG
DAG состоит из следующих задач:

1. `ensure_output_dir` - создает директорию для сохранения результатов
2. `check_input_data` - проверяет наличие входного файла с данными
3. `generate_prediction_command` - генерирует команду для запуска скрипта
4. `run_predictions` - запускает скрипт предсказания
5. `check_results` - проверяет результаты

#### Результаты
Результаты сохраняются в директории:
```
{project_root}/preds/{year}-{month}/predictions_{year}-{month}-{day}.csv
```

## 🧪 Разработка и тестирование

### Запуск тестов

```bash
cd app/backend
pytest
```

### Локальное тестирование Airflow DAG

```bash
# Проверка DAG
python -c "from airflow.models import DagBag; dag = DagBag().get_dag('monthly_batch_predict'); print(f'DAG Loading status: {dag is not None}')"

# Тестовый запуск задачи
airflow tasks test monthly_batch_predict ensure_output_dir 2023-01-01
```

## 📚 Структура проекта

```
├── app
│   ├── backend            # FastAPI приложение
│   │   ├── api/          # API модули 
│   │   │   ├── check_address.py        # Модуль проверки адресов
│   │   │   ├── check_address_routes.py # Маршруты для проверки адресов
│   │   │   ├── open_sources.py         # Интеграция с открытыми источниками данных
│   │   │   ├── mistral_api.py          # Интеграция с Mistral AI
│   │   │   ├── routes.py               # Основные маршруты API
│   │   │   └── ...
│   │   ├── airflow/      # Компоненты Airflow
│   │   │   ├── dags/     # DAG-файлы Airflow
│   │   │   ├── logs/     # Логи Airflow
│   │   │   ├── plugins/  # Плагины Airflow
│   │   │   └── config/   # Конфигурация Airflow
│   │   ├── dags/         # Резервная копия DAG-файлов
│   │   ├── tests/        # Тесты
│   │   ├── main.py       # Точка входа FastAPI
│   │   ├── models.py     # Pydantic модели
│   │   ├── predict.py    # Логика предсказаний
│   │   ├── load_contacts.py # Загрузка контактных данных
│   │   ├── entrypoint.sh # Entrypoint скрипт для Docker
│   │   └── Dockerfile    # Dockerfile для backend
│   └── frontend          # Frontend (будет добавлен позже)
├── config                # Конфигурационные файлы
├── database              # SQL-скрипты
│   └── create_contacts_table.sql # Создание таблицы contacts
├── logs                  # Логи приложения
├── batch_predict.py      # Скрипт пакетного предсказания
├── docker-compose.yml    # Конфигурация Docker Compose
├── requirements.txt      # Python зависимости (основные)
└── env.example           # Пример переменных окружения
```

## 🤖 Система проверки адресов

### 📋 Описание

Система определяет, принадлежит ли адрес физическому или юридическому лицу. Она использует многоуровневый подход, интегрируя данные из нескольких источников:

1. **DaData API** - стандартизация и нормализация адресов
2. **ФНС (ЕГРЮЛ/ЕГРИП)** - проверка в реестре юридических лиц
3. **2ГИС API** - поиск организаций по адресу
4. **Mistral AI** - семантический анализ адреса
5. **Открытые источники данных**:
   - **ФИАС** - Федеральная информационная адресная система
   - **Росреестр** - данные о типе недвижимости
   - **Открытые данные ФНС** - распознавание признаков коммерческих адресов

### 🚀 Использование

#### Через Swagger UI

1. Запустите сервер:
   ```bash
   cd app/backend
   python -m uvicorn main:app --reload --port 8003
   ```

2. Откройте Swagger UI в браузере: `http://localhost:8003/docs`

3. Найдите раздел "Address Verification" и выберите метод `/address/check`

4. Нажмите "Try it out" и введите адрес для проверки:
   ```json
   {
     "address": "г. Москва, ул. Пушкина, д. 10, кв. 5",
     "include_details": true
   }
   ```

5. Нажмите "Execute" для отправки запроса

#### Через API запросы

##### POST запрос:
```bash
curl -X POST "http://localhost:8003/address/check" \
  -H "Content-Type: application/json" \
  -d '{"address": "г. Москва, Ленинский проспект, д. 15, офис 301", "include_details": true}'
```

##### GET запрос:
```bash
curl -X GET "http://localhost:8003/address/check?address=г.%20Москва,%20ул.%20Ленина,%20д.%2010,%20кв.%205&include_details=true"
```

### 📊 Формат ответа

```json
{
  "is_physical": false,          // Физическое лицо (true) или юридическое (false)
  "is_commercial": true,         // Юридическое лицо (true) или физическое (false)
  "probability": 0.94,           // Вероятность принадлежности к юр. лицу (0-1)
  "explanation": "Найдено ключевое слово 'офис' в адресе...", // Объяснение результата
  "normalized_address": "г Москва, Ленинский проспект, д 15, офис 301",
  "sources": [                   // Информация об использованных источниках
    {
      "name": "DaData",
      "is_available": true,
      "data": { ... },
      "confidence": 0.9
    },
    ...
  ],
  "status": "success"            // Статус обработки запроса
}
```



### 🔧 Настройка

1. Создайте файл `.env` в директории `app/backend/api` с ключами API:
   ```
   MISTRAL_API_KEY=your_mistral_api_key
   DADATA_API_KEY=your_dadata_api_key
   DADATA_SECRET_KEY=your_dadata_secret_key
   TWOGIS_API_KEY=your_2gis_api_key
   FIAS_API_KEY=your_fias_api_key
   FNS_API_TOKEN=your_fns_api_token
   ROSREESTR_API_KEY=your_rosreestr_api_key
   ```


   ```

### 📈 Точность

- **Точность системы**: 95% (по сравнению с 80% при использовании только AI)
- Система успешно обрабатывает сложные случаи (адреса смешанного использования)
- Предоставляет подробное объяснение результатов

### 🏗 Архитектура

Система построена по модульному принципу:

- `check_address.py` - основной модуль для проверки адресов
- `check_address_routes.py` - API маршруты
- `open_sources.py` - интеграция с открытыми источниками данных
- `test_*.py` - модули тестирования

### 🔍 Примеры

#### Жилой адрес
```
г. Москва, ул. Ленина, д. 10, кв. 5
```
Результат: Физическое лицо (вероятность: 0.18)

#### Коммерческий адрес
```
г. Москва, Ленинский проспект, д. 15, офис 301
```
Результат: Юридическое лицо (вероятность: 0.94)

#### Промышленный адрес
```
г. Москва, Хорошевское шоссе, д. 38, промзона
```
Результат: Юридическое лицо (вероятность: 0.68)

## 🤝 Команда разработчиков

- [@predatorevil666](https://github.com/predatorevil666) - Backend, DevOps, Airflow
- [@krasava1702](https://github.com/krasava1702) - Frontend
- [@mk1MoreBugs](https://github.com/mk1MoreBugs) - ETL, ML, обработка данных