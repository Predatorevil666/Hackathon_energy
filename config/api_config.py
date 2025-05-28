"""
Конфигурационный файл для настроек API.
"""

import os

# Настройки API
API_TITLE = "Energy Consumption Predictor API"
API_DESCRIPTION = (
    "API для предсказания типа потребителя энергии на основе данных потребления"
)
API_VERSION = "1.0.0"

# Настройки среды
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Настройки CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
CORS_METHODS = ["GET", "POST", "OPTIONS"]
CORS_HEADERS = ["Content-Type", "Authorization"]
