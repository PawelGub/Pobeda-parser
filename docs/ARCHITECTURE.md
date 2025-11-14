
### **2. docs/ARCHITECTURE.md**
```markdown
# 🏗 System Architecture

## Компоненты системы

### Backend Services
- **app.py** - Основное FastAPI приложение
- **flight_service.py** - Парсинг API Победы
- **anywhere_service.py** - AI поиск "Куда угодно"
- **city_service.py** - Управление городами
- **background_service.py** - Фоновые задачи

### Data Layer
- **PostgreSQL** - Основная база данных (рейсы, города, кеш)
- **Redis** - Кеширование запросов, сессии
- **Elasticsearch** - Логи, поиск, аналитика

### Event System
- **Kafka** - Центральная шина событий
- **Topics:** 
  - `search-events` - запросы поиска
  - `price-updates` - обновления цен
  - `error-logs` - ошибки системы
  - `user-analytics` - аналитика пользователей

### Monitoring
- **ELK Stack** - Логирование и поиск
- **Grafana** - Визуализация метрик
- **Kafka UI** - Мониторинг Kafka

## Потоки данных

1. **Поиск рейсов**:
User → Frontend → Backend → Pobeda API → Redis Cache → User
↓
Kafka (search-events) → Elasticsearch (logs)

2. **Поиск "Куда угодно"**:
User → Backend → City Service → Multiple Pobeda API calls →
Aggregate results → Sort by price → User
↓
Kafka (analytics) → Redis (cache)

3. **Фоновые задачи**:
Scheduler → Background Service → Update popular routes →
PostgreSQL + Redis Cache
↓
Kafka (price-updates)