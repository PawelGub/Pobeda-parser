# 🔌 API Documentation

## Основные эндпоинты

### Поиск рейсов

GET /flights/search?origin=MOW&destination=LED&promo_code=XYZ

Ответ:

json
{
  "origin": "Москва",
  "destination": "Санкт-Петербург", 
  "total_days": 30,
  "flights": [...]
}

Поиск "Куда угодно"
GET /flights/anywhere?origin=MOW&months_ahead=3&max_price=10000
Ответ(пример):
{
  "origin": "MOW",
  "total_destinations_found": 45,
  "cheapest_flights": [
    {
      "destination": "KZN",
      "min_price": 2499,
      "cheapest_date": "2024-11-15",
      "destination_name_ru": "Казань"
    }
  ]
}


Графики цен

GET /flights/charts?origin=MOW&destination=LED

Технические эндпоинты
GET / - Health check

GET /test-db - Тест базы данных

GET /test-redis - Тест Redis

GET /test-kafka - Тест Kafka

GET /admin/status - Статус системы