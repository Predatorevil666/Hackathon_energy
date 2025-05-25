"""
API маршруты для проверки адресов с помощью Mistral AI и внешних источников данных.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import sys
import os
import logging
import json

# Настраиваем логирование
logger = logging.getLogger("address_check_api")

# Добавляем текущую директорию в путь импорта
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Импортируем функцию проверки адреса
try:
    from app.backend.api.check_address import check_address
except ImportError:
    try:
        from check_address import check_address
    except ImportError:
        raise ImportError("Не удалось импортировать модуль check_address")


# Модели данных для API
class AddressRequest(BaseModel):
    """Модель запроса для проверки адреса."""
    address: str = Field(..., description="Адрес для проверки", 
                        example="г. Москва, ул. Пушкина, д. 10, кв. 5")
    include_details: bool = Field(False, description="Включить подробную информацию из всех источников")


class Source(BaseModel):
    """Информация об источнике данных."""
    name: str = Field(..., description="Название источника данных")
    is_available: bool = Field(..., description="Доступность источника")
    data: Optional[Dict[str, Any]] = Field(None, description="Данные от источника")
    confidence: Optional[float] = Field(None, description="Уверенность источника (0-1)")


class AddressResponse(BaseModel):
    """Модель ответа с результатами проверки адреса."""
    is_physical: bool = Field(..., description="Физическое лицо (true) или юридическое (false)")
    is_commercial: bool = Field(..., description="Юридическое лицо (true) или физическое (false)")
    probability: float = Field(..., description="Вероятность определения (0-1)", ge=0, le=1)
    explanation: Optional[str] = Field(None, description="Объяснение результата")
    normalized_address: Optional[str] = Field(None, description="Нормализованный адрес")
    sources: Optional[List[Source]] = Field(None, description="Информация об использованных источниках")
    status: str = Field("success", description="Статус обработки запроса")

    class Config:
        json_schema_extra = {
            "example": {
                "is_physical": True,
                "is_commercial": False,
                "probability": 0.85,
                "explanation": "Адрес содержит квартиру 5. Тип строения: жилой дом.",
                "normalized_address": "г Москва, ул Пушкина, д 10, кв 5",
                "status": "success"
            }
        }


# Создаем API роутер
router = APIRouter(prefix="/address", tags=["Address Verification"])


@router.post("/check", response_model=AddressResponse, 
            summary="Проверка типа адреса",
            description="Проверяет адрес и определяет, принадлежит ли он физическому или юридическому лицу")
async def check_address_endpoint(request: AddressRequest):
    """
    Проверяет адрес и определяет, принадлежит ли он физическому или юридическому лицу.
    
    Использует комбинацию нескольких источников данных для повышения точности:
    - DaData API для стандартизации адреса
    - 2ГИС API для поиска организаций
    - ФНС для проверки в реестре юридических лиц
    - Mistral AI для семантического анализа
    - Открытые источники (ФИАС, Росреестр)
    
    Args:
        request: Запрос, содержащий адрес для проверки
        
    Returns:
        Результат проверки адреса с вероятностью и объяснением
    """
    try:
        # Подготавливаем данные в формате, ожидаемом функцией check_address
        address_data = {"address": request.address}
        
        # Вызываем функцию проверки адреса
        result = check_address(address_data)
        
        # Обрабатываем результат
        if result is None:
            raise HTTPException(
                status_code=500, 
                detail="Не удалось определить тип адреса"
            )
        
        # Логируем результат
        logger.info(f"Результат проверки адреса '{request.address}': {json.dumps(result, ensure_ascii=False)}")
        
        # Получаем данные из результата
        is_physical = result["is_physical"]
        is_commercial = result["is_commercial"]
        probability = result["probability"]
        explanation = result.get("explanation", "")
        normalized_address = result.get("normalized_address")
        
        logger.info(f"Формирование ответа: is_physical={is_physical}, is_commercial={is_commercial}, probability={probability}")
        
        # Формируем базовый ответ
        response_data = {
            "is_physical": is_physical,
            "is_commercial": is_commercial,
            "probability": probability,
            "explanation": explanation,
            "status": "success"
        }
        
        # Добавляем нормализованный адрес, если доступен
        if normalized_address:
            response_data["normalized_address"] = normalized_address
            
        # Если запрошены детали, добавляем информацию об источниках
        if request.include_details and "sources" in result:
            sources_list = []
            for src in result["sources"]:
                source_data = {
                    "name": src["name"],
                    "is_available": src["is_available"]
                }
                
                if "data" in src:
                    source_data["data"] = src["data"]
                
                if "confidence" in src:
                    source_data["confidence"] = src["confidence"]
                
                sources_list.append(source_data)
            
            response_data["sources"] = sources_list
        
        # Создаем ответ через модель
        response = AddressResponse(**response_data)
        
        # Логируем финальный ответ для отладки
        logger.info(f"Отправляем ответ: {json.dumps(response.dict(), ensure_ascii=False)}")
        
        return response
    except Exception as e:
        logger.error(f"Ошибка при проверке адреса: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Ошибка при проверке адреса: {str(e)}"
        )


@router.get("/check", response_model=AddressResponse,
          summary="Проверка типа адреса (GET метод)",
          description="GET-версия метода проверки адреса")
async def check_address_get(
    address: str = Query(..., description="Адрес для проверки", 
                        example="г. Москва, ул. Пушкина, д. 10, кв. 5"),
    include_details: bool = Query(False, description="Включить подробную информацию")
):
    """GET-версия метода проверки адреса"""
    request = AddressRequest(address=address, include_details=include_details)
    return await check_address_endpoint(request) 