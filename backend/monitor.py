from parser import PobedaParser
from database import FlightDatabase
import time
from datetime import datetime

ALL_CITIES = [
    "Москва", "Санкт-Петербург", "Сочи", "Стамбул",
    "Минеральные Воды", "Казань", "Калининград", "Аланья", "Абу-Даби", "Анталия",
    "Владикавказ", "Гюмри", "Даламан", "Дубай", "Иркутск", "Волгоград",
    "Екатеринбург", "Новосибирск", "Владивосток", "Краснодар", "Красноярск",
    "Махачкала", "Минск", "Мурманск", "Нальчик", "Омск", "Пермь", "Самара",
    "Сургут", "Уфа", "Челябинск", "Тюмень", "Ташкент"
]

def monitor_job():
    print(f"\n🔄 [{datetime.now().strftime('%H:%M:%S')}] Запуск полного мониторинга...")

    db = FlightDatabase()

    total_cities = len(ALL_CITIES)
    total_routes = total_cities * (total_cities - 1)
    processed_cities = 0
    processed_routes = 0
    total_flights = 0

    # Инициализируем прогресс
    db.update_progress(total_cities, 0, total_routes, 0, 0, "starting", "")

    for i, departure in enumerate(ALL_CITIES):
        processed_cities = i + 1

        for j, arrival in enumerate(ALL_CITIES):
            if departure != arrival:
                current_route = f"{departure} → {arrival}"
                processed_routes += 1

                try:
                    print(f"🔍 [{processed_routes}/{total_routes}] {current_route}")

                    # Обновляем прогресс
                    db.update_progress(
                        total_cities, processed_cities, total_routes,
                        processed_routes, total_flights, "running", current_route
                    )

                    # Парсим маршрут
                    parser = PobedaParser(headless=True)
                    flights = parser.search_multiple_dates(departure, arrival, days=7)
                    parser.close()

                    # Сохраняем
                    for flight in flights:
                        db.save_flight(flight)
                        total_flights += 1

                    print(f"✅ Сохранено {len(flights)} рейсов")
                    time.sleep(1)  # Пауза между маршрутами

                except Exception as e:
                    print(f"❌ Ошибка {current_route}: {e}")

    # Завершаем
    db.update_progress(
        total_cities, total_cities, total_routes,
        total_routes, total_flights, "completed", ""
    )

    print(f"🎉 Мониторинг завершен! Сохранено {total_flights} рейсов")

if __name__ == "__main__":
    while True:
        monitor_job()
        print("💤 Ожидание 30 минут до следующего запуска...")
        time.sleep(1800)  # 30 минут