from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from database import FlightDatabase
import time
import re
from datetime import datetime, timedelta

class PobedaParser:
    def __init__(self, headless=True):  # По умолчанию headless для скорости
        self.base_url = "https://www.flypobeda.ru"
        self.setup_driver(headless)

    def setup_driver(self, headless=True):
        """Настраивает Chrome драйвер для максимальной скорости"""
        print("🚀 Инициализация ChromeDriver...")

        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1920,1080")

        # Оптимизации для скорости
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--disable-javascript")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        except:
            self.driver = webdriver.Chrome(options=chrome_options)

        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.wait = WebDriverWait(self.driver, 10)  # Уменьшил время ожидания

    def close(self):
        """Закрывает браузер"""
        if hasattr(self, 'driver') and self.driver:
            try:
                self.driver.quit()
            except:
                pass

    def clear_and_fill_input(self, element, text):
        """Очищает поле и вводит текст - оптимизированная версия"""
        element.click()
        time.sleep(0.3)
        element.send_keys(Keys.CONTROL + "a")
        element.send_keys(Keys.DELETE)
        time.sleep(0.2)
        element.send_keys(text)
        time.sleep(0.5)  # Уменьшил время ожидания

    def select_city(self, city_input_selector, city_name, field_name):
        """Выбор города - ускоренная версия"""
        try:
            print(f"🏙️ {field_name}: {city_name}")

            city_input = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, city_input_selector))
            )

            self.clear_and_fill_input(city_input, city_name)
            time.sleep(1)  # Уменьшил время ожидания

            # Ищем подсказку
            suggestion_xpath = f'//div[contains(@class, "suggestionName") and contains(text(), "{city_name}")]'
            try:
                suggestion = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, suggestion_xpath))
                )
                suggestion.click()
                time.sleep(0.5)
                return True
            except:
                try:
                    suggestion = self.driver.find_element(By.CSS_SELECTOR, 'div[class*="suggestionName"]')
                    suggestion.click()
                    time.sleep(0.5)
                    return True
                except:
                    print(f"   ❌ Не найдена подсказка для {city_name}")
                    return False

        except Exception as e:
            print(f"❌ Ошибка выбора {field_name}: {e}")
            return False

    def select_exact_date(self, target_date):
        """Точный выбор конкретной даты - ускоренная версия"""
        try:
            print(f"📅 Выбираем дату: {target_date.strftime('%d.%m.%Y')}")

            # Словарь для перевода месяцев
            month_translation = {
                'january': 'январь', 'february': 'февраль', 'march': 'март',
                'april': 'апрель', 'may': 'май', 'june': 'июнь',
                'july': 'июль', 'august': 'август', 'september': 'сентябрь',
                'october': 'октябрь', 'november': 'ноябрь', 'december': 'декабрь'
            }

            # Кликаем на поле даты
            date_input = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[placeholder="Туда"]'))
            )
            date_input.click()
            time.sleep(1)  # Уменьшил

            # Ждем календарь
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.dp-1rtdcua-root'))
            )
            time.sleep(0.5)

            # Получаем русское название месяца
            english_month = target_date.strftime("%B").lower()
            russian_month = month_translation.get(english_month, english_month)
            target_month_year = f"{russian_month} {target_date.year}".lower()
            day_to_select = target_date.day

            print(f"   🔍 Ищем {target_month_year}...")

            # Листаем календарь пока не найдем нужный месяц
            max_attempts = 6  # Уменьшил количество попыток
            for attempt in range(max_attempts):
                month_elements = self.driver.find_elements(By.CSS_SELECTOR, 'div.dp-odrzad-root-root')
                found_target_month = False

                for month_element in month_elements:
                    current_month_text = month_element.text.lower()
                    if target_month_year in current_month_text:
                        found_target_month = True
                        print(f"   ✅ Нашли нужный месяц: {current_month_text}")
                        break

                if found_target_month:
                    break
                else:
                    next_btn = self.driver.find_element(By.CSS_SELECTOR, 'button.dp-1u36f62-root-root-btn-nextBtn')
                    if not next_btn.get_attribute('disabled'):
                        next_btn.click()
                        time.sleep(0.5)  # Уменьшил
                    else:
                        print("   ❌ Достигнут конец календаря")
                        return False

            # Ищем нужный день
            print(f"   🔍 Ищем число {day_to_select}...")

            day_elements = self.driver.find_elements(
                By.CSS_SELECTOR,
                'button.dp-egwft6-root-root-root:not([disabled]):not([data-muted="true"])'
            )

            target_day_element = None
            for day_element in day_elements:
                if day_element.text == str(day_to_select):
                    target_day_element = day_element
                    break

            if target_day_element:
                target_day_element.click()
                time.sleep(0.5)  # Уменьшил
                print(f"   ✅ Дата {day_to_select}.{target_date.month}.{target_date.year} выбрана")
                return True
            else:
                print(f"   ❌ Дата {day_to_select} не найдена в календаре")
                return False

        except Exception as e:
            print(f"❌ Ошибка выбора даты: {e}")
            return False

    def search_single_date(self, departure_city, arrival_city, target_date):
        """Поиск рейсов для одной даты - СУПЕР УСКОРЕННАЯ ВЕРСИЯ"""
        try:
            print(f"📅 Поиск на {target_date.strftime('%d.%m.%Y')}...")

            # Новая вкладка
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])

            # Открываем сайт
            self.driver.get(self.base_url)
            time.sleep(1)

            # Город отправления
            if not self.select_city('input[placeholder="Откуда"]', departure_city, "Отправление"):
                self.driver.close()
                return []

            # Город прибытия
            if not self.select_city('input[placeholder="Куда"]', arrival_city, "Прибытие"):
                self.driver.close()
                return []

            # Дата
            if not self.select_exact_date(target_date):
                self.driver.close()
                return []

            # Одно направление
            try:
                one_way_btn = self.driver.find_element(By.CSS_SELECTOR, 'button.dp-zoryqo-root-root')
                one_way_btn.click()
                time.sleep(0.2)
            except:
                pass

            # Вкладки до поиска
            windows_before = self.driver.window_handles

            # Поиск
            search_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[type="submit"]'))
            )
            search_btn.click()

            # Ждем новую вкладку
            time.sleep(2)  # Уменьшил

            # Переключаемся на новую вкладку
            windows_after = self.driver.window_handles
            if len(windows_after) > len(windows_before):
                new_window = [w for w in windows_after if w not in windows_before][0]
                self.driver.switch_to.window(new_window)

                # Ждем загрузки
                time.sleep(3)  # Уменьшил

                # Парсим информацию
                flights_data = self.extract_complete_flight_info(target_date, departure_city, arrival_city)

                # Закрываем все вкладки
                for window in self.driver.window_handles:
                    try:
                        self.driver.switch_to.window(window)
                        self.driver.close()
                    except:
                        pass

                return flights_data
            else:
                time.sleep(3)
                flights_data = self.extract_complete_flight_info(target_date, departure_city, arrival_city)
                self.driver.close()
                return []

        except Exception as e:
            print(f"❌ Ошибка поиска: {e}")
            try:
                for window in self.driver.window_handles:
                    self.driver.switch_to.window(window)
                    self.driver.close()
            except:
                pass
            return []

    def extract_complete_flight_info(self, target_date, departure_city, arrival_city):
        """Извлекает полную информацию о рейсах - УСКОРЕННАЯ"""
        try:
            print("   🔍 Ищем информацию о рейсах...")

            time.sleep(1)

            # Ищем все строки с рейсами
            flight_rows = self.driver.find_elements(By.CSS_SELECTOR, "tr.contentRow")
            print(f"   📋 Найдено строк рейсов: {len(flight_rows)}")

            if not flight_rows:
                print("   ❌ Рейсы не найдены")
                return []

            flights_data = []

            # Берем только первые 2 рейса для скорости
            for row in flight_rows[:2]:
                try:
                    # Номер рейса
                    flight_number = "Не найден"
                    try:
                        number_elem = row.find_element(By.CSS_SELECTOR, ".racenumber span")
                        flight_number = number_elem.text.strip().replace(' ,', ',')
                    except:
                        pass

                    # Время вылета и прилета
                    departure_time = "00:00"
                    arrival_time = "00:00"
                    try:
                        time_elem = row.find_element(By.CSS_SELECTOR, "p.time")
                        time_text = time_elem.text
                        times = re.findall(r'(\d{1,2}:\d{2})', time_text)
                        if len(times) >= 2:
                            departure_time = times[0]
                            arrival_time = times[1]
                    except:
                        pass

                    # Длительность
                    duration = "0ч 0м"
                    try:
                        duration_elem = row.find_element(By.CSS_SELECTOR, "p.duration")
                        duration = duration_elem.text.strip()
                    except:
                        pass

                    # Цена БАЗОВОГО тарифа (только ее ищем для скорости)
                    price_basic = 0
                    try:
                        basic_elem = row.find_element(By.CSS_SELECTOR, "td.econom_type1 .price-cell__text")
                        price_text = basic_elem.text
                        price_basic = int(re.sub(r'[^\d]', '', price_text))
                    except:
                        continue  # Если нет цены - пропускаем

                    # Создаем запись только если есть цена
                    if price_basic > 0:
                        flight_data = {
                            'flight_number': flight_number,
                            'departure_time': departure_time,
                            'arrival_time': arrival_time,
                            'duration': duration,
                            'route': f"{departure_city} – {arrival_city}",
                            'price_basic': price_basic,
                            'price_profit': price_basic,
                            'price_maximum': price_basic,
                            'date': target_date.strftime('%Y-%m-%d'),
                            'departure_city': departure_city,
                            'arrival_city': arrival_city,
                            'search_timestamp': datetime.now().isoformat(),
                            'is_real_data': True
                        }

                        flights_data.append(flight_data)
                        print(f"     ✈️ {flight_number}: {departure_time}→{arrival_time} - {price_basic} руб.")

                except Exception as e:
                    print(f"     ⚠️ Ошибка парсинга строки: {e}")
                    continue

            return flights_data

        except Exception as e:
            print(f"❌ Ошибка извлечения информации: {e}")
            return []

    def search_multiple_dates(self, departure_city, arrival_city, days=7):
        """Поиск рейсов - НОВЫЙ ДРАЙВЕР ДЛЯ КАЖДОЙ ДАТЫ"""
        all_flights_data = []
        successful_dates = 0

        today = datetime.now().date()
        search_dates = [today + timedelta(days=i) for i in range(days)]

        print(f"\n🎯 Поиск из {departure_city} в {arrival_city} на {days} дней")
        print(f"📅 Период: {search_dates[0].strftime('%d.%m.%Y')} - {search_dates[-1].strftime('%d.%m.%Y')}")

        for i, target_date in enumerate(search_dates, 1):
            print(f"\n📊 [{i}/{days}] Поиск на {target_date.strftime('%d.%m.%Y')}...")

            start_time = time.time()

            try:
                # НОВЫЙ ДРАЙВЕР ДЛЯ КАЖДОЙ ДАТЫ
                date_parser = PobedaParser(headless=True)
                flights_for_date = date_parser.search_single_date(departure_city, arrival_city, target_date)
                date_parser.close()

                elapsed_time = time.time() - start_time

                if flights_for_date:
                    successful_dates += 1
                    all_flights_data.extend(flights_for_date)
                    print(f"✅ Найдено {len(flights_for_date)} рейсов за {elapsed_time:.1f}с")
                else:
                    print(f"❌ Рейсы не найдены за {elapsed_time:.1f}с")

            except Exception as e:
                print(f"💥 Ошибка: {e}")

        print(f"\n🎉 Поиск завершен! Успешных дат: {successful_dates}/{days}")
        return all_flights_data

    def get_all_destinations_from_city(self, city):
        """Получает все возможные направления из города"""
        all_cities = [
            "Москва", "Санкт-Петербург", "Сочи", "Стамбул",
            "Минеральные Воды", "Казань", "Калининград", "Аланья", "Абу-Даби", "Анталия",
            "Владикавказ", "Гюмри", "Даламан", "Дубай", "Иркутск", "Волгоград",
            "Екатеринбург", "Новосибирск", "Владивосток", "Краснодар", "Красноярск",
            "Махачкала", "Минск", "Мурманск", "Нальчик", "Омск", "Пермь", "Самара",
            "Сургут", "Уфа", "Челябинск", "Тюмень", "Ташкент"
        ]
        return [c for c in all_cities if c != city]

    def monitor_all_routes(self, days=3):
        """Мониторит все маршруты между всеми городами - ОГРАНИЧЕННАЯ ВЕРСИЯ"""
        all_cities = [
            "Москва", "Санкт-Петербург", "Сочи", "Стамбул",
            "Минеральные Воды", "Казань", "Калининград", "Аланья", "Абу-Даби", "Анталия"
        ]  # Ограничил 10 городами

        total_routes = len(all_cities) * (len(all_cities) - 1)
        completed = 0

        print(f"🎯 ЗАПУСК МОНИТОРИНГА {total_routes} МАРШРУТОВ")

        db = FlightDatabase()

        for departure in all_cities:
            for arrival in all_cities:
                if departure != arrival:
                    try:
                        print(f"🔍 {departure} -> {arrival} ({completed}/{total_routes})")
                        flights = self.search_multiple_dates(departure, arrival, days=days)

                        # Сохраняем в БД
                        for flight in flights:
                            db.save_flight(flight)

                        completed += 1
                        time.sleep(1)  # Минимальная пауза

                    except Exception as e:
                        print(f"❌ Ошибка маршрута {departure}->{arrival}: {e}")

