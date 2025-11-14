import asyncio
import aiohttp
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import logging
from datetime import datetime, timedelta
from flight_service import FlightService

logger = logging.getLogger(__name__)


class AnywhereService:
    def __init__(self, db: Session):
        self.db = db
        self.flight_service = FlightService(db)

    async def search_anywhere(
        self,
        origin: str,
        months_ahead: int = 1,
        promo_code: str = None,
        max_price: float = None,
    ) -> List[Dict]:
        """ПОИСК КУДА УГОДНО - ПОЛНАЯ МОЩЬ БЕЗ КОМПРОМИССОВ"""
        from city_service import CityService

        logger.info(
            f"🚀 ЗАПУСК ПОЛНОГО ПОИСКА КУДА УГОДНО: {origin}, {months_ahead} месяцев"
        )

        # 1. Проверяем что город активный
        city_service = CityService(self.db)
        has_flights = await city_service._check_city_has_flights(origin)

        if not has_flights:
            return [{"error": f"Из города {origin} нет рейсов Победы"}]

        # 2. Получаем ВСЕ доступные направления
        available_destinations = await city_service.get_available_destinations_from_api(
            origin
        )

        if not available_destinations:
            return [{"error": f"Нет доступных направлений из города {origin}"}]

        logger.info(f"🎯 Найдено {len(available_destinations)} направлений из {origin}")

        # 3. Берем ВСЕ направления без исключений
        destination_codes = [
            dest["codeEn"] for dest in available_destinations if dest.get("codeEn")
        ]

        logger.info(
            f"🔥 Запускаем поиск по ВСЕМ {len(destination_codes)} направлениям на {months_ahead} месяцев"
        )

        # 4. Полномасштабный поиск по ВСЕМ направлениям
        all_cheapest_flights = []

        # Прогресс-бар в логах
        total_destinations = len(destination_codes)
        processed = 0

        async def process_destination_with_progress(destination):
            nonlocal processed
            result = await self._find_cheapest_flight_full_power(
                origin, destination, months_ahead, promo_code, max_price
            )
            processed += 1
            if processed % 5 == 0:  # Логируем каждые 5 направлений
                logger.info(
                    f"📊 Прогресс: {processed}/{total_destinations} ({processed/total_destinations*100:.1f}%)"
                )
            return result

        # Запускаем ВСЕ задачи одновременно - пользователь ждет и получает ВСЕ!
        tasks = [
            process_destination_with_progress(destination)
            for destination in destination_codes
        ]

        logger.info(
            "⏳ Начинаем полномасштабный поиск... Это может занять несколько минут"
        )

        # Ждем завершения ВСЕХ задач - никаких ограничений!
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 5. Собираем и сортируем результаты
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Ошибка поиска: {result}")
            elif result:
                all_cheapest_flights.append(result)

        # Сортируем по цене
        all_cheapest_flights.sort(key=lambda x: x.get("min_price", float("inf")))

        logger.info(
            f"✅ ПОИСК ЗАВЕРШЕН! Найдено {len(all_cheapest_flights)} направлений с ценами"
        )
        return all_cheapest_flights

    async def _find_cheapest_flight_full_power(
        self,
        origin: str,
        destination: str,
        months_ahead: int = 1,
        promo_code: str = None,
        max_price: float = None,
    ) -> Optional[Dict]:
        """ПОЛНОМАСШТАБНЫЙ поиск - ВСЕ даты на ВСЕ месяцы"""
        try:
            # Генерируем ВСЕ даты на указанный период
            dates = self._generate_full_dates(months_ahead)
            logger.debug(f"Поиск {origin}->{destination}: {len(dates)} дней")

            # Используем полную версию поиска
            flights_data = await self.flight_service.search_flights_period(
                origin, destination, months_ahead, promo_code
            )

            if not flights_data:
                return None

            # Ищем абсолютный минимум за ВЕСЬ период
            min_price = float("inf")
            cheapest_date = None
            total_days_with_prices = 0

            for day_data in flights_data:
                if not day_data or "prices" not in day_data:
                    continue

                day_min_price = self._find_min_price_in_day(day_data)
                if day_min_price and day_min_price < min_price:
                    min_price = day_min_price
                    cheapest_date = day_data["date"]
                    total_days_with_prices += 1

            if min_price == float("inf"):
                return None

            # Применяем фильтр по максимальной цене
            if max_price and min_price > max_price:
                return None

            # Получаем ПОЛНУЮ информацию о городе назначения из БД
            from models import City

            dest_city = self.db.query(City).filter(City.code == destination).first()

            return {
                "origin": origin,
                "destination": destination,
                "destination_name_ru": dest_city.name_ru if dest_city else destination,
                "destination_name_en": dest_city.name_en if dest_city else destination,
                "destination_country_ru": (
                    dest_city.country_ru if dest_city else None
                ),  # ДОБАВЛЯЕМ СТРАНУ
                "destination_country_en": (
                    dest_city.country_en if dest_city else None
                ),  # ДОБАВЛЯЕМ СТРАНУ
                "min_price": min_price,
                "cheapest_date": cheapest_date,
                "currency": "RUB",
                "total_days_searched": len(flights_data),
                "total_days_with_prices": total_days_with_prices,
                "search_period_months": months_ahead,
                "search_timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Ошибка поиска {origin}->{destination}: {e}")
            return None

    def _generate_full_dates(self, months_ahead: int) -> List[Dict]:
        """Генерируем ВСЕ даты на указанный период"""
        dates = []
        today = datetime.now()
        end_date = today + timedelta(days=30 * months_ahead)

        current_date = today
        while current_date <= end_date:
            api_date = current_date.strftime("%d.%m.%Y")
            db_date = current_date.strftime("%Y-%m-%d")
            dates.append({"api": api_date, "db": db_date})
            current_date += timedelta(days=1)
        return dates

    def _find_min_price_in_day(self, day_data: Dict) -> Optional[float]:
        """Найти минимальную цену за день"""
        if not day_data or "prices" not in day_data:
            return None

        min_price = float("inf")
        for price_list in day_data["prices"]:
            for prices in price_list.values():
                for price_info in prices:
                    price = float(price_info.get("price", float("inf")))
                    if price < min_price:
                        min_price = price
        return min_price if min_price != float("inf") else None
