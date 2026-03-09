"""
Analytics Routes - Эндпоинты для аналитики пользователей (Kalshi-style)
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

try:
    from .models import get_db, User, Bet, BetHistory, BetStatus, BetType, Event, EventOption
    from .betting_models import BetDirection
    from .index import limiter
except ImportError:
    from models import get_db, User, Bet, BetHistory, BetStatus, BetType, Event, EventOption
    from betting_models import BetDirection
    limiter = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])

class BetHistoryItem(BaseModel):
    id: int
    event_id: int
    event_title: str
    option_text: str
    amount: float
    shares: float
    entry_price: float
    exit_price: Optional[float] = None
    fees_paid: float = 0.0
    pnl: Optional[float] = None
    status: str
    side: str
    direction: str
    created_at: datetime
    resolved_at: Optional[datetime] = None

class CategoryAnalytics(BaseModel):
    category: str
    total_bets: int = 0
    won_bets: int = 0
    lost_bets: int = 0
    win_rate: float = 0.0
    total_staked: float = 0.0
    total_pnl: float = 0.0
    roi: float = 0.0

def calculate_bet_analytics(db: Session, user_id: int) -> Dict[str, Any]:
    bets_query = db.query(Bet).filter(Bet.user_id == user_id)
    bet_history_query = db.query(BetHistory).filter(BetHistory.user_id == user_id)
    total_bets = bets_query.count() + bet_history_query.count()
    
    if total_bets == 0:
        return {"total_bets": 0, "active_bets": 0, "closed_bets": 0, "won_bets": 0, "lost_bets": 0,
                "win_rate": 0.0, "total_staked": 0.0, "total_pnl": 0.0, "total_fees": 0.0,
                "roi": 0.0, "avg_bet_size": 0.0, "largest_win": 0.0, "largest_loss": 0.0}
    
    all_bets = bets_query.all()
    bets_stats = {"active_bets": 0, "closed_bets": 0, "won_bets": 0, "lost_bets": 0,
                  "total_staked": 0.0, "total_pnl": 0.0, "total_fees": 0.0, "largest_win": 0.0, "largest_loss": 0.0}
    
    if all_bets:
        bets_stats["active_bets"] = sum(1 for b in all_bets if b.status in [BetStatus.OPEN, BetStatus.PENDING])
        bets_stats["closed_bets"] = sum(1 for b in all_bets if b.status in [BetStatus.CLOSED, BetStatus.WON, BetStatus.LOST])
        bets_stats["won_bets"] = sum(1 for b in all_bets if b.status == BetStatus.WON)
        bets_stats["lost_bets"] = sum(1 for b in all_bets if b.status == BetStatus.LOST)
        bets_stats["total_staked"] = sum(float(b.amount) for b in all_bets)
        bets_stats["total_pnl"] = sum(float(b.pnl) if b.pnl else 0.0 for b in all_bets)
        bets_stats["total_fees"] = sum(float(b.fees_paid) if b.fees_paid else 0.0 for b in all_bets)
        pnls = [float(b.pnl) if b.pnl else 0.0 for b in all_bets]
        bets_stats["largest_win"] = max([p for p in pnls if p > 0] or [0.0])
        bets_stats["largest_loss"] = abs(min([p for p in pnls if p < 0] or [0.0]))
    
    all_history = bet_history_query.all()
    history_stats = {"won_bets": 0, "lost_bets": 0, "total_staked": 0.0, "total_pnl": 0.0, 
                     "total_fees": 0.0, "largest_win": 0.0, "largest_loss": 0.0}
    
    if all_history:
        history_stats["won_bets"] = sum(1 for h in all_history if h.status == "won")
        history_stats["lost_bets"] = sum(1 for h in all_history if h.status == "lost")
        history_stats["total_staked"] = sum(h.amount for h in all_history)
        history_stats["total_pnl"] = sum(h.pnl if h.pnl else 0.0 for h in all_history)
        history_stats["total_fees"] = sum(h.fees_paid if h.fees_paid else 0.0 for h in all_history)
        h_pnls = [h.pnl if h.pnl else 0.0 for h in all_history]
        history_stats["largest_win"] = max([p for p in h_pnls if p > 0] or [0.0])
        history_stats["largest_loss"] = abs(min([p for p in h_pnls if p < 0] or [0.0]))
    
    total_won = bets_stats["won_bets"] + history_stats["won_bets"]
    total_lost = bets_stats["lost_bets"] + history_stats["lost_bets"]
    total_staked = bets_stats["total_staked"] + history_stats["total_staked"]
    total_pnl = bets_stats["total_pnl"] + history_stats["total_pnl"]
    total_fees = bets_stats["total_fees"] + history_stats["total_fees"]
    
    win_rate = total_won / (total_won + total_lost) if (total_won + total_lost) > 0 else 0.0
    roi = (total_pnl / total_staked * 100) if total_staked > 0 else 0.0
    avg_bet_size = total_staked / total_bets if total_bets > 0 else 0.0
    
    return {
        "active_bets": bets_stats["active_bets"],
        "closed_bets": bets_stats["closed_bets"] + len(all_history),
        "won_bets": total_won, "lost_bets": total_lost,
        "win_rate": round(win_rate, 4), "total_staked": round(total_staked, 2),
        "total_pnl": round(total_pnl, 2), "total_fees": round(total_fees, 2),
        "roi": round(roi, 2), "avg_bet_size": round(avg_bet_size, 2),
        "largest_win": round(max(bets_stats["largest_win"], history_stats["largest_win"]), 2),
        "largest_loss": round(max(bets_stats["largest_loss"], history_stats["largest_loss"]), 2)
    }

def get_category_analytics(db: Session, user_id: int) -> List[CategoryAnalytics]:
    categories = {}
    
    for bet in db.query(Bet).filter(Bet.user_id == user_id).all():
        event = db.query(Event).filter(Event.id == bet.market_id).first()
        if not event: continue
        category = event.category or "other"
        if category not in categories:
            categories[category] = {"total_bets": 0, "won_bets": 0, "lost_bets": 0, "total_staked": 0.0, "total_pnl": 0.0}
        categories[category]["total_bets"] += 1
        categories[category]["total_staked"] += float(bet.amount)
        categories[category]["total_pnl"] += float(bet.pnl) if bet.pnl else 0.0
        if bet.status == BetStatus.WON: categories[category]["won_bets"] += 1
        elif bet.status == BetStatus.LOST: categories[category]["lost_bets"] += 1
    
    for record in db.query(BetHistory).filter(BetHistory.user_id == user_id).all():
        event = db.query(Event).filter(Event.id == record.event_id).first()
        if not event: continue
        category = event.category or "other"
        if category not in categories:
            categories[category] = {"total_bets": 0, "won_bets": 0, "lost_bets": 0, "total_staked": 0.0, "total_pnl": 0.0}
        categories[category]["total_bets"] += 1
        categories[category]["total_staked"] += record.amount
        categories[category]["total_pnl"] += record.pnl if record.pnl else 0.0
        if record.status == "won": categories[category]["won_bets"] += 1
        elif record.status == "lost": categories[category]["lost_bets"] += 1
    
    result = []
    for cat, stats in categories.items():
        tw, tl = stats["won_bets"], stats["lost_bets"]
        wr = tw / (tw + tl) if (tw + tl) > 0 else 0.0
        roi = (stats["total_pnl"] / stats["total_staked"] * 100) if stats["total_staked"] > 0 else 0.0
        result.append(CategoryAnalytics(category=cat, total_bets=stats["total_bets"],
            won_bets=tw, lost_bets=tl, win_rate=round(wr, 4),
            total_staked=round(stats["total_staked"], 2), total_pnl=round(stats["total_pnl"], 2), roi=round(roi, 2)))
    return result

@router.get("/user/{telegram_id}")
async def get_user_analytics(request: Request, telegram_id: int, db: Session = Depends(get_db)):
    """Получить полную аналитику пользователя"""
    if limiter: await limiter.ratelimit("30/minute")(request)
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    
    analytics = calculate_bet_analytics(db, user.id)
    cat_analytics = get_category_analytics(db, user.id)
    best_cat = None
    worst_cat = None
    if cat_analytics:
        sorted_cats = sorted(cat_analytics, key=lambda x: x.roi, reverse=True)
        best_cat = sorted_cats[0].category if sorted_cats else None
        worst_cat = sorted_cats[-1].category if sorted_cats else None
    
    return {"telegram_id": telegram_id, "username": user.username, **analytics,
            "best_category": best_cat, "worst_category": worst_cat,
            "category_breakdown": cat_analytics, "created_at": user.created_at}

@router.get("/user/{telegram_id}/bets")
async def get_user_bet_history(request: Request, telegram_id: int, db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0),
    status: Optional[str] = None, bet_type: Optional[str] = None):
    """Получить историю ставок пользователя"""
    if limiter: await limiter.ratelimit("60/minute")(request)
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    
    bets = []
    bets_query = db.query(Bet).filter(Bet.user_id == user.id).order_by(Bet.created_at.desc())
    if status:
        status_map = {"open": BetStatus.OPEN, "closed": BetStatus.CLOSED, "won": BetStatus.WON,
                      "lost": BetStatus.LOST, "cancelled": BetStatus.CANCELLED, "pending": BetStatus.PENDING}
        if status in status_map: bets_query = bets_query.filter(Bet.status == status_map[status])
    if bet_type: bets_query = bets_query.filter(Bet.bet_type == BetType(bet_type))
    
    for bet in bets_query.offset(offset).limit(limit).all():
        event = db.query(Event).filter(Event.id == bet.market_id).first()
        opt_text = ""
        if bet.bet_type == BetType.EVENT and event:
            try:
                opts = event.options.split(",") if event.options else []
                idx = 0 if bet.direction == BetDirection.YES else 1
                if len(opts) > idx: opt_text = opts[idx]
            except: opt_text = str(bet.direction)
        else: opt_text = str(bet.direction)
        
        bets.append(BetHistoryItem(id=bet.id, event_id=bet.market_id,
            event_title=event.title if event else "Unknown", option_text=opt_text,
            amount=float(bet.amount), shares=float(bet.shares), entry_price=float(bet.entry_price),
            exit_price=float(bet.exit_price) if bet.exit_price else None,
            fees_paid=float(bet.fees_paid) if bet.fees_paid else 0.0,
            pnl=float(bet.pnl) if bet.pnl else None, status=bet.status.value,
            side=bet.direction.value, direction=bet.direction.value,
            created_at=bet.created_at, resolved_at=bet.resolved_at))
    
    total = db.query(Bet).filter(Bet.user_id == user.id).count() + db.query(BetHistory).filter(BetHistory.user_id == user.id).count()
    return {"bets": bets, "total": total, "limit": limit, "offset": offset}

@router.get("/user/{telegram_id}/categories")
async def get_user_category_analytics(request: Request, telegram_id: int, db: Session = Depends(get_db)):
    """Получить аналитику по категориям"""
    if limiter: await limiter.ratelimit("30/minute")(request)
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    
    cat_analytics = get_category_analytics(db, user.id)
    best_cat, worst_cat = None, None
    if cat_analytics:
        nz = [c for c in cat_analytics if c.total_bets > 0]
        if nz:
            sorted_cats = sorted(nz, key=lambda x: x.roi, reverse=True)
            best_cat, worst_cat = sorted_cats[0].category, sorted_cats[-1].category if len(sorted_cats) > 1 else None
    
    return {"categories": cat_analytics, "best_category": best_cat,
            "worst_category": worst_cat, "total_categories": len(cat_analytics)}

@router.get("/user/{telegram_id}/performance")
async def get_user_performance(request: Request, telegram_id: int, db: Session = Depends(get_db),
    days: int = Query(default=30, ge=1, le=365)):
    """Получить производительность за период"""
    if limiter: await limiter.ratelimit("30/minute")(request)
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    
    cutoff = datetime.utcnow() - timedelta(days=days)
    bets = db.query(Bet).filter(and_(Bet.user_id == user.id, Bet.created_at >= cutoff,
        Bet.status.in_([BetStatus.WON, BetStatus.LOST, BetStatus.CLOSED]))).all()
    
    daily = {}
    for bet in bets:
        dk = bet.created_at.date().isoformat()
        if dk not in daily: daily[dk] = {"date": dk, "pnl": 0.0, "bets": 0, "wins": 0, "losses": 0}
        daily[dk]["pnl"] += float(bet.pnl) if bet.pnl else 0.0
        daily[dk]["bets"] += 1
        if bet.status == BetStatus.WON: daily[dk]["wins"] += 1
        elif bet.status == BetStatus.LOST: daily[dk]["losses"] += 1
    
    perf = sorted(list(daily.values()), key=lambda x: x["date"])
    tp = sum(d["pnl"] for d in perf)
    tb = sum(d["bets"] for d in perf)
    tw = sum(d["wins"] for d in perf)
    tl = sum(d["losses"] for d in perf)
    wr = tw / (tw + tl) if (tw + tl) > 0 else 0.0
    
    return {"period_days": days, "total_pnl": round(tp, 2), "total_bets": tb,
            "win_rate": round(wr, 4), "daily_performance": perf}
