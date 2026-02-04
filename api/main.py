from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from datetime import datetime, timedelta
import json
import requests
from typing import List, Optional
import os
import asyncio
import hashlib
import hmac

# Импорты из models.py
from models import (
    get_db, User, Event, EventOption, UserPrediction, 
    Transaction, TransactionType, TransactionStatus
)

# CryptoBot API Configuration
CRYPTOBOT_API_TOKEN = os.getenv("CRYPTOBOT_API_TOKEN", "")
CRYPTOBOT_API_URL = "https://pay.crypt.bot/api"

# Admin Telegram IDs (comma-separated in env)
ADMIN_TELEGRAM_IDS = [int(x) for x in os.getenv("ADMIN_TELEGRAM_IDS", "").split(",") if x.strip()]

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

# Ключевые слова для определения категорий
CATEGORY_KEYWORDS = {
    'politics': ['trump', 'biden', 'election', 'president', 'congress', 'senate', 'vote', 'democrat', 'republican', 'political', 'government', 'minister', 'parliament', 'putin', 'zelensky', 'ukraine', 'russia', 'china', 'nato'],
    'sports': ['nba', 'nfl', 'mlb', 'soccer', 'football', 'basketball', 'baseball', 'tennis', 'golf', 'ufc', 'boxing', 'f1', 'formula', 'championship', 'world cup', 'super bowl', 'olympics', 'game', 'match', 'team', 'player'],
    'crypto': ['bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'blockchain', 'defi', 'nft', 'token', 'coin', 'binance', 'coinbase', 'solana', 'dogecoin', 'altcoin', 'mining'],
    'pop_culture': ['movie', 'film', 'oscar', 'grammy', 'emmy', 'celebrity', 'music', 'album', 'artist', 'actor', 'actress', 'tv show', 'netflix', 'disney', 'marvel', 'star wars', 'taylor swift', 'beyonce', 'kanye'],
    'business': ['stock', 'market', 'company', 'ceo', 'ipo', 'merger', 'earnings', 'revenue', 'tesla', 'apple', 'google', 'amazon', 'microsoft', 'nvidia', 'ai', 'layoff', 'startup', 'fed', 'interest rate', 'inflation'],
    'science': ['nasa', 'spacex', 'rocket', 'mars', 'moon', 'climate', 'vaccine', 'fda', 'research', 'discovery', 'scientist', 'study', 'experiment', 'technology', 'ai model', 'gpt', 'openai']
}

def detect_category(title: str, description: str = '') -> str:
    """Определяет категорию события по заголовку и описанию"""
    text = (title + ' ' + (description or '')).lower()
    
    category_scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in text)
        if score > 0:
            category_scores[category] = score
    
    if category_scores:
        return max(category_scores, key=category_scores.get)
    return 'other'

def fetch_polymarket_events(category: str = None, limit: int = 50):
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
            timeout=15
        )
        response.raise_for_status()
        markets = response.json()
        
        events = []
        for market in markets:
            # Пропускаем если нет нужных данных
            if not market.get('question') or not market.get('endDate'):
                continue
            
            title = market.get('question', '')
            description = market.get('description', '')
            detected_category = detect_category(title, description)
            
            # Фильтруем по категории если указана
            if category and category != 'all' and detected_category != category:
                continue
                
            # Формируем структуру события
            event_data = {
                'polymarket_id': market.get('conditionId', str(market.get('id', ''))),
                'title': title,
                'description': description,
                'category': detected_category,
                'image_url': market.get('image', ''),
                'end_time': market.get('endDate', ''),
                'volume': float(market.get('volume', 0) or 0),
                'liquidity': float(market.get('liquidity', 0) or 0),
                'options': [],
                'volumes': [],
                'prices': []
            }
            
            # Получаем опции (обычно Yes/No)
            tokens = market.get('tokens', [])
            for token in tokens:
                outcome = token.get('outcome', '')
                price = float(token.get('price', 0.5) or 0.5)
                event_data['options'].append(outcome)
                event_data['prices'].append(price)
                event_data['volumes'].append(price * 1000)
            
            # Если опций нет, создаём дефолтные
            if not event_data['options']:
                event_data['options'] = ['Yes', 'No']
                event_data['prices'] = [0.5, 0.5]
                event_data['volumes'] = [500.0, 500.0]
            
            events.append(event_data)
        
        # Сортируем по объему торгов
        events.sort(key=lambda x: x.get('volume', 0), reverse=True)
        
        return events
    except Exception as e:
        print(f"Error fetching Polymarket events: {e}")
        return []

