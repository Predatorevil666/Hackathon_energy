"""
Конфигурационный файл для настроек моделей и их загрузки.
"""

import os

# Настройки S3/MinIO по умолчанию
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "models")
MODEL_KEY = os.getenv("MODEL_KEY", "model.pkl")

# Путь для временного сохранения модели
TMP_MODEL_PATH = os.getenv("TMP_MODEL_PATH", "/tmp")

# Настройки предсказания
COMMERCIAL_THRESHOLD = os.getenv("COMMERCIAL_THRESHOLD", 0.5)
FALLBACK_THRESHOLD = os.getenv("FALLBACK_THRESHOLD", 10000)
