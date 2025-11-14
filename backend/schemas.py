from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

# Схемы для городов
class CityBase(BaseModel):
    code: str
    name_ru: str
    name_en: str
    country_ru: Optional[str] = None
    country_en: Optional[str] = None

class CityCreate(CityBase):
    pass

class City(CityBase):
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Схемы для рейсов (пока заглушки)
class FlightBase(BaseModel):
    origin: str
    destination: str
    date: str
    price: float
    currency: str = "RUB"

class Flight(FlightBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

# Схема для ответа API поиска рейсов
class FlightSearchResponse(BaseModel):
    origin: str
    destination: str
    date: str
    flights: list
    min_price: Optional[float] = None
    currency: str = "RUB"

# Схема для поиска "Куда угодно"
class AnywhereSearchResponse(BaseModel):
    origin: str
    date_from: str
    date_to: str
    destinations: list
    cheapest_flights: list