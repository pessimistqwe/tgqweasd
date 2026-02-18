from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timedelta
import os
import enum

Base = declarative_base()

# Enums for Transaction
class TransactionType(str, enum.Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    BET_PLACED = "bet_placed"
    BET_WON = "bet_won"

class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    username = Column(String(255))
    display_name = Column(String(255))

    # Crypto balances
    balance_usdt = Column(Float, default=0.0)
    balance_ton = Column(Float, default=0.0)

    # For withdrawals
    withdrawal_address = Column(String(255))

    # Profile customization
    custom_username = Column(String(255), nullable=True)  # Пользовательское имя
    avatar_url = Column(String(500), nullable=True)  # URL аватара

    created_at = Column(DateTime, default=datetime.utcnow)
    is_blocked = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)

    # Relationships
    predictions = relationship("UserPrediction", back_populates="user")
    created_events = relationship("Event", back_populates="creator")
    transactions = relationship("Transaction", back_populates="user")
    # Betting engine relationships
    bets = relationship("Bet", back_populates="user", foreign_keys="Bet.user_id")
    price_predictions = relationship("PricePrediction", back_populates="user", foreign_keys="PricePrediction.user_id")

class EventCategory(str, enum.Enum):
    ALL = "all"
    POLITICS = "politics"
    SPORTS = "sports"
    CRYPTO = "crypto"
    POP_CULTURE = "pop_culture"
    BUSINESS = "business"
    SCIENCE = "science"
    OTHER = "other"

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    polymarket_id = Column(String(255), unique=True)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    category = Column(String(50), default="other")
    image_url = Column(String(500))
    options = Column(Text, nullable=False)
    end_time = Column(DateTime, nullable=False)
    resolution_time = Column(DateTime)
    is_active = Column(Boolean, default=True)
    is_resolved = Column(Boolean, default=False)
    is_moderated = Column(Boolean, default=False)
    correct_option = Column(Integer, nullable=True)
    creator_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    total_pool = Column(Float, default=0.0)
    has_chart = Column(Boolean, default=False)  # Flag for events with price history chart

    # Relationships
    creator = relationship("User", back_populates="created_events")
    predictions = relationship("UserPrediction", back_populates="event")
    event_options = relationship("EventOption", back_populates="event", cascade="all, delete-orphan")
    # Betting engine relationships
    bets = relationship("Bet", back_populates="market", foreign_keys="Bet.market_id")
    price_predictions = relationship("PricePrediction", back_populates="market", foreign_keys="PricePrediction.market_id")

class EventOption(Base):
    __tablename__ = "event_options"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    option_index = Column(Integer, nullable=False)
    option_text = Column(String(255), nullable=False)
    total_stake = Column(Float, default=0.0)
    market_stake = Column(Float, default=0.0)
    current_price = Column(Float, default=0.5)  # Current probability as price

    event = relationship("Event", back_populates="event_options")

class PriceHistory(Base):
    """История изменения цен для графика"""
    __tablename__ = "price_history"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    option_index = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)  # Probability as price (0.0 - 1.0)
    volume = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    event = relationship("Event", backref="price_history")

class BetHistory(Base):
    """История ставок для событий (спорт, политика)"""
    __tablename__ = "bet_history"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    telegram_id = Column(Integer, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    option_index = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    shares = Column(Float, default=0.0)
    price = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    event = relationship("Event", backref="bet_history")
    user = relationship("User", backref="bet_history")

class UserPrediction(Base):
    __tablename__ = "user_predictions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    option_index = Column(Integer, nullable=False)
    
    # Polymarket-style: shares and average price
    shares = Column(Float, default=0.0)  # Number of shares owned
    average_price = Column(Float, default=0.0)  # Average purchase price per share
    
    # Legacy support
    amount = Column(Float, nullable=False)
    asset = Column(String(10), default="USDT")
    timestamp = Column(DateTime, default=datetime.utcnow)

    is_winner = Column(Boolean, nullable=True)
    payout = Column(Float, default=0.0)

    user = relationship("User", back_populates="predictions")
    event = relationship("Event", back_populates="predictions")

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Float, nullable=False)
    asset = Column(String(10), default="USDT")
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)

    invoice_id = Column(String(255))
    invoice_url = Column(String(500))
    withdrawal_address = Column(String(255))

    # Additional fields for tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    admin_comment = Column(Text)
    cryptobot_invoice_id = Column(String(255))

    user = relationship("User", back_populates="transactions")


