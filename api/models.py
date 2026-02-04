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
    
    created_at = Column(DateTime, default=datetime.utcnow)
    is_blocked = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    
    # Relationships
    predictions = relationship("UserPrediction", back_populates="user")
    created_events = relationship("Event", back_populates="creator")
    transactions = relationship("Transaction", back_populates="user")

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
    
    # Relationships
    creator = relationship("User", back_populates="created_events")
    predictions = relationship("UserPrediction", back_populates="event")
    event_options = relationship("EventOption", back_populates="event", cascade="all, delete-orphan")

class EventOption(Base):
    __tablename__ = "event_options"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    option_index = Column(Integer, nullable=False)
    option_text = Column(String(255), nullable=False)
    total_stake = Column(Float, default=0.0)
    market_stake = Column(Float, default=0.0)
    
    event = relationship("Event", back_populates="event_options")

class UserPrediction(Base):
    __tablename__ = "user_predictions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    option_index = Column(Integer, nullable=False)
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

# Database setup - Vercel compatible
# Используем /tmp для временной БД на Vercel
db_path = "/tmp/events.db"
engine = create_engine(f"sqlite:///{db_path}", echo=False, connect_args={"check_same_thread": False})
Base.metadata.create_all(engine)
with engine.connect() as connection:
    columns = [row[1] for row in connection.execute(text("PRAGMA table_info(event_options)")).fetchall()]
    if "market_stake" not in columns:
        connection.execute(text("ALTER TABLE event_options ADD COLUMN market_stake FLOAT DEFAULT 0.0"))
        connection.commit()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
