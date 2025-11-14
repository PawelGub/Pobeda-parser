from typing import List, Dict
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uvicorn
import asyncio
import logging
import redis
from kafka import KafkaProducer, KafkaConsumer
import json
import time
import subprocess
import threading
from flight_service import FlightService

logger = logging.getLogger(__name__)

from database import get_db, create_tables
from config import settings

# Глобальные клиенты (инициализируются в lifespan)
redis_client = None
kafka_producer = None
KAFKA_ENABLED = False


def start_kafka_services():
    """Запускает Zookeeper и Kafka в фоновых процессах"""

    def run_zookeeper():
        try:
            process = subprocess.Popen(
                [
                    "/kafka/bin/zookeeper-server-start.sh",
                    "/kafka/config/zookeeper.properties",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            logger.info("✅ Zookeeper started")
            return process
        except Exception as e:
            logger.error(f"❌ Failed to start Zookeeper: {e}")
            return None

    def run_kafka():
        try:
            # Ждем немного чтобы Zookeeper запустился
            time.sleep(10)
            process = subprocess.Popen(
                ["/kafka/bin/kafka-server-start.sh", "/kafka/config/server.properties"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            logger.info("✅ Kafka started")
            return process
        except Exception as e:
            logger.error(f"❌ Failed to start Kafka: {e}")
            return None

    # Запускаем в отдельных потоках
    import threading

    zk_thread = threading.Thread(target=run_zookeeper, daemon=True)
    kafka_thread = threading.Thread(target=run_kafka, daemon=True)

    zk_thread.start()
    kafka_thread.start()

    logger.info("🚀 Kafka services starting in background threads...")


async def init_redis():
    """Инициализация Redis с повторными попытками"""
    global redis_client
    max_retries = 5
    for i in range(max_retries):
        try:
            redis_client = redis.Redis(host="redis", port=6379, decode_responses=True, socket_connect_timeout=5)
            redis_client.ping()
            logger.info("✅ Redis connected successfully")
            return True
        except Exception as e:
            logger.warning(f"Redis connection attempt {i+1}/{max_retries} failed: {e}")
            if i < max_retries - 1:
                await asyncio.sleep(2)

    logger.error("❌ Redis connection failed after all retries")
    return False


async def init_kafka():
    """Инициализация Kafka с повторными попытками"""
    global kafka_producer, KAFKA_ENABLED
    max_retries = 5
    for i in range(max_retries):
        try:
            kafka_producer = KafkaProducer(
                bootstrap_servers=["localhost:9092"],  # ← ИЗМЕНИТЬ С 'kafka:9092' на 'localhost:9092'
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                retries=3,
                request_timeout_ms=10000,
            )
            # Тестовый запрос для проверки подключения
            kafka_producer.send("health-check", {"status": "test"})
            KAFKA_ENABLED = True
            logger.info("✅ Kafka connected successfully")
            return True
        except Exception as e:
            logger.warning(f"Kafka connection attempt {i+1}/{max_retries} failed: {e}")
            if i < max_retries - 1:
                await asyncio.sleep(3)

    logger.warning("❌ Kafka connection failed, running without Kafka")
    KAFKA_ENABLED = False
    return False


def send_kafka_event(topic: str, event_data: dict):
    """Безопасная отправка событий в Kafka"""
    if KAFKA_ENABLED and kafka_producer:
        try:
            event_data["timestamp"] = datetime.utcnow().isoformat()
            event_data["service"] = "pobeda-backend"
            kafka_producer.send(topic, event_data)
            logger.info(f"📨 Sent event to {topic}: {event_data.get('event_type', 'unknown')}")
        except Exception as e:
            logger.error(f"Failed to send Kafka event to {topic}: {e}")


# Фоновые задачи
background_tasks = set()


async def background_price_updater():
    """Фоновая задача для обновления цен"""
    while True:
        try:
            from database import SessionLocal
            from background_service import BackgroundPriceUpdater

            db = SessionLocal()
            updater = BackgroundPriceUpdater(db)

            logger.info("🚀 Starting background price update...")
            updated_count = await updater.update_all_popular_routes()

            # Отправляем событие в Kafka
            send_kafka_event(
                "background-jobs",
                {
                    "event_type": "price_update_completed",
                    "routes_updated": updated_count,
                },
            )

            logger.info(f"✅ Background update finished: {updated_count} routes updated")
            db.close()

        except Exception as e:
            logger.error(f"Error in background price updater: {e}")
            send_kafka_event(
                "error-logs",
                {
                    "event_type": "background_job_error",
                    "job": "price_updater",
                    "error": str(e),
                },
            )

        await asyncio.sleep(60 * 60)  # 1 hour


async def background_cities_updater():
    """Фоновая задача для обновления активных городов"""
    while True:
        try:
            from database import SessionLocal
            from city_service import CityService

            db = SessionLocal()
            city_service = CityService(db)

            logger.info("🚀 Starting background cities update...")
            updated_count = await city_service.update_active_cities_in_db()

            send_kafka_event(
                "background-jobs",
                {
                    "event_type": "cities_update_completed",
                    "active_cities": updated_count,
                },
            )

            logger.info(f"✅ Background cities update finished: {updated_count} active cities")
            db.close()

        except Exception as e:
            logger.error(f"Error in background cities updater: {e}")
            send_kafka_event(
                "error-logs",
                {
                    "event_type": "background_job_error",
                    "job": "cities_updater",
                    "error": str(e),
                },
            )

        await asyncio.sleep(24 * 60 * 60)  # 24 hours


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting Pobeda Parser API with Embedded Kafka...")

    # ✅ ДОБАВЬТЕ ЭТИ 4 СТРОЧКИ:
    # Запускаем Kafka сервисы
    start_kafka_services()

    # Ждем немного перед инициализацией Kafka клиента
    await asyncio.sleep(25)
    # ✅ КОНЕЦ ДОБАВЛЕНИЯ

    create_tables()
    logger.info("✅ Database tables created")

    # Инициализируем Redis и Kafka
    redis_ok = await init_redis()
    kafka_ok = await init_kafka()

    # Запускаем фоновые задачи
    price_task = asyncio.create_task(background_price_updater())
    cities_task = asyncio.create_task(background_cities_updater())

    background_tasks.add(price_task)
    background_tasks.add(cities_task)

    price_task.add_done_callback(background_tasks.discard)
    cities_task.add_done_callback(background_tasks.discard)

    logger.info("✅ Background tasks started")

    # Отправляем событие о старте приложения
    send_kafka_event(
        "system-events",
        {
            "event_type": "app_started",
            "redis_connected": redis_ok,
            "kafka_connected": kafka_ok,
        },
    )

    yield

    # Shutdown
    logger.info("🛑 Shutting down Pobeda Parser API...")

    for task in background_tasks:
        task.cancel()
    await asyncio.gather(*background_tasks, return_exceptions=True)

    # Закрываем соединения
    if redis_client:
        redis_client.close()
    if kafka_producer:
        kafka_producer.close()

    logger.info("✅ Pobeda Parser API stopped")


app = FastAPI(
    title="Pobeda Parser API",
    description="API для парсинга цен авиакомпании Победа",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check с проверкой всех сервисов
@app.get("/")
async def health_check():
    """Проверка здоровья всех компонентов системы"""
    redis_status = "unknown"
    if redis_client:
        try:
            redis_client.ping()
            redis_status = "healthy"
        except Exception as e:
            redis_status = f"error: {e}"

    return {
        "message": "Pobeda Parser API работает! 🚀",
        "status": "healthy",
        "services": {
            "redis": redis_status,
            "kafka": "enabled" if KAFKA_ENABLED else "disabled",
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


# Тестовые эндпоинты
@app.get("/test-redis")
async def test_redis():
    """Тест подключения к Redis"""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not initialized")

    try:
        # Тест записи
        test_key = f"test:{datetime.utcnow().strftime('%H%M%S')}"
        redis_client.set(test_key, "test_value", ex=60)

        # Тест чтения
        value = redis_client.get(test_key)

        send_kafka_event(
            "test-events",
            {
                "event_type": "redis_test",
                "status": "success",
                "key": test_key,
                "value": value,
            },
        )

        return {
            "status": "success",
            "message": "Redis connection OK",
            "data": {"key": test_key, "value": value},
        }
    except Exception as e:
        send_kafka_event("error-logs", {"event_type": "redis_test_error", "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Redis test failed: {e}")


@app.get("/test-kafka")
async def test_kafka():
    """Тест отправки сообщений в Kafka"""
    if not KAFKA_ENABLED:
        raise HTTPException(status_code=503, detail="Kafka not available")

    try:
        test_event = {
            "event_type": "kafka_test",
            "message": "Test message from Pobeda Parser API",
            "timestamp": datetime.utcnow().isoformat(),
        }

        send_kafka_event("test-events", test_event)

        return {
            "status": "success",
            "message": "Kafka event sent successfully",
            "event": test_event,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Kafka test failed: {e}")


@app.get("/cache-test")
async def cache_test():
    """Тест Redis и Kafka вместе"""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not initialized")

    try:
        # Тест Redis
        redis_client.set("cache_test_key", "cache_test_value", ex=60)
        value = redis_client.get("cache_test_key")

        # Тест Kafka
        send_kafka_event(
            "test-events",
            {"event_type": "cache_test", "action": "cache_test", "redis_value": value},
        )

        return {"redis": value, "kafka": "event_sent", "status": "success"}
    except Exception as e:
        send_kafka_event("error-logs", {"event_type": "cache_test_error", "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Cache test failed: {e}")


# Логирование
@app.post("/api/logs/frontend", summary="Прием логов с фронтенда")
async def receive_frontend_logs(log_data: dict, db: Session = Depends(get_db)):
    """Принимает логи с фронтенда и отправляет в ELK"""
    try:
        # Логируем на бекенде
        logger.info("Frontend log received", extra={"frontend_data": log_data})

        # Отправляем в Kafka
        send_kafka_event(
            "frontend-logs",
            {
                "event_type": "frontend_log",
                "level": log_data.get("level"),
                "message": log_data.get("message"),
                "user_agent": log_data.get("userAgent"),
                "url": log_data.get("url"),
            },
        )

        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error processing frontend log: {e}")
        send_kafka_event("error-logs", {"event_type": "log_processing_error", "error": str(e)})
        return {"status": "error", "message": str(e)}


@app.post("/api/logs/backend", summary="Логи бекенда")
async def receive_backend_logs(log_data: dict):
    """Принимает логи с других сервисов бекенда"""
    logger.info("Backend log received", extra={"backend_data": log_data})

    send_kafka_event("backend-logs", {"event_type": "backend_log", "data": log_data})

    return {"status": "success"}


@app.get("/cities")
async def get_cities(skip: int = 0, limit: int = 500, db: Session = Depends(get_db)):
    """Получить список всех городов"""
    from city_service import CityService
    from models import City

    city_service = CityService(db)

    # Обновляем города из API
    await city_service.update_cities_from_api()

    # Получаем все города из БД
    cities = db.query(City).offset(skip).limit(limit).all()

    send_kafka_event(
        "api-requests",
        {
            "event_type": "cities_request",
            "endpoint": "/cities",
            "cities_count": len(cities),
        },
    )

    return cities


@app.get(
    "/cities/active",
    summary="Получить активные города",
    description="Возвращает только города, откуда ЕСТЬ рейсы Победы",
)
async def get_active_cities(
    skip: int = Query(0, description="Количество пропущенных записей (для пагинации)"),
    limit: int = Query(500, description="Максимальное количество возвращаемых записей"),
    db: Session = Depends(get_db),
):
    """Получить список только АКТИВНЫХ городов (откуда есть рейсы)"""
    from models import City

    cities = db.query(City).filter(City.is_active == True).offset(skip).limit(limit).all()

    send_kafka_event(
        "api-requests",
        {
            "event_type": "cities_request",
            "endpoint": "/cities/active",
            "cities_count": len(cities),
        },
    )

    return {
        "total_active": db.query(City).filter(City.is_active == True).count(),
        "cities": cities,
    }


@app.get(
    "/flights/search",
    summary="Поиск рейсов на месяц",
    description="Ищет рейсы между двумя городами на 30 дней вперед",
)
async def search_flights(
    origin: str = Query(
        ...,
        description="Код города отправления из активных городов, (например: MOW, LED, AER)",
    ),
    destination: str = Query(..., description="Код города назначения из активных городов"),
    promo_code: str = Query(None, description="Промокод для поиска (опционально)"),
    db: Session = Depends(get_db),
):
    """Поиск рейсов между городами на месяц вперед"""
    from models import City
    from flight_service import FlightService

    # Проверяем что города активные
    origin_city = db.query(City).filter(City.code == origin, City.is_active == True).first()
    destination_city = db.query(City).filter(City.code == destination, City.is_active == True).first()

    if not origin_city:
        raise HTTPException(
            status_code=400,
            detail=f"Город отправления '{origin}' не найден или не активен",
        )
    if not destination_city:
        raise HTTPException(
            status_code=400,
            detail=f"Город назначения '{destination}' не найден или не активен",
        )

    # Отправляем событие о начале поиска
    send_kafka_event(
        "search-events",
        {
            "event_type": "search_started",
            "origin": origin,
            "destination": destination,
            "promo_code": promo_code,
        },
    )

    flight_service = FlightService(db)
    search_result = await flight_service.search_flights_month(origin, destination, promo_code)

    # Отправляем событие о завершении поиска
    send_kafka_event(
        "search-events",
        {
            "event_type": "search_completed",
            "origin": origin,
            "destination": destination,
            "flights_found": len(search_result["flights"]),
            "promo_code": promo_code,
            "is_complete": search_result["is_complete"],
        },
    )

    return {
        "origin": origin_city.name_ru,
        "destination": destination_city.name_ru,
        "promo_code": promo_code,
        "total_days_searched": search_result["total_days_searched"],
        "days_with_data": search_result["days_with_data"],
        "is_complete": search_result["is_complete"],
        "has_retry_data": search_result["has_retry_data"],
        "flights": search_result["flights"],
    }


@app.get(
    "/flights/anywhere",
    summary="Поиск 'Куда угодно'",
    description="Ищет самые дешевые рейсы из указанного города во ВСЕ доступные направления на выбранный месяц",
)
async def search_anywhere(
    origin: str = Query(
        ...,
        description="Код города отправления (например: MOW, LED, AER). Получить коды городов: /cities/active",
    ),
    months_ahead: int = Query(1, description="На сколько месяцев вперед искать (1-6 месяцев, по умолчанию 1)"),
    promo_code: str = Query(None, description="Промокод для поиска (опционально)"),
    max_price: float = Query(None, description="Максимальная цена билета в рублях (опционально)"),
    db: Session = Depends(get_db),
):
    """Поиск самых дешевых рейсов из города в любые доступные направления"""
    from anywhere_service import AnywhereService

    # Валидация параметров
    if months_ahead < 1 or months_ahead > 6:
        raise HTTPException(status_code=400, detail="months_ahead должен быть от 1 до 6")

    # Отправляем событие о начале поиска "Куда угодно"
    send_kafka_event(
        "anywhere-search",
        {
            "event_type": "anywhere_search_started",
            "origin": origin,
            "months_ahead": months_ahead,
            "max_price": max_price,
        },
    )

    anywhere_service = AnywhereService(db)
    results = await anywhere_service.search_anywhere(origin, months_ahead, promo_code, max_price)

    # Отправляем событие о завершении поиска
    send_kafka_event(
        "anywhere-search",
        {
            "event_type": "anywhere_search_completed",
            "origin": origin,
            "destinations_found": len(results),
            "months_ahead": months_ahead,
        },
    )

    return {
        "origin": origin,
        "months_ahead": months_ahead,
        "promo_code": promo_code,
        "max_price": max_price,
        "total_destinations_found": len(results),
        "cheapest_flights": results,
    }


# Основные эндпоинты для городов
@app.get("/cities/for-frontend", summary="Города для выбора на фронтенде")
async def get_cities_for_frontend(db: Session = Depends(get_db)):
    """Получить активные города в формате для фронтенда"""
    from city_service import CityService

    city_service = CityService(db)
    cities = city_service.get_cities_for_frontend()

    return {"cities": cities, "total": len(cities)}


@app.post("/admin/update-active-cities", summary="Обновить активные города")
async def update_active_cities(db: Session = Depends(get_db)):
    """Принудительное обновление списка активных городов"""
    from city_service import CityService

    city_service = CityService(db)
    updated_count = await city_service.update_active_cities_in_db()

    return {
        "status": "success",
        "message": f"Updated {updated_count} active cities",
        "updated_count": updated_count,
    }


@app.get("/cities/active", summary="Активные города")
async def get_active_cities(db: Session = Depends(get_db)):
    """Получить список активных городов"""
    from models import City

    cities = db.query(City).filter(City.is_active == True).all()
    return {"total": len(cities), "cities": cities}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
