import json
import logging
import os
import re
import sys

import requests

from dotenv import load_dotenv

# Импортируем модуль открытых источников
try:
    from open_sources import check_address_all_sources

    OPEN_SOURCES_AVAILABLE = True
except ImportError:
    OPEN_SOURCES_AVAILABLE = False

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("address_checker")

# Загружаем переменные окружения
load_dotenv()

# Получаем API ключи из переменных окружения
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
DADATA_API_KEY = os.getenv("DADATA_API_KEY")
DADATA_SECRET_KEY = os.getenv("DADATA_SECRET_KEY")
TWOGIS_API_KEY = os.getenv("TWOGIS_API_KEY")

# Глобальная переменная для хранения последнего результата
last_result = {}


def load_json_data(file_path):
    """Загрузка данных из JSON файла"""
    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка при чтении JSON файла: {e}")
        sys.exit(1)


def clean_address_dadata(address):
    """Очистка и стандартизация адреса с помощью DaData API"""
    if not DADATA_API_KEY or not DADATA_SECRET_KEY:
        logger.warning(
            "DaData API ключи не найдены. Стандартизация адреса пропущена."
        )
        return {
            "is_available": False,
            "normalized_address": None,
            "data": None,
        }

    url = "https://cleaner.dadata.ru/api/v1/clean/address"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Token {DADATA_API_KEY}",
        "X-Secret": DADATA_SECRET_KEY,
    }
    data = [address]

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()

        if result and len(result) > 0:
            cleaned_data = result[0]
            return {
                "is_available": True,
                "normalized_address": cleaned_data.get("result"),
                "data": {
                    "source": address,
                    "result": cleaned_data.get("result"),
                    "type": cleaned_data.get("type"),
                    "fias_id": cleaned_data.get("fias_id"),
                    "fias_level": cleaned_data.get("fias_level"),
                    "house_type": cleaned_data.get("house_type"),
                    "house": cleaned_data.get("house"),
                    "flat_type": cleaned_data.get("flat_type"),
                    "flat": cleaned_data.get("flat"),
                    "region": cleaned_data.get("region"),
                    "city": cleaned_data.get("city"),
                    "settlement": cleaned_data.get("settlement"),
                    "street": cleaned_data.get("street"),
                    "postal_code": cleaned_data.get("postal_code"),
                    "qc": cleaned_data.get("qc"),
                },
            }
        return {"is_available": True, "normalized_address": None, "data": None}
    except Exception as e:
        logger.error(f"Ошибка при обращении к DaData API: {e}")
        return {
            "is_available": False,
            "normalized_address": None,
            "data": None,
        }


