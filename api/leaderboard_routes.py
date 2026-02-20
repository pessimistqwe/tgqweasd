"""
Leaderboard Routes - API endpoints для таблицы лидеров

Функционал:
- GET /api/leaderboard/pnl - Топ по PnL (profit/loss)
- GET /api/leaderboard/winrate - Топ по win rate
- GET /api/leaderboard/volume - Топ по объёму ставок
- GET /api/user/{telegram_id}/stats - Расширенная статистика пользователя
- GET /api/user/{telegram_id}/pnl - PnL история пользователя

Все endpoints публичные (не требуют аутентификации).
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc, asc
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal

try:
    from .models import get_db, User, Event, EventOption, UserPrediction, Transaction, TransactionType
    from .betting_models import Bet
except ImportError:
    from models import get_db, User, Event, EventOption, UserPrediction, Transaction, TransactionType
    from betting_models import Bet

router = APIRouter(prefix="/api", tags=["Leaderboard", "User Stats"])

# ==================== Pydantic Models ====================

class LeaderboardEntry(BaseModel):
    """Запись в таблице лидеров"""
    rank: int
    telegram_id: int
    username: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    value: float
    is_verified: bool = False


class LeaderboardResponse(BaseModel):
    """Ответ таблицы лидеров"""
    total_users: int
    period: str
    last_updated: str
    leaderboard: List[LeaderboardEntry]


class UserStatsResponse(BaseModel):
    """Расширенная статистика пользователя"""
    telegram_id: int
    username: Optional[str]
    display_name: Optional[str]
    avatar_url: Optional[str]
    created_at: str

    # Балансы
    balance_usdt: float
    balance_ton: float
    total_deposited: float
    total_withdrawn: float

    # Статистика ставок
    total_bets: int
    winning_bets: int
    losing_bets: int
    win_rate: float

    # PnL
    total_pnl: float
    realized_pnl: float
    unrealized_pnl: float

    # Объемы
    total_volume: float
    total_wagered: float

    # Профили
    total_predictions: int
    active_predictions: int


class UserPnLHistoryEntry(BaseModel):
    """Запись истории PnL"""
    date: str
    pnl: float
    bets_count: int


class UserPnLHistoryResponse(BaseModel):
    """История PnL пользователя"""
    telegram_id: int
    period_days: int
    total_pnl: float
    history: List[UserPnLHistoryEntry]


class UserBetHistoryEntry(BaseModel):
    """Запись истории ставок"""
    id: int
    event_id: int
    event_title: str
    option_index: int
    option_text: str
    amount: float
    shares: float
    average_price: float
    payout: float
    is_winner: Optional[bool]
    timestamp: str


class UserBetHistoryResponse(BaseModel):
    """История ставок пользователя"""
    telegram_id: int
    total_bets: int
    total_pnl: float
    bets: List[UserBetHistoryEntry]


# ==================== Helper Functions ====================

def calculate_user_pnl(db: Session, user_id: int) -> Dict[str, float]:
    """
    Рассчитать PnL пользователя

    Args:
        db: Сессия БД
        user_id: ID пользователя

    Returns:
        Dict с realized_pnl и unrealized_pnl
    """
    # Realized PnL (закрытые ставки)
    predictions = db.query(UserPrediction).filter(
        UserPrediction.user_id == user_id
    ).all()

    realized_pnl = 0.0
    unrealized_pnl = 0.0

    for pred in predictions:
        event = db.query(Event).filter(Event.id == pred.event_id).first()
        if not event:
            continue

        if event.is_resolved:
            # Закрытая ставка
            if pred.is_winner:
                realized_pnl += pred.payout - pred.amount
            else:
                realized_pnl -= pred.amount
        else:
            # Открытая ставка - рассчитываем текущую стоимость
            option = db.query(EventOption).filter(
                EventOption.event_id == event.id,
                EventOption.option_index == pred.option_index
            ).first()

            if option:
                current_value = pred.shares * option.current_price
                unrealized_pnl += current_value - pred.amount

    return {
        "realized_pnl": realized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "total_pnl": realized_pnl + unrealized_pnl
    }


def get_period_filter(period: str) -> Optional[datetime]:
    """
    Получить дату начала периода

    Args:
        period: 'day', 'week', 'month', 'all'

    Returns:
        Дата начала периода или None для 'all'
    """
    now = datetime.utcnow()

    if period == "day":
        return now - timedelta(days=1)
    elif period == "week":
        return now - timedelta(weeks=1)
    elif period == "month":
        return now - timedelta(days=30)
    else:
        return None


# ==================== Leaderboard Endpoints ====================

@router.get("/leaderboard/pnl", response_model=LeaderboardResponse)
async def get_pnl_leaderboard(
    period: str = Query(default="all", description="Период: day, week, month, all"),
    limit: int = Query(default=50, ge=1, le=100, description="Максимум результатов"),
    db: Session = Depends(get_db)
):
    """
    Таблица лидеров по PnL (profit/loss)

    Сортирует пользователей по общему PnL (реализованный + нереализованный).
    """
    # Получаем всех пользователей
    users = db.query(User).filter(User.is_blocked == False).all()

    # Рассчитываем PnL для каждого
    user_pnls = []
    for user in users:
        pnl_data = calculate_user_pnl(db, user.id)
        if pnl_data["total_pnl"] != 0:  # Только пользователи с активностью
            user_pnls.append({
                "user": user,
                "pnl": pnl_data["total_pnl"]
            })

    # Сортируем по PnL
    user_pnls.sort(key=lambda x: x["pnl"], reverse=True)

    # Формируем ответ
    leaderboard = []
    for rank, item in enumerate(user_pnls[:limit], 1):
        user = item["user"]
        leaderboard.append(LeaderboardEntry(
            rank=rank,
            telegram_id=user.telegram_id,
            username=user.username,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            value=round(item["pnl"], 2),
            is_verified=bool(user.is_admin)
        ))

    return LeaderboardResponse(
        total_users=len(users),
        period=period,
        last_updated=datetime.utcnow().isoformat(),
        leaderboard=leaderboard
    )


@router.get("/leaderboard/winrate", response_model=LeaderboardResponse)
async def get_winrate_leaderboard(
    period: str = Query(default="all", description="Период: day, week, month, all"),
    min_bets: int = Query(default=5, ge=1, description="Минимум ставок"),
    limit: int = Query(default=50, ge=1, le=100, description="Максимум результатов"),
    db: Session = Depends(get_db)
):
    """
    Таблица лидеров по Win Rate

    Требует минимальное количество ставок для попадания в рейтинг.
    """
    # Получаем пользователей с их ставками
    users = db.query(User).filter(User.is_blocked == False).all()

    user_winrates = []
    for user in users:
        predictions = db.query(UserPrediction).filter(
            UserPrediction.user_id == user.id
        ).all()

        if len(predictions) < min_bets:
            continue

        # Считаем выигрыши
        resolved_predictions = [p for p in predictions if p.is_winner is not None]
        if not resolved_predictions:
            continue

        wins = sum(1 for p in resolved_predictions if p.is_winner)
        win_rate = (wins / len(resolved_predictions)) * 100

        user_winrates.append({
            "user": user,
            "win_rate": win_rate,
            "total_bets": len(resolved_predictions)
        })

    # Сортируем по win rate
    user_winrates.sort(key=lambda x: x["win_rate"], reverse=True)

    # Формируем ответ
    leaderboard = []
    for rank, item in enumerate(user_winrates[:limit], 1):
        user = item["user"]
        leaderboard.append(LeaderboardEntry(
            rank=rank,
            telegram_id=user.telegram_id,
            username=user.username,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            value=round(item["win_rate"], 2),
            is_verified=bool(user.is_admin)
        ))

    return LeaderboardResponse(
        total_users=len(users),
        period=period,
        last_updated=datetime.utcnow().isoformat(),
        leaderboard=leaderboard
    )


@router.get("/leaderboard/volume", response_model=LeaderboardResponse)
async def get_volume_leaderboard(
    period: str = Query(default="all", description="Период: day, week, month, all"),
    limit: int = Query(default=50, ge=1, le=100, description="Максимум результатов"),
    db: Session = Depends(get_db)
):
    """
    Таблица лидеров по объёму ставок

    Сортирует по общей сумме всех ставок.
    """
    # Получаем cutoff дату
    cutoff_date = get_period_filter(period)

    # Query для суммы ставок
    query = db.query(
        UserPrediction.user_id,
        func.sum(UserPrediction.amount).label("total_volume")
    ).group_by(UserPrediction.user_id)

    if cutoff_date:
        query = query.filter(UserPrediction.timestamp >= cutoff_date)

    results = query.all()

    # Получаем пользователей
    user_ids = [r.user_id for r in results]
    users = {u.id: u for u in db.query(User).filter(
        User.id.in_(user_ids),
        User.is_blocked == False
    ).all()}

    # Формируем leaderboard
    volume_data = []
    for result in results:
        user = users.get(result.user_id)
        if user:
            volume_data.append({
                "user": user,
                "volume": float(result.total_volume)
            })

    # Сортируем по объёму
    volume_data.sort(key=lambda x: x["volume"], reverse=True)

    # Формируем ответ
    leaderboard = []
    for rank, item in enumerate(volume_data[:limit], 1):
        user = item["user"]
        leaderboard.append(LeaderboardEntry(
            rank=rank,
            telegram_id=user.telegram_id,
            username=user.username,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            value=round(item["volume"], 2),
            is_verified=bool(user.is_admin)
        ))

    return LeaderboardResponse(
        total_users=db.query(User).filter(User.is_blocked == False).count(),
        period=period,
        last_updated=datetime.utcnow().isoformat(),
        leaderboard=leaderboard
    )


# ==================== User Stats Endpoints ====================

@router.get("/user/{telegram_id}/stats", response_model=UserStatsResponse)
async def get_user_stats(
    telegram_id: int,
    db: Session = Depends(get_db)
):
    """
    Расширенная статистика пользователя

    Включает:
    - Балансы (USDT, TON)
    - PnL (реализованный и нереализованный)
    - Win rate
    - Общий объём ставок
    - История транзакций
    """
    user = db.query(User).filter(User.telegram_id == telegram_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # PnL расчет
    pnl_data = calculate_user_pnl(db, user.id)

    # Статистика ставок
    predictions = db.query(UserPrediction).filter(
        UserPrediction.user_id == user.id
    ).all()

    total_bets = len(predictions)
    winning_bets = sum(1 for p in predictions if p.is_winner is True)
    losing_bets = sum(1 for p in predictions if p.is_winner is False)
    win_rate = (winning_bets / total_bets * 100) if total_bets > 0 else 0

    # Объемы
    total_volume = sum(p.amount for p in predictions)
    total_wagered = total_volume

    # Транзакции
    deposits = db.query(Transaction).filter(
        Transaction.user_id == user.id,
        Transaction.type == TransactionType.DEPOSIT,
        Transaction.status == TransactionStatus.COMPLETED
    ).all()

    withdrawals = db.query(Transaction).filter(
        Transaction.user_id == user.id,
        Transaction.type == TransactionType.WITHDRAWAL,
        Transaction.status.in_([TransactionStatus.COMPLETED, TransactionStatus.APPROVED])
    ).all()

    total_deposited = sum(t.amount for t in deposits)
    total_withdrawn = sum(t.amount for t in withdrawals)

    # Активные прогнозы
    active_events = db.query(Event).filter(
        Event.is_resolved == False
    ).all()
    active_event_ids = {e.id for e in active_events}
    active_predictions = sum(1 for p in predictions if p.event_id in active_event_ids)

    return UserStatsResponse(
        telegram_id=user.telegram_id,
        username=user.username,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        created_at=user.created_at.isoformat() if user.created_at else None,
        balance_usdt=round(user.balance_usdt, 2),
        balance_ton=round(user.balance_ton, 2),
        total_deposited=round(total_deposited, 2),
        total_withdrawn=round(total_withdrawn, 2),
        total_bets=total_bets,
        winning_bets=winning_bets,
        losing_bets=losing_bets,
        win_rate=round(win_rate, 2),
        total_pnl=round(pnl_data["total_pnl"], 2),
        realized_pnl=round(pnl_data["realized_pnl"], 2),
        unrealized_pnl=round(pnl_data["unrealized_pnl"], 2),
        total_volume=round(total_volume, 2),
        total_wagered=round(total_wagered, 2),
        total_predictions=total_bets,
        active_predictions=active_predictions
    )


@router.get("/user/{telegram_id}/pnl", response_model=UserPnLHistoryResponse)
async def get_user_pnl_history(
    telegram_id: int,
    days: int = Query(default=30, ge=1, le=365, description="Период в днях"),
    db: Session = Depends(get_db)
):
    """
    История PnL пользователя по дням

    Показывает ежедневный PnL за указанный период.
    """
    user = db.query(User).filter(User.telegram_id == telegram_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Получаем закрытые ставки по дням
    predictions = db.query(UserPrediction).filter(
        UserPrediction.user_id == user.id,
        UserPrediction.timestamp >= cutoff_date
    ).all()

    # Группируем по датам
    daily_pnl: Dict[str, float] = {}
    daily_bets: Dict[str, int] = {}

    for pred in predictions:
        event = db.query(Event).filter(Event.id == pred.event_id).first()
        if not event or not event.is_resolved:
            continue

        date_str = pred.timestamp.strftime("%Y-%m-%d")

        if date_str not in daily_pnl:
            daily_pnl[date_str] = 0
            daily_bets[date_str] = 0

        daily_bets[date_str] += 1

        if pred.is_winner:
            daily_pnl[date_str] += pred.payout - pred.amount
        else:
            daily_pnl[date_str] -= pred.amount

    # Формируем историю
    history = []
    for date_str in sorted(daily_pnl.keys()):
        history.append(UserPnLHistoryEntry(
            date=date_str,
            pnl=round(daily_pnl[date_str], 2),
            bets_count=daily_bets[date_str]
        ))

    total_pnl = sum(daily_pnl.values())

    return UserPnLHistoryResponse(
        telegram_id=telegram_id,
        period_days=days,
        total_pnl=round(total_pnl, 2),
        history=history
    )


@router.get("/user/{telegram_id}/bets", response_model=UserBetHistoryResponse)
async def get_user_bet_history(
    telegram_id: int,
    limit: int = Query(default=50, ge=1, le=200, description="Максимум результатов"),
    offset: int = Query(default=0, ge=0),
    resolved_only: bool = Query(default=False, description="Только закрытые ставки"),
    db: Session = Depends(get_db)
):
    """
    История ставок пользователя

    Показывает все ставки с деталями событий.
    """
    user = db.query(User).filter(User.telegram_id == telegram_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Query для ставок
    query = db.query(UserPrediction).filter(
        UserPrediction.user_id == user.id
    )

    if resolved_only:
        query = query.join(Event).filter(Event.is_resolved == True)

    query = query.order_by(UserPrediction.timestamp.desc())
    query = query.limit(limit).offset(offset)

    predictions = query.all()

    # Формируем ответ
    bets = []
    total_pnl = 0

    for pred in predictions:
        event = db.query(Event).filter(Event.id == pred.event_id).first()
        option = db.query(EventOption).filter(
            EventOption.event_id == event.id,
            EventOption.option_index == pred.option_index
        ).first() if event else None

        if pred.is_winner is not None:
            if pred.is_winner:
                total_pnl += pred.payout - pred.amount
            else:
                total_pnl -= pred.amount

        bets.append(UserBetHistoryEntry(
            id=pred.id,
            event_id=event.id if event else 0,
            event_title=event.title[:100] if event else "Unknown",
            option_index=pred.option_index,
            option_text=option.option_text if option else "Unknown",
            amount=pred.amount,
            shares=pred.shares,
            average_price=pred.average_price,
            payout=pred.payout,
            is_winner=pred.is_winner,
            timestamp=pred.timestamp.isoformat()
        ))

    return UserBetHistoryResponse(
        telegram_id=telegram_id,
        total_bets=len(bets),
        total_pnl=round(total_pnl, 2),
        bets=bets
    )


# ==================== Combined Leaderboard ====================

@router.get("/leaderboard")
async def get_combined_leaderboard(
    period: str = Query(default="all", description="Период: day, week, month, all"),
    limit: int = Query(default=20, ge=1, le=50, description="Максимум результатов"),
    db: Session = Depends(get_db)
):
    """
    Комбинированная таблица лидеров

    Возвращает топ по PnL, win rate и volume в одном запросе.
    """
    # Получаем все три leaderboard параллельно (в реальном приложении использовать asyncio.gather)
    pnl_response = await get_pnl_leaderboard(period, limit, db)
    winrate_response = await get_winrate_leaderboard(period, 5, limit, db)
    volume_response = await get_volume_leaderboard(period, limit, db)

    return {
        "period": period,
        "limit": limit,
        "last_updated": datetime.utcnow().isoformat(),
        "total_users": pnl_response.total_users,
        "categories": {
            "pnl": {
                "title": "Top PnL",
                "unit": "USDT",
                "leaderboard": pnl_response.leaderboard
            },
            "winrate": {
                "title": "Top Win Rate",
                "unit": "%",
                "leaderboard": winrate_response.leaderboard
            },
            "volume": {
                "title": "Top Volume",
                "unit": "USDT",
                "leaderboard": volume_response.leaderboard
            }
        }
    }
