#!/usr/bin/env python
"""
Скрипт для пакетного предсказания коммерческих потребителей энергии.
Использует модель из S3/MinIO хранилища для предсказания.
"""

import os
import argparse
import pandas as pd
import sys

# Добавление корневого каталога в sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config.logging_config import logger
from predict import ModelLoader, predict_records


def load_data(input_path: str) -> pd.DataFrame:
    """
    Загружает данные для предсказания из CSV или JSON файла.

    Args:
        input_path: Путь к входному файлу

    Returns:
        DataFrame с данными для предсказания
    """
    logger.info(f"Загрузка данных из {input_path}")

    file_ext = os.path.splitext(input_path)[1].lower()

    if file_ext == ".csv":
        df = pd.read_csv(input_path)
    elif file_ext == ".json":
        df = pd.read_json(input_path)
    else:
        raise ValueError(
            f"Неподдерживаемый формат файла: {file_ext}. Поддерживаются: .csv, .json"
        )

    # Проверка наличия обязательных колонок
    required_cols = ["accountId", "consumption"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"В данных отсутствует обязательная колонка: {col}")

    # Если consumption в виде строки, преобразуем в словарь
    if df["consumption"].dtype == "object" and isinstance(
        df["consumption"].iloc[0], str
    ):
        import json

        df["consumption"] = df["consumption"].apply(json.loads)

    logger.info(f"Загружены данные по {len(df)} потребителям")
    return df


def save_predictions(predictions: pd.DataFrame, output_path: str) -> None:
    """
    Сохраняет результаты предсказаний в указанный путь.

    Args:
        predictions: DataFrame с результатами предсказаний
        output_path: Путь для сохранения результатов
    """
    logger.info(f"Сохранение результатов в {output_path}")

    # Создаем директорию, если не существует
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Определяем формат файла
    file_ext = os.path.splitext(output_path)[1].lower()

    # Сохраняем в соответствующем формате
    if file_ext == ".csv":
        predictions.to_csv(output_path, index=False)
    elif file_ext == ".json":
        predictions.to_json(output_path, orient="records")
    else:
        # По умолчанию сохраняем в CSV
        if not output_path.endswith(".csv"):
            output_path = f"{output_path}.csv"
        predictions.to_csv(output_path, index=False)

    logger.info(f"Результаты сохранены: {len(predictions)} предсказаний")

    # Выводим статистику по предсказаниям
    commercial_count = predictions["isCommercial"].sum()
    logger.info(
        f"Обнаружено коммерческих потребителей: {commercial_count} "
        f"({commercial_count / len(predictions) * 100:.1f}%)"
    )


def parse_args():
    """
    Парсинг аргументов командной строки.

    Returns:
        argparse.Namespace: Аргументы командной строки
    """
    parser = argparse.ArgumentParser(
        description="Пакетное предсказание коммерческих потребителей энергии"
    )

    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Путь к входному файлу с данными (CSV или JSON)",
    )

    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Путь для сохранения результатов предсказаний",
    )

    # Параметры для S3/MinIO
    parser.add_argument(
        "--model-key", type=str, default="model.pkl", help="Ключ модели в S3/MinIO"
    )

    parser.add_argument(
        "--bucket", type=str, default="models", help="Имя бакета S3/MinIO"
    )

    parser.add_argument(
        "--endpoint-url", type=str, default="http://localhost:9000", help="URL S3/MinIO"
    )

    parser.add_argument(
        "--aws-access-key-id", type=str, default="minio", help="Ключ доступа S3/MinIO"
    )

    parser.add_argument(
        "--aws-secret-access-key",
        type=str,
        default="minio123",
        help="Секретный ключ S3/MinIO",
    )

    return parser.parse_args()


def main():
    """
    Основная функция скрипта.
    """
    args = parse_args()

    try:
        # Загрузка данных
        df = load_data(args.input)

        # Инициализация загрузчика модели
        model_loader = ModelLoader(
            model_key=args.model_key,
            bucket=args.bucket,
            endpoint_url=args.endpoint_url,
            aws_access_key_id=args.aws_access_key_id,
            aws_secret_access_key=args.aws_secret_access_key,
        )

        # Проверка, что модель загружена
        model = model_loader.get_model()
        if model is None:
            logger.warning(
                "Модель не загружена, будет использована логика по умолчанию"
            )
        else:
            logger.info("Модель успешно загружена")

        # Выполнение предсказаний
        logger.info("Выполнение предсказаний...")
        predictions = predict_records(df)

        # Сохранение результатов
        save_predictions(predictions, args.output)

        logger.info("Пакетное предсказание успешно завершено")
        return 0

    except Exception as e:
        logger.error(f"Ошибка при выполнении пакетного предсказания: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
