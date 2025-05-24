# Airflow DAGs для Hackathon Energy

В этой директории содержатся DAGs для Apache Airflow, которые автоматизируют различные задачи и процессы проекта.

## Monthly Batch Prediction DAG

DAG `monthly_batch_predict` выполняет ежемесячное предсказание коммерческих потребителей энергии.

### Расписание
- Запускается в полночь первого числа каждого месяца
- Cron-выражение: `0 0 1 * *`

### Параметры
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

### Структура DAG
DAG состоит из следующих задач:

1. `ensure_output_dir` - создает директорию для сохранения результатов
2. `check_input_data` - проверяет наличие входного файла с данными
3. `generate_prediction_command` - генерирует команду для запуска скрипта
4. `run_predictions` - запускает скрипт предсказания
5. `check_results` - проверяет результаты

### Результаты
Результаты сохраняются в директории:
```
{project_root}/preds/{year}-{month}/predictions_{year}-{month}-{day}.csv
```

## Настройка

### Требования
- Apache Airflow 2.0+
- Python 3.10+
- Доступ к S3/MinIO для загрузки модели

### Установка
1. Поместите DAG-файлы в директорию `dags` вашего Airflow
2. Настройте переменные в Airflow через UI или CLI
3. Убедитесь, что скрипт `batch_predict.py` доступен по пути `{project_root}/batch_predict.py`

### Тестирование локально
Для тестирования DAG локально можно использовать:
```bash
# Проверка DAG
python -c "from airflow.models import DagBag; dag = DagBag().get_dag('monthly_batch_predict'); print(f'DAG Loading status: {dag is not None}')"

# Тестовый запуск задачи
airflow tasks test monthly_batch_predict ensure_output_dir 2023-01-01
``` 