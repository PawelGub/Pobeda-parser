from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
from database import FlightDatabase
import time
from datetime import datetime, timedelta
import re
import json

app = Flask(__name__)
CORS(app)  # Защита CORS

# Защита от XSS инъекций
def safe_html(text):
    """Экранирование HTML символов"""
    if not text:
        return ""
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#x27;'))

# Swagger документация
SWAGGER_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Pobeda Parser API</title>
    <script src="https://unpkg.com/swagger-ui-dist@3/swagger-ui-standalone-preset.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@3/swagger-ui-bundle.js"></script>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@3/swagger-ui.css">
</head>
<body>
    <div id="swagger-ui"></div>
    <script>
        const ui = SwaggerUIBundle({
            url: "/api/swagger.json",
            dom_id: '#swagger-ui',
            presets: [SwaggerUIBundle.presets.apis],
            layout: "BaseLayout"
        })
    </script>
</body>
</html>
'''

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎯 Умный трекер цен Победы</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #2563eb;
            --primary-dark: #1d4ed8;
            --success: #10b981;
            --warning: #f59e0b;
            --error: #ef4444;
            --bg: #f8fafc;
            --card: #ffffff;
            --text: #1e293b;
            --text-light: #64748b;
            --border: #e2e8f0;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Inter', sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: var(--text);
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .glass-card {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .header { 
            text-align: center; 
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--primary), #7c3aed);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }
        
        .controls {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr auto;
            gap: 15px;
            align-items: end;
            margin-bottom: 30px;
        }
        
        @media (max-width: 768px) {
            .controls {
                grid-template-columns: 1fr;
            }
        }
        
        .form-group { display: flex; flex-direction: column; }
        .form-group label { 
            font-weight: 500; 
            margin-bottom: 5px;
            color: var(--text-light);
        }
        
        select, input, button {
            padding: 12px 16px;
            border: 2px solid var(--border);
            border-radius: 12px;
            font-size: 16px;
            transition: all 0.3s;
            background: white;
        }
        
        select:focus, input:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }
        
        button {
            background: var(--primary);
            color: white;
            border: none;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        button:hover { background: var(--primary-dark); transform: translateY(-1px); }
        button:disabled { background: var(--text-light); cursor: not-allowed; transform: none; }
        
        .progress-section { margin: 30px 0; }
        .progress-bar {
            height: 8px;
            background: var(--border);
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--success), var(--primary));
            border-radius: 10px;
            transition: width 0.5s;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            border-left: 4px solid var(--primary);
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .stat-number {
            font-size: 2rem;
            font-weight: 700;
            color: var(--primary);
        }
        
        .calendar {
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 10px;
            margin: 20px 0;
        }
        
        @media (max-width: 768px) {
            .calendar {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        
        .day {
            padding: 15px;
            border: 2px solid var(--border);
            border-radius: 12px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            background: white;
        }
        
        .day:hover { border-color: var(--primary); transform: translateY(-2px); }
        .day.cheap { background: #dcfce7; border-color: var(--success); }
        .day.expensive { background: #fecaca; border-color: var(--error); }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        }
        
        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }
        
        th {
            background: var(--primary);
            color: white;
            font-weight: 600;
        }
        
        tr:hover { background: #f8fafc; }
        
        .api-link {
            text-align: center;
            margin: 20px 0;
        }
        
        .api-link a {
            color: var(--primary);
            text-decoration: none;
            font-weight: 500;
            padding: 10px 20px;
            border: 2px solid var(--primary);
            border-radius: 8px;
            transition: all 0.3s;
        }
        
        .api-link a:hover {
            background: var(--primary);
            color: white;
        }
        
        .status-message {
            padding: 15px;
            border-radius: 12px;
            margin: 10px 0;
            text-align: center;
            font-weight: 500;
        }
        
        .status-success { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
        .status-warning { background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }
        .status-error { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
    </style>
</head>
<body>
    <div class="container">
        <div class="glass-card">
            <div class="header">
                <h1>🎯 Умный трекер цен Победы</h1>
                <p>Автоматический поиск билетов на 7 дней вперед • Данные обновляются каждые 30 минут</p>
            </div>
            
            <div class="controls">
                <div class="form-group">
                    <label>🛫 Откуда</label>
                    <select id="fromCity">
                        <option value="">Выберите город</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label>🎯 Направление</label>
                    <select id="toCity">
                        <option value="ANYWHERE">Куда угодно</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label>📅 Дата начала</label>
                    <input type="date" id="startDate">
                </div>
                
                <button onclick="loadPrices()" id="searchBtn">
                    <span>🔍</span>
                    <span>Найти билеты</span>
                </button>
            </div>
            
            <div id="statusMessage"></div>
            
            <div id="progressSection" class="progress-section" style="display: none;">
                <h3>📡 Прогресс загрузки данных</h3>
                <div class="progress-bar">
                    <div id="progressFill" class="progress-fill" style="width: 0%"></div>
                </div>
                <div id="progressText">Загрузка данных...</div>
            </div>
            
            <div id="stats" class="stats-grid" style="display: none;"></div>
            
            <div id="calendarInfo" style="display: none;">
                <h3>📅 Календарь цен на 7 дней</h3>
                <div id="priceCalendar" class="calendar"></div>
            </div>
            
            <div id="flightsList"></div>
            
            <div class="api-link">
                <a href="/api/docs" target="_blank">📚 API Documentation</a>
            </div>
        </div>
    </div>

    <script>
        const API_BASE = window.location.origin + '/api';
        const CITIES = {{ cities|tojson }};
        let priceChart = null;
        let currentPriceCalendar = {};
        
        // Инициализация
        document.addEventListener('DOMContentLoaded', function() {
            initCities();
            checkProgress();
            setInterval(checkProgress, 10000); // Проверяем прогресс каждые 10 сек
        });
        
        function initCities() {
            const fromSelect = document.getElementById('fromCity');
            const toSelect = document.getElementById('toCity');
            
            CITIES.forEach(city => {
                fromSelect.innerHTML += `<option value="${city}">${city}</option>`;
                if (city !== 'ANYWHERE') {
                    toSelect.innerHTML += `<option value="${city}">${city}</option>`;
                }
            });
            
            // Устанавливаем дату (завтра)
            const tomorrow = new Date();
            tomorrow.setDate(tomorrow.getDate() + 1);
            document.getElementById('startDate').value = tomorrow.toISOString().split('T')[0];
            document.getElementById('startDate').min = new Date().toISOString().split('T')[0];
            
            // Обновляем направления при изменении города отправления
            fromSelect.addEventListener('change', updateDestinations);
        }
        
        function updateDestinations() {
            const fromCity = document.getElementById('fromCity').value;
            const toSelect = document.getElementById('toCity');
            
            toSelect.innerHTML = '<option value="ANYWHERE">Куда угодно</option>';
            
            if (fromCity) {
                CITIES.filter(city => city !== fromCity).forEach(city => {
                    toSelect.innerHTML += `<option value="${city}">${city}</option>`;
                });
            }
        }
        
        async function checkProgress() {
            try {
                const response = await fetch(`${API_BASE}/progress`);
                const data = await response.json();
                
                const progressSection = document.getElementById('progressSection');
                const progressFill = document.getElementById('progressFill');
                const progressText = document.getElementById('progressText');
                const statusMessage = document.getElementById('statusMessage');
                
                if (data.progress) {
                    const progress = data.progress;
                    
                    if (progress.status === 'completed') {
                        progressSection.style.display = 'none';
                        if (data.total_flights > 0) {
                            showStatus('✅ Данные готовы к поиску! Найдено ' + data.total_flights + ' рейсов', 'success');
                        }
                    } else {
                        progressSection.style.display = 'block';
                        const percent = progress.total_routes > 0 ? 
                            Math.round((progress.processed_routes / progress.total_routes) * 100) : 0;
                        progressFill.style.width = percent + '%';
                        
                        progressText.innerHTML = `
                            ${progress.status === 'running' ? '🔄' : '⏳'} 
                            ${progress.current_route || 'Подготовка...'} 
                            (${percent}% • ${progress.processed_routes}/${progress.total_routes} маршрутов)
                        `;
                        
                        showStatus('⏳ Идет загрузка данных...', 'warning');
                    }
                } else if (data.total_flights > 0) {
                    progressSection.style.display = 'none';
                    showStatus('✅ Данные готовы к поиску! Найдено ' + data.total_flights + ' рейсов', 'success');
                } else {
                    showStatus('📊 База данных пуста. Запустите мониторинг.', 'warning');
                }
                
            } catch (error) {
                console.error('Ошибка проверки прогресса:', error);
                showStatus('❌ Ошибка подключения к серверу', 'error');
            }
        }
        
        function showStatus(message, type) {
            const statusMessage = document.getElementById('statusMessage');
            statusMessage.innerHTML = `<div class="status-message status-${type}">${message}</div>`;
        }
        
        async function loadPrices() {
            const fromCity = document.getElementById('fromCity').value;
            const toCity = document.getElementById('toCity').value;
            const startDate = document.getElementById('startDate').value;
            const searchBtn = document.getElementById('searchBtn');
            
            if (!fromCity) {
                showStatus('❌ Выберите город отправления', 'error');
                return;
            }
            
            if (!startDate) {
                showStatus('❌ Выберите дату начала', 'error');
                return;
            }
            
            searchBtn.disabled = true;
            searchBtn.innerHTML = '<span>⏳</span><span>Ищем билеты...</span>';
            showStatus('🔍 Ищем билеты...', 'warning');
            
            // Скрываем предыдущие результаты
            document.getElementById('calendarInfo').style.display = 'none';
            document.getElementById('stats').style.display = 'none';
            document.getElementById('flightsList').innerHTML = '';
            
            const params = new URLSearchParams({
                city_from: fromCity,
                city_to: toCity,
                date: formatDate(startDate)
            });
            
            try {
                const response = await fetch(`${API_BASE}/flights?${params}`);
                const data = await response.json();
                
                if (data.error) {
                    showStatus('❌ ' + data.error, 'error');
                } else if (data.data && data.data.length > 0) {
                    showStatus(`✅ Найдено ${data.data.length} рейсов`, 'success');
                    renderCalendar(data.data, startDate);
                    renderStats(data.data);
                    renderFlights(data.data);
                } else {
                    showStatus('❌ Рейсы не найдены', 'error');
                }
            } catch (error) {
                console.error('Ошибка:', error);
                showStatus('❌ Ошибка подключения: ' + error.message, 'error');
            } finally {
                searchBtn.disabled = false;
                searchBtn.innerHTML = '<span>🔍</span><span>Найти билеты</span>';
            }
        }
        
        function formatDate(dateString) {
            const date = new Date(dateString);
            return date.toLocaleDateString('ru-RU');
        }
        
        function renderCalendar(flights, startDate) {
            const calendarDiv = document.getElementById('priceCalendar');
            const calendarInfo = document.getElementById('calendarInfo');
            
            if (!flights || flights.length === 0) {
                calendarInfo.style.display = 'none';
                return;
            }
            
            // Группируем по датам
            const flightsByDate = {};
            flights.forEach(flight => {
                if (!flightsByDate[flight.date]) {
                    flightsByDate[flight.date] = [];
                }
                flightsByDate[flight.date].push(flight);
            });
            
            // Находим мин и макс цены
            const prices = flights.map(f => f.price_basic).filter(p => p > 0);
            const minPrice = Math.min(...prices);
            const maxPrice = Math.max(...prices);
            
            let html = '';
            const start = new Date(startDate);
            
            for (let i = 0; i < 7; i++) {
                const currentDate = new Date(start);
                currentDate.setDate(start.getDate() + i);
                const dateStr = currentDate.toISOString().split('T')[0];
                const dayFlights = flightsByDate[dateStr];
                const minPriceForDay = dayFlights ? Math.min(...dayFlights.map(f => f.price_basic)) : null;
                
                let dayClass = 'day';
                if (minPriceForDay) {
                    if (minPriceForDay === minPrice) dayClass += ' cheap';
                    if (minPriceForDay === maxPrice) dayClass += ' expensive';
                }
                
                html += `<div class="${dayClass}">
                    <div style="font-weight: bold;">${currentDate.getDate()} ${currentDate.toLocaleString('ru', { month: 'short' })}</div>
                    <div style="font-size: 12px; color: #666;">${currentDate.toLocaleString('ru', { weekday: 'short' })}</div>
                    <div style="margin-top: 5px; font-weight: bold;">${minPriceForDay ? minPriceForDay + ' ₽' : 'Нет данных'}</div>
                </div>`;
            }
            
            calendarDiv.innerHTML = html;
            calendarInfo.style.display = 'block';
        }
        
        function renderStats(flights) {
            const statsDiv = document.getElementById('stats');
            
            if (!flights || flights.length === 0) {
                statsDiv.style.display = 'none';
                return;
            }
            
            const prices = flights.map(f => f.price_basic).filter(p => p > 0);
            const minPrice = Math.min(...prices);
            const maxPrice = Math.max(...prices);
            const avgPrice = Math.round(prices.reduce((a, b) => a + b, 0) / prices.length);
            const uniqueDates = new Set(flights.map(f => f.date)).size;
            const uniqueRoutes = new Set(flights.map(f => f.departure_city + '->' + f.arrival_city)).size;
            
            statsDiv.innerHTML = `
                <div class="stat-card">
                    <div class="stat-number">${minPrice}</div>
                    <div>Минимальная цена</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${maxPrice}</div>
                    <div>Максимальная цена</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${avgPrice}</div>
                    <div>Средняя цена</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${flights.length}</div>
                    <div>Всего рейсов</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${uniqueDates}</div>
                    <div>Дней с данными</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${uniqueRoutes}</div>
                    <div>Уникальных маршрутов</div>
                </div>
            `;
            
            statsDiv.style.display = 'grid';
        }
        
        function renderFlights(flights) {
            const flightsList = document.getElementById('flightsList');
            
            if (!flights || flights.length === 0) {
                flightsList.innerHTML = '<p>Рейсы не найдены</p>';
                return;
            }
            
            let html = '<h3>🎫 Найденные рейсы</h3><table><tr><th>Дата</th><th>Рейс</th><th>Вылет</th><th>Прилет</th><th>В пути</th><th>Направление</th><th>Цена</th></tr>';
            
            flights.forEach(flight => {
                html += `<tr>
                    <td>${flight.date}</td>
                    <td>${flight.flight_number}</td>
                    <td>${flight.departure_time}</td>
                    <td>${flight.arrival_time}</td>
                    <td>${flight.duration}</td>
                    <td>${flight.departure_city} → ${flight.arrival_city}</td>
                    <td style="font-weight: bold; color: #10b981;">${flight.price_basic} ₽</td>
                </tr>`;
            });
            
            html += '</table>';
            flightsList.innerHTML = html;
        }
    </script>
</body>
</html>
'''