def sync_polymarket_events(db: Session, category: str = None):
    """Синхронизирует события из Polymarket в БД"""
    try:
        polymarket_events = fetch_polymarket_events(category=category, limit=100)
        added_count = 0
        
        for pm_event in polymarket_events:
            # Проверяем, существует ли событие
            existing = db.query(Event).filter(
                Event.polymarket_id == pm_event['polymarket_id']
            ).first()
            
            if existing:
                # Обновляем существующее событие
                existing.category = pm_event['category']
                existing.image_url = pm_event.get('image_url', '')
                db.commit()
                continue
            
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
                category=pm_event['category'],
                image_url=pm_event.get('image_url', ''),
                options=json.dumps(pm_event['options']),
                end_time=end_time,
                is_active=True,
                is_moderated=True,
                total_pool=sum(pm_event['volumes'])
            )
            db.add(new_event)
            db.flush()
            
            # Создаём опции с ценами
            for idx, (option_text, volume, price) in enumerate(zip(
                pm_event['options'], 
                pm_event['volumes'],
                pm_event['prices']
            )):
                event_option = EventOption(
                    event_id=new_event.id,
                    option_index=idx,
                    option_text=option_text,
                    total_stake=volume
                )
                db.add(event_option)
            
            db.commit()
            added_count += 1
            print(f"Added event: {new_event.title[:50]}... [{new_event.category}]")
        
        return added_count
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

@app.get("/categories")
async def get_categories():
    """Получить список категорий"""
    return {
        "categories": [
            {"id": "all", "name": "All", "icon": "🔥", "name_ru": "Все"},
            {"id": "politics", "name": "Politics", "icon": "🏛️", "name_ru": "Политика"},
            {"id": "sports", "name": "Sports", "icon": "⚽", "name_ru": "Спорт"},
            {"id": "crypto", "name": "Crypto", "icon": "₿", "name_ru": "Крипто"},
            {"id": "pop_culture", "name": "Pop Culture", "icon": "🎬", "name_ru": "Поп-культура"},
            {"id": "business", "name": "Business", "icon": "📈", "name_ru": "Бизнес"},
            {"id": "science", "name": "Science", "icon": "🔬", "name_ru": "Наука"},
            {"id": "other", "name": "Other", "icon": "📌", "name_ru": "Другое"}
        ]
    }

