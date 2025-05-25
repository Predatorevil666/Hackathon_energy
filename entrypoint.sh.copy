#!/bin/bash
set -e

# Проверка прав доступа к директориям логов
if [ ! -w "/app/logs" ]; then
    echo "Warning: No write permission to /app/logs, trying to create directories..."
    # Пытаемся создать директории, но игнорируем ошибки
    mkdir -p /app/logs/logs_info /app/logs/logs_error /app/logs/logs_warning || true
    # Пытаемся изменить владельца, но игнорируем ошибки
    chown -R appuser:appuser /app/logs || echo "Could not change ownership of logs directory, continuing anyway"
fi

# Запустить переданную команду
exec "$@" 