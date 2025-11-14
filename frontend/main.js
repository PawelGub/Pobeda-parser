// Инициализация после загрузки всех классов
document.addEventListener('DOMContentLoaded', function () {
    // Создаем главное приложение
    window.app = new PobedaParserApp();

    // Инициализируем модули
    window.flightSearch = new FlightSearch(window.app);
    window.anywhereSearch = new AnywhereSearch(window.app);
    window.charts = new PriceCharts(window.app);

    console.log('All modules initialized successfully');
});