from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
import json
import requests
from typing import List, Optional
import os

# Импорты из models.py
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

def fetch_polymarket_events():
    """Получает активные события из Polymarket API"""
    try:
        # Получаем список активных рынков
        response = requests.get(
            f"{POLYMARKET_API_URL}/markets",
            params={
                "closed": "false",
                "active": "true",
                "limit": 20
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
                event_data['volumes'].append(float(token.get('price', 0)) * 1000)
            
            # Если опций нет, создаём дефолтные
            if not event_data['options']:
                event_data['options'] = ['Да', 'Нет']
                event_data['volumes'] = [500.0, 500.0]
            
            events.append(event_data)
        
        return events
    except Exception as e:
        print(f"Error fetching Polymarket events: {e}")
        return []

def sync_polymarket_events(db: Session):
    """Синхронизирует события из Polymarket в БД"""
    try:
        polymarket_events = fetch_polymarket_events()
        
        for pm_event in polymarket_events:
            # Проверяем, существует ли событие
            existing = db.query(Event).filter(
                Event.polymarket_id == pm_event['polymarket_id']
            ).first()
            
            if existing:
                continue  # Событие уже есть
            
            # Парсим дату окончания
            try:
                end_time = datetime.fromisoformat(pm_event['end_time'].replace('Z', '+00:00'))
            except:
                end_time = datetime.utcnow() + timedelta(days=7)
            
            # Создаём событие
            new_event = Event(
                polymarket_id=pm_event['polymarket_id'],
                title=pm_event['title'][:500],
                description=pm_event['description'][:1000] if pm_event['description'] else None,
                options=json.dumps(pm_event['options']),
                end_time=end_time,
                is_active=True,
                is_moderated=True,
                total_pool=sum(pm_event['volumes'])
            )
            db.add(new_event)
            db.flush()
            
            # Создаём опции
            for idx, (option_text, volume) in enumerate(zip(pm_event['options'], pm_event['volumes'])):
                event_option = EventOption(
                    event_id=new_event.id,
                    option_index=idx,
                    option_text=option_text,
                    total_stake=volume
                )
                db.add(event_option)
            
            db.commit()
            print(f"✅ Added event: {new_event.title}")
        
        return len(polymarket_events)
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
        # Синхронизируем события из Polymarket (если их мало)
        event_count = db.query(Event).filter(Event.is_active == True).count()
        if event_count < 5:
            sync_polymarket_events(db)
        
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
                            total_stake=0.0
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
                        "total_points": opt.total_stake
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
