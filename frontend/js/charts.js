class PriceCharts {
    constructor(app) {
        this.app = app;
        this.chart = null;
    }

    async showPriceChart() {
        const origin = document.getElementById('chart-origin').value;
        const destination = document.getElementById('chart-destination').value;

        if (!origin || !destination) {
            this.app.showNotification('Выберите города для построения графика', 'error');
            return;
        }

        if (origin === destination) {
            this.app.showNotification('Города не должны совпадать', 'error');
            return;
        }

        const container = document.getElementById('chart-container');
        container.style.display = 'block';

        // Показываем временный спиннер
        container.innerHTML = `
            <div class="chart-loading">
                <div class="spinner"></div>
                <p>Строим график цен...</p>
            </div>
        `;

        try {
            // Получаем данные за последние 30 дней
            const response = await fetch(`${this.app.API_BASE}/flights/search?origin=${origin}&destination=${destination}`);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Ошибка загрузки данных');
            }

            // Используем названия городов из ответа API
            this.renderPriceChart(data, data.origin, data.destination);

        } catch (error) {
            container.innerHTML = `
                <div class="chart-error">
                    <i class="fas fa-chart-line"></i>
                    <h3>Не удалось построить график</h3>
                    <p>${error.message}</p>
                </div>
            `;
            console.error('Chart error:', error);
        }
    }

    renderPriceChart(data, originName, destinationName) {
        const container = document.getElementById('chart-container');

        if (!data.flights || data.flights.length === 0) {
            container.innerHTML = `
                <div class="no-data">
                    <i class="fas fa-database"></i>
                    <h3>Нет данных для графика</h3>
                    <p>На выбранном направлении нет данных о ценах</p>
                </div>
            `;
            return;
        }

        // Подготавливаем данные для графика
        const chartData = this.prepareChartData(data.flights);

        if (chartData.labels.length === 0) {
            container.innerHTML = `
                <div class="no-data">
                    <i class="fas fa-search"></i>
                    <h3>Нет цен для отображения</h3>
                    <p>На выбранном направлении не найдено доступных цен</p>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <div class="chart-header">
                <h3>Динамика цен: ${originName} → ${destinationName}</h3>
                <div class="chart-stats">
                    <span class="stat">Минимум: ${this.app.formatPrice(chartData.stats.min)}</span>
                    <span class="stat">Максимум: ${this.app.formatPrice(chartData.stats.max)}</span>
                    <span class="stat">Среднее: ${this.app.formatPrice(chartData.stats.avg)}</span>
                </div>
            </div>
            <div class="chart-wrapper">
                <canvas id="price-chart"></canvas>
            </div>
            <div class="chart-legend">
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #e31e24"></div>
                    <span>Минимальная цена за день</span>
                </div>
            </div>
        `;

        this.createChart(chartData);
        this.addChartStyles();
    }

    prepareChartData(flights) {
        const pricesByDate = {};
        let minPrice = Infinity;
        let maxPrice = 0;
        let totalPrice = 0;
        let priceCount = 0;

        // Собираем минимальные цены по дням
        flights.forEach(dayData => {
            if (!dayData || !dayData.prices || !Array.isArray(dayData.prices)) return;

            const dayMinPrice = this.findDayMinPrice(dayData.prices);
            if (dayMinPrice && !isNaN(dayMinPrice)) {
                const date = dayData.date;
                pricesByDate[date] = dayMinPrice;

                // Обновляем статистику
                minPrice = Math.min(minPrice, dayMinPrice);
                maxPrice = Math.max(maxPrice, dayMinPrice);
                totalPrice += dayMinPrice;
                priceCount++;
            }
        });

        // Сортируем по дате
        const sortedDates = Object.keys(pricesByDate).sort((a, b) => {
            return new Date(a.split('.').reverse().join('-')) - new Date(b.split('.').reverse().join('-'));
        });

        const labels = sortedDates.map(date => {
            const d = new Date(date.split('.').reverse().join('-'));
            return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
        });

        const data = sortedDates.map(date => pricesByDate[date]);

        return {
            labels,
            data,
            stats: {
                min: minPrice !== Infinity ? minPrice : 0,
                max: maxPrice,
                avg: priceCount > 0 ? Math.round(totalPrice / priceCount) : 0
            }
        };
    }

    findDayMinPrice(prices) {
        let minPrice = Infinity;

        if (!prices || !Array.isArray(prices)) {
            return null;
        }

        // Обрабатываем новую структуру цен
        prices.forEach(priceGroup => {
            // priceGroup выглядит как: {"44684148-44684149": [{...}]}
            Object.values(priceGroup).forEach(priceArray => {
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

    createChart(chartData) {
        const ctx = document.getElementById('price-chart').getContext('2d');

        // Уничтожаем предыдущий график если есть
        if (this.chart) {
            this.chart.destroy();
        }

        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: chartData.labels,
                datasets: [{
                    label: 'Цена билета',
                    data: chartData.data,
                    borderColor: '#e31e24',
                    backgroundColor: 'rgba(227, 30, 36, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#e31e24',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 5,
                    pointHoverRadius: 7
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: (context) => {
                                return `Цена: ${this.app.formatPrice(context.parsed.y)}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        ticks: {
                            callback: (value) => this.app.formatPrice(value)
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                },
                elements: {
                    line: {
                        tension: 0.4
                    }
                }
            }
        });
    }

    addChartStyles() {
        if (!document.querySelector('.chart-styles')) {
            const styles = document.createElement('style');
            styles.className = 'chart-styles';
            styles.textContent = `
                .chart-header {
                    margin-bottom: 2rem;
                    text-align: center;
                }
                .chart-header h3 {
                    color: var(--secondary);
                    margin-bottom: 1rem;
                }
                .chart-stats {
                    display: flex;
                    justify-content: center;
                    gap: 2rem;
                    flex-wrap: wrap;
                }
                .stat {
                    background: var(--background);
                    padding: 0.5rem 1rem;
                    border-radius: var(--radius);
                    font-weight: 600;
                    color: var(--primary);
                }
                .chart-wrapper {
                    height: 400px;
                    margin-bottom: 2rem;
                }
                .chart-legend {
                    display: flex;
                    justify-content: center;
                    gap: 2rem;
                }
                .legend-item {
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                }
                .legend-color {
                    width: 20px;
                    height: 20px;
                    border-radius: 4px;
                }
                .chart-loading, .chart-error, .no-data {
                    text-align: center;
                    padding: 3rem;
                    color: var(--text-light);
                }
                .chart-loading i, .chart-error i, .no-data i {
                    font-size: 4rem;
                    margin-bottom: 1rem;
                    opacity: 0.5;
                }
            `;
            document.head.appendChild(styles);
        }
    }
}