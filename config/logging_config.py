from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler
import logging
import os
import sys

# Получаем путь к корневой директории проекта
PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# Настройка логгера
logger = logging.getLogger('hackathon_energy')
logger.setLevel(logging.INFO)

# Определяем, находимся ли мы в Docker-контейнере
IN_DOCKER = os.environ.get('PYTHONPATH', '').startswith('/app:/')

# Обработчик для вывода в консоль
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# Если мы не в Docker, настраиваем также запись в файлы
if not IN_DOCKER:
    # Создание папок для логов, если они не существуют
    log_dirs = {
        "info": os.path.join(PROJECT_ROOT, "logs/logs_info"),
        "error": os.path.join(PROJECT_ROOT, "logs/logs_error"),
        "warning": os.path.join(PROJECT_ROOT, "logs/logs_warning"),
    }

    for dir in log_dirs.values():
        if not os.path.exists(dir):
            os.makedirs(dir)

    # Настройка обработчиков для разных уровней логирования
    info_handler = TimedRotatingFileHandler(
        os.path.join(log_dirs["info"], "logs_info.log"),
        when="midnight",
        backupCount=7,
    )
    info_handler.setLevel(logging.INFO)
    info_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    info_handler.setFormatter(info_formatter)
    logger.addHandler(info_handler)

    error_handler = TimedRotatingFileHandler(
        os.path.join(log_dirs["error"], "logs_error.log"),
        when="midnight",
        backupCount=7,
    )
    error_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(exc_info)s')
    error_handler.setFormatter(error_formatter)
    logger.addHandler(error_handler)

    warning_handler = TimedRotatingFileHandler(
        os.path.join(log_dirs["warning"], "logs_warning.log"),
        when="midnight",
        backupCount=7,
    )
    warning_handler.setLevel(logging.WARNING)
    warning_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    warning_handler.setFormatter(warning_formatter)
    logger.addHandler(warning_handler)

# Логирование SQLAlchemy
logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG) 