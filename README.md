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
   pip install -r requirements.txt
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

### Использование API

API будет доступен по адресу http://localhost:8000

Документация Swagger доступна по адресу http://localhost:8000/docs

**Пример запроса для предсказания:**
```bash
curl -X POST "http://localhost:8000/predict" \
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

## 📊 Airflow DAGs

В проекте настроены DAG для Apache Airflow, автоматизирующие регулярные задачи.

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
│   │   ├── dags          # Airflow DAGs
│   │   ├── tests         # Тесты
│   │   ├── main.py       # Точка входа FastAPI
│   │   ├── models.py     # Pydantic модели
│   │   └── predict.py    # Логика предсказаний
│   └── frontend          # Frontend (будет добавлен позже)
├── config                # Конфигурационные файлы
├── logs                  # Логи
├── batch_predict.py      # Скрипт пакетного предсказания
├── docker-compose.yml    # Конфигурация Docker Compose
├── requirements.txt      # Python зависимости
└── env.example           # Пример переменных окружения
```

## 🤝 Команда разработчиков

- [@predatorevil666](https://github.com/predatorevil666) - Backend, DevOps, Airflow
- [@krasava1702](https://github.com/krasava1702) - Frontend
- [@mk1MoreBugs](https://github.com/mk1MoreBugs) - ETL, ML, обработка данных

