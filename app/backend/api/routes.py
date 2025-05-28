"""
API маршруты для взаимодействия с Mistral AI.
"""

import os
import sys

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, validator

# Добавляем текущую директорию в путь импорта
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Импортируем функции из существующих скриптов
try:
    from mistral_api import query_mistral, setup_environment
    from mistral_web_search import analyze_with_mistral, web_search
except ImportError:
    try:
        from app.backend.api.mistral_api import (
            query_mistral,
            setup_environment,
        )
        from app.backend.api.mistral_web_search import (
            analyze_with_mistral,
            web_search,
        )
    except ImportError:
        raise ImportError(
            "Не удалось импортировать модули mistral_api и mistral_web_search"
        )

# Импортируем маршруты для проверки адресов
try:
    from check_address_routes import router as address_router

    has_address_api = True
except ImportError:
    try:
        from app.backend.api.check_address_routes import (
            router as address_router,
        )

        has_address_api = True
    except ImportError:
        print(
            "Модуль check_address_routes не найден, маршруты проверки адресов будут недоступны"
        )
        has_address_api = False

# Создаем API роутер
router = APIRouter(prefix="/mistral", tags=["Mistral AI"])


# Модели данных для API
class MistralRequest(BaseModel):
    """Модель запроса к Mistral API."""

    prompt: str
    model: Optional[str] = "mistral-large-2411"


class WebSearchRequest(BaseModel):
    """Модель запроса для веб-поиска."""

    query: str
    num_results: Optional[int] = 3
    model: Optional[str] = "mistral-large-2411"
    search_engines: Optional[List[str]] = None

    # Добавляем валидатор для query
    @validator("query")
    def query_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Поисковый запрос не может быть пустым")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Солнечные батареи",
                "num_results": 3,
                "model": "mistral-large-2411",
                "search_engines": ["wikipedia", "duckduckgo", "google"],
            }
        }


class MistralResponse(BaseModel):
    """Модель ответа от Mistral API."""

    response: str


class WebSearchResponse(BaseModel):
    """Модель ответа от веб-поиска."""

    results: List[Dict[str, Any]]
    analysis: str
    results_count: Optional[int] = None
    search_query: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "title": "Пример результата",
                        "href": "https://example.com",
                        "body": "Описание результата",
                        "source": "wikipedia",
                    }
                ],
                "analysis": "Анализ результатов поиска",
                "results_count": 1,
                "search_query": "Пример запроса",
            }
        }


# Маршруты API
@router.post("/query", response_model=MistralResponse)
async def process_mistral_query(request: MistralRequest):
    """
    Отправляет запрос к Mistral AI и возвращает ответ.

    Args:
        request: Запрос, содержащий prompt и model

    Returns:
        Ответ от Mistral AI
    """
    try:
        # Проверяем наличие API ключа
        setup_environment()

        # Получаем ответ от Mistral
        response = query_mistral(request.prompt, model=request.model)

        return MistralResponse(response=response)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при запросе к Mistral API: {str(e)}",
        )


@router.post("/web-search", response_model=WebSearchResponse)
async def process_web_search(request: WebSearchRequest):
    """
    Выполняет веб-поиск и анализирует результаты с помощью Mistral AI.

    Args:
        request: Запрос, содержащий query, num_results и model

    Returns:
        Результаты поиска и их анализ
    """
    # Добавляем отладочное логирование
    print(
        f"DEBUG: Получен запрос веб-поиска: query='{request.query}', num_results={request.num_results}, search_engines={request.search_engines}"
    )

    # Проверяем корректность параметра search_engines
    if request.search_engines and (
        len(request.search_engines) == 1
        and request.search_engines[0] == "string"
    ):
        print(
            "DEBUG: Обнаружен некорректный параметр search_engines=['string'], устанавливаем значение None"
        )
        request.search_engines = None

    try:
        # Проверяем наличие API ключа
        try:
            setup_environment()
        except Exception as e:
            print(f"Ошибка при настройке окружения: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Ошибка при настройке API ключа. Проверьте наличие MISTRAL_API_KEY",
            )

        # Выполняем поиск
        try:
            search_results = web_search(
                request.query,
                num_results=request.num_results,
                search_engines=request.search_engines,
            )
            print(
                f"DEBUG: Получены результаты поиска: {len(search_results)} результатов"
            )
        except Exception as e:
            print(f"Ошибка при выполнении веб-поиска: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Произошла ошибка при выполнении поиска. Попробуйте изменить параметры поиска.",
            )

        if not search_results:
            print(
                f"DEBUG: Поиск не дал результатов для запроса '{request.query}'"
            )
            # Возвращаем 200 OK вместо 404 Not Found для пустых результатов
            return WebSearchResponse(
                results=[],
                analysis="Поиск не дал результатов по вашему запросу.",
                results_count=0,
                search_query=request.query,
            )

        # Анализируем результаты
        analysis = analyze_with_mistral(
            search_results, request.query, model=request.model
        )
        print(
            f"DEBUG: Анализ результатов выполнен, длина анализа: {len(analysis)} символов"
        )

        response = WebSearchResponse(
            results=search_results,
            analysis=analysis,
            results_count=len(search_results),
            search_query=request.query,
        )
        print(f"DEBUG: Отправляем ответ: {len(response.results)} результатов")
        return response
    except HTTPException:
        # Пробрасываем HTTPException дальше
        raise
    except ValueError as e:
        # Обрабатываем ошибки валидации
        print(f"DEBUG: Ошибка валидации: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        print(f"Непредвиденная ошибка при обработке запроса: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при выполнении веб-поиска: {str(e)}",
        )
