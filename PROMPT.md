
### **5. PROMPT.md** (для нейросетей)
```markdown
# 🤖 Pobeda Parser - Context for AI Assistance

## Project Context
Это полнофункциональная платформа для парсинга авиабилетов авиакомпании "Победа" с AI-поиском направлений.

## Core Architecture
- **Backend**: FastAPI + PostgreSQL + Redis + Kafka
- **Frontend**: Vanilla JS (пока) с планами перехода на React
- **Infrastructure**: Docker + Kubernetes + ELK
- **Key Feature**: "Куда угодно" - поиск самых дешевых направлений

## Current File Structure

PobedaParser/
├── backend/
│ ├── app.py # FastAPI main (работает)
│ ├── models.py # SQLAlchemy models
│ ├── flight_service.py # Pobeda API parsing (работает)
│ ├── anywhere_service.py # "Куда угодно" логика (работает)
│ ├── city_service.py # City management (работает)
│ ├── background_service.py # Background tasks
│ ├── database.py # DB config (работает)
│ ├── config.py # Settings (работает)
│ └── requirements.txt # Python dependencies
├── k8s/ # Kubernetes manifests
│ ├── pobeda-deployment.yml # Backend deployment (обновлен)
│ ├── postgres.yml # PostgreSQL (работает)
│ ├── redis.yml # Redis cache (новый)
│ ├── kafka.yml # Kafka broker (новый)
│ ├── zookeeper.yml # Zookeeper (новый)
│ ├── elasticsearch.yml # Elasticsearch (работает)
│ └── kafka-ui.yml # Kafka web UI (новый)
└── docker-compose.full.yml # Full stack compose


## Current Status
✅ **Работает**: Backend API, PostgreSQL, Elasticsearch, базовый поиск  
🔄 **В разработке**: Redis кеширование, Kafka события, мониторинг  
📋 **Планируется**: React фронтенд, Grafana, CI/CD, продвинутая аналитика

## Key Services Description
- **flight_service.py**: Парсит API Победы, кеширует результаты
- **anywhere_service.py**: Ищет самые дешевые направления из города
- **city_service.py**: Управляет списком городов и направлениями
- **app.py**: Основное FastAPI приложение с эндпоинтами

## Development Principles
- Используем асинхронное программирование (async/await)
- Кешируем всё что можно в Redis
- Все события пишем в Kafka для аналитики
- Мониторинг через ELK + Grafana
- Масштабируемая микросервисная архитектура

## When Assisting With Code
- Сохраняй существующую архитектуру
- Добавляй логирование в Kafka
- Используй Redis для кеширования
- Документируй новые функции
- Тестируй с существующими сервисами