class EventComment(Base):
    """Комментарии пользователей к событиям"""
    __tablename__ = "event_comments"
    
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    telegram_id = Column(Integer, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    comment_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    is_deleted = Column(Boolean, default=False)
    is_hidden = Column(Boolean, default=False)  # Скрыто модерацией
    
    # Relationships
    user = relationship("User", backref="comments")
    event = relationship("Event", backref="comments")

# Database setup - Vercel compatible
# Используем /tmp для временной БД на Vercel, или тестовую БД если задана
db_path = os.getenv("TEST_DB_PATH", "/tmp/events.db")
engine = create_engine(f"sqlite:///{db_path}", echo=False, connect_args={"check_same_thread": False})
Base.metadata.create_all(engine)
with engine.connect() as connection:
    # Миграция: добавление market_stake
    columns = [row[1] for row in connection.execute(text("PRAGMA table_info(event_options)")).fetchall()]
    if "market_stake" not in columns:
        connection.execute(text("ALTER TABLE event_options ADD COLUMN market_stake FLOAT DEFAULT 0.0"))
        connection.commit()
    
    # Миграция: добавление current_price
    columns = [row[1] for row in connection.execute(text("PRAGMA table_info(event_options)")).fetchall()]
    if "current_price" not in columns:
        connection.execute(text("ALTER TABLE event_options ADD COLUMN current_price FLOAT DEFAULT 0.5"))
        connection.commit()
    
    # Миграция: создание таблицы price_history
    tables = [row[0] for row in connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()]
    if "price_history" not in tables:
        connection.execute(text("""
            CREATE TABLE price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                option_index INTEGER NOT NULL,
                price REAL NOT NULL,
                volume REAL DEFAULT 0.0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES events(id)
            )
        """))
        connection.execute(text("CREATE INDEX idx_price_history_event ON price_history(event_id)"))
        connection.execute(text("CREATE INDEX idx_price_history_timestamp ON price_history(timestamp)"))
        connection.commit()
    
    # Миграция: создание таблицы event_comments
    tables = [row[0] for row in connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()]
    if "event_comments" not in tables:
        connection.execute(text("""
            CREATE TABLE event_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                user_id INTEGER,
                telegram_id INTEGER NOT NULL,
                username VARCHAR(255),
                comment_text TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_deleted BOOLEAN DEFAULT 0,
                is_hidden BOOLEAN DEFAULT 0,
                FOREIGN KEY (event_id) REFERENCES events(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """))
        connection.execute(text("CREATE INDEX idx_event_comments_event ON event_comments(event_id)"))
        connection.execute(text("CREATE INDEX idx_event_comments_telegram ON event_comments(telegram_id)"))
        connection.execute(text("CREATE INDEX idx_event_comments_created ON event_comments(created_at)"))
        connection.commit()
    
    # Миграция: добавление custom_username и avatar_url
    columns = [row[1] for row in connection.execute(text("PRAGMA table_info(users)")).fetchall()]
    if "custom_username" not in columns:
        connection.execute(text("ALTER TABLE users ADD COLUMN custom_username VARCHAR(255)"))
        connection.commit()
    if "avatar_url" not in columns:
        connection.execute(text("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500)"))
        connection.commit()

    # Миграция: добавление has_chart в events
    columns = [row[1] for row in connection.execute(text("PRAGMA table_info(events)")).fetchall()]
    if "has_chart" not in columns:
        connection.execute(text("ALTER TABLE events ADD COLUMN has_chart BOOLEAN DEFAULT 0"))
        connection.commit()

    # Миграция: добавление shares и average_price в user_predictions
    columns = [row[1] for row in connection.execute(text("PRAGMA table_info(user_predictions)")).fetchall()]
    if "shares" not in columns:
        connection.execute(text("ALTER TABLE user_predictions ADD COLUMN shares FLOAT DEFAULT 0.0"))
        connection.commit()
    if "average_price" not in columns:
        connection.execute(text("ALTER TABLE user_predictions ADD COLUMN average_price FLOAT DEFAULT 0.0"))
        connection.commit()

    # Миграция: создание таблицы bet_history
    tables = [row[0] for row in connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()]
    if "bet_history" not in tables:
        connection.execute(text("""
            CREATE TABLE bet_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                user_id INTEGER,
                telegram_id INTEGER NOT NULL,
                username VARCHAR(255),
                option_index INTEGER NOT NULL,
                amount REAL NOT NULL,
                shares REAL DEFAULT 0.0,
                price REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES events(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """))
        connection.execute(text("CREATE INDEX idx_bet_history_event ON bet_history(event_id)"))
        connection.execute(text("CREATE INDEX idx_bet_history_telegram ON bet_history(telegram_id)"))
        connection.execute(text("CREATE INDEX idx_bet_history_timestamp ON bet_history(timestamp)"))
        connection.commit()

    # Миграция: создание таблицы bets
    if "bets" not in tables:
        connection.execute(text("""
            CREATE TABLE bets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                market_id INTEGER NOT NULL,
                bet_type VARCHAR(20) NOT NULL,
                direction VARCHAR(20) NOT NULL,
                amount DECIMAL(20, 8) NOT NULL,
                shares DECIMAL(20, 8) DEFAULT 0,
                entry_price DECIMAL(20, 8) NOT NULL,
                leverage DECIMAL(10, 2) DEFAULT 1,
                liquidation_price DECIMAL(20, 8),
                exit_price DECIMAL(20, 8),
                potential_payout DECIMAL(20, 8) DEFAULT 0,
                actual_payout DECIMAL(20, 8) DEFAULT 0,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                resolved_at DATETIME,
                symbol VARCHAR(50),
                take_profit_price DECIMAL(20, 8),
                stop_loss_price DECIMAL(20, 8),
                comment TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (market_id) REFERENCES events(id)
            )
        """))
        connection.execute(text("CREATE INDEX idx_bets_user_id ON bets(user_id)"))
        connection.execute(text("CREATE INDEX idx_bets_market_id ON bets(market_id)"))
        connection.execute(text("CREATE INDEX idx_bets_status ON bets(status)"))
        connection.execute(text("CREATE INDEX idx_bets_created_at ON bets(created_at)"))
        connection.execute(text("CREATE INDEX idx_bets_user_status ON bets(user_id, status)"))
        connection.commit()

    # Миграция: создание таблицы price_predictions
    if "price_predictions" not in tables:
        connection.execute(text("""
            CREATE TABLE price_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                market_id INTEGER NOT NULL,
                direction VARCHAR(20) NOT NULL,
                symbol VARCHAR(50) NOT NULL,
                amount DECIMAL(20, 8) NOT NULL,
                odds DECIMAL(10, 4) NOT NULL,
                entry_price DECIMAL(20, 8) NOT NULL,
                exit_price DECIMAL(20, 8),
                potential_payout DECIMAL(20, 8) NOT NULL,
                actual_payout DECIMAL(20, 8) DEFAULT 0,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                resolved_at DATETIME,
                duration_seconds INTEGER DEFAULT 300,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (market_id) REFERENCES events(id)
            )
        """))
        connection.execute(text("CREATE INDEX idx_price_predictions_user_id ON price_predictions(user_id)"))
        connection.execute(text("CREATE INDEX idx_price_predictions_market_id ON price_predictions(market_id)"))
        connection.execute(text("CREATE INDEX idx_price_predictions_status ON price_predictions(status)"))
        connection.execute(text("CREATE INDEX idx_price_predictions_created_at ON price_predictions(created_at)"))
        connection.commit()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