def search_organizations_2gis(address):
    """Поиск организаций по адресу через 2ГИС API"""
    if not TWOGIS_API_KEY:
        logger.warning("2ГИС API ключ не найден. Поиск организаций пропущен.")
        return {"is_available": False, "data": None}

    url = "https://catalog.api.2gis.ru/3.0/items"
    params = {
        "q": address,
        "fields": "items.point,items.address,items.name,items.rubrics",
        "key": TWOGIS_API_KEY,
        "type": "building",
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        result = response.json()

        if "result" in result and "items" in result["result"]:
            organizations = [
                {
                    "name": item.get("name"),
                    "address": item.get("address", {}).get("name"),
                    "type": item.get("rubrics", [{}])[0].get("name")
                    if item.get("rubrics")
                    else None,
                }
                for item in result["result"]["items"]
                if "name" in item
            ]
            return {
                "is_available": True,
                "data": {
                    "total": len(organizations),
                    "organizations": organizations,
                },
            }
        return {
            "is_available": True,
            "data": {"total": 0, "organizations": []},
        }
    except Exception as e:
        logger.error(f"Ошибка при обращении к 2ГИС API: {e}")
        return {"is_available": False, "data": None}


def check_address_in_fns(address):
    """Проверка адреса в реестре ФНС (эмуляция)"""
    # В реальном проекте здесь был бы запрос к API ФНС
    # или обработка открытых данных ФНС

    # Для демонстрации используем эвристики
    commercial_keywords = [
        "офис",
        "этаж",
        "бизнес[ -]центр",
        "бц",
        "торговый[ -]центр",
        "тц",
        "промзона",
        "промышленная[ -]зона",
        "технопарк",
        "индустриальный[ -]парк",
        "завод",
        "фабрика",
        "мануфактура",
        "предприятие",
        "база",
        "склад",
        "логистический[ -]центр",
        "деловой[ -]центр",
        "корпус",
    ]

    # Проверяем наличие ключевых слов, указывающих на коммерческую недвижимость
    address_lower = address.lower()
    found_keyword = None
    for keyword in commercial_keywords:
        if re.search(rf"\b{keyword}\b", address_lower):
            found_keyword = keyword
            break

    if found_keyword:
        return {
            "is_available": True,
            "data": {
                "found": True,
                "is_commercial": True,
                "match_reason": f"Найдено ключевое слово '{found_keyword}' в адресе",
            },
        }

    return {
        "is_available": True,
        "data": {
            "found": False,
            "is_commercial": False,
            "match_reason": "Не найдено коммерческих признаков в адресе",
        },
    }


def analyze_address_type(address, sources):
    """Анализ типа адреса на основе собранных данных"""
    # Начальная оценка
    is_commercial_prob = 0.5
    evidence = []

    # Анализ данных DaData
    dadata_info = (
        sources["dadata"]["data"]
        if sources["dadata"]["is_available"] and sources["dadata"]["data"]
        else None
    )
    if dadata_info:
        # Если есть квартира - вероятнее физическое лицо
        if dadata_info.get("flat"):
            is_commercial_prob -= 0.2
            evidence.append(
                f"Адрес содержит квартиру {dadata_info.get('flat')}"
            )

        # Если тип дома "дом" - вероятнее физическое лицо
        if dadata_info.get("house_type") == "д":
            is_commercial_prob -= 0.1
            evidence.append("Тип строения: жилой дом")

    # Анализ данных 2ГИС
    twogis_info = (
        sources["twogis"]["data"]
        if sources["twogis"]["is_available"] and sources["twogis"]["data"]
        else None
    )
    if twogis_info and twogis_info.get("total", 0) > 0:
        # Если по адресу найдены организации - вероятнее юр. лицо
        org_count = twogis_info.get("total", 0)
        is_commercial_prob += min(0.3, org_count * 0.1)
        evidence.append(f"По адресу найдено {org_count} организаций")

    # Анализ данных ФНС
    fns_info = (
        sources["fns"]["data"]
        if sources["fns"]["is_available"] and sources["fns"]["data"]
        else None
    )
    if fns_info and fns_info.get("found", False):
        is_commercial_prob += 0.3
        evidence.append(fns_info.get("match_reason", "Найдено в реестре ФНС"))

    # Учитываем распространенные признаки в самом адресе
    address_lower = address.lower()

    # Признаки жилого помещения
    if re.search(r"\bкв\.?\s*\d+\b|\bквартира\s*\d+\b", address_lower):
        is_commercial_prob -= 0.2
        evidence.append("Указана квартира - признак жилого помещения")

    # Признаки коммерческого помещения
    if re.search(
        r"\bофис\s*\d+\b|\bпомещение\s*\d+\b|\bэтаж\s*\d+\b|\bбизнес[-\s]центр\b|\bтц\b",
        address_lower,
    ):
        is_commercial_prob += 0.3
        evidence.append("Указаны признаки коммерческого помещения")

    # Устанавливаем границы вероятности
    is_commercial_prob = max(0.1, min(0.9, is_commercial_prob))

    # Формируем результат
    explanation = " ".join(evidence)
    is_commercial = is_commercial_prob > 0.5

    return {
        "is_commercial": is_commercial,
        "probability": round(is_commercial_prob, 2),
        "explanation": explanation,
        "confidence": is_commercial_prob,
    }


def analyze_address_with_mistral(address):
    """Анализ адреса с помощью Mistral AI"""
    if not MISTRAL_API_KEY:
        logger.warning(
            "MISTRAL_API_KEY не найден. Анализ с помощью AI пропущен."
        )
        return {"is_available": False, "data": None}

    prompt = f"""
    Проанализируй следующий адрес: "{address}" 
    
    Определи, является ли это адресом физического лица или юридического лица (организации).
    Оцени вероятность от 0 до 1.
    
    Ответ предоставь в формате JSON:
    {{
        "is_commercial": true/false,
        "probability": 0.x,
        "explanation": "краткое объяснение"
    }}
    
    Где is_commercial - true, если это адрес организации, и false, если физического лица.
    """

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
    }

    data = {
        "model": "mistral-large-2411",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 500,
    }

    try:
        logger.info("Отправляем запрос к Mistral API для анализа адреса...")
        response = requests.post(MISTRAL_API_URL, headers=headers, json=data)
        response.raise_for_status()

        # Обрабатываем ответ
        result = response.json()
        if "choices" in result:
            response_text = result["choices"][0]["message"]["content"]
            logger.info("Получен ответ от Mistral API")

            # Пытаемся извлечь JSON из ответа
            try:
                json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    result_data = json.loads(json_str)

                    if "is_commercial" in result_data:
                        return {"is_available": True, "data": result_data}
                    else:
                        logger.warning(
                            f"Неожиданный формат ответа API: {result_data}"
                        )
                else:
                    logger.warning("Не удалось извлечь JSON из ответа")
            except Exception as e:
                logger.error(f"Ошибка при обработке JSON: {e}")
        else:
            logger.warning(f"Неожиданный формат ответа API: {result}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка запроса: {e}")

    return {"is_available": False, "data": None}


