from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler
import logging
import os

# Получаем путь к корневой директории проекта
PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# Создание папок для логов, если они не существуют
log_dirs = {
    "info": os.path.join(PROJECT_ROOT, "logs/logs_info"),
    "error": os.path.join(PROJECT_ROOT, "logs/logs_error"),
    "warning": os.path.join(PROJECT_ROOT, "logs/logs_warning"),
}

for dir in log_dirs.values():
    if not os.path.exists(dir):
        os.makedirs(dir)


# Добавление StreamHandler для вывода в терминал
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
)

# Настройка логирования
info_handler = TimedRotatingFileHandler(
    filename=os.path.join(
        log_dirs["info"],
        "logs_info.log"
    ),
    when='M',
    interval=1,
    backupCount=30,
    encoding="utf-8",
    delay=False,
    utc=False,
)
info_handler.setLevel(logging.DEBUG)
info_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
)

error_handler = RotatingFileHandler(
    os.path.join(
        log_dirs["error"],
        "logs_error.log"
    ),
    encoding="utf-8"
)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
)

warning_handler = RotatingFileHandler(
    os.path.join(
        log_dirs["warning"],
        "logs_warning.log"
    ),
    encoding="utf-8"
)
warning_handler.setLevel(logging.WARNING)
warning_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
)


# Основной логгер
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Установите уровень логирования для логгера
logger.addHandler(info_handler)
logger.addHandler(error_handler)
logger.addHandler(warning_handler)
logger.addHandler(console_handler)

# Логирование SQLAlchemy
logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG) 