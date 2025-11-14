# force_update_cities.py
import asyncio
import sys
import os

sys.path.append("/app")

from database import SessionLocal
from city_service import CityService


async def force_update_cities():
    """Принудительное обновление городов при запуске контейнера"""
    db = SessionLocal()
    try:
        city_service = CityService(db)

        print("🔄 Force updating cities from API...")
        result = await city_service.update_cities_from_api()
        print(f"✅ Cities updated: {result}")

        print("🔄 Discovering and saving active cities...")
        updated_count = await city_service.update_active_cities_in_db()

        print(f"🎯 Total active cities in DB: {updated_count}")

    except Exception as e:
        print(f"❌ Error in force_update_cities: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(force_update_cities())
