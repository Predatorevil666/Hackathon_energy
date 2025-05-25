"""
DAG для запуска ежемесячного пакетного предсказания коммерческих потребителей энергии.
"""
from datetime import datetime, timedelta
from pathlib import Path
import os

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.models import Variable
from airflow.utils.email import send_email
from airflow.exceptions import AirflowException

# Настройки по умолчанию для DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email': Variable.get('admin_email', 'admin@example.com'),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'provide_context': True,
}

# Путь к скрипту batch_predict.py относительно корня проекта
SCRIPT_PATH = os.path.join('{{ var.value.project_root }}', 'batch_predict.py')

# Путь к директории для хранения предсказаний
PREDS_DIR = os.path.join('{{ var.value.project_root }}', 'preds')

# Настройки S3/MinIO
MINIO_ENDPOINT = Variable.get('minio_endpoint', 'http://minio:9000')
MINIO_ACCESS_KEY = Variable.get('minio_access_key', 'minio')
MINIO_SECRET_KEY = Variable.get('minio_secret_key', 'minio123')
MINIO_BUCKET = Variable.get('minio_bucket', 'models')
MODEL_KEY = Variable.get('model_key', 'model.pkl')

# Путь к входным данным
INPUT_DATA_PATH = Variable.get('input_data_path', '/data/energy_consumption.csv')


def on_failure_callback(context):
    """Колбэк для обработки ошибок в DAG."""
    dag_id = context['dag'].dag_id
    task_id = context['task'].task_id
    execution_date = context['execution_date']
    exception = context.get('exception')
    
    subject = f"Airflow Alert: Ошибка в {dag_id}.{task_id}"
    html_content = f"""
    <h2>Произошла ошибка в DAG {dag_id}</h2>
    <p><b>Дата выполнения:</b> {execution_date}</p>
    <p><b>Задача:</b> {task_id}</p>
    <p><b>Ошибка:</b> {exception}</p>
    """
    
    send_email(
        to=default_args['email'],
        subject=subject,
        html_content=html_content
    )


def ensure_output_dir(ds, **kwargs):
    """
    Создает директорию для сохранения результатов предсказания.
    
    Args:
        ds: Строка с датой выполнения в формате YYYY-MM-DD
        kwargs: Дополнительные аргументы из контекста Airflow
    
    Returns:
        str: Путь к директории для сохранения результатов
    """
    # Создаем директорию на основе даты запуска
    date_format = datetime.strptime(ds, '%Y-%m-%d')
    year_month = date_format.strftime('%Y-%m')
    
    output_dir = os.path.join(PREDS_DIR, year_month)
    os.makedirs(output_dir, exist_ok=True)
    
    return output_dir


def generate_prediction_command(ds, **kwargs):
    """
    Генерирует команду для запуска скрипта batch_predict.py
    
    Args:
        ds: Строка с датой выполнения в формате YYYY-MM-DD
        kwargs: Дополнительные аргументы из контекста Airflow
    
    Returns:
        str: Команда для запуска скрипта
    """
    # Получаем директорию для сохранения результатов
    ti = kwargs['ti']
    output_dir = ti.xcom_pull(task_ids='ensure_output_dir')
    
    # Формируем имя выходного файла с датой
    date_format = datetime.strptime(ds, '%Y-%m-%d')
    output_filename = f"predictions_{date_format.strftime('%Y-%m-%d')}.csv"
    output_path = os.path.join(output_dir, output_filename)
    
    # Собираем команду для запуска скрипта
    command = f"""
    python {SCRIPT_PATH} \
    --input "{INPUT_DATA_PATH}" \
    --output "{output_path}" \
    --model-key "{MODEL_KEY}" \
    --bucket "{MINIO_BUCKET}" \
    --endpoint-url "{MINIO_ENDPOINT}" \
    --aws-access-key-id "{MINIO_ACCESS_KEY}" \
    --aws-secret-access-key "{MINIO_SECRET_KEY}"
    """
    
    return command


# Определение DAG
with DAG(
    'monthly_batch_predict',
    default_args=default_args,
    description='Ежемесячное предсказание коммерческих потребителей энергии',
    schedule_interval='0 0 1 * *',  # В полночь первого числа каждого месяца
    start_date=datetime(2023, 1, 1),
    catchup=False,
    tags=['energy', 'predictions', 'monthly'],
    on_failure_callback=on_failure_callback,
) as dag:
    
    # Задача 1: Проверка зависимостей и подготовка директории
    ensure_dir_task = PythonOperator(
        task_id='ensure_output_dir',
        python_callable=ensure_output_dir,
    )
    
    # Задача 2: Проверка доступности входных данных
    check_input_data = BashOperator(
        task_id='check_input_data',
        bash_command=f'test -f "{INPUT_DATA_PATH}" || (echo "Input file not found" && exit 1)',
    )
    
    # Задача 3: Генерация команды для запуска скрипта
    generate_command_task = PythonOperator(
        task_id='generate_prediction_command',
        python_callable=generate_prediction_command,
    )
    
    # Задача 4: Запуск предсказаний
    run_prediction_task = BashOperator(
        task_id='run_predictions',
        bash_command="{{ ti.xcom_pull(task_ids='generate_prediction_command') }}",
    )
    
    # Задача 5: Проверка результатов
    check_results_task = BashOperator(
        task_id='check_results',
        bash_command="""
        OUTPUT_DIR="{{ ti.xcom_pull(task_ids='ensure_output_dir') }}"
        ls -la $OUTPUT_DIR
        echo "Проверка выполнена успешно: $(date)"
        """,
    )
    
    # Определение зависимостей между задачами
    ensure_dir_task >> check_input_data >> generate_command_task >> run_prediction_task >> check_results_task


"""
Для тестирования DAG локально можно использовать скрипт test_dag.py:

```bash
# Проверка задачи ensure_output_dir
./test_dag.py --dag monthly_batch_predict.py --task ensure_output_dir --date 2023-05-01

# Проверка задачи generate_prediction_command
./test_dag.py --dag monthly_batch_predict.py --task generate_prediction_command --date 2023-05-01

# Запуск всего DAG (не запускает реальные команды, только показывает их)
airflow dags test monthly_batch_predict 2023-05-01
```

При использовании в реальном окружении Airflow, необходимо:
1. Установить переменные в Airflow UI или через CLI:
   - project_root: путь к корневой директории проекта
   - admin_email: email для уведомлений
   - input_data_path: путь к файлу с данными
   - minio_endpoint, minio_access_key, minio_secret_key: настройки S3/MinIO
   - minio_bucket, model_key: настройки модели

2. Убедиться, что скрипт batch_predict.py доступен по указанному пути
3. Настроить соединение с S3/MinIO в Airflow (если необходимо)
"""
