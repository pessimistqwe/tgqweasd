"""Historical Routes - API endpoints для исторических данных Polymarket"""

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging

try:
    from index import fetch_polymarket_price_history, POLYMARKET_CANDLES_RESOLUTIONS, POLYMARKET_CANDLES_LIMITS
    limiter = None
except ImportError:
    try:
        from .index import fetch_polymarket_price_history, POLYMARKET_CANDLES_RESOLUTIONS, POLYMARKET_CANDLES_LIMITS, limiter
    except ImportError:
        limiter = None
        fetch_polymarket_price_history = None
        POLYMARKET_CANDLES_RESOLUTIONS = {}
        POLYMARKET_CANDLES_LIMITS = {}

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/historical", tags=["Historical Data"])

class CandleData(BaseModel):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    open_percent: float
    high_percent: float
    low_percent: float
    close_percent: float

class CandleResponse(BaseModel):
    market_id: str
    outcome: str
    resolution: str
    candles: List[CandleData]
    count: int
    first_timestamp: Optional[str] = None
    last_timestamp: Optional[str] = None

class ResolutionInfo(BaseModel):
    resolution: str
    minutes: int
    max_limit: int
    description: str

class ResolutionsResponse(BaseModel):
    resolutions: List[ResolutionInfo]
    default_resolution: str = "1h"

def _get_res_desc(res: str) -> str:
    d = {'1m':'1 мин','5m':'5 мин','15m':'15 мин','30m':'30 мин','1h':'1 час','2h':'2 часа','4h':'4 часа','6h':'6 часов','12h':'12 часов','1d':'1 день','3d':'3 дня','1w':'1 неделя','1M':'1 месяц'}
    return d.get(res, 'Custom')

def _calc_candles(days: int, res: str) -> int:
    if not POLYMARKET_CANDLES_RESOLUTIONS: return 100
    mins_day, res_mins = 1440, POLYMARKET_CANDLES_RESOLUTIONS.get(res, 60)
    return min(int((mins_day/res_mins)*days), POLYMARKET_CANDLES_LIMITS.get(res, 200) if POLYMARKET_CANDLES_LIMITS else 200)

@router.get("/resolutions")
async def get_resolutions(request: Request):
    if not POLYMARKET_CANDLES_RESOLUTIONS:
        return {"resolutions": [], "default_resolution": "1h", "error": "Not configured"}
    resolutions = [ResolutionInfo(resolution=r, minutes=m, max_limit=POLYMARKET_CANDLES_LIMITS.get(r, 200) if POLYMARKET_CANDLES_LIMITS else 200, description=_get_res_desc(r)) for r, m in POLYMARKET_CANDLES_RESOLUTIONS.items()]
    return ResolutionsResponse(resolutions=resolutions, default_resolution="1h")

@router.get("/candles/{market_id}", response_model=CandleResponse)
async def get_candles(market_id: str, outcome: str = Query(default="Yes"), resolution: str = Query(default="1h"), limit: int = Query(default=None, ge=1, le=500)):
    if not fetch_polymarket_price_history:
        raise HTTPException(status_code=503, detail="Historical service not available")
    if resolution not in POLYMARKET_CANDLES_RESOLUTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid resolution. Valid: {list(POLYMARKET_CANDLES_RESOLUTIONS.keys())}")
    history = fetch_polymarket_price_history(condition_id=market_id, outcome=outcome, resolution=resolution, limit=limit)
    if not history:
        raise HTTPException(status_code=404, detail=f"No data for {market_id}/{outcome}/{resolution}")
    candles = [CandleData(timestamp=t.isoformat(), open=o, high=h, low=l, close=c, volume=v, open_percent=round(o*100,2), high_percent=round(h*100,2), low_percent=round(l*100,2), close_percent=round(c*100,2)) for t, c, v, o, h, l in history]
    candles.sort(key=lambda x: x.timestamp)
    return CandleResponse(market_id=market_id, outcome=outcome, resolution=resolution, candles=candles, count=len(candles), first_timestamp=candles[0].timestamp if candles else None, last_timestamp=candles[-1].timestamp if candles else None)

@router.get("/candles/{market_id}/latest")
async def get_latest(market_id: str, outcome: str = Query(default="Yes"), resolution: str = Query(default="1h")):
    if not fetch_polymarket_price_history:
        raise HTTPException(status_code=503, detail="Historical service not available")
    if resolution not in POLYMARKET_CANDLES_RESOLUTIONS:
        raise HTTPException(status_code=400, detail="Invalid resolution")
    history = fetch_polymarket_price_history(condition_id=market_id, outcome=outcome, resolution=resolution, limit=1)
    if not history:
        raise HTTPException(status_code=404, detail=f"No data for {market_id}/{outcome}")
    t, c, v, o, h, l = history[-1]
    return {"market_id": market_id, "outcome": outcome, "resolution": resolution, "candle": {"timestamp": t.isoformat(), "open": o, "high": h, "low": l, "close": c, "volume": v, "open_percent": round(o*100,2), "high_percent": round(h*100,2), "low_percent": round(l*100,2), "close_percent": round(c*100,2)}}

@router.get("/candles/{market_id}/stats")
async def get_stats(market_id: str, outcome: str = Query(default="Yes"), resolution: str = Query(default="1d"), period: int = Query(default=30, ge=1, le=365)):
    if not fetch_polymarket_price_history:
        raise HTTPException(status_code=503, detail="Historical service not available")
    if resolution not in POLYMARKET_CANDLES_RESOLUTIONS:
        raise HTTPException(status_code=400, detail="Invalid resolution")
    history = fetch_polymarket_price_history(condition_id=market_id, outcome=outcome, resolution=resolution, limit=_calc_candles(period, resolution))
    if not history:
        raise HTTPException(status_code=404, detail=f"No data for {market_id}/{outcome}")
    prices, volumes = [i[1] for i in history], [i[2] for i in history]
    avg, mx, mn = sum(prices)/len(prices), max(prices), min(prices)
    vol = (sum((p-avg)**2 for p in prices)/len(prices))**0.5
    fp, lp = prices[0], prices[-1]
    chg, chg_pct = lp-fp, ((lp-fp)/fp*100) if fp > 0 else 0
    trend = "up" if chg > 0 else "down" if chg < 0 else "flat"
    return {"market_id": market_id, "outcome": outcome, "resolution": resolution, "period_days": period, "data_points": len(history), "statistics": {"avg_price": round(avg,4), "avg_price_percent": round(avg*100,2), "max_price": round(mx,4), "max_price_percent": round(mx*100,2), "min_price": round(mn,4), "min_price_percent": round(mn*100,2), "total_volume": round(sum(volumes),2), "volatility": round(vol,4), "volatility_percent": round(vol*100,2), "price_change": round(chg,4), "price_change_percent": round(chg_pct,2), "trend": trend, "first_price": round(fp,4), "last_price": round(lp,4)}}