@app.route('/')
def home():
    cities = [
        "Москва", "Санкт-Петербург", "Сочи", "Стамбул",
        "Минеральные Воды", "Казань", "Калининград", "Аланья", "Абу-Даби", "Анталия",
        "Владикавказ", "Гюмри", "Даламан", "Дубай", "Иркутск", "Волгоград",
        "Екатеринбург", "Новосибирск", "Владивосток", "Краснодар", "Красноярск",
        "Махачкала", "Минск", "Мурманск", "Нальчик", "Омск", "Пермь", "Самара",
        "Сургут", "Уфа", "Челябинск", "Тюмень", "Ташкент"
    ]
    return render_template_string(HTML_TEMPLATE, cities=cities)

@app.route('/api/flights')
def get_flights():
    """API для поиска рейсов"""
    city_from = request.args.get('city_from', '').strip()
    city_to = request.args.get('city_to', '').strip()
    date_str = request.args.get('date', '').strip()

    # Валидация входных данных
    if not city_from:
        return jsonify({'error': 'Параметр city_from обязателен'}), 400

    if not date_str:
        return jsonify({'error': 'Параметр date обязателен (формат: dd.mm.yyyy)'}), 400

    # Проверяем формат даты
    try:
        datetime.strptime(date_str, '%d.%m.%Y')
    except ValueError:
        return jsonify({'error': 'Неверный формат даты. Используйте: dd.mm.yyyy'}), 400

    db = FlightDatabase()

    try:
        if city_to.upper() == 'ANYWHERE':
            # Для "Куда угодно" - получаем все рейсы из города
            flights = db.get_anywhere_flights(city_from, 7)
        else:
            # Конкретный маршрут
            flights = db.get_flights_by_route(city_from, city_to, date_str, 7)

        return jsonify({
            'success': True,
            'data': flights,
            'total': len(flights),
            'search_params': {
                'city_from': city_from,
                'city_to': city_to,
                'date': date_str
            }
        })

    except Exception as e:
        return jsonify({'error': f'Ошибка при поиске рейсов: {str(e)}'}), 500

