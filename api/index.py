# api/index.py - ВСЁ В ОДНОМ ФАЙЛЕ

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime, timedelta
import os
import enum

# Database
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    engine = create_engine(DATABASE_URL)
else:
    engine = create_engine("sqlite:///./test.db")

Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Enums
class TransactionType(str, enum.Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    BET_PLACED = "bet_placed"
    BET_WON = "bet_won"

class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

# Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, index=True)
    username = Column(String(255))
    balance_usdt = Column(Float, default=0.0)
    balance_ton = Column(Float, default=0.0)
    withdrawal_address = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    is_blocked = Column(Boolean, default=False)

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    polymarket_id = Column(String(255), unique=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    end_time = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    is_resolved = Column(Boolean, default=False)
    is_moderated = Column(Boolean, default=False)
    correct_option = Column(Integer, nullable=True)
    total_pool = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

class EventOption(Base):
    __tablename__ = "event_options"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    option_index = Column(Integer, nullable=False)
    option_text = Column(String(255), nullable=False)
    total_stake = Column(Float, default=0.0)

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
    is_paid = Column(Boolean, default=False)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Float, nullable=False)
    asset = Column(String(10), default="USDT")
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)
    invoice_id = Column(String(255), index=True)
    invoice_url = Column(String(500))
    withdrawal_address = Column(String(255))
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

# Create tables
Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI(title="Telegram Events Prediction API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def root():
    return {"message": "API Working!"}

@app.get("/events")
def get_events(db: Session = Depends(get_db)):
    try:
        now = datetime.utcnow()
        events = db.query(Event).filter(
            Event.is_active == True,
            Event.is_moderated == True,
            Event.end_time > now
        ).order_by(Event.end_time.asc()).all()
        
        result = []
        for event in events:
            options = db.query(EventOption).filter(
                EventOption.event_id == event.id
            ).order_by(EventOption.option_index.asc()).all()
            
            result.append({
                "id": event.id,
                "title": event.title,
                "description": event.description,
                "options": [{"index": opt.option_index, "text": opt.option_text} for opt in options],
                "total_pool": event.total_pool,
                "end_time": event.end_time.isoformat(),
                "time_left": (event.end_time - now).total_seconds()
            })
        
        return {"events": result, "count": len(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
