import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+psycopg2://pobeda_user:pobeda_password@localhost:5432/pobeda_flights"

    # API
    POBEDA_API_BASE_URL: str = "https://ticket.flypobeda.ru/websky/json"

    # Cache
    FLIGHT_CACHE_TTL_HOURS: int = 6

    # App
    DEBUG: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
