import aiohttp
from sqlalchemy.orm import Session
from datetime import datetime
import logging
import asyncio

logger = logging.getLogger(__name__)

class PobedaAPIClient:
    def __init__(self):
        self.base_url = "https://ticket.flypobeda.ru/websky/json"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Origin": "https://ticket.flypobeda.ru",
            "Referer": "https://ticket.flypobeda.ru/websky/",
        }

    async def get_all_cities(self) -> list:
        """Получить ВСЕ города из справочника - GET запрос!"""
        url = f"{self.base_url}/dict-cities"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=self.headers, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        if isinstance(data, list):
                            logger.info(f"✅ Received {len(data)} cities from API")
                            return data
                        else:
                            logger.error(f"❌ Unexpected API response format: {type(data)}")
                            return []
                    else:
                        logger.error(f"❌ API returned status {response.status}")
                        return []
            except Exception as e:
                logger.error(f"❌ Error fetching cities: {e}")
                return []

    async def get_available_destinations(self, origin_city_code: str) -> list:
        """Получить города, в которые МОЖНО улететь из указанного города"""
        url = f"{self.base_url}/dependence-cities"
        data = {
            "returnPoints": "destination",
            "cityCode": origin_city_code,
            "isBooking": "true",
            "lang": "ru"
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=self.headers, data=data, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        destinations = data.get("destination", [])
                        logger.info(f"✅ Found {len(destinations)} destinations from {origin_city_code}")
                        return destinations
                    elif response.status == 403:
                        logger.warning(f"⚠️ API 403 Forbidden for {origin_city_code}")
                        return []  # Возвращаем пустой список при 403
                    else:
                        logger.error(f"❌ API returned status {response.status} for {origin_city_code}")
                        return []
            except asyncio.TimeoutError:
                logger.error(f"⏰ Timeout fetching destinations from {origin_city_code}")
                return []
            except Exception as e:
                logger.error(f"❌ Error fetching destinations from {origin_city_code}: {e}")
                return []

class CityService:
    def __init__(self, db: Session):
        self.db = db
        self.api_client = PobedaAPIClient()

    async def update_cities_from_api(self) -> dict:
        """Обновить список всех городов из API и вернуть статистику"""
        from models import City

        cities_data = await self.api_client.get_all_cities()

        if not cities_data:
            return {"error": "No data received from API"}

        updated = 0
        created = 0

        for city_data in cities_data:
            city_code = city_data.get("codeEn")
            if not city_code:
                continue

            existing_city = self.db.query(City).filter(
                City.code == city_code
            ).first()

            if existing_city:
                # Обновляем существующий - НЕ меняем is_active!
                existing_city.name_ru = city_data.get("nameRu", "")
                existing_city.name_en = city_data.get("nameEn", "")
                existing_city.country_ru = city_data.get("countryRu", "")
                existing_city.country_en = city_data.get("countryEn", "")
                existing_city.updated_at = datetime.utcnow()
                updated += 1
            else:
                # Создаем новый город - по умолчанию НЕ активный!
                new_city = City(
                    code=city_code,
                    name_ru=city_data.get("nameRu", ""),
                    name_en=city_data.get("nameEn", ""),
                    country_ru=city_data.get("countryRu", ""),
                    country_en=city_data.get("countryEn", ""),
                    is_active=False  # ⚠️ ВАЖНО: новые города не активны по умолчанию!
                )
                self.db.add(new_city)
                created += 1

        self.db.commit()

        return {
            "total_received": len(cities_data),
            "created": created,
            "updated": updated,
            "total_in_db": self.db.query(City).count()
        }

    async def get_available_destinations_from_api(self, origin_city_code: str) -> list:
        """Получить доступные направления из API Победы"""
        return await self.api_client.get_available_destinations(origin_city_code)

    async def _check_city_has_flights(self, city_code: str) -> bool:
        """Проверяет есть ли рейсы из города"""
        try:
            destinations = await self.api_client.get_available_destinations(city_code)

            # Простая проверка - если есть хоть одно направление
            valid_destinations = [
                dest for dest in destinations
                if dest and dest.get('codeEn') and dest.get('codeEn') != city_code
            ]

            has_flights = len(valid_destinations) > 0

            if has_flights:
                logger.info(f"✅ City {city_code} has {len(valid_destinations)} destinations")
            else:
                logger.info(f"❌ City {city_code} has NO flights")

            return has_flights

        except Exception as e:
            logger.error(f"❌ Error checking city {city_code}: {e}")
            return False

    async def get_active_cities_codes_simple(self) -> list:
        """УПРОЩЕННАЯ версия - используем заранее известные активные города"""
        # Основные российские аэропорты, откуда точно есть рейсы Победы
        main_active_cities = [
            'MOW', 'LED', 'SVX', 'KZN', 'AER', 'OVB', 'UFA', 'KRR', 'ROV', 'MRV',
            'GOJ', 'VKO', 'STW', 'KGD', 'OMS', 'CEK', 'KUF', 'NUX', 'IJK', 'NNM'
        ]

        logger.info(f"🔄 Using predefined {len(main_active_cities)} active cities")
        return main_active_cities

    async def get_active_cities_codes(self) -> list:
        """Получить коды активных городов - УПРОЩЕННАЯ ВЕРСИЯ"""
        # Временно используем упрощенную версию из-за проблем с API
        return await self.get_active_cities_codes_simple()

    async def discover_active_cities(self) -> list:
        """Основной метод: находим все активные города через доступные направления"""
        # Основные российские аэропорты для старта
        main_active_cities = [
            'MOW', 'LED', 'SVX', 'KZN', 'AER', 'OVB', 'UFA', 'KRR', 'ROV', 'MRV',
            'GOJ', 'VKO', 'STW', 'KGD', 'OMS', 'CEK', 'KUF', 'NUX', 'IJK', 'NNM'
        ]

        active_cities_set = set()

        # Проверяем каждый основной город и находим все доступные направления
        for origin_city in main_active_cities:
            try:
                destinations = await self.api_client.get_available_destinations(origin_city)

                # Добавляем город отправления (он активный)
                active_cities_set.add(origin_city)

                # Добавляем все города назначения
                for dest in destinations:
                    if dest.get('codeEn'):
                        active_cities_set.add(dest['codeEn'])

                logger.info(f"✅ Processed {origin_city}, found {len(destinations)} destinations")
                await asyncio.sleep(1)  # Пауза между запросами

            except Exception as e:
                logger.error(f"❌ Error processing {origin_city}: {e}")
                continue

        active_cities_list = list(active_cities_set)
        logger.info(f"🎯 Total active cities discovered: {len(active_cities_list)}")
        return active_cities_list

    async def update_active_cities_in_db(self):
        """Обновляем активные города в базе данных"""
        from models import City

        try:
            # Получаем все активные города через API
            active_codes = await self.discover_active_cities()

            # Сначала помечаем все города как неактивные
            self.db.query(City).update({City.is_active: False})

            # Помечаем найденные активные города
            activated_count = 0
            for code in active_codes:
                city = self.db.query(City).filter(City.code == code).first()
                if city:
                    city.is_active = True
                    activated_count += 1
                else:
                    # Если города нет в базе, создаем его
                    new_city = City(
                        code=code,
                        name_ru=code,  # Временное название
                        name_en=code,
                        country_ru="Россия",
                        country_en="Russia",
                        is_active=True
                    )
                    self.db.add(new_city)
                    activated_count += 1

            self.db.commit()
            logger.info(f"✅ Updated {activated_count} active cities in database")
            return activated_count

        except Exception as e:
            logger.error(f"❌ Error updating active cities: {e}")
            self.db.rollback()
            return 0

    async def save_active_cities(self, active_codes: list):
        """Сохранить активные города в БД"""
        from models import City

        try:
            # Помечаем все города как неактивные
            self.db.query(City).update({City.is_active: False})

            # Помечаем активные города
            activated_count = 0
            for code in active_codes:
                city = self.db.query(City).filter(City.code == code).first()
                if city:
                    city.is_active = True
                    activated_count += 1
                else:
                    logger.warning(f"⚠️ City {code} not found in database")

            self.db.commit()
            logger.info(f"✅ Saved {activated_count} active cities")

        except Exception as e:
            logger.error(f"❌ Error saving active cities: {e}")
            self.db.rollback()
            raise

    def get_cities_for_frontend(self) -> list:
        """Получить города в формате для фронтенда"""
        from models import City

        cities = self.db.query(City).filter(City.is_active == True).order_by(City.name_ru).all()

        result = []
        for city in cities:
            result.append({
                "value": city.code,
                "label": f"{city.name_ru} ({city.code})",
                "name_ru": city.name_ru,
                "name_en": city.name_en,
                "country_ru": city.country_ru
            })

        return result