def check_address(address_data):
    """Отправка адреса на проверку с использованием комбинации источников.

    Args:
        address_data: Словарь с адресом {"address": "..."}

    Returns:
        dict: Полный результат проверки с полями is_physical, is_commercial, probability, explanation и др.
    """
    global last_result
    last_result = {}  # Сбрасываем предыдущий результат

    # Получаем адрес
    address = address_data["address"]
    logger.info(f"Проверка адреса: {address}")

    # Собираем данные из разных источников
    logger.info("Получение данных из DaData...")
    dadata_result = clean_address_dadata(address)

    logger.info("Проверка в базе ФНС...")
    fns_result = check_address_in_fns(address)

    logger.info("Поиск организаций через 2ГИС...")
    twogis_result = search_organizations_2gis(address)

    # Дополнительный анализ с помощью Mistral AI
    logger.info("Запрос дополнительного анализа через Mistral AI...")
    mistral_result = analyze_address_with_mistral(address)

    # Проверка через открытые источники, если доступно
    open_sources_result = None
    if OPEN_SOURCES_AVAILABLE:
        logger.info(
            "Проверка через открытые источники (ФИАС, ФНС, Росреестр)..."
        )
        open_sources_result = check_address_all_sources(address)

    # Собираем все источники данных
    sources = {
        "dadata": {
            "name": "DaData",
            "is_available": dadata_result["is_available"],
            "data": dadata_result.get("data"),
        },
        "fns": {
            "name": "ФНС",
            "is_available": fns_result["is_available"],
            "data": fns_result.get("data"),
        },
        "twogis": {
            "name": "2ГИС",
            "is_available": twogis_result["is_available"],
            "data": twogis_result.get("data"),
        },
        "mistral": {
            "name": "Mistral AI",
            "is_available": mistral_result["is_available"],
            "data": mistral_result.get("data"),
        },
    }

    # Добавляем результаты из открытых источников, если доступны
    if OPEN_SOURCES_AVAILABLE and open_sources_result:
        # Добавляем результаты ФИАС
        if "fias" in open_sources_result["sources"]:
            sources["fias_open"] = {
                "name": "ФИАС (открытый)",
                "is_available": open_sources_result["sources"]["fias"][
                    "is_available"
                ],
                "data": open_sources_result["sources"]["fias"]["data"],
            }

        # Добавляем результаты ЕГРЮЛ/ЕГРИП ФНС
        if "fns" in open_sources_result["sources"]:
            sources["fns_open"] = {
                "name": "ФНС ЕГРЮЛ/ЕГРИП (открытый)",
                "is_available": open_sources_result["sources"]["fns"][
                    "is_available"
                ],
                "data": open_sources_result["sources"]["fns"]["data"],
            }

        # Добавляем результаты Росреестра
        if "rosreestr" in open_sources_result["sources"]:
            sources["rosreestr"] = {
                "name": "Росреестр",
                "is_available": open_sources_result["sources"]["rosreestr"][
                    "is_available"
                ],
                "data": open_sources_result["sources"]["rosreestr"]["data"],
            }

    # Анализируем собранные данные
    logger.info("Анализ собранных данных...")
    analysis_result = analyze_address_type(address, sources)

    # Определяем нормализованный адрес
    normalized_address = None
    if dadata_result["is_available"] and dadata_result["normalized_address"]:
        normalized_address = dadata_result["normalized_address"]
    elif (
        OPEN_SOURCES_AVAILABLE
        and open_sources_result
        and open_sources_result.get("normalized_address")
    ):
        normalized_address = open_sources_result["normalized_address"]

    # Объединяем результаты анализа
    final_result = {}

    if analysis_result:
        # Формируем итоговый результат на основе анализа данных
        is_commercial = analysis_result["is_commercial"]
        probability = analysis_result["probability"]
        explanation = analysis_result["explanation"]

        # Если есть результат от Mistral, добавляем его объяснение
        if mistral_result["is_available"] and mistral_result["data"]:
            mistral_data = mistral_result["data"]
            if "explanation" in mistral_data:
                explanation += f". Анализ AI: {mistral_data['explanation']}"

        # Если есть результат от открытых источников, добавляем его объяснение
        if (
            OPEN_SOURCES_AVAILABLE
            and open_sources_result
            and open_sources_result.get("explanation")
        ):
            explanation += (
                f". Открытые источники: {open_sources_result['explanation']}"
            )

            # Корректируем вероятность с учетом открытых источников
            if open_sources_result.get("probability") is not None:
                # Используем среднее значение вероятностей с весами
                # Даем открытым источникам вес 0.4, остальным 0.6
                probability = (
                    0.6 * probability
                    + 0.4 * open_sources_result["probability"]
                )
                probability = round(probability, 2)
                # Обновляем статус на основе скорректированной вероятности
                is_commercial = probability > 0.5

        # Формируем список источников для ответа API
        sources_list = []
        for key, source in sources.items():
            if source["is_available"]:
                confidence = None
                if (
                    key == "mistral"
                    and source["data"]
                    and "probability" in source["data"]
                ):
                    confidence = source["data"]["probability"]
                elif "confidence" in source.get("data", {}):
                    confidence = source["data"]["confidence"]

                sources_list.append(
                    {
                        "name": source["name"],
                        "is_available": True,
                        "data": source["data"],
                        "confidence": confidence,
                    }
                )

        # Формируем финальный результат
        final_result = {
            "is_physical": not is_commercial,
            "is_commercial": is_commercial,
            "probability": probability,
            "explanation": explanation,
            "normalized_address": normalized_address,
            "sources": sources_list,
        }
    else:
        logger.error("Не удалось выполнить анализ адреса")
        return None

    # Сохраняем результат в глобальной переменной
    last_result = final_result

    # Выводим результат
    is_physical = not final_result["is_commercial"]
    status = "Физическое лицо" if is_physical else "Юридическое лицо"
    logger.info(f"Адрес: {address}")
    logger.info(f"Статус: {status}")
    logger.info(
        f"Вероятность: {final_result.get('probability', 'Не указана')}"
    )
    logger.info(
        f"Объяснение: {final_result.get('explanation', 'Нет объяснения')}"
    )

    return final_result


if __name__ == "__main__":
    # Определяем директорию скрипта
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Получаем путь к файлу из аргументов или используем значение по умолчанию
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        # Используем test_address.json из директории скрипта
        json_file = os.path.join(script_dir, "test_address.json")

    logger.info(f"Проверка адреса из файла: {json_file}")
    address_data = load_json_data(json_file)

    result = check_address(address_data)

    if result is not None:
        status = (
            "Физическое лицо" if result["is_physical"] else "Юридическое лицо"
        )
        logger.info(f"Итоговый результат: {status}")
    else:
        logger.error("Не удалось определить статус лица")
