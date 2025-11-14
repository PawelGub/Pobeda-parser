class PobedaParserApp {
    constructor() {
        this.API_BASE = 'http://localhost:8000';
        this.cities = [];
        this.init();
    }

    async init() {
        await this.loadCities();
        this.setupEventListeners();
        this.showNotification('Добро пожаловать в Pobeda Parser!', 'success');
    }

    async loadCities() {
        try {
            const response = await fetch(`${this.API_BASE}/cities/for-frontend`);
            const data = await response.json();
            this.cities = data.cities;

            // Сохраняем также сырые данные для поиска по кодам
            this.rawCities = data.cities;

            console.log('Loaded cities:', this.cities);
            console.log('Available city codes:', this.cities.map(c => c.value));

            this.populateCitySelects();
        } catch (error) {
            this.showNotification('Ошибка загрузки городов', 'error');
            console.error('Error loading cities:', error);
        }
    }

    // ДОБАВЬТЕ ЭТОТ МЕТОД
    getCityName(cityCode) {
        if (!cityCode) return 'Неизвестный город';

        // Ищем город в загруженном списке
        const city = this.cities.find(c => c.value === cityCode);
        if (city) {
            return city.name_ru || city.label || cityCode;
        }

        // Если не нашли, возвращаем код города
        return cityCode;
    }

    // ДОБАВЬТЕ ТАКЖЕ ЭТОТ МЕТОД ДЛЯ ПОЛНОГО ИМЕНИ
    getFullCityName(cityCode) {
        if (!cityCode) return 'Неизвестный город';

        const city = this.cities.find(c => c.value === cityCode);
        if (city) {
            return `${city.name_ru} (${cityCode})`;
        }

        return cityCode;
    }

    populateCitySelects() {
        const selects = document.querySelectorAll('.city-select');
        selects.forEach(select => {
            // Сохраняем выбранное значение
            const currentValue = select.value;
            select.innerHTML = '<option value="">Выберите город</option>';

            this.cities.forEach(city => {
                const option = document.createElement('option');
                option.value = city.value;
                option.textContent = city.label;
                select.appendChild(option);
            });

            // Восстанавливаем выбранное значение если есть
            if (currentValue) {
                select.value = currentValue;
            }
        });
    }

    populateCitySelects() {
        const selects = document.querySelectorAll('.city-select');
        selects.forEach(select => {
            // Сохраняем выбранное значение
            const currentValue = select.value;
            select.innerHTML = '<option value="">Выберите город</option>';

            this.cities.forEach(city => {
                const option = document.createElement('option');
                option.value = city.value;
                option.textContent = city.label;
                select.appendChild(option);
            });

            // Восстанавливаем выбранное значение если есть
            if (currentValue) {
                select.value = currentValue;
            }
        });
    }

    setupEventListeners() {
        // Навигация
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        // Поиск рейсов
        document.getElementById('search-btn').addEventListener('click', () => {
            if (window.flightSearch) {
                window.flightSearch.searchFlights();
            }
        });

        // Поиск куда угодно
        document.getElementById('anywhere-btn').addEventListener('click', () => {
            if (window.anywhereSearch) {
                window.anywhereSearch.searchAnywhere();
            }
        });

        // Графики
        document.getElementById('chart-btn').addEventListener('click', () => {
            if (window.charts) {
                window.charts.showPriceChart();
            }
        });

        // Enter в полях ввода
        document.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                if (e.target.closest('#search-tab') && window.flightSearch) {
                    window.flightSearch.searchFlights();
                } else if (e.target.closest('#anywhere-tab') && window.anywhereSearch) {
                    window.anywhereSearch.searchAnywhere();
                }
            }
        });
    }

    switchTab(tabName) {
        // Обновляем активные кнопки
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Показываем активный контент
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');
    }

    showNotification(message, type = 'info') {
        // Создаем уведомление
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-${type === 'success' ? 'check' : type === 'error' ? 'exclamation-triangle' : 'info'}"></i>
                <span>${message}</span>
            </div>
        `;

        // Добавляем стили для уведомлений
        if (!document.querySelector('.notification-styles')) {
            const styles = document.createElement('style');
            styles.className = 'notification-styles';
            styles.textContent = `
                .notification {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    padding: 1rem 1.5rem;
                    border-radius: 8px;
                    color: white;
                    z-index: 1000;
                    animation: slideIn 0.3s ease;
                    max-width: 400px;
                }
                .notification-success { background: #10b981; }
                .notification-error { background: #ef4444; }
                .notification-info { background: #3b82f6; }
                .notification-content {
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                }
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
            `;
            document.head.appendChild(styles);
        }

        document.body.appendChild(notification);

        // Удаляем через 5 секунд
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    formatPrice(price) {
        return new Intl.NumberFormat('ru-RU', {
            style: 'currency',
            currency: 'RUB',
            minimumFractionDigits: 0
        }).format(price);
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('ru-RU', {
            day: 'numeric',
            month: 'long',
            year: 'numeric'
        });
    }
}
