#!/usr/bin/env python
"""
Скрипт для тестирования DAG. 
Этот скрипт создает простую эмуляцию окружения Airflow и позволяет проверить
работоспособность DAG без полноценной установки Airflow.
"""
import sys
import os
import logging
from datetime import datetime
import importlib.util
import argparse
import json

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Настройка переменных окружения для имитации Airflow
os.environ['AIRFLOW_HOME'] = os.path.abspath(os.path.dirname(__file__))
os.environ['project_root'] = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')
)


def mock_airflow_variables():
    """Создает мок-объекты для Airflow"""
    
    class MockVariable:
        """Мок для Airflow Variable"""
        @staticmethod
        def get(key, default=None):
            mock_values = {
                'project_root': os.environ.get('project_root'),
                'admin_email': 'test@example.com',
                'input_data_path': os.path.join(
                    os.environ.get('project_root'), 'test_data.csv'
                ),
                'minio_endpoint': 'http://localhost:9000',
                'minio_access_key': 'minioadmin',
                'minio_secret_key': 'minioadmin',
                'minio_bucket': 'test-bucket',
                'model_key': 'test_model.pkl'
            }
            return mock_values.get(key, default)
    
    class MockDAG:
        """Мок для Airflow DAG"""
        def __init__(self, *args, **kwargs):
            self.dag_id = kwargs.get('dag_id', 'test_dag')
            self.default_args = kwargs.get('default_args', {})
            self.schedule_interval = kwargs.get('schedule_interval')
            self.description = kwargs.get('description', '')
            self.tasks = []
    
    class MockOperator:
        """Мок для Airflow Operator"""
        def __init__(self, **kwargs):
            self.task_id = kwargs.get('task_id', 'test_task')
            self.dag = None
        
        def __rshift__(self, other):
            return self
    
    class MockPythonOperator(MockOperator):
        """Мок для PythonOperator"""
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.python_callable = kwargs.get('python_callable')
    
    class MockBashOperator(MockOperator):
        """Мок для BashOperator"""
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.bash_command = kwargs.get('bash_command')
    
    # Создаем моки модулей Airflow
    sys.modules['airflow'] = type('airflow', (), {})
    sys.modules['airflow.models'] = type('models', (), {'Variable': MockVariable})
    sys.modules['airflow.operators.python'] = type(
        'python', (), {'PythonOperator': MockPythonOperator}
    )
    sys.modules['airflow.operators.bash'] = type(
        'bash', (), {'BashOperator': MockBashOperator}
    )
    sys.modules['airflow.utils.email'] = type(
        'email', (), {'send_email': lambda **kwargs: None}
    )
    sys.modules['airflow.exceptions'] = type(
        'exceptions', (), {'AirflowException': Exception}
    )
    
    # Добавляем DAG в модуль airflow
    sys.modules['airflow'].DAG = MockDAG


def load_dag_file(file_path):
    """
    Загружает DAG из файла.
    
    Args:
        file_path: Путь к файлу с DAG
    
    Returns:
        module: Загруженный модуль
    """
    logger.info(f"Загрузка DAG из файла: {file_path}")
    
    # Проверяем, что файл существует
    if not os.path.exists(file_path):
        logger.error(f"Файл не найден: {file_path}")
        return None
    
    try:
        # Загружаем модуль из файла
        module_name = os.path.basename(file_path).replace('.py', '')
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        logger.info(f"DAG успешно загружен: {module_name}")
        return module
    except Exception as e:
        logger.error(f"Ошибка при загрузке DAG: {str(e)}")
        return None


def test_dag_task(dag_file_path, task_name, execution_date):
    """
    Тестирует конкретную задачу DAG.
    
    Args:
        dag_file_path: Путь к файлу с DAG
        task_name: Имя задачи для тестирования
        execution_date: Дата выполнения в формате YYYY-MM-DD
    """
    # Создаем мок-объекты Airflow
    mock_airflow_variables()
    
    # Загружаем модуль с DAG
    module = load_dag_file(dag_file_path)
    if not module:
        return
    
    # Ищем объект DAG в модуле
    dag = None
    for name, obj in vars(module).items():
        if isinstance(obj, sys.modules['airflow'].DAG):
            dag = obj
            break
    
    if not dag:
        logger.error("DAG не найден в модуле")
        return
    
    # Ищем задачу с указанным именем
    task = None
    for name, obj in vars(module).items():
        is_python = isinstance(
            obj, sys.modules['airflow.operators.python'].PythonOperator
        )
        is_bash = isinstance(
            obj, sys.modules['airflow.operators.bash'].BashOperator
        )
        if (is_python or is_bash) and obj.task_id == task_name:
            task = obj
            break
    
    if not task:
        logger.error(f"Задача {task_name} не найдена в DAG")
        return
    
    # Создаем контекст выполнения
    date_obj = datetime.strptime(execution_date, '%Y-%m-%d')
    context = {
        'dag': dag,
        'task': task,
        'execution_date': date_obj,
        'ds': execution_date,
        'ti': type('TaskInstance', (), {
            'xcom_pull': lambda task_ids: f"/tmp/test/{task_ids}",
            'xcom_push': lambda key, value: None
        })()
    }
    
    # Выполняем задачу
    logger.info(f"Запуск задачи {task_name} для даты {execution_date}")
    try:
        is_python = isinstance(
            task, sys.modules['airflow.operators.python'].PythonOperator
        )
        if is_python:
            result = task.python_callable(**context)
            logger.info(f"Результат выполнения задачи: {result}")
        else:
            logger.info(f"Команда для выполнения: {task.bash_command}")
            # Если это тест, мы не выполняем bash-команды
            logger.info("Это тестовый запуск, bash-команда не будет выполнена")
        
        logger.info(f"Задача {task_name} успешно выполнена")
    except Exception as e:
        logger.error(f"Ошибка при выполнении задачи: {str(e)}")


def main():
    """Основная функция."""
    parser = argparse.ArgumentParser(description='Тестирование DAG Airflow')
    parser.add_argument('--dag', required=True, help='Путь к файлу DAG')
    parser.add_argument('--task', required=True, help='Имя задачи для тестирования')
    parser.add_argument(
        '--date', 
        default=datetime.now().strftime('%Y-%m-%d'),
        help='Дата выполнения в формате YYYY-MM-DD'
    )
    
    args = parser.parse_args()
    
    test_dag_task(args.dag, args.task, args.date)


if __name__ == '__main__':
    main()