def find_cheapest_flights(flights_data):
    """Находит самые дешевые перелеты по дням"""
    if not flights_data:
        return {}

    flights_by_date = {}

    for flight in flights_data:
        date = flight['date']
        price = flight['price_basic']

        if flight.get('is_real_data', False) and price > 0:
            if date not in flights_by_date or price < flights_by_date[date]['cheapest_price']:
                flights_by_date[date] = {
                    'cheapest_price': price,
                    'flight': flight,
                    'is_real_data': True
                }

    return flights_by_date

def generate_price_calendar(flights_data):
    """Генерирует календарь цен"""
    return find_cheapest_flights(flights_data)

def calculate_stats(flights_data):
    """Вычисляет статистику"""
    if not flights_data:
        return {
            'total_flights': 0,
            'cheapest_price': 0,
            'average_price': 0,
            'dates_covered': 0
        }

    real_flights = [f for f in flights_data if f.get('is_real_data', False) and f['price_basic'] > 0]
    real_prices = [f['price_basic'] for f in real_flights]

    if not real_prices:
        return {
            'total_flights': len(real_flights),
            'cheapest_price': 0,
            'average_price': 0,
            'dates_covered': len(set(f['date'] for f in real_flights))
        }

    return {
        'total_flights': len(real_flights),
        'cheapest_price': min(real_prices),
        'average_price': sum(real_prices) / len(real_prices),
        'dates_covered': len(set(f['date'] for f in real_flights))
    }

if __name__ == "__main__":
    print("🧪 ТЕСТ ПАРСЕРА")
    parser = PobedaParser(headless=True)
    flights = parser.search_multiple_dates("Москва", "Стамбул", days=3)
    parser.close()