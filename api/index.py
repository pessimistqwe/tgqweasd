from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
import json
import requests
from typing import List, Optional
import os

# Импорт моделей
try:
    from .models import (
        get_db, User, Event, EventOption, UserPrediction, 
        Transaction, TransactionType, TransactionStatus
    )
except ImportError:
    from models import (
        get_db, User, Event, EventOption, UserPrediction, 
        Transaction, TransactionType, TransactionStatus
    )

app = FastAPI(title="EventPredict API")

# CORS для работы с frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== POLYMARKET API INTEGRATION ====================

POLYMARKET_API_URL = "https://gamma-api.polymarket.com"
POLYMARKET_SYNC_INTERVAL_SECONDS = int(os.getenv("POLYMARKET_SYNC_INTERVAL", "300"))
last_polymarket_sync = datetime.min

def fetch_polymarket_events(limit: int = 50):
    """Получает активные события из Polymarket API"""
    try:
        # Получаем список активных рынков
        response = requests.get(
            f"{POLYMARKET_API_URL}/markets",
            params={
                "closed": "false",
                "active": "true",
                "limit": limit
            },
            timeout=10
        )
        response.raise_for_status()
        markets = response.json()
        
        events = []
        for market in markets:
            # Пропускаем если нет нужных данных
            if not market.get('question') or not market.get('endDate'):
                continue
                
            # Формируем структуру события
            event_data = {
                'polymarket_id': market.get('conditionId', ''),
                'title': market.get('question', ''),
                'description': market.get('description', ''),
                'end_time': market.get('endDate', ''),
                'options': [],
                'volumes': []
            }
            
            # Получаем опции (обычно Yes/No)
            tokens = market.get('tokens', [])
            for token in tokens:
                event_data['options'].append(token.get('outcome', ''))
                price = float(token.get('price', 0.5) or 0.5)
                event_data['volumes'].append(price * 1000)
            
            # Если опций нет, создаём дефолтные
            if not event_data['options']:
                event_data['options'] = ['Да', 'Нет']
                event_data['volumes'] = [500.0, 500.0]
            
            events.append(event_data)
        
        return events
    except Exception as e:
        print(f"Error fetching Polymarket events: {e}")
        return []

def parse_polymarket_end_time(end_time: str) -> datetime:
    if not end_time:
        return datetime.utcnow() + timedelta(days=7)
    try:
        return datetime.fromisoformat(end_time.replace('Z', '+00:00'))
    except Exception:
        return datetime.utcnow() + timedelta(days=7)

def update_event_total_pool(db: Session, event: Event) -> None:
    options = db.query(EventOption).filter(EventOption.event_id == event.id).all()
    event.total_pool = sum(
        (opt.total_stake or 0.0) + (opt.market_stake or 0.0)
        for opt in options
    )

def upsert_polymarket_event(db: Session, pm_event: dict) -> bool:
    end_time = parse_polymarket_end_time(pm_event.get('end_time'))
    is_active = end_time > datetime.utcnow()
    options = pm_event.get('options', [])
    volumes = pm_event.get('volumes', [])

    existing = db.query(Event).filter(
        Event.polymarket_id == pm_event['polymarket_id']
    ).first()

    if existing:
        existing.title = pm_event['title'][:500]
        existing.description = pm_event['description'][:1000] if pm_event['description'] else None
        existing.end_time = end_time
        existing.is_active = is_active
        existing.options = json.dumps(options)

        existing_options = {
            opt.option_index: opt
            for opt in db.query(EventOption).filter(EventOption.event_id == existing.id).all()
        }

        for idx, (option_text, volume) in enumerate(zip(options, volumes)):
            option = existing_options.get(idx)
            if option:
                option.option_text = option_text
                option.market_stake = volume
            else:
                db.add(EventOption(
                    event_id=existing.id,
                    option_index=idx,
                    option_text=option_text,
                    total_stake=0.0,
                    market_stake=volume
                ))

        for idx, option in existing_options.items():
            if idx >= len(options):
                db.delete(option)

        update_event_total_pool(db, existing)
        return False

    new_event = Event(
        polymarket_id=pm_event['polymarket_id'],
        title=pm_event['title'][:500],
        description=pm_event['description'][:1000] if pm_event['description'] else None,
        options=json.dumps(options),
        end_time=end_time,
        is_active=is_active,
        is_moderated=True,
        total_pool=sum(volumes)
    )
    db.add(new_event)
    db.flush()

    for idx, (option_text, volume) in enumerate(zip(options, volumes)):
        db.add(EventOption(
            event_id=new_event.id,
            option_index=idx,
            option_text=option_text,
            total_stake=0.0,
            market_stake=volume
        ))

    return True

def sync_polymarket_events(db: Session):
    """Синхронизирует события из Polymarket в БД"""
    try:
        polymarket_events = fetch_polymarket_events(limit=100)
        synced_count = 0
        
        for pm_event in polymarket_events:
            created = upsert_polymarket_event(db, pm_event)
            update_event = "Added" if created else "Updated"
            db.commit()
            synced_count += 1
            print(f"✅ {update_event} event: {pm_event['title']}")
        
        return synced_count
    except Exception as e:
        db.rollback()
        print(f"Error syncing events: {e}")
        return 0

