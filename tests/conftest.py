"""
Pytest configuration and fixtures

Используется для всех тестов проекта.
"""

import pytest
import os
import sys

# Добавляем api в path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

# Устанавливаем флаг для тестового режима ДО импорта models
os.environ["TEST_MODE"] = "1"

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="session")
def test_db_url():
    """URL тестовой БД в памяти"""
    return "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_engine(test_db_url):
    """Создать движок БД"""
    engine = create_engine(
        test_db_url,
        echo=False,
        connect_args={"check_same_thread": False}
    )
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Создать сессию БД"""
    # Импортируем Base после создания engine
    from models import Base
    
    # Создаем таблицы
    Base.metadata.create_all(db_engine)
    
    # Добавляем миграции вручную
    with db_engine.connect() as connection:
        # Миграция: добавление market_stake
        try:
            connection.execute(text("ALTER TABLE event_options ADD COLUMN market_stake FLOAT DEFAULT 0.0"))
        except:
            pass
        
        # Миграция: добавление current_price
        try:
            connection.execute(text("ALTER TABLE event_options ADD COLUMN current_price FLOAT DEFAULT 0.5"))
        except:
            pass
            
        connection.commit()
    
    # Создаем сессию
    Session = sessionmaker(bind=db_engine)
    session = Session()
    
    yield session
    
    # Cleanup
    session.close()
    Base.metadata.drop_all(db_engine)
