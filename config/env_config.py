import os
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла, если он существует
load_dotenv()

# Настройки приложения
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")


# Настройки базы данных
POSTGRES_DB = os.getenv("POSTGRES_DB", "hackathon_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres_password")


def get_env_var(var_name, default=None):
    """
    Получает значение переменной окружения.

    Args:
        var_name (str): Имя переменной окружения
        default (Any): Значение по умолчанию, если переменная не определена

    Returns:
        str: Значение переменной окружения или default
    """
    return os.environ.get(var_name, default)