# ==================== PYDANTIC MODELS ====================

class PredictionRequest(BaseModel):
    telegram_id: int
    event_id: int
    option_index: int
    points: float

class UserResponse(BaseModel):
    telegram_id: int
    username: Optional[str]
    points: float
    stats: dict

# ==================== API ENDPOINTS ====================

@app.get("/")
async def root():
    return {"status": "ok", "message": "EventPredict API"}

@app.get("/events")
async def get_events(db: Session = Depends(get_db)):
    """Получить все активные события"""
    try:
        global last_polymarket_sync
        now = datetime.utcnow()
        if (now - last_polymarket_sync).total_seconds() >= POLYMARKET_SYNC_INTERVAL_SECONDS:
            sync_polymarket_events(db)
            last_polymarket_sync = datetime.utcnow()
        
        # Получаем активные события
        events = db.query(Event).filter(
            Event.is_active == True,
            Event.end_time > datetime.utcnow()
        ).order_by(Event.created_at.desc()).limit(50).all()
        
        result = []
        for event in events:
            # Получаем опции
            options = db.query(EventOption).filter(
                EventOption.event_id == event.id
            ).all()
            
            # Парсим опции из JSON если нет в EventOption
            if not options and event.options:
                try:
                    options_list = json.loads(event.options)
                    for idx, opt_text in enumerate(options_list):
                        opt = EventOption(
                            event_id=event.id,
                            option_index=idx,
                            option_text=opt_text,
                            total_stake=0.0,
                            market_stake=0.0
                        )
                        db.add(opt)
                    db.commit()
                    options = db.query(EventOption).filter(
                        EventOption.event_id == event.id
                    ).all()
                except:
                    pass
            
            # Вычисляем оставшееся время
            time_left = int((event.end_time - datetime.utcnow()).total_seconds())
            total_stakes = sum(
                (opt.total_stake or 0.0) + (opt.market_stake or 0.0)
                for opt in options
            ) or 1
            
            result.append({
                "id": event.id,
                "title": event.title,
                "description": event.description,
                "end_time": event.end_time.isoformat(),
                "time_left": max(0, time_left),
                "total_pool": event.total_pool,
                "options": [
                    {
                        "index": opt.option_index,
                        "text": opt.option_text,
                        "total_points": (opt.total_stake or 0.0) + (opt.market_stake or 0.0),
                        "probability": round(((opt.total_stake or 0.0) + (opt.market_stake or 0.0)) / total_stakes * 100, 1)
                    }
                    for opt in options
                ]
            })
        
        return {"events": result}
    except Exception as e:
        print(f"Error loading events: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/{telegram_id}")
async def get_user(telegram_id: int, db: Session = Depends(get_db)):
    """Получить информацию о пользователе"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        # Создаём нового пользователя с начальными очками
        user = User(
            telegram_id=telegram_id,
            balance_usdt=1000.0  # Стартовые очки
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Статистика
    active_predictions = db.query(UserPrediction).filter(
        UserPrediction.user_id == user.id,
        UserPrediction.is_winner == None
    ).count()
    
    return {
        "telegram_id": user.telegram_id,
        "username": user.username,
        "points": user.balance_usdt,
        "stats": {
            "active_predictions": active_predictions,
            "total_won": 0,
            "total_lost": 0
        }
    }

@app.post("/predict")
async def make_prediction(request: PredictionRequest, db: Session = Depends(get_db)):
    """Сделать прогноз"""
    try:
        # Получаем пользователя
        user = db.query(User).filter(User.telegram_id == request.telegram_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        # Проверяем баланс
        if user.balance_usdt < request.points:
            raise HTTPException(status_code=400, detail="Недостаточно средств")
        
        # Проверяем событие
        event = db.query(Event).filter(Event.id == request.event_id).first()
        if not event or not event.is_active:
            raise HTTPException(status_code=404, detail="Событие не найдено")
        
        if event.end_time <= datetime.utcnow():
            raise HTTPException(status_code=400, detail="Событие завершено")
        
        # Списываем средства
        user.balance_usdt -= request.points
        
        # Создаём прогноз
        prediction = UserPrediction(
            user_id=user.id,
            event_id=event.id,
            option_index=request.option_index,
            amount=request.points,
            asset="USDT"
        )
        db.add(prediction)
        
        # Обновляем статистику опции
        option = db.query(EventOption).filter(
            EventOption.event_id == event.id,
            EventOption.option_index == request.option_index
        ).first()
        
        if option:
            option.total_stake += request.points
        
        # Обновляем общий пул
        event.total_pool += request.points
        
        db.commit()
        
        return {
            "success": True,
            "message": "Прогноз принят",
            "new_balance": user.balance_usdt
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error making prediction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/sync-polymarket")
async def manual_sync(db: Session = Depends(get_db)):
    """Ручная синхронизация событий из Polymarket"""
    try:
        count = sync_polymarket_events(db)
        return {
            "success": True,
            "message": f"Синхронизировано событий: {count}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Vercel serverless handler
handler = app
