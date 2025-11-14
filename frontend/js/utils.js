// Утилиты для работы с датами, форматами и т.д.
class Utils {
    static formatFlightTime(minutes) {
        const hours = Math.floor(minutes / 60);
        const mins = minutes % 60;
        return `${hours}ч ${mins}м`;
    }

    static getTimeDifference(departure, arrival) {
        const dep = new Date(`2000-01-01T${departure}`);
        const arr = new Date(`2000-01-01T${arrival}`);

        // Если время прибытия меньше времени вылета, значит это следующий день
        if (arr < dep) {
            arr.setDate(arr.getDate() + 1);
        }

        const diff = arr - dep;
        const hours = Math.floor(diff / (1000 * 60 * 60));
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

        return `${hours}ч ${minutes}м`;
    }

    static debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    static animateValue(element, start, end, duration) {
        const range = end - start;
        const increment = end > start ? 1 : -1;
        const stepTime = Math.abs(Math.floor(duration / range));
        let current = start;

        const timer = setInterval(() => {
            current += increment;
            element.textContent = this.formatPrice(current);

            if (current === end) {
                clearInterval(timer);
            }
        }, stepTime);
    }

    static createElement(tag, classes = '', html = '') {
        const element = document.createElement(tag);
        if (classes) element.className = classes;
        if (html) element.innerHTML = html;
        return element;
    }

    static formatPrice(price) {
        return new Intl.NumberFormat('ru-RU', {
            style: 'currency',
            currency: 'RUB',
            minimumFractionDigits: 0
        }).format(price);
    }

    static getRandomColor() {
        const colors = [
            '#e31e24', '#3b82f6', '#10b981', '#f59e0b',
            '#ef4444', '#8b5cf6', '#06b6d4', '#84cc16'
        ];
        return colors[Math.floor(Math.random() * colors.length)];
    }

    static copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            // Можно показать уведомление об успешном копировании
        }).catch(err => {
            console.error('Copy failed:', err);
        });
    }

    static isMobile() {
        return window.innerWidth <= 768;
    }

    static addCss(styles) {
        const style = document.createElement('style');
        style.textContent = styles;
        document.head.appendChild(style);
    }
}

// Дополнительные CSS стили
Utils.addCss(`
    .fade-in {
        animation: fadeIn 0.5s ease-in;
    }
    
    .slide-up {
        animation: slideUp 0.5s ease-out;
    }
    
    .pulse {
        animation: pulse 2s infinite;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    
    @keyframes slideUp {
        from { transform: translateY(20px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    
    /* Дополнительные утилитарные классы */
    .text-center { text-align: center; }
    .text-left { text-align: left; }
    .text-right { text-align: right; }
    
    .mt-1 { margin-top: 0.5rem; }
    .mt-2 { margin-top: 1rem; }
    .mt-3 { margin-top: 1.5rem; }
    .mt-4 { margin-top: 2rem; }
    
    .mb-1 { margin-bottom: 0.5rem; }
    .mb-2 { margin-bottom: 1rem; }
    .mb-3 { margin-bottom: 1.5rem; }
    .mb-4 { margin-bottom: 2rem; }
    
    .flex { display: flex; }
    .flex-center { display: flex; align-items: center; justify-content: center; }
    .flex-between { display: flex; align-items: center; justify-content: space-between; }
    .flex-column { display: flex; flex-direction: column; }
    
    .hidden { display: none; }
    .visible { display: block; }
    
    .text-primary { color: var(--primary); }
    .text-secondary { color: var(--secondary); }
    .text-muted { color: var(--text-light); }
    
    .bg-primary { background: var(--primary); }
    .bg-secondary { background: var(--secondary); }
    .bg-surface { background: var(--surface); }
`);

// Экспортируем утилиты в глобальную область видимости
window.Utils = Utils;