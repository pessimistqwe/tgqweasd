"""
Volatility Routes - API endpoints для расчета коэффициентов на основе волатильности
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, List
from decimal import Decimal
import asyncio

try:
    from .volatility_service import (
        volatility_service,
        get_volatility_odds,
        get_cached_volatility_odds,
        start_volatility_service,
        stop_volatility_service
    )
except ImportError:
    from volatility_service import (
        volatility_service,
        get_volatility_odds,
        get_cached_volatility_odds,
        start_volatility_service,
        stop_volatility_service
    )

router = APIRouter(prefix="/volatility", tags=["volatility"])


class VolatilityResponse(BaseModel):
    """Ответ с данными о волатильности"""
    symbol: str
    volatility: float  # Волатильность в процентах
    odds: float  # Коэффициент
    cached: bool  # Из кэша или свежий расчет
    timestamp: Optional[str] = None
    price_count: Optional[int] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    current_price: Optional[float] = None
    error: Optional[str] = None


class VolatilityBatchResponse(BaseModel):
    """Ответ для пакетного запроса"""
    data: Dict[str, VolatilityResponse]


@router.get("/odds/{symbol}", response_model=VolatilityResponse)
async def get_odds_for_symbol(symbol: str):
    """
    Получить коэффициент для торговой пары
    
    Пример:
    - GET /api/volatility/odds/BTCUSDT
    
    Возвращает волатильность и коэффициент рассчитанный на основе
    реальных цен за последние 5 минут
    """
    try:
        result = await get_volatility_odds(symbol)
        return VolatilityResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/odds", response_model=VolatilityBatchResponse)
async def get_odds_batch(symbols: str = Query(..., description="Список символов через запятую")):
    """
    Получить коэффициенты для нескольких торговых пар
    
    Пример:
    - GET /api/volatility/odds?symbols=BTCUSDT,ETHUSDT,SOLUSDT
    
    Возвращает волатильность и коэффициенты для всех запрошенных символов
    """
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    
    if not symbol_list:
        raise HTTPException(status_code=400, detail="No symbols provided")
    
    # Запрашиваем все символы параллельно
    tasks = [get_volatility_odds(symbol) for symbol in symbol_list]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    data = {}
    for symbol, result in zip(symbol_list, results):
        if isinstance(result, Exception):
            data[symbol] = {
                "symbol": symbol,
                "volatility": 0.0,
                "odds": 1.90,
                "cached": False,
                "error": str(result)
            }
        else:
            data[symbol] = result
    
    return VolatilityBatchResponse(data=data)


@router.get("/cache/{symbol}", response_model=VolatilityResponse)
async def get_cached_odds(symbol: str):
    """
    Получить закэшированный коэффициент (быстрый ответ)
    
    Пример:
    - GET /api/volatility/cache/BTCUSDT
    
    Возвращает последний рассчитанный коэффициент без нового запроса к API
    """
    result = get_cached_volatility_odds(symbol)
    
    if result is None:
        raise HTTPException(status_code=404, detail="No cached data for symbol")
    
    return VolatilityResponse(**result)


@router.get("/config")
async def get_volatility_config():
    """
    Получить конфигурацию сервиса волатильности
    
    Возвращает пороги волатильности и соответствующие коэффициенты
    """
    return {
        "update_interval_seconds": volatility_service.UPDATE_INTERVAL_SECONDS,
        "volatility_period_minutes": volatility_service.VOLATILITY_PERIOD_MINUTES,
        "thresholds": {
            "low_volatility": {
                "max_percent": float(volatility_service.LOW_VOLATILITY_THRESHOLD),
                "odds_range": [
                    float(volatility_service.BASE_ODDS_LOW_VOLATILITY) - 0.05,
                    float(volatility_service.BASE_ODDS_LOW_VOLATILITY)
                ]
            },
            "medium_volatility": {
                "min_percent": float(volatility_service.LOW_VOLATILITY_THRESHOLD),
                "max_percent": float(volatility_service.HIGH_VOLATILITY_THRESHOLD),
                "odds_range": [1.80, 1.90]
            },
            "high_volatility": {
                "min_percent": float(volatility_service.HIGH_VOLATILITY_THRESHOLD),
                "odds_range": [
                    float(volatility_service.MIN_ODDS),
                    float(volatility_service.BASE_ODDS_HIGH_VOLATILITY)
                ]
            }
        },
        "limits": {
            "min_odds": float(volatility_service.MIN_ODDS),
            "max_odds": float(volatility_service.MAX_ODDS)
        }
    }


@router.post("/start")
async def start_service():
    """Запустить фоновое обновление коэффициентов"""
    await start_volatility_service()
    return {"status": "started", "message": "Volatility service started"}


@router.post("/stop")
async def stop_service():
    """Остановить фоновое обновление коэффициентов"""
    await stop_volatility_service()
    return {"status": "stopped", "message": "Volatility service stopped"}


@router.get("/status")
async def get_service_status():
    """Получить статус сервиса волатильности"""
    return {
        "running": volatility_service._background_task is not None,
        "cache_size": len(volatility_service._odds_cache),
        "update_interval": volatility_service.UPDATE_INTERVAL_SECONDS
    }
