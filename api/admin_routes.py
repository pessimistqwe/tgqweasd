"""
Admin Routes - Расширенные endpoints для админ-панели

Функционал:
- Просмотр всех активных ставок
- Ручное разрешение спорных событий
- Настройка комиссии платформы
- Бан пользователей
- Статистика по доходам платформы
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal

try:
    from .models import (
        get_db, User, Event, EventOption, UserPrediction,
        Transaction, TransactionType, TransactionStatus,
        BetHistory, EventComment
    )
    from .betting_models import Bet
except ImportError:
    from models import (
        get_db, User, Event, EventOption, UserPrediction,
        Transaction, TransactionType, TransactionStatus,
        BetHistory, EventComment
    )
    from betting_models import Bet

router = APIRouter(prefix="/api/admin", tags=["Admin"])

# Admin Telegram ID из переменных окружения
import os
ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "1972885597"))


# ==================== Pydantic Models ====================

class PlatformCommissionUpdate(BaseModel):
    """Обновление комиссии платформы"""
    commission_percent: float = Field(..., ge=0, le=10, description="Комиссия в процентах (0-10%)")


class UserBanRequest(BaseModel):
    """Запрос на бан пользователя"""
    telegram_id: int
    reason: str = Field(..., description="Причина бана")
    is_blocked: bool = True


class EventResolveRequest(BaseModel):
    """Запрос на разрешение события"""
    event_id: int
    winning_option_index: int = Field(..., description="Индекс выигрышного варианта (0, 1, ...)")
    resolution_time: Optional[str] = None


class ActiveBetsResponse(BaseModel):
    """Ответ со списком активных ставок"""
    total_bets: int
    total_volume: float
    bets: List[Dict[str, Any]]


class PlatformStatsResponse(BaseModel):
    """Статистика платформы"""
    total_users: int
    active_users_24h: int
    total_events: int
    active_events: int
    resolved_events: int
    total_volume: float
    total_commission_earned: float
    pending_withdrawals: int
    blocked_users: int


# ==================== Helper Functions ====================

def check_admin(telegram_id: int):
    """Проверяет права администратора"""
    if telegram_id != ADMIN_TELEGRAM_ID:
        raise HTTPException(status_code=403, detail="Not authorized. Admin only.")
    return True


# ==================== Active Bets ====================

@router.get("/bets/active", response_model=ActiveBetsResponse)
async def get_active_bets(
    telegram_id: int = Query(..., description="Telegram ID администратора"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Получить все активные ставки
    
    Требуются права администратора.
    """
    check_admin(telegram_id)
    
    # Получаем активные ставки из таблицы bets
    active_bets = db.query(Bet).filter(
        Bet.status == "open"
    ).order_by(Bet.created_at.desc()).limit(limit).offset(offset).all()
    
    # Считаем общий объем
    total_volume = db.query(func.sum(Bet.amount)).filter(
        Bet.status == "open"
    ).scalar() or 0.0
    
    return {
        "total_bets": len(active_bets),
        "total_volume": float(total_volume),
        "bets": [
            {
                "id": bet.id,
                "user_id": bet.user_id,
                "market_id": bet.market_id,
                "bet_type": bet.bet_type,
                "direction": bet.direction,
                "amount": str(bet.amount),
                "shares": str(bet.shares) if bet.shares else "0",
                "entry_price": str(bet.entry_price),
                "leverage": str(bet.leverage) if bet.leverage else "1",
                "potential_payout": str(bet.potential_payout) if bet.potential_payout else "0",
                "status": bet.status,
                "created_at": bet.created_at.isoformat() if bet.created_at else None,
                "symbol": bet.symbol
            }
            for bet in active_bets
        ]
    }


