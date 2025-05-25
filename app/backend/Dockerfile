# Этап 1: Сборка
FROM python:3.12-slim AS builder

WORKDIR /build

# Создание виртуального окружения
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Установка зависимостей для сборки
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Обновление pip и инструментов сборки
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Копирование файла с зависимостями
COPY requirements.txt .

# Сборка wheels из зависимостей
RUN pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements.txt

# Этап 2: Финальный образ
FROM python:3.12-slim

# Установка необходимых системных пакетов для запуска
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Создание и настройка виртуального окружения
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Копирование и установка wheels из этапа сборки
COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# Создание непривилегированного пользователя
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Настройка рабочей директории
WORKDIR /app

# Копирование кода приложения
COPY . .

# Копирование и настройка entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Создание директорий для логов с правильными правами
RUN mkdir -p /app/logs/logs_info /app/logs/logs_error /app/logs/logs_warning && \
    chown -R appuser:appuser /app /app/logs

# Настройка переменных окружения Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Порт, который будет прослушивать приложение
EXPOSE 8003

# Использование entrypoint и cmd
ENTRYPOINT ["/entrypoint.sh"]

# Переключение на непривилегированного пользователя
USER appuser

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]