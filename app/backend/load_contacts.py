"""
Скрипт для загрузки контактных данных в базу данных PostgreSQL.
Данные берутся из результатов скрипта osint.py.
"""
import os
import sys
import json
import argparse
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import insert

# Добавляем корневую директорию проекта в PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config.logging_config import logger
from config.env_config import get_env_var

# Настройка подключения к базе данных
def get_db_engine():
    """
    Создает и возвращает SQLAlchemy engine для работы с базой данных.
    Использует параметры подключения из переменных окружения.
    
    Returns:
        sqlalchemy.engine.Engine: Объект для работы с базой данных
    """
    db_url = get_env_var("DATABASE_URL")
    if not db_url:
        # Формируем URL из отдельных параметров, если DATABASE_URL не указан
        db_user = get_env_var("POSTGRES_USER", "postgres")
        db_pass = get_env_var("POSTGRES_PASSWORD", "postgres")
        db_host = get_env_var("POSTGRES_HOST", "localhost")
        db_port = get_env_var("POSTGRES_PORT", "5432")
        db_name = get_env_var("POSTGRES_DB", "energy_db")
        
        db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    
    logger.info(f"Подключение к базе данных: {db_url.replace(':'.join(db_url.split(':')[2:]).split('@')[0], '***:***')}")
    return create_engine(db_url)

def load_osint_data(file_path):
    """
    Загружает данные из файла результатов osint.py.
    
    Args:
        file_path (str): Путь к файлу с результатами osint.py
        
    Returns:
        pandas.DataFrame: DataFrame с загруженными данными
    """
    logger.info(f"Загрузка данных из файла: {file_path}")
    
    # Определяем формат файла по расширению
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if file_ext == '.json':
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        df = pd.DataFrame(data)
    elif file_ext == '.csv':
        df = pd.read_csv(file_path)
    else:
        raise ValueError(f"Неподдерживаемый формат файла: {file_ext}. Поддерживаются .json и .csv")
    
    logger.info(f"Загружено {len(df)} записей")
    return df

def process_data(df):
    """
    Обрабатывает данные перед загрузкой в базу данных.
    
    Args:
        df (pandas.DataFrame): Исходные данные
        
    Returns:
        pandas.DataFrame: Обработанные данные
    """
    # Убедимся, что все необходимые колонки присутствуют
    required_columns = ['account_id', 'phone', 'email', 'url1', 'url2', 'comment']
    existing_columns = df.columns.tolist()
    
    # Создаем недостающие колонки
    for col in required_columns:
        if col not in existing_columns:
            df[col] = None
    
    # Очистка и нормализация данных
    if 'phone' in df.columns:
        # Удаляем нетелефонные символы и нормализуем формат
        df['phone'] = df['phone'].astype(str).str.replace(r'[^\d+]', '', regex=True)
    
    if 'email' in df.columns:
        # Приводим email к нижнему регистру
        df['email'] = df['email'].astype(str).str.lower()
    
    return df[required_columns]

def bulk_insert_contacts(engine, data_df):
    """
    Выполняет пакетную вставку данных в таблицу contacts с обработкой дубликатов.
    
    Args:
        engine (sqlalchemy.engine.Engine): SQLAlchemy engine
        data_df (pandas.DataFrame): DataFrame с данными для вставки
        
    Returns:
        tuple: (количество добавленных записей, количество обновленных записей)
    """
    if data_df.empty:
        logger.warning("Нет данных для вставки")
        return 0, 0
    
    # Преобразуем DataFrame в список словарей
    records = data_df.to_dict('records')
    
    inserted = 0
    updated = 0
    
    try:
        with engine.connect() as conn:
            # Подготавливаем upsert запрос с обработкой конфликтов
            table_name = 'contacts'
            
            # Разбиваем на пакеты по 1000 записей для эффективной вставки
            batch_size = 1000
            for i in range(0, len(records), batch_size):
                batch = records[i:i+batch_size]
                
                # Конструируем запрос insert ... on conflict (UPSERT)
                stmt = insert(text(table_name)).values(batch)
                
                # Указываем, что делать при конфликте (обновляем существующие записи)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['account_id', 'phone', 'email'],
                    set_={
                        'url1': stmt.excluded.url1,
                        'url2': stmt.excluded.url2,
                        'comment': stmt.excluded.comment,
                        'updated_at': text('CURRENT_TIMESTAMP')
                    }
                )
                
                result = conn.execute(stmt)
                
                # Подсчитываем добавленные и обновленные записи
                if hasattr(result, 'rowcount'):
                    batch_count = result.rowcount
                    # В PostgreSQL rowcount содержит общее количество затронутых строк
                    # Мы не можем точно определить, сколько вставлено, а сколько обновлено
                    inserted += batch_count
                
                conn.commit()
                
                logger.info(f"Обработано {i+len(batch)}/{len(records)} записей")
            
            logger.info(f"Всего записей обработано: {inserted}")
            
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при вставке данных: {str(e)}")
        raise
    
    return inserted, updated

def parse_args():
    """
    Парсинг аргументов командной строки.
    
    Returns:
        argparse.Namespace: Аргументы командной строки
    """
    parser = argparse.ArgumentParser(
        description='Загрузка контактных данных из результатов osint.py в базу данных PostgreSQL'
    )
    
    parser.add_argument(
        '--input', 
        type=str, 
        required=True,
        help='Путь к файлу с результатами osint.py (JSON или CSV)'
    )
    
    return parser.parse_args()

def main():
    """
    Основная функция скрипта.
    """
    args = parse_args()
    
    try:
        # Получаем подключение к базе данных
        engine = get_db_engine()
        
        # Загружаем данные из файла
        data_df = load_osint_data(args.input)
        
        # Обрабатываем данные
        processed_df = process_data(data_df)
        
        # Вставляем данные в базу
        inserted, updated = bulk_insert_contacts(engine, processed_df)
        
        logger.info(f"Загрузка данных успешно завершена. Добавлено/обновлено {inserted} записей.")
        return 0
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении скрипта: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())