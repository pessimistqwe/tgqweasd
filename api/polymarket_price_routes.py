"""
Polymarket Price Routes - API endpoints для получения реальных цен

Endpoints:
- GET /api/polymarket/price/{token_id} - Цена для одного токена
- GET /api/polymarket/prices - Массовый запрос цен
- GET /api/polymarket/market/{market_id}/prices - Цены для всех исходов рынка
- GET /api/polymarket/price/stats - Статистика кэша цен
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

try:
    from .models import get_db, Event, EventOption
    from .polymarket_price_service import (
        get_price, get_prices, get_market_prices,
        get_last_trade_price, sync_prices_to_db,
        get_cache_stats, clear_cache
    )
except ImportError:
    from models import get_db, Event, EventOption
    from polymarket_price_service import (
        get_price, get_prices, get_market_prices,
        get_last_trade_price, sync_prices_to_db,
        get_cache_stats, clear_cache
    )

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/polymarket/price", tags=["Polymarket Price"])

# ==================== Pydantic Models ====================

class PriceResponse(BaseModel):
    """Ответ с ценой"""
    token_id: str
    price: float
    price_percent: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    last_trade: Optional[float] = None
    volume_24h: Optional[float] = None
    change_24h: Optional[float] = None
    timestamp: str
    cached: bool = False


class MarketPricesResponse(BaseModel):
    """Ответ с ценами для рынка"""
    market_id: str
    outcomes: Dict[str, Dict[str, Any]]
    timestamp: str


class PriceStatsResponse(BaseModel):
    """Статистика кэша цен"""
    cached_prices: int
    cache_ttl_seconds: int
    rate_limit: Dict[str, Any]

# ==================== API Endpoints ====================

@router.get("/{token_id}", response_model=PriceResponse)
async def get_token_price(
    token_id: str,
    use_cache: bool = Query(default=True, description="Использовать кэш")
):
    """
    Получить цену для одного токена
    
    - **token_id**: Polymarket token ID
    - **use_cache**: Использовать ли кэш (default: True)
    """
    # Проверяем кэш перед запросом
    cached_price = None
    try:
        from .polymarket_price_service import get_cached_price
        cached_price = get_cached_price(token_id)
    except:
        pass
    
    if cached_price and use_cache:
        return PriceResponse(
            token_id=token_id,
            price=cached_price.price,
            price_percent=cached_price.price_percent,
            bid=cached_price.bid,
            ask=cached_price.ask,
            last_trade=cached_price.last_trade,
            volume_24h=cached_price.volume_24h,
            change_24h=cached_price.change_24h,
            timestamp=cached_price.timestamp.isoformat(),
            cached=True
        )
    
    # Запрос к API
    price = get_price(token_id, use_cache=use_cache)
    
    if not price:
        raise HTTPException(status_code=404, detail=f"Price not found for token {token_id}")
    
    return PriceResponse(
        token_id=token_id,
        price=price.price,
        price_percent=price.price_percent,
        bid=price.bid,
        ask=price.ask,
        last_trade=price.last_trade,
        volume_24h=price.volume_24h,
        change_24h=price.change_24h,
        timestamp=price.timestamp.isoformat(),
        cached=False
    )


@router.get("/last-trade/{token_id}")
async def get_token_last_trade(token_id: str):
    """
    Получить цену последней сделки для токена
    """
    last_price = get_last_trade_price(token_id)
    
    if last_price is None:
        raise HTTPException(status_code=404, detail=f"Last trade price not found for {token_id}")
    
    return {
        "token_id": token_id,
        "last_trade_price": last_price,
        "last_trade_price_percent": round(last_price * 100, 2)
    }


@router.get("")
async def get_multiple_prices(
    token_ids: str = Query(..., description="Список token_id через запятую"),
    use_cache: bool = Query(default=True, description="Использовать кэш")
):
    """
    Массовый запрос цен для нескольких токенов
    
    - **token_ids**: Список token_id через запятую
    - **use_cache**: Использовать ли кэш
    """
    ids = [id.strip() for id in token_ids.split(",") if id.strip()]
    
    if not ids:
        raise HTTPException(status_code=400, detail="No valid token_ids provided")
    
    prices = get_prices(ids, use_cache=use_cache)
    
    if not prices:
        raise HTTPException(status_code=404, detail="No prices found")
    
    return {
        "prices": {
            token_id: price.to_dict()
            for token_id, price in prices.items()
        },
        "count": len(prices)
    }


@router.get("/market/{market_id}", response_model=MarketPricesResponse)
async def get_market_all_prices(market_id: str):
    """
    Получить цены для всех исходов рынка
    
    - **market_id**: Polymarket market ID (conditionId)
    """
    prices = get_market_prices(market_id)
    
    if not prices:
        raise HTTPException(status_code=404, detail=f"No prices found for market {market_id}")
    
    return MarketPricesResponse(
        market_id=market_id,
        outcomes={
            outcome: price.to_dict()
            for outcome, price in prices.items()
        },
        timestamp=datetime.utcnow().isoformat()
    )


@router.post("/sync")
async def sync_prices(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Синхронизировать цены из Polymarket в локальную БД
    
    - **limit**: Количество событий для синхронизации
    """
    try:
        sync_prices_to_db(db, limit=limit)
        return {
            "success": True,
            "synced_limit": limit
        }
    except Exception as e:
        logger.error(f"Sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=PriceStatsResponse)
async def get_price_service_stats():
    """
    Получить статистику сервиса цен
    """
    stats = get_cache_stats()
    return PriceStatsResponse(
        cached_prices=stats["cached_prices"],
        cache_ttl_seconds=stats["cache_ttl_seconds"],
        rate_limit=stats["rate_limit"]
    )


@router.post("/cache/clear")
async def clear_price_cache():
    """
    Очистить кэш цен
    """
    clear_cache()
    return {"success": True, "message": "Price cache cleared"}
