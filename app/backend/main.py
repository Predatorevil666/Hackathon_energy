from fastapi import FastAPI, HTTPException
from typing import List
import sys
import os

# Добавление корневого каталога в sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

# Импорт моделей данных
try:
    from models import Record, PredictionResponse
except ImportError:
    try:
        from app.backend.models import Record, PredictionResponse
    except ImportError:
        raise ImportError("Не удалось импортировать модели данных")

import pandas as pd
# Импорт других модулей
try:
    from predict import predict_records
    from config.logging_config import logger
    from config.api_config import API_TITLE, API_DESCRIPTION, API_VERSION
except ImportError:
    try:
        from app.backend.predict import predict_records
        from app.backend.config.logging_config import logger
        from app.backend.config.api_config import API_TITLE, API_DESCRIPTION, API_VERSION
    except ImportError:
        raise ImportError("Не удалось импортировать необходимые модули")

# Импорт маршрутов Mistral API
try:
    from api.routes import router as mistral_router
    has_mistral_api = True
except ImportError:
    try:
        from app.backend.api.routes import router as mistral_router
        has_mistral_api = True
    except ImportError:
        try:
            logger.warning("Модуль Mistral API не найден, соответствующие маршруты будут недоступны")
        except:
            print("Модуль Mistral API не найден, соответствующие маршруты будут недоступны")
        has_mistral_api = False

# Импорт маршрутов для проверки адресов
try:
    from api.check_address_routes import router as address_router
    has_address_api = True
except ImportError:
    try:
        from app.backend.api.check_address_routes import router as address_router
        has_address_api = True
    except ImportError:
        try:
            logger.warning("Модуль проверки адресов не найден, соответствующие маршруты будут недоступны")
        except:
            print("Модуль проверки адресов не найден, соответствующие маршруты будут недоступны")
        has_address_api = False

# Настройка приложения
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
)

# Включение маршрутов Mistral, если они доступны
if has_mistral_api:
    app.include_router(mistral_router)
    try:
        logger.info("Маршруты Mistral API успешно добавлены")
    except:
        print("Маршруты Mistral API успешно добавлены")

# Включение маршрутов проверки адресов, если они доступны
if has_address_api:
    app.include_router(address_router)
    try:
        logger.info("Маршруты проверки адресов успешно добавлены")
    except:
        print("Маршруты проверки адресов успешно добавлены")


@app.get("/health", tags=["System"])
async def health():
    """
    Проверка состояния сервиса.
    
    Возвращает статус ok, если сервис работает.
    """
    return {"status": "ok"}


@app.get("/", tags=["System"])
async def root():
    """
    Получить информацию о сервисе.
    
    Возвращает базовую информацию о сервисе и его назначении.
    """
    return {
        "name": "Energy Consumption Predictor API",
        "version": "1.0.0",
        "description": "API для предсказания коммерческих потребителей энергии"
    }


@app.post("/predict", response_model=List[PredictionResponse], tags=["Prediction"])
async def predict(records: List[Record]):
    """
    Предсказать тип потребителя энергии.
    
    Принимает список записей с данными о потреблении энергии и возвращает 
    предсказания о том, является ли каждый потребитель коммерческим.
    
    Args:
        records: Список записей с данными о потреблении
        
    Returns:
        Список объектов PredictionResponse с результатами предсказаний
    """
    try:
        logger.info(f"Получен запрос на предсказание для {len(records)} объектов")
        
        if not records:
            logger.warning("Получен пустой список записей")
            return []
        
        # Конвертируем в DataFrame для обработки
        df = pd.DataFrame([r.model_dump() for r in records])
        
        # Выполняем предсказания
        results = predict_records(df)
        
        # Формируем ответ
        predictions = []
        for _, row in results.iterrows():
            predictions.append(
                PredictionResponse(
                    accountId=row["accountId"],
                    isCommercial=bool(row["isCommercial"]),
                    probability=float(row["probability"])
                )
            )
        
        logger.info(f"Предсказания выполнены успешно: {len(predictions)} результатов")
        return predictions
    
    except Exception as e:
        logger.error(f"Ошибка при выполнении предсказаний: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка обработки: {str(e)}") 