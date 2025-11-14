class FlightSearch {
    constructor(app) {
        this.app = app;
    }

    async searchFlights() {
        const origin = document.getElementById('origin').value;
        const destination = document.getElementById('destination').value;
        const promoCode = document.getElementById('promo-code').value;

        // Валидация
        if (!origin || !destination) {
            this.app.showNotification('Выберите города отправления и назначения', 'error');
            return;
        }

        if (origin === destination) {
            this.app.showNotification('Города отправления и назначения не могут совпадать', 'error');
            return;
        }

        // Показываем loading
        const resultsContainer = document.getElementById('search-results');
        const loading = document.getElementById('search-loading');
        const flightsContainer = document.getElementById('search-flights');

        resultsContainer.style.display = 'block';
        loading.style.display = 'block';
        flightsContainer.innerHTML = '';

        try {
            // Формируем URL
            let url = `${this.app.API_BASE}/flights/search?origin=${origin}&destination=${destination}`;
            if (promoCode) {
                url += `&promo_code=${promoCode}`;
            }

            const response = await fetch(url);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Ошибка поиска');
            }

            loading.style.display = 'none';
            this.displayFlights(data);

        } catch (error) {
            loading.style.display = 'none';
            this.app.showNotification(error.message, 'error');
            console.error('Search error:', error);
        }
    }

    displayFlights(data) {
        const container = document.getElementById('search-flights');

        if (!data.flights || data.flights.length === 0) {
            container.innerHTML = `
            <div class="no-results">
                <i class="fas fa-plane-slash"></i>
                <h3>Рейсы не найдены</h3>
                <p>На выбранном направлении нет доступных рейсов на ближайший месяц</p>
            </div>
        `;
            return;
        }

        let html = `
        <div class="search-summary">
            <div class="summary-card">
                <div class="summary-item">
                    <i class="fas fa-route"></i>
                    <div>
                        <div class="summary-label">Маршрут</div>
                        <div class="summary-value">${this.getCityName(data.origin)} → ${this.getCityName(data.destination)}</div>
                    </div>
                </div>
                <div class="summary-item">
                    <i class="fas fa-calendar-alt"></i>
                    <div>
                        <div class="summary-label">Период поиска</div>
                        <div class="summary-value">${data.total_days} дней</div>
                    </div>
                </div>
                <div class="summary-item">
                    <i class="fas fa-chart-bar"></i>
                    <div>
                        <div class="summary-label">Найдено дней с рейсами</div>
                        <div class="summary-value">${data.days_with_data}</div>
                    </div>
                </div>
                ${!data.is_complete ? `
                <div class="summary-item warning">
                    <i class="fas fa-exclamation-triangle"></i>
                    <div>
                        <div class="summary-label">Статус данных</div>
                        <div class="summary-value">Частично загружено</div>
                    </div>
                </div>
                ` : `
                <div class="summary-item success">
                    <i class="fas fa-check-circle"></i>
                    <div>
                        <div class="summary-label">Статус данных</div>
                        <div class="summary-value">Полностью загружено</div>
                    </div>
                </div>
                `}
                <div class="summary-item">
                    <i class="fas fa-tag"></i>
                    <div>
                        <div class="summary-label">Промокод</div>
                        <div class="summary-value">${data.promo_code || 'Не использован'}</div>
                    </div>
                </div>
            </div>
        </div>
    `;

        // Сортируем по дате
        const sortedFlights = data.flights
            .filter(day => day) // убираем пустые
            .sort((a, b) => new Date(a.date.split('.').reverse().join('-')) - new Date(b.date.split('.').reverse().join('-')));

        let displayedDays = 0;

        sortedFlights.forEach(dayData => {
            const minPrice = this.findMinPrice(dayData.prices);
            if (minPrice) {
                html += this.createFlightCard(dayData, minPrice);
                displayedDays++;
            }
        });

        if (displayedDays === 0) {
            container.innerHTML = `
                <div class="no-results">
                    <i class="fas fa-receipt"></i>
                    <h3>Цены не найдены</h3>
                    <p>На выбранном направлении нет доступных цен на ближайший месяц</p>
                </div>
            `;
            return;
        }

        container.innerHTML = html;
        this.addSummaryStyles();
    }

    findMinPrice(prices) {
        if (!prices || !Array.isArray(prices)) return null;

        let minPrice = Infinity;

        prices.forEach(priceList => {
            Object.values(priceList).forEach(priceArray => {
                if (Array.isArray(priceArray)) {
                    priceArray.forEach(priceInfo => {
                        if (priceInfo && priceInfo.price) {
                            const price = parseFloat(priceInfo.price);
                            if (!isNaN(price) && price < minPrice) {
                                minPrice = price;
                            }
                        }
                    });
                }
            });
        });

        return minPrice !== Infinity ? minPrice : null;
    }

    createFlightCard(dayData, minPrice) {
        const date = this.app.formatDate(dayData.date.split('.').reverse().join('-'));
        const flightsCount = dayData.flights?.length || 0;

        return `
            <div class="flight-card">
                <div class="flight-header">
                    <div class="flight-date">${date}</div>
                    <div class="flight-price">${this.app.formatPrice(minPrice)}</div>
                </div>
                <div class="flight-details">
                    <div class="flight-info">
                        <i class="fas fa-plane"></i>
                        <span>${flightsCount} рейс${this.getPlural(flightsCount)}</span>
                    </div>
                    <div class="flight-info">
                        <i class="fas fa-clock"></i>
                        <span>Лучшая цена</span>
                    </div>
                    <button class="view-details-btn" onclick="window.flightSearch.showFlightDetails('${dayData.date}')">
                        <i class="fas fa-eye"></i>
                        Подробнее
                    </button>
                </div>
                <div class="flight-details-content" id="details-${dayData.date}" style="display: none; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border);">
                    ${this.createFlightDetails(dayData)}
                </div>
            </div>
        `;
    }

    createFlightDetails(dayData) {
        if (!dayData.flights || dayData.flights.length === 0) {
            return '<p>Нет информации о рейсах</p>';
        }

        let html = '<div class="flight-details-list">';

        dayData.flights.forEach(flightGroup => {
            flightGroup.flights.forEach(flight => {
                html += `
                    <div class="flight-detail-card">
                        <div class="flight-route">
                            <div class="flight-time">
                                <strong>${flight.departuretime}</strong>
                                <span>${flight.originport}</span>
                            </div>
                            <div class="flight-duration">
                                <i class="fas fa-arrow-right"></i>
                                <span>${flight.flighttime}</span>
                            </div>
                            <div class="flight-time">
                                <strong>${flight.arrivaltime}</strong>
                                <span>${flight.destinationport}</span>
                            </div>
                        </div>
                        <div class="flight-info-row">
                            <span><i class="fas fa-plane"></i> Рейс ${flight.racenumber}</span>
                            <span><i class="fas fa-chair"></i> ${flight.airplane}</span>
                        </div>
                        ${this.createPriceTable(dayData.prices, flightGroup.chainId)}
                    </div>
                `;
            });
        });

        html += '</div>';
        return html;
    }

    createPriceTable(prices, chainId) {
        const priceInfo = prices.find(p => p[chainId]);
        if (!priceInfo) return '<p>Цены не найдены</p>';

        const tariffs = priceInfo[chainId];

        let html = `
            <div class="price-table">
                <h4>Тарифы:</h4>
                <div class="tariffs-grid">
        `;

        tariffs.forEach(tariff => {
            const brandName = this.getBrandName(tariff.brand);
            html += `
                <div class="tariff-card ${tariff.available > 0 ? 'available' : 'sold-out'}">
                    <div class="tariff-name">${brandName}</div>
                    <div class="tariff-price">${this.app.formatPrice(tariff.price)}</div>
                    <div class="tariff-availability">
                        ${tariff.available > 0 ?
                    `${tariff.available} мест` :
                    '<span class="sold-out-badge">Нет мест</span>'
                }
                    </div>
                </div>
            `;
        });

        html += '</div></div>';
        return html;
    }

    getBrandName(brandCode) {
        const brands = {
            'DP.EC.Y.1.ST': 'Стандарт',
            'DP.EC.Y.2.AD': 'Адванс',
            'DP.EC.Y.3.MX': 'Максимум'
        };
        return brands[brandCode] || brandCode;
    }

    showFlightDetails(date) {
        const details = document.getElementById(`details-${date}`);
        const isVisible = details.style.display !== 'none';

        details.style.display = isVisible ? 'none' : 'block';
    }

    getCityName(cityCode) {
        const city = this.app.cities.find(c => c.value === cityCode);
        return city ? city.name_ru : cityCode;
    }

    getPlural(number) {
        return number === 1 ? '' : number > 1 && number < 5 ? 'а' : 'ов';
    }

    addSummaryStyles() {
        if (!document.querySelector('.search-summary-styles')) {
            const styles = document.createElement('style');
            styles.className = 'search-summary-styles';
            styles.textContent = `
                .search-summary {
                    margin-bottom: 2rem;
                }
                .summary-card {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 1.5rem;
                    border-radius: var(--radius);
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 1rem;
                }
                .summary-item {
                    display: flex;
                    align-items: center;
                    gap: 1rem;
                }
                .summary-item i {
                    font-size: 1.5rem;
                    opacity: 0.9;
                }
                .summary-label {
                    font-size: 0.9rem;
                    opacity: 0.8;
                }
                .summary-value {
                    font-weight: 600;
                    font-size: 1.1rem;
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
                .flight-info {
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                }
                .view-details-btn {
                    background: var(--accent);
                    color: white;
                    border: none;
                    padding: 0.5rem 1rem;
                    border-radius: var(--radius);
                    cursor: pointer;
                    transition: all 0.3s ease;
                }
                .view-details-btn:hover {
                    background: #3182ce;
                }
                .flight-detail-card {
                    background: var(--surface);
                    padding: 1rem;
                    border-radius: var(--radius);
                    margin-bottom: 1rem;
                    border: 1px solid var(--border);
                }
                .flight-route {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    margin-bottom: 1rem;
                }
                .flight-time {
                    text-align: center;
                }
                .flight-duration {
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    color: var(--text-light);
                }
                .flight-info-row {
                    display: flex;
                    gap: 1rem;
                    margin-bottom: 1rem;
                    flex-wrap: wrap;
                }
                .price-table {
                    margin-top: 1rem;
                }
                .tariffs-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                    gap: 1rem;
                    margin-top: 0.5rem;
                }
                .tariff-card {
                    padding: 1rem;
                    border-radius: var(--radius);
                    border: 2px solid var(--border);
                    text-align: center;
                    transition: all 0.3s ease;
                }
                .tariff-card.available {
                    border-color: var(--primary);
                    background: rgba(227, 30, 36, 0.05);
                }
                .tariff-card.sold-out {
                    opacity: 0.6;
                }
                .tariff-name {
                    font-weight: 600;
                    margin-bottom: 0.5rem;
                }
                .tariff-price {
                    font-size: 1.2rem;
                    font-weight: 700;
                    color: var(--primary);
                    margin-bottom: 0.5rem;
                }
                .sold-out-badge {
                    background: var(--text-light);
                    color: white;
                    padding: 0.25rem 0.5rem;
                    border-radius: 1rem;
                    font-size: 0.8rem;
                }
            `;
            document.head.appendChild(styles);
        }
    }
}