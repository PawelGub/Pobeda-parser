# quick_fix.py
import asyncio

from city_service import CityService
from database import SessionLocal


async def quick_fix():
    db = SessionLocal()
    city_service = CityService(db)

    # Обновляем города из API
    print("🔄 Updating cities from API...")
    result = await city_service.update_cities_from_api()
    print(f"✅ Cities updated: {result}")

    # Получаем активные коды
    print("🔄 Checking active cities...")
    active_codes = await city_service.get_active_cities_codes()
    print(f"✅ Active cities found: {len(active_codes)}")
    print(f"📋 Active codes: {active_codes}")

    # Сохраняем в БД
    print("🔄 Saving to database...")
    await city_service.save_active_cities(active_codes)
    print("✅ Active cities saved to database")

    db.close()


if __name__ == "__main__":
    asyncio.run(quick_fix())
