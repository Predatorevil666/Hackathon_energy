from typing import Dict, Optional

from pydantic import BaseModel


class Record(BaseModel):
    """
    Модель данных для запроса предсказаний.
    """

    accountId: int
    roomsCount: Optional[int] = None
    residentsCount: Optional[int] = None
    buildingType: Optional[str] = None
    consumption: Dict[str, float]  # {"1": 3484, "2": 2216, ... "12": 3000}


class PredictionResponse(BaseModel):
    """
    Модель данных для ответа с предсказаниями.
    
    Attributes:
        accountId (int): Идентификатор аккаунта
        isCommercial (bool): Признак коммерческого помещения
        probability (float): Вероятность предсказания (0-1)
        explanation (Optional[str]): Объяснение результата предсказания
        normalized_address (Optional[str]): Нормализованный адрес
        sources (Optional[List[Dict]]): Список источников данных с их результатами
        status (str): Статус обработки запроса
    """

    accountId: int
    isCommercial: bool
    probability: float
