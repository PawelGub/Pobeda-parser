import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import aiohttp
from models import FlightCache
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class FlightService:
    def __init__(self, db: Session):
        self.db = db
        self.base_url = "https://ticket.flypobeda.ru/websky/json"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Origin": "https://ticket.flypobeda.ru",
            "Referer": "https://ticket.flypobeda.ru/websky/",
        }
        self.max_concurrent_requests = 3  # 3 одновременных запросов к API Победы (было 10 - у Победы анти-DDos защита)!

    def _generate_month_dates(self) -> List[Dict]:
        """Генерируем даты на 30 дней вперед"""
        dates = []
        today = datetime.now()
        for i in range(30):
            date = today + timedelta(days=i)
            api_date = date.strftime("%d.%m.%Y")
            db_date = date.strftime("%Y-%m-%d")
            dates.append({"api": api_date, "db": db_date})
        return dates

    def _generate_dates(self, months_ahead: int = 1) -> List[Dict]:
        """Генерируем даты на N месяцев вперед"""
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

    async def search_flights_month(self, origin: str, destination: str, promo_code: Optional[str] = None) -> Dict:
        """Поиск рейсов на месяц вперед с информацией о полноте"""
        dates = self._generate_month_dates()
        total_days = len(dates)
        logger.info(f"Searching flights {origin} -> {destination} for {total_days} dates")

        # Сначала проверяем кеш
        date_strings = [date_info["db"] for date_info in dates]
        cached_data = self._get_cached_flights_batch(origin, destination, date_strings, promo_code)

        cached_results = []
        uncached_dates = []

        for date_info in dates:
            if date_info["db"] in cached_data:
                cached_day = cached_data[date_info["db"]]
                if cached_day.get("flights") or cached_day.get("prices"):
                    cached_results.append(cached_day)
            else:
                uncached_dates.append(date_info)

        logger.info(f"Found {len(cached_results)} cached with flights, {len(uncached_dates)} to fetch")

        fresh_results = []
        retry_results = []
        is_complete = True  # Флаг полноты данных

        if uncached_dates:
            # Первый проход
            fresh_results = await self._search_flights_parallel(origin, destination, uncached_dates, promo_code)

            # Фильтруем успешные результаты
            valid_fresh_results = [r for r in fresh_results if r and (r.get("flights") or r.get("prices"))]

            # Ищем даты с 403 ошибками
            failed_dates: List[Dict] = []
            for i, result in enumerate(fresh_results):
                if result is None:  # 403 ошибка
                    failed_dates.append(uncached_dates[i])
                    is_complete = False  # Данные не полные!

            # Сохраняем в кеш успешные результаты
            if valid_fresh_results:
                self._cache_flights_batch(origin, destination, valid_fresh_results, promo_code)

            # Второй проход для 403 ошибок
            if failed_dates:
                logger.info(f"Background retry for {len(failed_dates)} failed dates...")
                retry_results = await self._search_flights_slow_retry(origin, destination, failed_dates, promo_code)

                # Фильтруем успешные повторные попытки
                valid_retry_results = [r for r in retry_results if r and (r.get("flights") or r.get("prices"))]

                if valid_retry_results:
                    self._cache_flights_batch(origin, destination, valid_retry_results, promo_code)
                    valid_fresh_results.extend(valid_retry_results)

                # Если после повторной попытки остались ошибки - данные не полные
                if len(valid_retry_results) < len(failed_dates):
                    is_complete = False

        # Объединяем все результаты
        all_results = cached_results + (valid_fresh_results if uncached_dates else [])

        # ДЕБАГ
        days_with_data = len(all_results)
        logger.info(f"FINAL: {days_with_data}/{total_days} days with data, complete: {is_complete}")

        return {
            "flights": all_results,
            "total_days_searched": total_days,
            "days_with_data": days_with_data,
            "is_complete": is_complete,
            "has_retry_data": len(retry_results) > 0,
        }

    async def _search_flights_slow_retry(
        self, origin: str, destination: str, dates: List[Dict], promo_code: str = None
    ) -> List[Dict]:
        """Медленный повторный поиск ТОЛЬКО для потенциальных дат"""
        async with aiohttp.ClientSession() as session:
            results = []

            for date_info in dates:
                try:
                    # Большая пауза между запросами
                    await asyncio.sleep(8 + random.random() * 4)  # 8-12 секунд

                    result = await self._search_single_flight(
                        session, origin, destination, date_info["api"], promo_code
                    )
                    if result and (result.get("flights") or result.get("prices")):
                        results.append(result)
                        logger.info(f"✅ Retry SUCCESS for {origin}-{destination} on {date_info['api']}")
                    else:
                        # Не добавляем пустые результаты
                        logger.info(f"⏩ Retry SKIP for {origin}-{destination} on {date_info['api']} (no flights)")

                except Exception as e:
                    logger.error(f"❌ Retry error for {origin}-{destination} on {date_info['api']}: {e}")

            return results

    async def search_flights_period(
        self,
        origin: str,
        destination: str,
        months_ahead: int = 1,
        promo_code: str = None,
    ) -> List[Dict]:
        """Поиск рейсов на указанный период вперед - ОПТИМИЗИРОВАННАЯ ВЕРСИЯ"""
        dates = self._generate_dates(months_ahead)
        logger.info(f"Searching flights {origin} -> {destination} for {len(dates)} days ({months_ahead} months)")

        # ПАКЕТНАЯ проверка кеша
        date_strings = [date_info["db"] for date_info in dates]
        cached_data = self._get_cached_flights_batch(origin, destination, date_strings, promo_code)

        cached_results = []
        uncached_dates = []

        for date_info in dates:
            if date_info["db"] in cached_data:
                cached_results.append(cached_data[date_info["db"]])
            else:
                uncached_dates.append(date_info)

        logger.info(f"Found {len(cached_results)} cached, {len(uncached_dates)} to fetch")

        if uncached_dates:
            fresh_results = await self._search_flights_parallel(origin, destination, uncached_dates, promo_code)
            self._cache_flights_batch(origin, destination, fresh_results, promo_code)
            return cached_results + fresh_results

        return cached_results

    def _get_cached_flights_batch(
        self, origin: str, destination: str, dates: List[str], promo_code: str = None
    ) -> Dict[str, Dict]:
        """ПАКЕТНАЯ проверка кеша для списка дат - ОДИН запрос к БД!"""
        if not dates:
            return {}

        from datetime import datetime

        # ОДИН запрос для всех дат!
        caches = (
            self.db.query(FlightCache)
            .filter(
                FlightCache.origin_city_code == origin,
                FlightCache.destination_city_code == destination,
                FlightCache.flight_date.in_(dates),
                FlightCache.promo_code == promo_code,
                FlightCache.expires_at > datetime.utcnow(),
            )
            .all()
        )

        # Создаем словарь {дата: данные_кеша}
        cached_data = {}
        for cache in caches:
            cached_data[cache.flight_date] = cache.flight_data

        return cached_data

    def _cache_flights_batch(self, origin: str, destination: str, fresh_results: List[Dict], promo_code: str):
        """Пакетное сохранение в кеш"""
        for result in fresh_results:
            if result and "flights" in result:
                try:
                    api_date = result["date"]
                    db_date = datetime.strptime(api_date, "%d.%m.%Y").strftime("%Y-%m-%d")
                    self._cache_flight(origin, destination, db_date, promo_code, result)
                except ValueError as e:
                    logger.error(f"Error converting date {result['date']}: {e}")

    def _cache_flight(
        self,
        origin: str,
        destination: str,
        date: str,
        promo_code: str,
        flight_data: Dict,
    ):
        """Сохранить рейсы в кеш на 6 часов"""
        # Сначала проверяем, нет ли уже записи
        existing = (
            self.db.query(FlightCache)
            .filter(
                FlightCache.origin_city_code == origin,
                FlightCache.destination_city_code == destination,
                FlightCache.flight_date == date,
                FlightCache.promo_code == promo_code,
            )
            .first()
        )

        if existing:
            # Обновляем существующую запись
            existing.flight_data = flight_data
            existing.expires_at = datetime.utcnow() + timedelta(hours=6)
        else:
            # Создаем новую запись
            cache = FlightCache(
                origin_city_code=origin,
                destination_city_code=destination,
                flight_date=date,
                promo_code=promo_code,
                flight_data=flight_data,
                expires_at=datetime.utcnow() + timedelta(hours=6),
            )
            self.db.add(cache)

        self.db.commit()

    async def _search_flights_parallel(
        self, origin: str, destination: str, dates: List[Dict], promo_code: str = None
    ) -> List[Dict]:
        """Параллельный поиск рейсов для списка дат"""
        async with aiohttp.ClientSession() as session:
            semaphore = asyncio.Semaphore(self.max_concurrent_requests)

            async def bounded_search(date_info):
                async with semaphore:
                    return await self._search_single_flight(session, origin, destination, date_info["api"], promo_code)

            tasks = [bounded_search(date_info) for date_info in dates]
            results = []
            for task in asyncio.as_completed(tasks):
                try:
                    result = await task
                    results.append(result)
                except Exception as e:
                    logger.error(f"Task failed: {e}")
                    results.append(None)

            successful_results = []
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Request failed: {result}")
                elif result:
                    successful_results.append(result)

            return successful_results

    async def _search_single_flight(
        self,
        session: aiohttp.ClientSession,
        origin: str,
        destination: str,
        date: str,
        promo_code: str = None,
    ) -> Optional[Dict]:
        """Поиск рейсов на одну конкретную дату"""
        url = f"{self.base_url}/search-variants-mono-brand-cartesian"

        data = {
            "searchGroupId": "standard",
            "segmentsCount": "1",
            f"date[0]": date,
            f"origin-city-code[0]": origin,
            f"destination-city-code[0]": destination,
            "adultsCount": "1",
            "youngAdultsCount": "0",
            "childrenCount": "0",
            "infantsWithSeatCount": "0",
            "infantsWithoutSeatCount": "0",
        }

        if promo_code:
            data["promoCode"] = promo_code

        try:
            async with session.post(url, headers=self.headers, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "date": date,
                        "origin": origin,
                        "destination": destination,
                        "flights": result.get("flights", []),
                        "prices": result.get("prices", []),
                        "promo_code": promo_code,
                    }
                else:
                    logger.warning(f"API returned {response.status} for {origin}-{destination} on {date}")
                    return None
        except Exception as e:
            logger.error(f"Error searching flight {origin}-{destination} on {date}: {e}")
            return None

    async def search_flights_specific_date(
        self, origin: str, destination: str, date: str, promo_code: str = None
    ) -> Optional[Dict]:
        """Поиск рейсов на конкретную дату"""
        try:
            if len(date) == 10 and date[4] == "-":
                api_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m.%Y")
            else:
                api_date = date
        except ValueError:
            api_date = date

        async with aiohttp.ClientSession() as session:
            return await self._search_single_flight(session, origin, destination, api_date, promo_code)