@router.get("/bets/history")
async def get_bets_history(
    telegram_id: int = Query(..., description="Telegram ID администратора"),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Получить историю ставок за период
    
    Требуются права администратора.
    """
    check_admin(telegram_id)
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    bets = db.query(Bet).filter(
        Bet.resolved_at >= cutoff_date
    ).order_by(Bet.resolved_at.desc()).limit(500).all()
    
    return {
        "total": len(bets),
        "period_days": days,
        "bets": [
            {
                "id": bet.id,
                "user_id": bet.user_id,
                "bet_type": bet.bet_type,
                "direction": bet.direction,
                "amount": str(bet.amount),
                "actual_payout": str(bet.actual_payout) if bet.actual_payout else "0",
                "status": bet.status,
                "resolved_at": bet.resolved_at.isoformat() if bet.resolved_at else None
            }
            for bet in bets
        ]
    }


# ==================== Event Resolution ====================

@router.post("/events/resolve")
async def resolve_event(
    request: EventResolveRequest,
    telegram_id: int = Query(..., description="Telegram ID администратора"),
    db: Session = Depends(get_db)
):
    """
    Разрешить событие вручную
    
    Используется для спорных событий или когда оракул не сработал.
    Требуются права администратора.
    """
    check_admin(telegram_id)
    
    event = db.query(Event).filter(Event.id == request.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if event.is_resolved:
        raise HTTPException(status_code=400, detail="Event already resolved")
    
    # Обновляем событие
    event.is_resolved = True
    event.correct_option = request.winning_option_index
    
    if request.resolution_time:
        try:
            event.resolution_time = datetime.fromisoformat(request.resolution_time)
        except ValueError:
            event.resolution_time = datetime.utcnow()
    else:
        event.resolution_time = datetime.utcnow()
    
    # Рассчитываем выигрыши
    options = db.query(EventOption).filter(
        EventOption.event_id == event.id
    ).all()
    
    winning_option = None
    for opt in options:
        if opt.option_index == request.winning_option_index:
            winning_option = opt
            break
    
    if not winning_option:
        raise HTTPException(status_code=400, detail="Winning option not found")
    
    # Находим все ставки на это событие
    predictions = db.query(UserPrediction).filter(
        UserPrediction.event_id == event.id,
        UserPrediction.option_index == request.winning_option_index
    ).all()
    
    total_payout = 0.0
    
    for prediction in predictions:
        user = db.query(User).filter(User.id == prediction.user_id).first()
        if user and not user.is_blocked:
            # Вычисляем выигрыш
            payout = prediction.shares * 1.0  # Каждая акция стоит $1 при выигрыше
            user.balance_usdt += payout
            prediction.payout = payout
            prediction.is_winner = True
            total_payout += payout
    
    # Создаем транзакции для выигрышей
    for prediction in predictions:
        if prediction.payout > 0:
            transaction = Transaction(
                user_id=prediction.user_id,
                type=TransactionType.BET_WON,
                amount=prediction.payout,
                status=TransactionStatus.COMPLETED,
                admin_comment=f"Payout for event {event.id}, option {request.winning_option_index}"
            )
            db.add(transaction)
    
    db.commit()
    
    return {
        "success": True,
        "event_id": event.id,
        "winning_option": request.winning_option_index,
        "total_payout": total_payout,
        "winners_count": len(predictions)
    }


# ==================== Platform Commission ====================

# Хранилище комиссии платформы (в продакшене использовать БД или Redis)
_platform_commission = {"percent": 3.0}  # 3% по умолчанию


@router.get("/commission")
async def get_platform_commission(
    telegram_id: int = Query(..., description="Telegram ID администратора")
):
    """
    Получить текущую комиссию платформы
    
    Требуются права администратора.
    """
    check_admin(telegram_id)
    
    return {
        "commission_percent": _platform_commission["percent"],
        "last_updated": datetime.utcnow().isoformat()
    }


@router.post("/commission")
async def update_platform_commission(
    request: PlatformCommissionUpdate,
    telegram_id: int = Query(..., description="Telegram ID администратора")
):
    """
    Обновить комиссию платформы
    
    Значение от 0% до 10%.
    Требуются права администратора.
    """
    check_admin(telegram_id)
    
    _platform_commission["percent"] = request.commission_percent
    
    return {
        "success": True,
        "commission_percent": request.commission_percent,
        "message": f"Commission updated to {request.commission_percent}%"
    }


# ==================== User Management ====================

@router.post("/users/ban")
async def ban_user(
    request: UserBanRequest,
    telegram_id: int = Query(..., description="Telegram ID администратора"),
    db: Session = Depends(get_db)
):
    """
    Забанить или разбанить пользователя
    
    Требуются права администратора.
    """
    check_admin(telegram_id)
    
    user = db.query(User).filter(User.telegram_id == request.telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_blocked = request.is_blocked
    
    # Логируем действие в транзакции
    transaction = Transaction(
        user_id=user.id,
        type=TransactionType.WITHDRAWAL,  # Используем как лог
        amount=0,
        status=TransactionStatus.COMPLETED,
        admin_comment=f"User {'blocked' if request.is_blocked else 'unblocked'}. Reason: {request.reason}"
    )
    db.add(transaction)
    db.commit()
    
    return {
        "success": True,
        "user_telegram_id": request.telegram_id,
        "is_blocked": request.is_blocked,
        "reason": request.reason
    }


@router.get("/users/blocked")
async def get_blocked_users(
    telegram_id: int = Query(..., description="Telegram ID администратора"),
    db: Session = Depends(get_db)
):
    """
    Получить список заблокированных пользователей
    
    Требуются права администратора.
    """
    check_admin(telegram_id)
    
    users = db.query(User).filter(User.is_blocked == True).all()
    
    return {
        "total": len(users),
        "users": [
            {
                "telegram_id": u.telegram_id,
                "username": u.username,
                "blocked_since": u.created_at.isoformat()  # Используем created_at как заглушку
            }
            for u in users
        ]
    }


# ==================== Platform Statistics ====================

@router.get("/stats/platform", response_model=PlatformStatsResponse)
async def get_platform_statistics(
    telegram_id: int = Query(..., description="Telegram ID администратора"),
    db: Session = Depends(get_db)
):
    """
    Получить полную статистику платформы
    
    Требуются права администратора.
    """
    check_admin(telegram_id)
    
    # Основные метрики
    total_users = db.query(User).count()
    
    # Активные пользователи за 24 часа (по транзакциям)
    cutoff_24h = datetime.utcnow() - timedelta(hours=24)
    active_users_24h = db.query(func.count(func.distinct(Transaction.user_id))).filter(
        Transaction.created_at >= cutoff_24h
    ).scalar() or 0
    
    # События
    total_events = db.query(Event).count()
    active_events = db.query(Event).filter(
        Event.is_active == True,
        Event.is_resolved == False
    ).count()
    resolved_events = db.query(Event).filter(
        Event.is_resolved == True
    ).count()
    
    # Объемы
    total_volume = db.query(func.sum(Event.total_pool)).scalar() or 0.0
    
    # Комиссии (сумма всех завершенных транзакций типа bet_won)
    total_commission = db.query(func.sum(Transaction.amount)).filter(
        Transaction.type == TransactionType.BET_WON,
        Transaction.status == TransactionStatus.COMPLETED
    ).scalar() or 0.0
    
    # Применяем комиссию платформы
    commission_earned = total_commission * (_platform_commission["percent"] / 100)
    
    # Ожидающие выводы
    pending_withdrawals = db.query(Transaction).filter(
        Transaction.type == TransactionType.WITHDRAWAL,
        Transaction.status == TransactionStatus.PENDING
    ).count()
    
    # Заблокированные пользователи
    blocked_users = db.query(User).filter(User.is_blocked == True).count()
    
    return {
        "total_users": total_users,
        "active_users_24h": active_users_24h,
        "total_events": total_events,
        "active_events": active_events,
        "resolved_events": resolved_events,
        "total_volume": round(total_volume, 2),
        "total_commission_earned": round(commission_earned, 2),
        "pending_withdrawals": pending_withdrawals,
        "blocked_users": blocked_users
    }


@router.get("/stats/revenue")
async def get_revenue_statistics(
    telegram_id: int = Query(..., description="Telegram ID администратора"),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Получить статистику доходов платформы
    
    Требуются права администратора.
    """
    check_admin(telegram_id)
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Группировка по дням
    daily_revenue = db.query(
        func.date(Transaction.created_at).label('date'),
        func.sum(Transaction.amount).label('total')
    ).filter(
        Transaction.type == TransactionType.BET_WON,
        Transaction.status == TransactionStatus.COMPLETED,
        Transaction.created_at >= cutoff_date
    ).group_by(
        func.date(Transaction.created_at)
    ).all()
    
    # Общая сумма
    total_revenue = sum(r.total or 0 for r in daily_revenue)
    commission_earned = total_revenue * (_platform_commission["percent"] / 100)
    
    return {
        "period_days": days,
        "total_revenue": round(total_revenue, 2),
        "commission_earned": round(commission_earned, 2),
        "commission_percent": _platform_commission["percent"],
        "daily_breakdown": [
            {"date": str(r.date), "revenue": round(r.total or 0, 2)}
            for r in daily_revenue
        ]
    }


# ==================== Withdrawals Management ====================

@router.get("/withdrawals/pending")
async def get_pending_withdrawals(
    telegram_id: int = Query(..., description="Telegram ID администратора"),
    db: Session = Depends(get_db)
):
    """
    Получить ожидающие выводы средств
    
    Требуются права администратора.
    """
    check_admin(telegram_id)
    
    withdrawals = db.query(Transaction).filter(
        Transaction.type == TransactionType.WITHDRAWAL,
        Transaction.status == TransactionStatus.PENDING
    ).order_by(Transaction.created_at.desc()).all()
    
    return {
        "total": len(withdrawals),
        "withdrawals": [
            {
                "id": t.id,
                "user_id": t.user_id,
                "amount": t.amount,
                "asset": t.asset,
                "address": t.withdrawal_address,
                "created_at": t.created_at.isoformat(),
                "admin_comment": t.admin_comment
            }
            for t in withdrawals
        ]
    }


@router.post("/withdrawals/action")
async def process_withdrawal(
    withdrawal_id: int = Body(..., embed=True),
    action: str = Body(..., embed=True),  # "approve" or "reject"
    admin_comment: str = Body(None, embed=True),
    telegram_id: int = Query(..., description="Telegram ID администратора"),
    db: Session = Depends(get_db)
):
    """
    Одобрить или отклонить вывод средств
    
    Требуются права администратора.
    """
    check_admin(telegram_id)
    
    withdrawal = db.query(Transaction).filter(Transaction.id == withdrawal_id).first()
    if not withdrawal:
        raise HTTPException(status_code=404, detail="Withdrawal not found")
    
    if withdrawal.status != TransactionStatus.PENDING:
        raise HTTPException(status_code=400, detail="Withdrawal already processed")
    
    if action == "approve":
        withdrawal.status = TransactionStatus.APPROVED
        withdrawal.admin_comment = admin_comment or "Approved by admin"
        
        # Списываем с баланса пользователя
        user = db.query(User).filter(User.id == withdrawal.user_id).first()
        if user:
            if withdrawal.asset == "USDT":
                user.balance_usdt -= withdrawal.amount
            elif withdrawal.asset == "TON":
                user.balance_ton -= withdrawal.amount
    
    elif action == "reject":
        withdrawal.status = TransactionStatus.REJECTED
        withdrawal.admin_comment = admin_comment or "Rejected by admin"
        
        # Возвращаем на баланс пользователя
        user = db.query(User).filter(User.id == withdrawal.user_id).first()
        if user:
            if withdrawal.asset == "USDT":
                user.balance_usdt += withdrawal.amount
            elif withdrawal.asset == "TON":
                user.balance_ton += withdrawal.amount
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'approve' or 'reject'")
    
    db.commit()
    
    return {
        "success": True,
        "withdrawal_id": withdrawal_id,
        "action": action,
        "new_status": withdrawal.status.value
    }
