class AnywhereSearch {
    constructor(app) {
        this.app = app;
        this.logger = this.setupFrontendLogger();
    }

    setupFrontendLogger() {
        return {
            info: (message, data = {}) => this.sendFrontendLog('INFO', message, data),
            error: (message, error = null) => this.sendFrontendLog('ERROR', message, {
                error: error?.message,
                stack: error?.stack
            }),
            warn: (message, data = {}) => this.sendFrontendLog('WARN', message, data),
            debug: (message, data = {}) => this.sendFrontendLog('DEBUG', message, data)
        };
    }

    async sendFrontendLog(level, message, data) {
        const logEntry = {
            timestamp: new Date().toISOString(),
            level: level,
            service: 'frontend-anywhere-search',
            message: message,
            ...data,
            userAgent: navigator.userAgent,
            url: window.location.href,
            // Добавляем метрики производительности
            performance: {
                memory: performance.memory,
                timing: performance.timing
            }
        };

        // 1. Отправляем на бекенд в ELK
        try {
            await fetch('/api/logs/frontend', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(logEntry)
            });
        } catch (error) {
            console.log('Fallback frontend log:', logEntry);
        }

        // 2. Также логируем в консоль для разработки
        console[level.toLowerCase()](`[FRONTEND] ${message}`, data);
    }

    generateSearchId() {
        return 'search_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    async searchAnywhere() {
        const origin = document.getElementById('anywhere-origin').value;
        const months = parseInt(document.getElementById('anywhere-months').value) || 1;
        const promoCode = document.getElementById('anywhere-promo').value;
        const maxPrice = document.getElementById('max-price').value;

        // Логируем начало поиска на фронтенде
        this.logger.info('Anywhere search started on frontend', {
            origin,
            months,
            promoCode,
            maxPrice,
            searchId: this.generateSearchId()
        });

        console.log('Search params:', { origin, months, promoCode, maxPrice });

        if (!origin) {
            this.app.showNotification('Выберите город отправления', 'error');
            return;
        }

        // Показываем loading
        const resultsContainer = document.getElementById('anywhere-results');
        const loading = document.getElementById('anywhere-loading');
        const flightsContainer = document.getElementById('anywhere-flights');

        resultsContainer.style.display = 'block';
        loading.style.display = 'block';

        // Показываем крутой индикатор загрузки
        flightsContainer.innerHTML = this.createFullPowerLoading(origin, months);

        try {
            // Формируем URL с правильными параметрами
            let url = `${this.app.API_BASE}/flights/anywhere?origin=${encodeURIComponent(origin)}&months_ahead=${months}`;
            if (promoCode) url += `&promo_code=${encodeURIComponent(promoCode)}`;
            if (maxPrice) url += `&max_price=${parseFloat(maxPrice)}`;

            console.log('Final URL:', url);

            const response = await fetch(url);

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('Response data:', data);

            loading.style.display = 'none';
            this.displayDestinations(data);

        } catch (error) {
            loading.style.display = 'none';
            console.error('Anywhere search full error:', error);
            this.app.showNotification(error.message || 'Ошибка поиска', 'error');
        }
    }

    createFullPowerLoading(origin, months) {
        const cityName = this.getCityName(origin);
        const monthText = this.getMonthText(months);
        const daysCount = months * 30;

        return `
            <div class="full-power-loading">
                <div class="loading-spinner"></div>
                <h3>🚀 Запускаем полномасштабный поиск "Куда угодно"!</h3>
                <p>Ищем самые дешевые билеты из <strong>${cityName}</strong> во ВСЕ доступные направления</p>
                <div class="progress-info">
                    <div class="progress-text">
                        <span>Проверяем все направления на ${months} ${monthText} вперед...</span>
                    </div>
                    <div class="progress-time">
                        <i class="fas fa-clock"></i>
                        <span>Это может занять 2-5 минут</span>
                    </div>
                </div>
                <div class="loading-features">
                    <div class="feature">
                        <i class="fas fa-check"></i>
                        <span>Проверяем ВСЕ доступные города</span>
                    </div>
                    <div class="feature">
                        <i class="fas fa-check"></i>
                        <span>Анализируем цены на ${daysCount} дней</span>
                    </div>
                    <div class="feature">
                        <i class="fas fa-check"></i>
                        <span>Ищем самые дешевые варианты</span>
                    </div>
                </div>
                <div class="loading-tip">
                    <i class="fas fa-lightbulb"></i>
                    <span>Чем больше период поиска - тем больше шансов найти выгодные предложения!</span>
                </div>
            </div>
        `;
    }

    displayDestinations(data) {
        const container = document.getElementById('anywhere-flights');

        if (!data.cheapest_flights || data.cheapest_flights.length === 0) {
            container.innerHTML = `
                <div class="no-results">
                    <i class="fas fa-globe-europe"></i>
                    <h3>Направления не найдены</h3>
                    <p>Попробуйте изменить параметры поиска</p>
                </div>
            `;
            return;
        }

        // Фильтруем ошибки и сортируем по цене
        const validFlights = data.cheapest_flights.filter(flight =>
            flight && flight.min_price && !flight.error
        ).sort((a, b) => a.min_price - b.min_price);

        if (validFlights.length === 0) {
            container.innerHTML = `
                <div class="no-results">
                    <i class="fas fa-search"></i>
                    <h3>Подходящих направлений нет</h3>
                    <p>Попробуйте увеличить максимальную цену или изменить период поиска</p>
                </div>
            `;
            return;
        }

        let html = `
            <div class="search-stats">
                <div class="stats-card">
                    <div class="stat-item">
                        <div class="stat-number">${validFlights.length}</div>
                        <div class="stat-label">направлений найдено</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number">${this.app.formatPrice(validFlights[0].min_price)}</div>
                        <div class="stat-label">самый дешевый билет</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number">${data.months_ahead || 1}</div>
                        <div class="stat-label">месяца поиска</div>
                    </div>
                </div>
            </div>
            <div class="results-header">
                <h3>🎉 Найдено ${validFlights.length} направлений из ${this.getCityName(data.origin)}</h3>
                <p class="results-subtitle">Отсортировано по цене (сначала самые дешевые)</p>
            </div>
        `;

        validFlights.forEach(flight => {
            html += this.createDestinationCard(flight, data.origin);
        });

        container.innerHTML = html;
        this.addAnywhereStyles();
        this.addFullPowerLoadingStyles();
    }

    createDestinationCard(flight, origin) {
        const date = flight.cheapest_date ?
            this.app.formatDate(flight.cheapest_date.split('.').reverse().join('-')) :
            'Дата не указана';

        const daysInfo = flight.total_days_with_prices ?
            `${flight.total_days_with_prices} дней с ценами` :
            'Данные о рейсах';

        // Определяем название страны ТОЛЬКО через английский код и словарь
        let countryName;

        if (flight.destination_country_en) {
            countryName = this.getCountryNameFromCode(flight.destination_country_en);
        } else {
            // Если английского кода нет, пытаемся определить по коду города
            countryName = this.getCountryName(flight.destination);
        }

        return `
        <div class="destination-card">
            <div class="destination-header">
                <div class="destination-flag">
                    <i class="fas fa-map-marker-alt"></i>
                </div>
                <div class="destination-info">
                    <div class="destination-name">${flight.destination_name_ru || flight.destination}</div>
                    <div class="destination-country">${countryName}</div>
                </div>
                <div class="destination-badge">
                    <span class="price-badge">Лучшая цена</span>
                </div>
            </div>
            
            <div class="destination-price">${this.app.formatPrice(flight.min_price)}</div>
            
            <div class="destination-details">
                <div class="detail-item">
                    <i class="fas fa-calendar"></i>
                    <span>${date}</span>
                </div>
                <div class="detail-item">
                    <i class="fas fa-chart-line"></i>
                    <span>${daysInfo}</span>
                </div>
                <div class="detail-item">
                    <i class="fas fa-search"></i>
                    <span>${flight.search_period_months || 1} месяц поиска</span>
                </div>
            </div>
            
            <button class="destination-button" onclick="window.anywhereSearch.bookFlight('${origin}', '${flight.destination}')">
                <i class="fas fa-shopping-cart"></i>
                Найти билеты
            </button>
        </div>
    `;
    }

    getCityName(cityCode) {
        const city = this.app.cities.find(c => c.value === cityCode);
        return city ? city.name_ru : cityCode;
    }

    getCountryName(cityCode) {
        // Сначала проверяем, есть ли город в основном массиве с информацией о стране
        const city = this.app.cities.find(c => c.value === cityCode);

        if (city && city.country_ru && city.country_ru !== 'undefined') {
            return city.country_ru;
        }

        // Если в основном массиве нет, ищем в сырых данных
        const rawCity = this.app.rawCities ? this.app.rawCities.find(c => c.code === cityCode) : null;
        if (rawCity && rawCity.country_ru) {
            return rawCity.country_ru;
        }

        // Если в данных приходит destination_country_ru - используем его
        // Для этого нужно передавать flight объект, а не только cityCode
        console.warn(`Country not found for city: ${cityCode}`);
        return 'Неизвестно';
    }

    getCountryNameFromCode(countryCode) {
        const countryMap = {
            'RU': 'Россия',
            'US': 'США',
            'TH': 'Таиланд',
            'TR': 'Турция',
            'DE': 'Германия',
            'FR': 'Франция',
            'IT': 'Италия',
            'ES': 'Испания',
            'CN': 'Китай',
            'JP': 'Япония',
            'KR': 'Корея',
            'AE': 'ОАЭ',
            'EG': 'Египет',
            'IL': 'Израиль',
            'IN': 'Индия',
            'KZ': 'Казахстан',
            'BY': 'Беларусь',
            'UA': 'Украина',
            'AZ': 'Азербайджан',
            'AM': 'Армения',
            'GE': 'Грузия',
            'UZ': 'Узбекистан',
            'TJ': 'Таджикистан',
            'TM': 'Туркменистан',
            'KG': 'Киргизия',
            'LV': 'Латвия',
            'LT': 'Литва',
            'EE': 'Эстония',
            'FI': 'Финляндия',
            'PL': 'Польша',
            'CZ': 'Чехия',
            'SK': 'Словакия',
            'HU': 'Венгрия',
            'RO': 'Румыния',
            'BG': 'Болгария',
            'GR': 'Греция',
            'CY': 'Кипр',
            'MT': 'Мальта',
            'PT': 'Португалия',
            'NL': 'Нидерланды',
            'BE': 'Бельгия',
            'CH': 'Швейцария',
            'AT': 'Австрия',
            'SE': 'Швеция',
            'NO': 'Норвегия',
            'DK': 'Дания',
            'IE': 'Ирландия',
            'GB': 'Великобритания',
            'CA': 'Канада',
            'MX': 'Мексика',
            'BR': 'Бразилия',
            'AR': 'Аргентина',
            'CL': 'Чили',
            'PE': 'Перу',
            'CO': 'Колумбия',
            'AU': 'Австралия',
            'NZ': 'Новая Зеландия',
            'ID': 'Индонезия',
            'MY': 'Малайзия',
            'SG': 'Сингапур',
            'VN': 'Вьетнам',
            'PH': 'Филиппины',
            'SA': 'Саудовская Аравия',
            'QA': 'Катар',
            'OM': 'Оман',
            'BH': 'Бахрейн',
            'KW': 'Кувейт',
            'JO': 'Иордания',
            'LB': 'Ливан',
            'SY': 'Сирия',
            'IQ': 'Ирак',
            'IR': 'Иран',
            'PK': 'Пакистан',
            'BD': 'Бангладеш',
            'LK': 'Шри-Ланка',
            'NP': 'Непал',
            'MM': 'Мьянма',
            'KH': 'Камбоджа',
            'LA': 'Лаос',
            'MN': 'Монголия',
            'KP': 'КНДР',
            'TW': 'Тайвань',
            'HK': 'Гонконг',
            'MO': 'Макао'
        };

        return countryMap[countryCode] || countryCode;
    }

    getMonthText(months) {
        if (months === 1) return 'месяц';
        if (months >= 2 && months <= 4) return 'месяца';
        return 'месяцев';
    }

    bookFlight(origin, destination) {
        // Переключаем на вкладку поиска и заполняем поля
        window.app.switchTab('search');

        document.getElementById('origin').value = origin;
        document.getElementById('destination').value = destination;

        // Запускаем поиск
        setTimeout(() => {
            window.flightSearch.searchFlights();
        }, 500);

        window.app.showNotification(`Поиск рейсов ${origin} → ${destination}`, 'info');
    }

    addFullPowerLoadingStyles() {
        if (!document.querySelector('.full-power-styles')) {
            const styles = document.createElement('style');
            styles.className = 'full-power-styles';
            styles.textContent = `
                .full-power-loading {
                    text-align: center;
                    padding: 3rem 2rem;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border-radius: var(--radius);
                    margin: 2rem 0;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                }
                .loading-spinner {
                    width: 60px;
                    height: 60px;
                    border: 4px solid rgba(255,255,255,0.3);
                    border-top: 4px solid white;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin: 0 auto 2rem;
                }
                .full-power-loading h3 {
                    font-size: 1.5rem;
                    margin-bottom: 1rem;
                    font-weight: 700;
                }
                .full-power-loading p {
                    font-size: 1.1rem;
                    margin-bottom: 2rem;
                    opacity: 0.9;
                }
                .progress-info {
                    background: rgba(255,255,255,0.1);
                    padding: 1.5rem;
                    border-radius: var(--radius);
                    margin-bottom: 2rem;
                    border: 1px solid rgba(255,255,255,0.2);
                }
                .progress-text {
                    font-size: 1.1rem;
                    font-weight: 600;
                    margin-bottom: 1rem;
                }
                .progress-time {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 0.5rem;
                    opacity: 0.8;
                }
                .loading-features {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 1rem;
                    margin-bottom: 2rem;
                }
                .feature {
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                    background: rgba(255,255,255,0.1);
                    padding: 1rem;
                    border-radius: var(--radius);
                    backdrop-filter: blur(10px);
                }
                .feature i {
                    color: #4ade80;
                }
                .loading-tip {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 0.5rem;
                    background: rgba(255,255,255,0.15);
                    padding: 1rem;
                    border-radius: var(--radius);
                    font-style: italic;
                    border-left: 4px solid #f59e0b;
                }
                .loading-tip i {
                    color: #f59e0b;
                }
                .results-header {
                    text-align: center;
                    margin-bottom: 2rem;
                    padding: 1.5rem;
                    background: var(--surface);
                    border-radius: var(--radius);
                    border-left: 4px solid var(--primary);
                }
                .results-header h3 {
                    color: var(--secondary);
                    margin-bottom: 0.5rem;
                }
                .results-subtitle {
                    color: var(--text-light);
                    font-size: 0.9rem;
                }
                .destination-badge {
                    margin-left: auto;
                }
                .price-badge {
                    background: var(--primary);
                    color: white;
                    padding: 0.25rem 0.75rem;
                    border-radius: 1rem;
                    font-size: 0.8rem;
                    font-weight: 600;
                }
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            `;
            document.head.appendChild(styles);
        }
    }

    addAnywhereStyles() {
        if (!document.querySelector('.anywhere-styles')) {
            const styles = document.createElement('style');
            styles.className = 'anywhere-styles';
            styles.textContent = `
                .search-stats {
                    margin-bottom: 2rem;
                }
                .stats-card {
                    background: linear-gradient(135deg, #fd746c 0%, #ff9068 100%);
                    color: white;
                    padding: 1.5rem;
                    border-radius: var(--radius);
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                    gap: 1rem;
                    text-align: center;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                }
                .stat-number {
                    font-size: 1.5rem;
                    font-weight: 700;
                    margin-bottom: 0.25rem;
                }
                .stat-label {
                    font-size: 0.9rem;
                    opacity: 0.9;
                }
                .destination-card {
                    background: white;
                    border-radius: var(--radius);
                    padding: 1.5rem;
                    margin-bottom: 1rem;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                    border: 1px solid var(--border);
                    transition: all 0.3s ease;
                }
                .destination-card:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 5px 20px rgba(0,0,0,0.15);
                }
                .destination-header {
                    display: flex;
                    align-items: center;
                    gap: 1rem;
                    margin-bottom: 1rem;
                }
                .destination-flag {
                    width: 40px;
                    height: 40px;
                    background: var(--primary);
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    flex-shrink: 0;
                }
                .destination-info {
                    flex: 1;
                }
                .destination-name {
                    font-weight: 600;
                    font-size: 1.1rem;
                    color: var(--secondary);
                }
                .destination-country {
                    font-size: 0.9rem;
                    color: var(--text-light);
                    margin-top: 0.25rem;
                }
                .destination-price {
                    font-size: 2rem;
                    font-weight: 700;
                    color: var(--primary);
                    text-align: center;
                    margin: 1rem 0;
                    background: rgba(227, 30, 36, 0.1);
                    padding: 0.75rem;
                    border-radius: var(--radius);
                    border: 2px solid rgba(227, 30, 36, 0.2);
                }
                .destination-details {
                    margin-bottom: 1.5rem;
                }
                .detail-item {
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    margin-bottom: 0.5rem;
                    color: var(--text-light);
                    font-size: 0.9rem;
                }
                .destination-button {
                    width: 100%;
                    background: var(--primary);
                    color: white;
                    border: none;
                    padding: 0.75rem 1rem;
                    border-radius: var(--radius);
                    cursor: pointer;
                    transition: all 0.3s ease;
                    font-weight: 500;
                    font-size: 1rem;
                }
                .destination-button:hover {
                    background: var(--primary-dark);
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(227, 30, 36, 0.3);
                }
                .no-results {
                    text-align: center;
                    padding: 3rem;
                    color: var(--text-light);
                }
                .no-results i {
                    font-size: 4rem;
                    margin-bottom: 1rem;
                    opacity: 0.5;
                }
            `;
            document.head.appendChild(styles);
        }
    }
}