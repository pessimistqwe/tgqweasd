from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json
import os
from dotenv import load_dotenv
from crypto_api import crypto_api
from models import (
    SessionLocal, User, Event, EventOption, UserPrediction, get_db,
    Transaction, TransactionType, TransactionStatus
)
from moderation import is_admin, approve_event, reject_event

load_dotenv()

app = FastAPI(title="Telegram Events Prediction API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://*.telegram.org", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_user_from_telegram(telegram_id: int, db: Session):
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        user = User(telegram_id=telegram_id, points=1000.0)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

@app.get("/")
def root():
    return {"message": "Telegram Events Prediction API", "version": "1.0"}

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
                "options": [{
                    "index": opt.option_index,
                    "text": opt.option_text,
                    "total_points": opt.total_points
                } for opt in options],
                "end_time": event.end_time.isoformat(),
                "time_left": (event.end_time - now).total_seconds()
            })
        
        return {"events": result, "count": len(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки событий: {str(e)}")

@app.post("/predict")
def make_prediction(
    telegram_id: int,
    event_id: int,
    option_index: int,
    points: float,
    db: Session = Depends(get_db)
):
    try:
        user = get_user_from_telegram(telegram_id, db)
        if user.points < points:
            raise HTTPException(status_code=400, detail="Недостаточно очков")
        
        event = db.query(Event).filter(
            Event.id == event_id,
            Event.is_active == True,
            Event.is_moderated == True
        ).first()
        
        if not event or event.end_time < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Событие недоступно")
        
        options = db.query(EventOption).filter(EventOption.event_id == event_id).all()
        if option_index >= len(options):
            raise HTTPException(status_code=400, detail="Неверный вариант")
        
        user.points -= points
        prediction = UserPrediction(user_id=user.id, event_id=event_id, option_index=option_index, points=points)
        db.add(prediction)
        
        option = options[option_index]
        option.total_points += points
        
        db.commit()
        return {"status": "success", "new_balance": user.points}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")

@app.get("/user/{telegram_id}")
def get_user_profile(telegram_id: int, db: Session = Depends(get_db)):
    try:
        user = get_user_from_telegram(telegram_id, db)
        active = db.query(UserPrediction).join(Event).filter(
            UserPrediction.user_id == user.id,
            Event.is_resolved == False
        ).count()
        
        return {
            "telegram_id": telegram_id,
            "points": user.points,
            "created_at": user.created_at.isoformat(),
            "stats": {
                "active_predictions": active,
                "completed_predictions": 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")

@app.post("/events/create")
def create_user_event(
    telegram_id: int,
    title: str,
    description: str,
    options: str,
    hours_until_end: int,
    db: Session = Depends(get_db)
):
    try:
        if len(title) > 500:
            raise HTTPException(status_code=400, detail="Заголовок слишком длинный")
        
        try:
            options_list = json.loads(options)
            if not isinstance(options_list, list) or len(options_list) < 2:
                raise ValueError
        except:
            raise HTTPException(status_code=400, detail="Варианты должны быть JSON массивом минимум из 2 элементов")
        
        user = get_user_from_telegram(telegram_id, db)
        event = Event(
            title=title,
            description=description,
            options=options,
            end_time=datetime.utcnow() + timedelta(hours=hours_until_end),
            creator_id=user.id,
            is_moderated=True
        )
        db.add(event)
        db.flush()
        
        for idx, opt_text in enumerate(options_list):
            option = EventOption(event_id=event.id, option_index=idx, option_text=opt_text)
            db.add(option)
        
        db.commit()
        return {"status": "success", "event_id": event.id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка создания: {str(e)}")

@app.post("/admin/approve/{event_id}")
def admin_approve(event_id: int, telegram_id: int, db: Session = Depends(get_db)):
    if not is_admin(telegram_id):
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        approve_event(event_id, db)
        return {"status": "approved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from crypto_api import crypto_api
from models import Transaction, TransactionType, TransactionStatus

# DEPOSIT ENDPOINTS
@app.post("/deposit/create")
def create_deposit(
    telegram_id: int,
    amount: float,
    asset: str = "USDT",  # USDT, TON, BTC
    db: Session = Depends(get_db)
):
    """Создать счет для пополнения"""
    try:
        user = get_user_from_telegram(telegram_id, db)
        
        # Создаем инвойс в Crypto Bot
        invoice = crypto_api.create_invoice(
            amount=amount,
            asset=asset,
            description=f"Пополнение баланса на {amount} {asset}",
            user_id=telegram_id
        )
        
        if not invoice:
            raise HTTPException(status_code=500, detail="Failed to create invoice")
        
        # Сохраняем транзакцию в БД
        transaction = Transaction(
            user_id=user.id,
            type=TransactionType.DEPOSIT,
            amount=amount,
            asset=asset,
            invoice_id=invoice["invoice_id"],
            invoice_url=invoice["pay_url"],
            status=TransactionStatus.PENDING
        )
        db.add(transaction)
        db.commit()
        
        return {
            "status": "pending",
            "invoice_url": invoice["pay_url"],
            "invoice_id": invoice["invoice_id"],
            "amount": amount,
            "asset": asset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/deposit/check")
def check_deposit(
    invoice_id: str,
    db: Session = Depends(get_db)
):
    """Проверить статус платежа и зачислить средства"""
    try:
        transaction = db.query(Transaction).filter(
            Transaction.invoice_id == invoice_id
        ).first()
        
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        if transaction.status == TransactionStatus.COMPLETED:
            return {"status": "completed", "message": "Already credited"}
        
        # Проверяем в Crypto Bot
        invoice = crypto_api.check_invoice(invoice_id)
        
        if not invoice:
            return {"status": "pending", "message": "Waiting for payment"}
        
        if invoice["status"] == "paid":
            # Зачисляем средства
            user = db.query(User).filter(User.id == transaction.user_id).first()
            
            if transaction.asset == "USDT":
                user.balance_usdt += transaction.amount
            elif transaction.asset == "TON":
                user.balance_ton += transaction.amount
            elif transaction.asset == "BTC":
                user.balance_btc += transaction.amount
            
            transaction.status = TransactionStatus.COMPLETED
            transaction.completed_at = datetime.utcnow()
            db.commit()
            
            return {
                "status": "completed",
                "amount": transaction.amount,
                "asset": transaction.asset,
                "new_balance": getattr(user, f"balance_{transaction.asset.lower()}")
            }
        
        return {"status": invoice["status"], "message": "Payment pending"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# WITHDRAWAL ENDPOINTS (ТРЕБУЕТ РУЧНОГО ПОДТВЕРЖДЕНИЯ!)
@app.post("/withdrawal/request")
def request_withdrawal(
    telegram_id: int,
    amount: float,
    asset: str,
    address: str,  # Крипто-адрес для вывода
    db: Session = Depends(get_db)
):
    """Запрос на вывод (требует модерации)"""
    try:
        user = get_user_from_telegram(telegram_id, db)
        
        # Проверяем баланс
        balance = getattr(user, f"balance_{asset.lower()}")
        if balance < amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")
        
        # Блокируем сумму на балансе
        setattr(user, f"balance_{asset.lower()}", balance - amount)
        
        # Создаем транзакцию на вывод (в статусе pending)
        transaction = Transaction(
            user_id=user.id,
            type=TransactionType.WITHDRAWAL,
            amount=amount,
            asset=asset,
            withdrawal_address=address,
            status=TransactionStatus.PENDING
        )
        db.add(transaction)
        db.commit()
        
        # ЗДЕСЬ ДОЛЖНА БЫТЬ ОТПРАВКА УВЕДОМЛЕНИЯ АДМИНУ
        # Для ручного подтверждения вывода!
        
        return {
            "status": "pending_approval",
            "transaction_id": transaction.id,
            "message": "Withdrawal request created. Waiting for admin approval."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Обновленный endpoint для ставок (теперь с реальными деньгами)
@app.post("/predict")
def make_prediction(
    telegram_id: int,
    event_id: int,
    option_index: int,
    amount: float,
    asset: str = "USDT",  # Валюта ставки
    db: Session = Depends(get_db)
):
    """Сделать ставку реальными деньгами"""
    try:
        user = get_user_from_telegram(telegram_id, db)
        
        # Проверяем баланс
        balance = getattr(user, f"balance_{asset.lower()}")
        if balance < amount:
            raise HTTPException(status_code=400, detail=f"Insufficient {asset} balance")
        
        # Проверяем событие
        event = db.query(Event).filter(
            Event.id == event_id,
            Event.is_active == True,
            Event.is_moderated == True
        ).first()
        
        if not event or event.end_time < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Event not available")
        
        # Списываем деньги
        setattr(user, f"balance_{asset.lower()}", balance - amount)
        
        # Создаем прогноз
        prediction = UserPrediction(
            user_id=user.id,
            event_id=event_id,
            option_index=option_index,
            amount=amount,
            asset=asset
        )
        db.add(prediction)
        
        # Обновляем пул события
        event.total_pool += amount
        option = db.query(EventOption).filter(
            EventOption.event_id == event_id,
            EventOption.option_index == option_index
        ).first()
        option.total_stake += amount
        
        # Создаем транзакцию
        transaction = Transaction(
            user_id=user.id,
            type=TransactionType.BET_PLACED,
            amount=amount,
            asset=asset,
            status=TransactionStatus.COMPLETED
        )
        db.add(transaction)
        
        db.commit()
        return {
            "status": "success",
            "message": f"Bet placed: {amount} {asset}",
            "remaining_balance": getattr(user, f"balance_{asset.lower()}")
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint для админа (зачисление выигрыша)
@app.post("/admin/payout")
def process_payout(
    admin_id: int,
    prediction_id: int,
    db: Session = Depends(get_db)
):
    """Зачислить выигрыш (только для админа)"""
    if not is_admin(admin_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        prediction = db.query(UserPrediction).filter(
            UserPrediction.id == prediction_id
        ).first()
        
        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")
        
        if prediction.is_winner is None:
            raise HTTPException(status_code=400, detail="Event not resolved yet")
        
        if prediction.payout <= 0:
            raise HTTPException(status_code=400, detail="No payout for this prediction")
        
        user = db.query(User).filter(User.id == prediction.user_id).first()
        
        # Зачисляем выигрыш
        current_balance = getattr(user, f"balance_{prediction.asset.lower()}")
        setattr(user, f"balance_{prediction.asset.lower()}", current_balance + prediction.payout)
        
        # Создаем транзакцию выигрыша
        transaction = Transaction(
            user_id=user.id,
            type=TransactionType.BET_WON,
            amount=prediction.payout,
            asset=prediction.asset,
            status=TransactionStatus.COMPLETED
        )
        db.add(transaction)
        db.commit()
        
        return {
            "status": "success",
            "payout": prediction.payout,
            "asset": prediction.asset,
            "new_balance": getattr(user, f"balance_{prediction.asset.lower()}")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)