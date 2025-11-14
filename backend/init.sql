-- Создаем расширение для UUID если нужно
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Таблица городов
CREATE TABLE IF NOT EXISTS cities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(10) UNIQUE NOT NULL,
    name_ru VARCHAR(100) NOT NULL,
    name_en VARCHAR(100) NOT NULL,
    country_ru VARCHAR(50),
    country_en VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для городов
CREATE INDEX IF NOT EXISTS idx_cities_code ON cities(code);
CREATE INDEX IF NOT EXISTS idx_cities_country ON cities(country_en);
CREATE INDEX IF NOT EXISTS idx_cities_active ON cities(is_active);

-- Таблица кеша рейсов
CREATE TABLE IF NOT EXISTS flight_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    origin_city_code VARCHAR(10) NOT NULL,
    destination_city_code VARCHAR(10) NOT NULL,
    flight_date DATE NOT NULL,
    search_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    adults_count INTEGER DEFAULT 1,
    promo_code VARCHAR(50),

    -- Данные рейсов (храним как JSON для гибкости)
    flight_data JSONB NOT NULL,

    -- Минимальная цена для быстрого поиска
    min_price DECIMAL(10,2),

    -- Время жизни кеша
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для быстрого поиска рейсов
CREATE INDEX IF NOT EXISTS idx_flight_cache_route ON flight_cache(origin_city_code, destination_city_code);
CREATE INDEX IF NOT EXISTS idx_flight_cache_date ON flight_cache(flight_date);
CREATE INDEX IF NOT EXISTS idx_flight_cache_search ON flight_cache(origin_city_code, destination_city_code, flight_date);
CREATE INDEX IF NOT EXISTS idx_flight_cache_promo ON flight_cache(promo_code);
CREATE INDEX IF NOT EXISTS idx_flight_cache_price ON flight_cache(min_price);
CREATE INDEX IF NOT EXISTS idx_flight_cache_expires ON flight_cache(expires_at);

-- Таблица промокодов
CREATE TABLE IF NOT EXISTS promo_codes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Таблица поисковых запросов (для аналитики)
CREATE TABLE IF NOT EXISTS search_queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    origin_city_code VARCHAR(10),
    destination_city_code VARCHAR(10),
    search_type VARCHAR(20) NOT NULL, -- 'specific', 'anywhere', 'dates_range'
    dates_range DATERANGE,
    promo_code VARCHAR(50),
    user_ip INET,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Функция для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггер для автоматического обновления updated_at
CREATE TRIGGER update_cities_updated_at BEFORE UPDATE ON cities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Вставляем тестовые данные если нужно
INSERT INTO cities (code, name_ru, name_en, country_ru, country_en) VALUES
    ('MOW', 'Москва', 'Moscow', 'Россия', 'Russia'),
    ('LED', 'Санкт-Петербург', 'St Petersburg', 'Россия', 'Russia'),
    ('SVX', 'Екатеринбург', 'Yekaterinburg', 'Россия', 'Russia')
ON CONFLICT (code) DO UPDATE SET
    name_ru = EXCLUDED.name_ru,
    name_en = EXCLUDED.name_en,
    updated_at = CURRENT_TIMESTAMP;