@app.get("/events")
async def get_events(category: str = None, db: Session = Depends(get_db)):
    """Получить события с фильтрацией по категории"""
    try:
        # Синхронизируем события из Polymarket (если их мало)
        event_count = db.query(Event).filter(Event.is_active == True).count()
        if event_count < 10:
            sync_polymarket_events(db, category=category)
        
        # Базовый запрос
        query = db.query(Event).filter(
            Event.is_active == True,
            Event.end_time > datetime.utcnow()
        )
        
        # Фильтр по категории
        if category and category != 'all':
            query = query.filter(Event.category == category)
        
        # Получаем активные события
        events = query.order_by(Event.total_pool.desc()).limit(50).all()
        
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
            
            # Вычисляем вероятности на основе ставок
            total_stakes = sum(opt.total_stake for opt in options) or 1
            
            result.append({
                "id": event.id,
                "title": event.title,
                "description": event.description,
                "category": event.category or "other",
                "image_url": event.image_url,
                "end_time": event.end_time.isoformat(),
                "time_left": max(0, time_left),
                "total_pool": event.total_pool,
                "options": [
                    {
                        "index": opt.option_index,
                        "text": opt.option_text,
                        "total_points": opt.total_stake,
                        "probability": round((opt.total_stake / total_stakes) * 100, 1)
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

# ==================== CRYPTOBOT PAYMENT INTEGRATION ====================

def cryptobot_request(method: str, params: dict = None):
    """Отправка запроса к CryptoBot API"""
    if not CRYPTOBOT_API_TOKEN:
        raise HTTPException(status_code=500, detail="CryptoBot API token not configured")
    
    headers = {
        "Crypto-Pay-API-Token": CRYPTOBOT_API_TOKEN,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            f"{CRYPTOBOT_API_URL}/{method}",
            headers=headers,
            json=params or {},
            timeout=30
        )
        data = response.json()
        
        if not data.get("ok"):
            error_msg = data.get("error", {}).get("name", "Unknown error")
            raise HTTPException(status_code=400, detail=f"CryptoBot error: {error_msg}")
        
        return data.get("result")
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"CryptoBot connection error: {str(e)}")

class DepositRequest(BaseModel):
    telegram_id: int
    amount: float
    asset: str = "USDT"

class WithdrawRequest(BaseModel):
    telegram_id: int
    amount: float
    asset: str = "USDT"

class AdminWithdrawAction(BaseModel):
    admin_telegram_id: int
    transaction_id: int
    action: str  # "approve" or "reject"
    comment: Optional[str] = None

@app.post("/wallet/deposit")
async def create_deposit(request: DepositRequest, db: Session = Depends(get_db)):
    """Создание инвойса для пополнения через CryptoBot"""
    try:
        # Получаем или создаём пользователя
        user = db.query(User).filter(User.telegram_id == request.telegram_id).first()
        if not user:
            user = User(telegram_id=request.telegram_id, balance_usdt=0.0)
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Минимальная сумма
        if request.amount < 1:
            raise HTTPException(status_code=400, detail="Minimum deposit is 1 USDT")
        
        # Создаём инвойс в CryptoBot
        invoice_data = cryptobot_request("createInvoice", {
            "asset": request.asset,
            "amount": str(request.amount),
            "description": f"Deposit to EventPredict",
            "hidden_message": f"user_{user.id}",
            "paid_btn_name": "callback",
            "paid_btn_url": f"https://t.me/YourBotUsername",  # Замените на вашего бота
            "allow_comments": False,
            "allow_anonymous": False,
            "expires_in": 3600  # 1 час
        })
        
        # Сохраняем транзакцию
        transaction = Transaction(
            user_id=user.id,
            type=TransactionType.DEPOSIT,
            amount=request.amount,
            asset=request.asset,
            status=TransactionStatus.PENDING,
            cryptobot_invoice_id=str(invoice_data.get("invoice_id")),
            invoice_url=invoice_data.get("pay_url")
        )
        db.add(transaction)
        db.commit()
        
        return {
            "success": True,
            "invoice_id": invoice_data.get("invoice_id"),
            "pay_url": invoice_data.get("pay_url"),
            "amount": request.amount,
            "asset": request.asset,
            "expires_in": 3600
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Deposit error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/wallet/withdraw")
async def create_withdrawal(request: WithdrawRequest, db: Session = Depends(get_db)):
    """Создание заявки на вывод (требует подтверждения админа)"""
    try:
        # Получаем пользователя
        user = db.query(User).filter(User.telegram_id == request.telegram_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Проверяем баланс
        if user.balance_usdt < request.amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")
        
        # Минимальная сумма вывода
        if request.amount < 5:
            raise HTTPException(status_code=400, detail="Minimum withdrawal is 5 USDT")
        
        # Блокируем средства (списываем с баланса)
        user.balance_usdt -= request.amount
        
        # Создаём заявку на вывод
        transaction = Transaction(
            user_id=user.id,
            type=TransactionType.WITHDRAWAL,
            amount=request.amount,
            asset=request.asset,
            status=TransactionStatus.PENDING
        )
        db.add(transaction)
        db.commit()
        
        return {
            "success": True,
            "message": "Withdrawal request created. Waiting for admin approval.",
            "transaction_id": transaction.id,
            "amount": request.amount,
            "asset": request.asset,
            "new_balance": user.balance_usdt
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Withdrawal error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/wallet/balance/{telegram_id}")
async def get_wallet_balance(telegram_id: int, db: Session = Depends(get_db)):
    """Получение баланса кошелька"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        user = User(telegram_id=telegram_id, balance_usdt=1000.0)
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Получаем историю транзакций
    transactions = db.query(Transaction).filter(
        Transaction.user_id == user.id
    ).order_by(desc(Transaction.created_at)).limit(20).all()
    
    return {
        "telegram_id": telegram_id,
        "balance_usdt": user.balance_usdt,
        "balance_ton": user.balance_ton,
        "transactions": [
            {
                "id": t.id,
                "type": t.type.value,
                "amount": t.amount,
                "asset": t.asset,
                "status": t.status.value,
                "created_at": t.created_at.isoformat() if t.created_at else None
            }
            for t in transactions
        ]
    }

@app.get("/wallet/transactions/{telegram_id}")
async def get_transactions(telegram_id: int, db: Session = Depends(get_db)):
    """Получение истории транзакций пользователя"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        return {"transactions": []}
    
    transactions = db.query(Transaction).filter(
        Transaction.user_id == user.id
    ).order_by(desc(Transaction.created_at)).limit(50).all()
    
    return {
        "transactions": [
            {
                "id": t.id,
                "type": t.type.value,
                "amount": t.amount,
                "asset": t.asset,
                "status": t.status.value,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "invoice_url": t.invoice_url
            }
            for t in transactions
        ]
    }

@app.post("/webhook/cryptobot")
async def cryptobot_webhook(payload: dict, db: Session = Depends(get_db)):
    """Вебхук для обработки платежей CryptoBot"""
    try:
        update_type = payload.get("update_type")
        
        if update_type == "invoice_paid":
            invoice = payload.get("payload", {})
            invoice_id = str(invoice.get("invoice_id"))
            
            # Находим транзакцию
            transaction = db.query(Transaction).filter(
                Transaction.cryptobot_invoice_id == invoice_id
            ).first()
            
            if transaction and transaction.status == TransactionStatus.PENDING:
                # Помечаем как выполненную
                transaction.status = TransactionStatus.COMPLETED
                
                # Пополняем баланс пользователя
                user = db.query(User).filter(User.id == transaction.user_id).first()
                if user:
                    user.balance_usdt += transaction.amount
                
                db.commit()
                return {"ok": True}
        
        return {"ok": True}
    except Exception as e:
        print(f"Webhook error: {e}")
        db.rollback()
        return {"ok": False, "error": str(e)}

# ==================== ADMIN PANEL ENDPOINTS ====================

def check_admin(telegram_id: int, db: Session) -> User:
    """Проверка прав администратора"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Проверяем по списку админов из env или по флагу в БД
    if telegram_id not in ADMIN_TELEGRAM_IDS and not user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied. Admin only.")
    
    return user

@app.get("/admin/check/{telegram_id}")
async def check_admin_status(telegram_id: int, db: Session = Depends(get_db)):
    """Проверка является ли пользователь админом"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    is_admin = telegram_id in ADMIN_TELEGRAM_IDS or (user and user.is_admin)
    return {"is_admin": is_admin}

@app.get("/admin/withdrawals")
async def get_pending_withdrawals(
    admin_telegram_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Получение списка заявок на вывод для админа"""
    check_admin(admin_telegram_id, db)
    
    # Получаем все pending выводы
    withdrawals = db.query(Transaction).filter(
        Transaction.type == TransactionType.WITHDRAWAL,
        Transaction.status == TransactionStatus.PENDING
    ).order_by(desc(Transaction.created_at)).all()
    
    result = []
    for w in withdrawals:
        user = db.query(User).filter(User.id == w.user_id).first()
        result.append({
            "id": w.id,
            "user_telegram_id": user.telegram_id if user else None,
            "username": user.username if user else None,
            "amount": w.amount,
            "asset": w.asset,
            "status": w.status.value,
            "created_at": w.created_at.isoformat() if w.created_at else None
        })
    
    return {"withdrawals": result}

@app.post("/admin/withdrawal/action")
async def process_withdrawal(request: AdminWithdrawAction, db: Session = Depends(get_db)):
    """Обработка заявки на вывод (одобрение/отклонение)"""
    check_admin(request.admin_telegram_id, db)
    
    # Находим транзакцию
    transaction = db.query(Transaction).filter(Transaction.id == request.transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if transaction.status != TransactionStatus.PENDING:
        raise HTTPException(status_code=400, detail="Transaction already processed")
    
    user = db.query(User).filter(User.id == transaction.user_id).first()
    
    if request.action == "approve":
        # Одобряем вывод
        transaction.status = TransactionStatus.APPROVED
        transaction.admin_comment = request.comment
        
        # Здесь можно добавить автоматический вывод через CryptoBot
        # cryptobot_request("transfer", {...})
        
        return {
            "success": True,
            "message": f"Withdrawal approved for {transaction.amount} {transaction.asset}"
        }
    
    elif request.action == "reject":
        # Отклоняем вывод и возвращаем средства
        transaction.status = TransactionStatus.REJECTED
        transaction.admin_comment = request.comment
        
        if user:
            user.balance_usdt += transaction.amount
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Withdrawal rejected. {transaction.amount} {transaction.asset} returned to user."
        }
    
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'approve' or 'reject'")

@app.get("/admin/stats")
async def get_admin_stats(
    admin_telegram_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Статистика для админ панели"""
    check_admin(admin_telegram_id, db)
    
    total_users = db.query(User).count()
    total_events = db.query(Event).filter(Event.is_active == True).count()
    total_predictions = db.query(UserPrediction).count()
    
    pending_withdrawals = db.query(Transaction).filter(
        Transaction.type == TransactionType.WITHDRAWAL,
        Transaction.status == TransactionStatus.PENDING
    ).count()
    
    total_deposits = db.query(Transaction).filter(
        Transaction.type == TransactionType.DEPOSIT,
        Transaction.status == TransactionStatus.COMPLETED
    ).count()
    
    return {
        "total_users": total_users,
        "total_events": total_events,
        "total_predictions": total_predictions,
        "pending_withdrawals": pending_withdrawals,
        "total_deposits": total_deposits
    }

# ==================== AUTO-SYNC POLYMARKET ====================

@app.get("/admin/force-sync")
async def force_sync_polymarket(
    admin_telegram_id: int = Query(None),
    db: Session = Depends(get_db)
):
    """Принудительная синхронизация с Polymarket"""
    try:
        count = sync_polymarket_events(db)
        return {
            "success": True,
            "synced_events": count,
            "message": f"Successfully synced {count} events from Polymarket"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
