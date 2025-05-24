from pydantic import BaseModel
from typing import Dict, List, Optional


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
    """
    accountId: int
    isCommercial: bool
    probability: float 