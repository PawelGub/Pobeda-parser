#!/bin/bash
set -e

echo "🚀 Pobeda Backend Entrypoint"

# Переходим в рабочую директорию
cd /app

# Функция для ожидания БД
wait_for_db() {
    echo "⏳ Waiting for PostgreSQL..."
    while ! nc -z postgres 5432; do
        sleep 1
    done
    echo "✅ PostgreSQL is ready!"
}

# Функция для принудительного обновления городов
force_update_cities() {
    echo "🔄 Force updating cities with main airports..."
    python force_update_cities.py
}

# Основной процесс
wait_for_db

# Создаем таблицы
echo "🔄 Creating database tables..."
python -c "
from database import create_tables
create_tables()
print('✅ Database tables created')
"

# Принудительно обновляем города
force_update_cities

# Запускаем приложение
echo "🎉 Starting FastAPI application..."
exec "$@"