from sqlalchemy import Column, String, Boolean, DateTime, Integer, Date, JSON, DECIMAL
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from datetime import datetime
from database import Base


class City(Base):
    __tablename__ = "cities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(10), unique=True, index=True, nullable=False)
    name_ru = Column(String(100), nullable=False)
    name_en = Column(String(100), nullable=False)
    country_ru = Column(String(50))
    country_en = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FlightCache(Base):
    __tablename__ = "flight_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    origin_city_code = Column(String(10), nullable=False, index=True)
    destination_city_code = Column(String(10), nullable=False, index=True)
    flight_date = Column(Date, nullable=False, index=True)
    search_date = Column(DateTime(timezone=True), server_default=func.now())
    adults_count = Column(Integer, default=1)
    promo_code = Column(String(50), index=True)
    flight_data = Column(JSONB, nullable=False)
    min_price = Column(DECIMAL(10, 2), index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# Убери остальные модели пока
