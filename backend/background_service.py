# background_service.py
import asyncio
import logging
from datetime import datetime

from city_service import CityService
from flight_service import FlightService
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class BackgroundPriceUpdater:
    def __init__(self, db: Session):
        self.db = db
        self.city_service = CityService(db)
        self.flight_service = FlightService(db)

    async def update_all_popular_routes(self):
        """Обновить цены на популярные маршруты"""
        try:
            from models import City

            # Берем топ-10 популярных городов
            popular_origins = [
                "MOW",
                "LED",
                "SVX",
                "KZN",
                "AER",
                "OVB",
                "UFA",
                "KRR",
                "ROV",
                "MRV",
            ]

            updated_routes = 0

            for origin in popular_origins:
                # Получаем доступные направления из каждого популярного города
                destinations = await self.city_service.get_available_destinations_from_api(origin)
                if not destinations:
                    continue

                # Берем первые 5 направлений из каждого города
                destination_codes = [dest["codeEn"] for dest in destinations[:5] if dest.get("codeEn")]

                for destination in destination_codes:
                    try:
                        # Обновляем цены на 1 месяц вперед
                        await self.flight_service.search_flights_period(origin, destination, months_ahead=1)
                        updated_routes += 1
                        logger.info(f"Updated prices for {origin} -> {destination}")

                        # Пауза чтобы не перегружать API
                        await asyncio.sleep(2)

                    except Exception as e:
                        logger.error(f"Error updating {origin}->{destination}: {e}")

            logger.info(f"Background update completed: {updated_routes} routes updated")
            return updated_routes

        except Exception as e:
            logger.error(f"Error in background update: {e}")
            return 0
