"""
Chart Routes - API endpoints для загрузки исторических данных графиков

Особенности:
1. Failover между зеркалами Binance API
2. Кэширование последних данных (5 минут TTL)
3. Обработка ошибки 451 (Binance блокировка)
4. Fallback на кэш при недоступности API
5. Timeout для защиты от зависания
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict
import requests
import logging
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chart", tags=["chart"])

# Binance API endpoints (failover список)
BINANCE_ENDPOINTS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://api4.binance.com",
]

# Текущий активный endpoint
CURRENT_ENDPOINT_INDEX = 0

# Headers для запросов
BINANCE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
}

# Timeout для запросов (15 секунд)
REQUEST_TIMEOUT = 15

# Кэш данных
CHART_CACHE: Dict[str, Dict] = {}
CACHE_TTL_SECONDS = 300  # 5 минут


def get_current_endpoint() -> str:
    """Получить текущий активный endpoint"""
    global CURRENT_ENDPOINT_INDEX
    return BINANCE_ENDPOINTS[CURRENT_ENDPOINT_INDEX % len(BINANCE_ENDPOINTS)]


def switch_to_next_endpoint():
    """Переключиться на следующий endpoint"""
    global CURRENT_ENDPOINT_INDEX
    CURRENT_ENDPOINT_INDEX += 1
    logger.warning(f"🔄 Switched to Binance endpoint: {get_current_endpoint()}")


def get_from_cache(key: str) -> Optional[Dict]:
    """Получить данные из кэша"""
    if key not in CHART_CACHE:
        return None
    
    cached = CHART_CACHE[key]
    age = (datetime.utcnow() - cached["timestamp"]).total_seconds()
    
    if age > CACHE_TTL_SECONDS:
        logger.warning(f"⚠️ Cache expired for {key}")
        return None
    
    return cached


def save_to_cache(key: str, data: Dict):
    """Сохранить данные в кэш"""
    CHART_CACHE[key] = {
        "data": data,
        "timestamp": datetime.utcnow(),
    }
    logger.debug(f"💾 Cached data for {key}")


class CandleData(BaseModel):
    """Модель свечи"""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class ChartHistoryResponse(BaseModel):
    """Ответ с данными графика"""
    symbol: str
    interval: str
    candles: List[CandleData]
    labels: List[str]  # ISO timestamps для Chart.js
    prices: List[float]  # Close prices для Chart.js
    first_price: float
    last_price: float
    cached: bool = False
    error: Optional[str] = None


@router.get("/history/{symbol}", response_model=ChartHistoryResponse)
async def get_chart_history(
    symbol: str,
    interval: str = Query(default="15m", description="Таймфрейм: 1m, 5m, 15m, 1h, 4h, 1d"),
    limit: int = Query(default=96, description="Количество свечей")
):
    """
    Получить исторические данные для графика из Binance API
    
    Пример:
    - GET /api/chart/history/BTCUSDT?interval=15m&limit=96
    - GET /api/chart/history/ETHUSDT?interval=1h&limit=168
    
    Возвращает свечи для построения графика с кэшированием и fallback
    """
    # Нормализация символа
    normalized_symbol = symbol.upper()
    if not normalized_symbol.endswith('USDT'):
        normalized_symbol = normalized_symbol + 'USDT'
    
    cache_key = f"{normalized_symbol}-{interval}"
    
    # Проверяем кэш
    cached_data = get_from_cache(cache_key)
    if cached_data:
        logger.info(f"💾 Using cached data for {cache_key}")
        return ChartHistoryResponse(
            symbol=normalized_symbol,
            interval=interval,
            candles=[CandleData(**c) for c in cached_data["candles"]],
            labels=cached_data["labels"],
            prices=cached_data["prices"],
            first_price=cached_data["first_price"],
            last_price=cached_data["last_price"],
            cached=True
        )
    
    # Binance interval mapping
    interval_map = {
        "1m": "1m", "5m": "5m", "15m": "15m",
        "30m": "30m", "1h": "1h", "2h": "2h",
        "4h": "4h", "6h": "6h", "12h": "12h",
        "1d": "1d", "3d": "3d", "1w": "1w", "1M": "1M"
    }
    binance_interval = interval_map.get(interval, "15m")
    
    # Пробуем каждый endpoint
    endpoints_to_try = [get_current_endpoint()] + [
        ep for ep in BINANCE_ENDPOINTS if ep != get_current_endpoint()
    ]
    
    last_error = None
    
    for i, endpoint in enumerate(endpoints_to_try[:3]):  # Максимум 3 попытки
        try:
            logger.info(f"🔄 Attempt {i+1}: Trying endpoint {endpoint}")
            
            url = f"{endpoint}/api/v3/klines"
            params = {
                "symbol": normalized_symbol,
                "interval": binance_interval,
                "limit": min(limit, 1000)  # Binance max limit
            }
            
            # Используем asyncio для non-blocking запроса
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda ep=endpoint, p=params: requests.get(
                    f"{ep}/api/v3/klines",
                    params=p,
                    headers=BINANCE_HEADERS,
                    timeout=REQUEST_TIMEOUT
                )
            )
            
            # Обработка ошибки 451
            if response.status_code == 451:
                logger.error(f"🚫 Binance blocked request (451) for {normalized_symbol} from {endpoint}")
                switch_to_next_endpoint()
                continue
            
            if not response.ok:
                logger.error(f"❌ Binance API error {response.status_code} for {normalized_symbol}")
                last_error = f"Binance API error: {response.status_code}"
                switch_to_next_endpoint()
                continue
            
            data = response.json()
            
            if not data or len(data) == 0:
                logger.warning(f"⚠️ Empty response from Binance for {normalized_symbol}")
                last_error = "No data from Binance"
                continue
            
            # Обрабатываем свечи
            candles = []
            labels = []
            prices = []
            
            for candle in data:
                if len(candle) >= 6:
                    candle_data = {
                        "timestamp": candle[0],
                        "open": float(candle[1]),
                        "high": float(candle[2]),
                        "low": float(candle[3]),
                        "close": float(candle[4]),
                        "volume": float(candle[5])
                    }
                    candles.append(candle_data)
                    labels.append(datetime.fromtimestamp(candle[0] / 1000).isoformat())
                    prices.append(float(candle[4]))
            
            if not candles:
                logger.warning(f"⚠️ No valid candles parsed for {normalized_symbol}")
                continue
            
            result_data = {
                "candles": candles,
                "labels": labels,
                "prices": prices,
                "first_price": prices[0],
                "last_price": prices[-1]
            }
            
            # Сохраняем в кэш
            save_to_cache(cache_key, result_data)
            
            logger.info(f"✅ Successfully fetched {len(candles)} candles for {normalized_symbol}")
            
            return ChartHistoryResponse(
                symbol=normalized_symbol,
                interval=interval,
                candles=[CandleData(**c) for c in candles],
                labels=labels,
                prices=prices,
                first_price=prices[0],
                last_price=prices[-1],
                cached=False
            )
            
        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Timeout fetching data for {normalized_symbol} from {endpoint}")
            last_error = "Request timeout"
            switch_to_next_endpoint()
            continue
            
        except Exception as e:
            logger.error(f"❌ Error fetching chart data for {normalized_symbol}: {e}")
            last_error = str(e)
            switch_to_next_endpoint()
            continue
    
    # Все endpoints не сработали - пробуем вернуть кэш даже если устарел
    logger.error(f"🚫 All Binance endpoints failed for {normalized_symbol}")
    
    # Возвращаем последний известный кэш
    all_cache_keys = [k for k in CHART_CACHE.keys() if k.startswith(normalized_symbol)]
    if all_cache_keys:
        for key in all_cache_keys:
            cached = CHART_CACHE.get(key)
            if cached:
                logger.warning(f"⚠️ Returning stale cache for {normalized_symbol}")
                return ChartHistoryResponse(
                    symbol=normalized_symbol,
                    interval=interval,
                    candles=[CandleData(**c) for c in cached["candles"]],
                    labels=cached["labels"],
                    prices=cached["prices"],
                    first_price=cached["first_price"],
                    last_price=cached["last_price"],
                    cached=True,
                    error="Using stale cache (Binance API unavailable)"
                )
    
    # Если кэша нет - выбрасываем ошибку
    raise HTTPException(
        status_code=503,
        detail=last_error or "Binance API unavailable and no cached data"
    )


@router.get("/status")
async def get_chart_service_status():
    """Получить статус сервиса графиков"""
    return {
        "cache_size": len(CHART_CACHE),
        "current_endpoint": get_current_endpoint(),
        "available_endpoints": len(BINANCE_ENDPOINTS),
        "cache_ttl_seconds": CACHE_TTL_SECONDS
    }


@router.post("/cache/clear")
async def clear_chart_cache(symbol: Optional[str] = Query(default=None)):
    """Очистить кэш графиков"""
    if symbol:
        keys_to_delete = [k for k in CHART_CACHE.keys() if symbol.upper() in k]
        for key in keys_to_delete:
            del CHART_CACHE[key]
        return {"cleared": len(keys_to_delete), "symbol": symbol}
    else:
        CHART_CACHE.clear()
        return {"cleared": "all"}
