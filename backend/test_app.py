from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uvicorn
import aiohttp

from database import get_db, create_tables
from config import settings

app = FastAPI(
    title="Pobeda Parser API",
    description="API для парсинга цен авиакомпании Победа",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    create_tables()


@app.get("/")
async def healthCheck():
    return {"message": "Pobeda Parser API работает! 🚀"}


@app.post("/cities/debug-load")
async def debug_load_cities(db: Session = Depends(get_db)):
    """Дебаг: загрузить города напрямую"""
    from models import City

    # Очищаем таблицу
    db.query(City).delete()

    # Тестовые данные
    test_cities = [
        {
            "code": "MOW",
            "name_ru": "Москва",
            "name_en": "Moscow",
            "country_ru": "Россия",
            "country_en": "Russia",
        },
        {
            "code": "LED",
            "name_ru": "Санкт-Петербург",
            "name_en": "St Petersburg",
            "country_ru": "Россия",
            "country_en": "Russia",
        },
        {
            "code": "SVX",
            "name_ru": "Екатеринбург",
            "name_en": "Yekaterinburg",
            "country_ru": "Россия",
            "country_en": "Russia",
        },
        {
            "code": "KZN",
            "name_ru": "Казань",
            "name_en": "Kazan",
            "country_ru": "Россия",
            "country_en": "Russia",
        },
        {
            "code": "AER",
            "name_ru": "Сочи",
            "name_en": "Sochi",
            "country_ru": "Россия",
            "country_en": "Russia",
        },
        {
            "code": "OVB",
            "name_ru": "Новосибирск",
            "name_en": "Novosibirsk",
            "country_ru": "Россия",
            "country_en": "Russia",
        },
    ]

    for city_data in test_cities:
        city = City(**city_data)
        db.add(city)

    db.commit()

    return {"loaded": len(test_cities), "total": db.query(City).count()}


@app.get("/cities/debug")
async def debug_get_cities(db: Session = Depends(get_db)):
    """Дебаг: получить города"""
    from models import City

    cities = db.query(City).all()
    return {
        "total_cities": len(cities),
        "cities": [{"code": c.code, "name_ru": c.name_ru} for c in cities],
    }


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