@app.route('/api/progress')
def get_progress():
    """API для получения прогресса мониторинга"""
    try:
        db = FlightDatabase()
        progress = db.get_progress()
        total_flights = db.get_total_flights_count()

        return jsonify({
            'progress': progress,
            'total_flights': total_flights,
            'has_data': total_flights > 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/docs')
def swagger_ui():
    """Swagger UI интерфейс"""
    return render_template_string(SWAGGER_HTML)

@app.route('/api/swagger.json')
def swagger_json():
    """Swagger спецификация API"""
    swagger = {
        "openapi": "3.0.0",
        "info": {
            "title": "Pobeda Parser API",
            "description": "API для поиска авиабилетов авиакомпании Победа",
            "version": "1.0.0",
            "contact": {
                "name": "API Support"
            }
        },
        "servers": [
            {
                "url": "http://localhost:5000",
                "description": "Development server"
            }
        ],
        "paths": {
            "/api/flights": {
                "get": {
                    "summary": "Поиск авиарейсов",
                    "description": "Поиск рейсов на 7 дней вперед с указанной даты",
                    "parameters": [
                        {
                            "name": "city_from",
                            "in": "query",
                            "required": True,
                            "schema": {
                                "type": "string"
                            },
                            "description": "Город отправления"
                        },
                        {
                            "name": "city_to",
                            "in": "query",
                            "required": False,
                            "schema": {
                                "type": "string"
                            },
                            "description": "Город прибытия (или ANYWHERE для поиска во все города)"
                        },
                        {
                            "name": "date",
                            "in": "query",
                            "required": True,
                            "schema": {
                                "type": "string"
                            },
                            "description": "Дата начала поиска в формате dd.mm.yyyy"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Успешный поиск",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "success": {"type": "boolean"},
                                            "data": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "flight_number": {"type": "string"},
                                                        "departure_time": {"type": "string"},
                                                        "arrival_time": {"type": "string"},
                                                        "duration": {"type": "string"},
                                                        "price_basic": {"type": "integer"},
                                                        "date": {"type": "string"},
                                                        "departure_city": {"type": "string"},
                                                        "arrival_city": {"type": "string"}
                                                    }
                                                }
                                            },
                                            "total": {"type": "integer"}
                                        }
                                    }
                                }
                            }
                        },
                        "400": {
                            "description": "Неверные параметры запроса"
                        },
                        "500": {
                            "description": "Внутренняя ошибка сервера"
                        }
                    }
                }
            },
            "/api/progress": {
                "get": {
                    "summary": "Получение прогресса мониторинга",
                    "description": "Возвращает текущий статус сбора данных",
                    "responses": {
                        "200": {
                            "description": "Успешный запрос",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "progress": {
                                                "type": "object",
                                                "properties": {
                                                    "total_cities": {"type": "integer"},
                                                    "processed_cities": {"type": "integer"},
                                                    "total_routes": {"type": "integer"},
                                                    "processed_routes": {"type": "integer"},
                                                    "total_flights": {"type": "integer"},
                                                    "status": {"type": "string"},
                                                    "current_route": {"type": "string"}
                                                }
                                            },
                                            "total_flights": {"type": "integer"},
                                            "has_data": {"type": "boolean"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    return jsonify(swagger)

@app.route('/api/health')
def health_check():
    """Проверка здоровья API"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)