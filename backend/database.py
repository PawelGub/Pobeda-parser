from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from config import settings
import selectors
import asyncio

# ФИКС для Windows - используем другой селектор
if hasattr(selectors, "DefaultSelector"):
    # Это фиксит проблему с file descriptors в Windows
    pass

# Создаем engine с оптимизированными настройками
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=20,  # Увеличиваем пул соединений
    max_overflow=30,  # Увеличиваем временные соединения
    echo=False,  # Выключаем логирование SQL
)

# Создаем SessionLocal класс
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для моделей
Base = declarative_base()


# Dependency для FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Функция для создания таблиц
def create_tables():
    from models import Base

    Base.metadata.create_all(bind=engine)
