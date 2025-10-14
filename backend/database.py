import sqlite3
import json
from datetime import datetime, timedelta
import re

class FlightDatabase:
    def __init__(self, db_path="flights.db"):
        self.db_path = db_path
        self.init_db()

    def safe_string(self, text):
        """Очистка строк от опасных символов"""
        if not text:
            return ""
        # Убираем опасные SQL символы
        cleaned = re.sub(r'[;\'"\\]', '', str(text))
        return cleaned.strip()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS flights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                departure_city TEXT,
                arrival_city TEXT,
                flight_number TEXT,
                departure_time TEXT,
                arrival_time TEXT,
                duration TEXT,
                price_basic INTEGER,
                price_profit INTEGER,
                price_maximum INTEGER,
                date TEXT,
                search_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(departure_city, arrival_city, flight_number, date)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monitoring_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total_cities INTEGER,
                processed_cities INTEGER,
                total_routes INTEGER,
                processed_routes INTEGER,
                total_flights INTEGER,
                status TEXT,
                current_route TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def update_progress(self, total_cities, processed_cities, total_routes, processed_routes, total_flights, status, current_route):
        """Обновляет прогресс мониторинга"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO monitoring_progress 
            (total_cities, processed_cities, total_routes, processed_routes, total_flights, status, current_route)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (total_cities, processed_cities, total_routes, processed_routes, total_flights, status, current_route))

        conn.commit()
        conn.close()

    def get_progress(self):
        """Получает текущий прогресс"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM monitoring_progress 
            ORDER BY created_at DESC 
            LIMIT 1
        ''')

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                'total_cities': result[1],
                'processed_cities': result[2],
                'total_routes': result[3],
                'processed_routes': result[4],
                'total_flights': result[5],
                'status': result[6],
                'current_route': result[7],
                'created_at': result[8]
            }
        return None

    def save_flight(self, flight_data):
        """Безопасное сохранение рейса"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Очищаем все строки
            clean_data = {k: self.safe_string(v) for k, v in flight_data.items()}

            cursor.execute('''
                INSERT OR REPLACE INTO flights 
                (departure_city, arrival_city, flight_number, departure_time, 
                 arrival_time, duration, price_basic, price_profit, price_maximum, date, search_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                clean_data['departure_city'],
                clean_data['arrival_city'],
                clean_data['flight_number'],
                clean_data['departure_time'],
                clean_data['arrival_time'],
                clean_data['duration'],
                clean_data['price_basic'],
                clean_data['price_profit'],
                clean_data['price_maximum'],
                clean_data['date'],
                datetime.now().strftime('%Y-%m-%d')
            ))

            conn.commit()
        except Exception as e:
            print(f"❌ Ошибка сохранения: {e}")
        finally:
            conn.close()

    def get_flights_by_route(self, city_from, city_to, start_date, days=7):
        """Безопасный поиск рейсов по маршруту"""
        # Очищаем входные данные
        city_from = self.safe_string(city_from)
        city_to = self.safe_string(city_to)

        try:
            start_date = datetime.strptime(start_date, '%d.%m.%Y')
        except:
            return []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Используем параметризованные запросы для защиты
        cursor.execute('''
            SELECT * FROM flights 
            WHERE departure_city = ? 
            AND arrival_city = ?
            AND date >= ?
            AND date <= ?
            ORDER BY date, price_basic
        ''', (city_from, city_to, start_date.strftime('%Y-%m-%d'),
              (start_date + timedelta(days=days)).strftime('%Y-%m-%d')))

        results = cursor.fetchall()
        conn.close()

        flights = []
        for row in results:
            flight = {
                'flight_number': row[3],
                'departure_time': row[4],
                'arrival_time': row[5],
                'duration': row[6],
                'price_basic': row[7],
                'price_profit': row[8],
                'price_maximum': row[9],
                'date': row[10],
                'departure_city': row[1],
                'arrival_city': row[2]
            }
            flights.append(flight)

        return flights


    def get_total_flights_count(self):
        """Получает общее количество рейсов в БД"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM flights')
        count = cursor.fetchone()[0]
        conn.close()

        return count