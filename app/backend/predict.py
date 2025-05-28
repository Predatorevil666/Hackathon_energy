import os
import pickle
import sys

from typing import Any, Optional

import boto3
import pandas as pd

from botocore.exceptions import ClientError

# Добавляем корневую директорию проекта в sys.path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
)

from config.logging_config import logger
from config.models_config import (
    COMMERCIAL_THRESHOLD,
    FALLBACK_THRESHOLD,
    MINIO_ACCESS_KEY,
    MINIO_BUCKET,
    MINIO_ENDPOINT,
    MINIO_SECRET_KEY,
    MODEL_KEY,
    TMP_MODEL_PATH,
)


class ModelLoader:
    """
    Класс для ленивой загрузки ML-модели из S3/MinIO хранилища
    с кэшированием в памяти.
    """

    _instance: Optional["ModelLoader"] = None
    _model: Any = None

    def __new__(cls, *args, **kwargs):
        """Реализация паттерна Singleton для класса ModelLoader."""
        if cls._instance is None:
            cls._instance = super(ModelLoader, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        model_key: str = MODEL_KEY,
        bucket: str = MINIO_BUCKET,
        endpoint_url: str = MINIO_ENDPOINT,
        aws_access_key_id: str = MINIO_ACCESS_KEY,
        aws_secret_access_key: str = MINIO_SECRET_KEY,
    ):
        """
        Инициализирует загрузчик модели.

        Args:
            model_key: Ключ модели в S3/MinIO
            bucket: Имя бакета S3/MinIO
            endpoint_url: URL S3/MinIO
            aws_access_key_id: Ключ доступа
            aws_secret_access_key: Секретный ключ
        """
        if not self._initialized:
            self.model_key = model_key
            self.bucket = bucket
            self.endpoint_url = endpoint_url
            self.aws_access_key_id = aws_access_key_id
            self.aws_secret_access_key = aws_secret_access_key
            self._initialized = True

    def _get_s3_client(self):
        """
        Создает клиент для S3/MinIO.

        Returns:
            boto3.client: Клиент S3
        """
        return boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
        )

    def _get_model_path(self):
        """
        Генерирует локальный путь для сохранения модели.

        Returns:
            str: Путь к файлу модели
        """
        return os.path.join(TMP_MODEL_PATH, os.path.basename(self.model_key))

    def load_model(self):
        """
        Загружает модель из S3/MinIO.

        Returns:
            object: Объект модели

        Raises:
            Exception: При ошибке загрузки модели
        """
        if self._model is not None:
            logger.debug("Using cached model")
            return self._model

        try:
            s3_client = self._get_s3_client()
            model_path = self._get_model_path()

            logger.info(
                f"Downloading model from {self.bucket}/{self.model_key}"
            )
            s3_client.download_file(self.bucket, self.model_key, model_path)

            logger.info(f"Loading model from {model_path}")
            with open(model_path, "rb") as f:
                self._model = pickle.load(f)

            logger.info("Model loaded successfully")
            return self._model

        except ClientError as e:
            logger.error(f"Error downloading model: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            return None

    def get_model(self):
        """
        Получает модель, загружая ее при необходимости.

        Returns:
            object: Объект модели или None в случае ошибки
        """
        try:
            return self.load_model()
        except Exception as e:
            logger.error(f"Failed to get model: {str(e)}")
            return None


def predict_records(data: pd.DataFrame) -> pd.DataFrame:
    """
    Выполнение предсказаний для набора данных.

    Args:
        data: DataFrame с данными для предсказания

    Returns:
        pd.DataFrame: DataFrame с результатами предсказаний

    Raises:
        RuntimeError: При ошибке предсказания
    """
    try:
        # Подготовка данных
        df = data.copy()

        # Расчет годового потребления
        df["total"] = df["consumption"].apply(
            lambda x: sum(float(value) for value in x.values())
        )

        # Ленивая загрузка модели
        model_loader = ModelLoader()
        model = model_loader.get_model()

        # В случае отсутствия модели используем простую логику
        if model is None:
            logger.warning("Model not available, using fallback logic")
            df["probability"] = df["total"].apply(
                lambda x: 0.9 if x > FALLBACK_THRESHOLD else 0.1
            )
            df["isCommercial"] = df["probability"] > COMMERCIAL_THRESHOLD
        else:
            # Применение реальной модели
            try:
                X = df[
                    ["total"]
                ]  # В реальном проекте здесь будет больше признаков
                df["probability"] = model.predict_proba(X)[:, 1]
                df["isCommercial"] = df["probability"] > COMMERCIAL_THRESHOLD
                logger.info(f"Predictions made for {len(df)} records")
            except Exception as e:
                logger.error(f"Error making predictions with model: {str(e)}")
                # Фолбэк на простую логику
                df["probability"] = df["total"].apply(
                    lambda x: 0.9 if x > FALLBACK_THRESHOLD else 0.1
                )
                df["isCommercial"] = df["probability"] > COMMERCIAL_THRESHOLD

        # Округляем вероятности для удобства представления
        df["probability"] = df["probability"].round(3)

        # Возвращаем только необходимые колонки
        return df[["accountId", "isCommercial", "probability"]]

    except Exception as e:
        logger.error(f"Error in predict_records: {str(e)}")
        raise RuntimeError(f"Failed to make predictions: {str(e)}")


# Функция для загрузки модели в S3/MinIO при необходимости
def upload_model_to_s3(
    local_model_path: str,
    model_key: str = MODEL_KEY,
    bucket: str = MINIO_BUCKET,
    endpoint_url: str = MINIO_ENDPOINT,
    aws_access_key_id: str = MINIO_ACCESS_KEY,
    aws_secret_access_key: str = MINIO_SECRET_KEY,
) -> bool:
    """
    Загрузка модели в S3/MinIO.

    Args:
        local_model_path: Локальный путь к файлу модели
        model_key: Ключ (путь) для сохранения модели в S3/MinIO
        bucket: Имя бакета S3/MinIO
        endpoint_url: URL эндпоинта S3/MinIO
        aws_access_key_id: Ключ доступа для S3/MinIO
        aws_secret_access_key: Секретный ключ для S3/MinIO

    Returns:
        bool: True, если загрузка прошла успешно

    Raises:
        Exception: При ошибке загрузки
    """
    try:
        logger.info(
            f"Uploading model from {local_model_path} to S3/MinIO bucket {bucket}"
        )
        s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )

        # Создаем бакет, если он не существует
        try:
            s3_client.head_bucket(Bucket=bucket)
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                logger.info(f"Creating bucket {bucket}")
                s3_client.create_bucket(Bucket=bucket)

        # Загрузка файла модели
        s3_client.upload_file(local_model_path, bucket, model_key)
        logger.info(
            f"Model successfully uploaded to s3://{bucket}/{model_key}"
        )
        return True
    except Exception as e:
        logger.error(f"Failed to upload model to S3/MinIO: {str(e)}")
        raise
