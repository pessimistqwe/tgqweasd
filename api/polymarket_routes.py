"""
Polymarket Routes - API endpoints для работы с Polymarket API

Функционал:
- GET /api/polymarket/market/{market_id} - Детали рынка
- GET /api/polymarket/search?q={query} - Поиск рынков
- GET /api/polymarket/candles - Исторические данные (candles)
- GET /api/polymarket/categories - Список категорий Polymarket

Все endpoints используют кэширование для снижения нагрузки на API.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import requests
import logging
import os

try:
    from .models import get_db, Event, EventOption
    from .cache_service import cache_result, get_cached, CacheNamespace
except ImportError:
    from models import get_db, Event, EventOption
    from cache_service import cache_result, get_cached, CacheNamespace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/polymarket", tags=["Polymarket"])

# ==================== Configuration ====================

POLYMARKET_GAMMA_URL = "https://gamma-api.polymarket.com"
POLYMARKET_CLOB_URL = "https://clob.polymarket.com"

# Timeout для запросов (секунды)
REQUEST_TIMEOUT = 15

# Headers для запросов
POLYMARKET_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# ==================== Pydantic Models ====================

class PolymarketMarket(BaseModel):
    """Модель рынка Polymarket"""
    id: str
    question: str
    image: Optional[str] = None
    volume: float = 0.0
    liquidity: float = 0.0
    openInterest: float = 0.0
    endDate: Optional[str] = None
    category: Optional[str] = None
    outcomes: List[str] = []
    outcomePrices: List[float] = []
    yesBid: Optional[float] = None
    yesAsk: Optional[float] = None
    noBid: Optional[float] = None
    noAsk: Optional[float] = None
    lastPrice: Optional[float] = None
    previousPrice: Optional[float] = None
    change24h: Optional[float] = None


class PolymarketSearchResult(BaseModel):
    """Результат поиска рынков"""
    total: int
    markets: List[PolymarketMarket]


class PolymarketCandle(BaseModel):
    """Модель свечи"""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class PolymarketCandlesResponse(BaseModel):
    """Ответ с данными свечей"""
    market: str
    outcome: str
    resolution: str
    candles: List[PolymarketCandle]


class PolymarketCategory(BaseModel):
    """Модель категории"""
    id: str
    name: str
    markets_count: int


# ==================== Helper Functions ====================

def fetch_polymarket_api(endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
    """
    Выполнить запрос к Polymarket Gamma API

    Args:
        endpoint: URL endpoint (например, "/markets/{id}")
        params: Параметры запроса

    Returns:
        Данные ответа или None при ошибке
    """
    url = f"{POLYMARKET_GAMMA_URL}{endpoint}"

    try:
        response = requests.get(
            url,
            params=params,
            headers=POLYMARKET_HEADERS,
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code == 404:
            logger.warning(f"Polymarket 404: {url}")
            return None

        if response.status_code != 200:
            logger.error(f"Polymarket API error {response.status_code}: {response.text[:200]}")
            return None

        return response.json()

    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching Polymarket: {url}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error fetching Polymarket: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching Polymarket: {e}")
        return None


def parse_market_data(data: Dict[str, Any]) -> PolymarketMarket:
    """
    Распарсить данные рынка из Polymarket API

    Args:
        data: Сырые данные от API

    Returns:
        PolymarketMarket
    """
    # Извлекаем outcomes
    outcomes = []
    outcome_prices = []

    # Формат 1: tokens array
    if "tokens" in data and isinstance(data["tokens"], list):
        for token in data["tokens"]:
            outcomes.append(token.get("outcome", ""))
            outcome_prices.append(float(token.get("price", 0.5)) * 100)

    # Формат 2: outcomes + outcomePrices
    elif "outcomes" in data and isinstance(data["outcomes"], list):
        outcomes = [str(o) for o in data["outcomes"]]
        if "outcomePrices" in data and isinstance(data["outcomePrices"], list):
            outcome_prices = [float(p) for p in data["outcomePrices"]]
        else:
            outcome_prices = [50.0] * len(outcomes)

    # Рассчитываем change24h
    change_24h = None
    if data.get("lastPrice") and data.get("previousPrice"):
        change_24h = ((data["lastPrice"] - data["previousPrice"]) / data["previousPrice"]) * 100

    return PolymarketMarket(
        id=data.get("id", data.get("conditionId", "")),
        question=data.get("question", data.get("title", "")),
        image=data.get("image"),
        volume=float(data.get("volume", 0) or 0),
        liquidity=float(data.get("liquidity", 0) or 0),
        openInterest=float(data.get("openInterest", 0) or 0),
        endDate=data.get("endDate"),
        category=data.get("category"),
        outcomes=outcomes,
        outcomePrices=outcome_prices,
        yesBid=data.get("yesBid"),
        yesAsk=data.get("yesAsk"),
        noBid=data.get("noBid"),
        noAsk=data.get("noAsk"),
        lastPrice=data.get("lastPrice"),
        previousPrice=data.get("previousPrice"),
        change24h=round(change_24h, 2) if change_24h else None
    )


# ==================== Market Details ====================

@router.get("/market/{market_id}", response_model=PolymarketMarket)
@cache_result(namespace=CacheNamespace.POLYMARKET, ttl_seconds=300)
async def get_market_details(market_id: str):
    """
    Получить детальную информацию о рынке из Polymarket

    Возвращает полную информацию о рынке включая:
    - Вопрос/название
    - Исходы и их цены
    - Объем и ликвидность
    - Время окончания
    - Изменение за 24h

    Кэширование: 5 минут
    """
    data = fetch_polymarket_api(f"/markets/{market_id}")

    if not data:
        # Пробуем fallback на /events
        data = fetch_polymarket_api(f"/events/{market_id}")

    if not data:
        raise HTTPException(status_code=404, detail=f"Market {market_id} not found in Polymarket")

    return parse_market_data(data)


# ==================== Market Search ====================

@router.get("/search", response_model=PolymarketSearchResult)
@cache_result(namespace=CacheNamespace.POLYMARKET, ttl_seconds=600)
async def search_markets(
    q: str = Query(..., min_length=2, description="Поисковый запрос"),
    limit: int = Query(20, ge=1, le=100, description="Максимум результатов"),
    category: Optional[str] = Query(None, description="Фильтр по категории")
):
    """
    Поиск рынков Polymarket по запросу

    Ищет по названию, описанию и категории.
    Поддерживает фильтрацию по категории.

    Кэширование: 10 минут
    """
    params = {
        "search": q,
        "limit": limit,
    }

    if category:
        params["category"] = category

    data = fetch_polymarket_api("/markets", params)

    if not data:
        # Fallback: пробуем искать через /events
        params["q"] = q
        data = fetch_polymarket_api("/events", params)

    if not data:
        return PolymarketSearchResult(total=0, markets=[])

    # Обрабатываем ответ
    markets_list = []
    if isinstance(data, list):
        markets_list = data
    elif isinstance(data, dict):
        markets_list = data.get("markets", data.get("events", data.get("results", [])))

    markets = [parse_market_data(m) for m in markets_list if isinstance(m, dict)]

    return PolymarketSearchResult(total=len(markets), markets=markets)


# ==================== Candles/History ====================

@router.get("/candles", response_model=PolymarketCandlesResponse)
@cache_result(namespace=CacheNamespace.POLYMARKET, ttl_seconds=180)
async def get_market_candles(
    market: str = Query(..., description="ID рынка (conditionId)"),
    outcome: str = Query(..., description="Название исхода (например, 'Yes')"),
    resolution: str = Query(default="hour", description="Разрешение: minute, hour, day, week"),
    limit: int = Query(default=168, ge=1, le=1000, description="Количество свечей")
):
    """
    Получить исторические данные свечей для рынка

    Polymarket candles API возвращает данные в формате:
    [timestamp, open, high, low, close, volume]

    Разрешения:
    - minute: 1 минута (макс 10080 точек = 7 дней)
    - hour: 1 час (макс 168 точек = 7 дней)
    - day: 1 день (макс 365 точек)
    - week: 1 неделя

    Кэширование: 3 минуты (для актуальности)
    """
    # Валидация resolution
    valid_resolutions = ["minute", "hour", "day", "week"]
    if resolution not in valid_resolutions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid resolution. Use: {', '.join(valid_resolutions)}"
        )

    params = {
        "market": market,
        "outcome": outcome,
        "resolution": resolution,
        "limit": limit
    }

    url = f"{POLYMARKET_GAMMA_URL}/candles"

    try:
        response = requests.get(
            url,
            params=params,
            headers=POLYMARKET_HEADERS,
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code != 200:
            logger.error(f"Candles API error {response.status_code}: {response.text[:200]}")
            raise HTTPException(status_code=502, detail="Polymarket candles API error")

        data = response.json()

        if not isinstance(data, list):
            return PolymarketCandlesResponse(
                market=market,
                outcome=outcome,
                resolution=resolution,
                candles=[]
            )

        candles = []
        for candle in data:
            if len(candle) >= 6:
                candles.append(PolymarketCandle(
                    timestamp=candle[0],
                    open=candle[1] / 100,  # Конвертируем 0-100 → 0-1
                    high=candle[2] / 100,
                    low=candle[3] / 100,
                    close=candle[4] / 100,
                    volume=float(candle[5])
                ))

        return PolymarketCandlesResponse(
            market=market,
            outcome=outcome,
            resolution=resolution,
            candles=candles
        )

    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Request timeout")
    except requests.exceptions.RequestException as e:
        logger.error(f"Candles request error: {e}")
        raise HTTPException(status_code=502, detail="Polymarket API unavailable")


# ==================== Categories ====================

@router.get("/categories", response_model=List[PolymarketCategory])
@cache_result(namespace=CacheNamespace.POLYMARKET, ttl_seconds=3600)
async def get_polymarket_categories():
    """
    Получить список категорий из Polymarket

    Возвращает категории с количеством рынков в каждой.

    Кэширование: 1 час
    """
    data = fetch_polymarket_api("/categories")

    if not data:
        # Возвращаем дефолтные категории
        return [
            PolymarketCategory(id="politics", name="Politics", markets_count=0),
            PolymarketCategory(id="sports", name="Sports", markets_count=0),
            PolymarketCategory(id="crypto", name="Crypto", markets_count=0),
            PolymarketCategory(id="pop_culture", name="Pop Culture", markets_count=0),
            PolymarketCategory(id="business", name="Business", markets_count=0),
            PolymarketCategory(id="science", name="Science", markets_count=0),
        ]

    categories = []
    if isinstance(data, list):
        for cat in data:
            categories.append(PolymarketCategory(
                id=cat.get("id", cat.get("slug", "")),
                name=cat.get("name", ""),
                markets_count=int(cat.get("marketsCount", cat.get("count", 0)))
            ))

    return categories


# ==================== Trending Markets ====================

@router.get("/trending", response_model=List[PolymarketMarket])
@cache_result(namespace=CacheNamespace.POLYMARKET, ttl_seconds=300)
async def get_trending_markets(
    limit: int = Query(20, ge=1, le=50, description="Максимум результатов")
):
    """
    Получить трендовые рынки

    Сортирует по объему торгов за 24 часа.

    Кэширование: 5 минут
    """
    params = {
        "order": "volume",
        "ascending": "false",
        "limit": limit,
        "closed": "false",
    }

    data = fetch_polymarket_api("/markets", params)

    if not data:
        return []

    markets_list = []
    if isinstance(data, list):
        markets_list = data
    elif isinstance(data, dict):
        markets_list = data.get("markets", data.get("events", []))

    return [parse_market_data(m) for m in markets_list if isinstance(m, dict)]


# ==================== Recent Markets ====================

@router.get("/recent", response_model=List[PolymarketMarket])
@cache_result(namespace=CacheNamespace.POLYMARKET, ttl_seconds=300)
async def get_recent_markets(
    limit: int = Query(20, ge=1, le=50, description="Максимум результатов")
):
    """
    Получить последние добавленные рынки

    Сортирует по дате создания (новые сначала).

    Кэширование: 5 минут
    """
    params = {
        "order": "created_at",
        "ascending": "false",
        "limit": limit,
    }

    data = fetch_polymarket_api("/markets", params)

    if not data:
        return []

    markets_list = []
    if isinstance(data, list):
        markets_list = data
    elif isinstance(data, dict):
        markets_list = data.get("markets", data.get("events", []))

    return [parse_market_data(m) for m in markets_list if isinstance(m, dict)]


# ==================== Market Stats ====================

@router.get("/market/{market_id}/stats")
@cache_result(namespace=CacheNamespace.POLYMARKET, ttl_seconds=180)
async def get_market_stats(market_id: str):
    """
    Получить статистику рынка

    Включает:
    - Объем за 24h
    - Ликвидность
    - Открытый интерес
    - Количество ставок
    - Изменение цены за 24h

    Кэширование: 3 минуты
    """
    data = fetch_polymarket_api(f"/markets/{market_id}")

    if not data:
        raise HTTPException(status_code=404, detail=f"Market {market_id} not found")

    market = parse_market_data(data)

    return {
        "market_id": market.id,
        "volume_24h": market.volume,
        "liquidity": market.liquidity,
        "open_interest": market.openInterest,
        "change_24h": market.change24h,
        "last_price": market.lastPrice,
        "yes_bid": market.yesBid,
        "yes_ask": market.yesAsk,
        "no_bid": market.noBid,
        "no_ask": market.noAsk,
        "outcomes_count": len(market.outcomes),
        "end_date": market.endDate
    }


# ==================== Health Check ====================

@router.get("/health")
async def get_polymarket_health():
    """
    Проверить доступность Polymarket API
    """
    try:
        response = requests.get(
            f"{POLYMARKET_GAMMA_URL}/health",
            headers=POLYMARKET_HEADERS,
            timeout=5
        )

        if response.status_code == 200:
            return {"status": "healthy", "api": "polymarket_gamma"}

    except Exception as e:
        logger.warning(f"Polymarket health check failed: {e}")

    # Fallback: пробуем сделать запрос к markets
    data = fetch_polymarket_api("/markets?limit=1")
    if data:
        return {"status": "healthy", "api": "polymarket_gamma", "fallback": True}

    return {"status": "degraded", "api": "polymarket_gamma"}
