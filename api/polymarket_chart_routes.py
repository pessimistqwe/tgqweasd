"""
Polymarket Chart Routes - Enhanced chart history using Polymarket Candles API

Features:
1. Real Polymarket market data via /candles endpoint
2. Multiple resolutions (minute, hour, day, week)
3. Cache with configurable TTL
4. Fallback to synthetic data if API unavailable
5. Support for multiple outcomes per market

Usage:
    GET /api/polymarket/chart/{market_id}?outcome=Yes&resolution=hour&limit=168
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import requests
import logging

try:
    from .models import get_db, Event, EventOption, PriceHistory
    from .cache_service import cache_result, CacheNamespace
except ImportError:
    from models import get_db, Event, EventOption, PriceHistory
    from cache_service import cache_result, CacheNamespace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/polymarket/chart", tags=["Polymarket Chart"])

# ==================== Configuration ====================

POLYMARKET_CANDLES_URL = "https://gamma-api.polymarket.com/candles"
REQUEST_TIMEOUT = 15

# Headers
POLYMARKET_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# Valid resolutions
VALID_RESOLUTIONS = ["minute", "hour", "day", "week"]

# ==================== Pydantic Models ====================

class CandleData(BaseModel):
    """Модель свечи"""
    timestamp: int  # Unix timestamp in milliseconds
    open: float
    high: float
    low: float
    close: float
    volume: float


class ChartHistoryResponse(BaseModel):
    """Ответ с данными графика"""
    market_id: str
    outcome: str
    resolution: str
    candles: List[CandleData]
    labels: List[str]  # ISO format timestamps
    prices: List[float]  # Close prices
    first_price: float
    last_price: float
    price_change: float  # Percentage change
    cached: bool = False
    source: str = "polymarket"  # "polymarket" or "synthetic"


class ChartStatsResponse(BaseModel):
    """Статистика графика"""
    market_id: str
    outcome: str
    current_price: float
    price_24h_ago: float
    price_change_24h: float
    high_24h: float
    low_24h: float
    volume_24h: float
    candles_count: int


# ==================== Helper Functions ====================

def fetch_polymarket_candles(
    market: str,
    outcome: str,
    resolution: str = "hour",
    limit: int = 168
) -> Optional[List[Dict]]:
    """
    Fetch candles from Polymarket API

    Args:
        market: Market ID (conditionId)
        outcome: Outcome name (e.g., "Yes", "No")
        resolution: Candle resolution (minute, hour, day, week)
        limit: Number of candles (max 1000)

    Returns:
        List of candle data or None on error
    """
    params = {
        "market": market,
        "outcome": outcome,
        "resolution": resolution,
        "limit": min(limit, 1000)
    }

    try:
        response = requests.get(
            POLYMARKET_CANDLES_URL,
            params=params,
            headers=POLYMARKET_HEADERS,
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code == 404:
            logger.warning(f"Polymarket candles 404 for market {market}")
            return None

        if response.status_code != 200:
            logger.error(f"Polymarket candles API error {response.status_code}")
            return None

        data = response.json()

        # Polymarket returns array of [timestamp, open, high, low, close, volume]
        if not isinstance(data, list) or len(data) == 0:
            logger.warning(f"No candles data for {market}/{outcome}")
            return None

        return data

    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching Polymarket candles for {market}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error fetching candles: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching candles: {e}")
        return None


def parse_candle_data(raw_candles: List[List]) -> List[CandleData]:
    """
    Parse raw Polymarket candle data

    Polymarket format: [timestamp_ms, open, high, low, close, volume]
    Prices are in 0-100 format, we convert to 0-1

    Args:
        raw_candles: Raw candle data from API

    Returns:
        List of CandleData objects
    """
    candles = []

    for candle in raw_candles:
        if len(candle) >= 6:
            candles.append(CandleData(
                timestamp=candle[0],  # Keep in ms for Chart.js
                open=candle[1] / 100,  # Convert 0-100 to 0-1
                high=candle[2] / 100,
                low=candle[3] / 100,
                close=candle[4] / 100,
                volume=float(candle[5])
            ))

    return candles


def generate_synthetic_candles(
    current_price: float,
    volatility: float = 0.05,
    limit: int = 168
) -> List[CandleData]:
    """
    Generate synthetic candle data when API is unavailable

    Uses random walk with drift to simulate price movement

    Args:
        current_price: Current market price
        volatility: Price volatility (0-1)
        limit: Number of candles to generate

    Returns:
        List of synthetic CandleData objects
    """
    import random

    candles = []
    now = datetime.utcnow()

    # Start from a price and walk backwards
    price = current_price
    base_time = now.timestamp() * 1000

    for i in range(limit, 0, -1):
        # Random walk
        change = random.uniform(-volatility, volatility)
        open_price = price
        close_price = price * (1 + change)

        # High/Low based on range
        high_price = max(open_price, close_price) * (1 + random.uniform(0, volatility / 2))
        low_price = min(open_price, close_price) * (1 - random.uniform(0, volatility / 2))

        # Volume (random)
        volume = random.uniform(100, 10000)

        candles.append(CandleData(
            timestamp=int(base_time - (i * 3600000)),  # Hourly candles
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume
        ))

        price = close_price

    return candles


def calculate_price_stats(candles: List[CandleData]) -> Dict[str, float]:
    """
    Calculate price statistics from candles

    Args:
        candles: List of candles

    Returns:
        Dict with price statistics
    """
    if not candles:
        return {
            "first_price": 0,
            "last_price": 0,
            "price_change": 0,
            "high": 0,
            "low": 0,
            "volume": 0
        }

    prices = [c.close for c in candles]
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]
    volumes = [c.volume for c in candles]

    first_price = prices[0]
    last_price = prices[-1]
    price_change = ((last_price - first_price) / first_price * 100) if first_price > 0 else 0

    return {
        "first_price": first_price,
        "last_price": last_price,
        "price_change": round(price_change, 2),
        "high": max(highs),
        "low": min(lows),
        "volume": sum(volumes)
    }


# ==================== API Endpoints ====================

@router.get("/{market_id}", response_model=ChartHistoryResponse)
@cache_result(namespace=CacheNamespace.POLYMARKET, ttl_seconds=180)
async def get_market_chart(
    market_id: str,
    outcome: str = Query(default="Yes", description="Outcome name"),
    resolution: str = Query(default="hour", description="Resolution: minute, hour, day, week"),
    limit: int = Query(default=168, ge=1, le=1000, description="Number of candles")
):
    """
    Get chart history for a Polymarket market

    Uses real Polymarket candles API for accurate historical data.
    Falls back to synthetic data if API is unavailable.

    - **market_id**: Polymarket market ID (conditionId)
    - **outcome**: Outcome name (e.g., "Yes", "No")
    - **resolution**: Candle resolution
    - **limit**: Number of candles to return
    """
    # Validate resolution
    if resolution not in VALID_RESOLUTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid resolution. Use: {', '.join(VALID_RESOLUTIONS)}"
        )

    # Try to fetch from Polymarket API
    raw_candles = fetch_polymarket_candles(market_id, outcome, resolution, limit)

    if raw_candles and len(raw_candles) > 0:
        # Parse real data
        candles = parse_candle_data(raw_candles)
        stats = calculate_price_stats(candles)

        logger.info(f"✅ Fetched {len(candles)} real candles for {market_id}")

        return ChartHistoryResponse(
            market_id=market_id,
            outcome=outcome,
            resolution=resolution,
            candles=candles,
            labels=[datetime.fromtimestamp(c.timestamp / 1000).isoformat() for c in candles],
            prices=[c.close for c in candles],
            first_price=stats["first_price"],
            last_price=stats["last_price"],
            price_change=stats["price_change"],
            cached=False,
            source="polymarket"
        )

    # Fallback: Try to get from local PriceHistory
    try:
        from sqlalchemy import desc
        # This would require DB session - skip for now
        logger.warning(f"No Polymarket data, would fallback to DB history")
    except Exception:
        pass

    # Final fallback: Generate synthetic data
    logger.warning(f"⚠️ Using synthetic data for {market_id}")

    # Get current price from event_options if possible
    current_price = 0.5  # Default
    # In production, query the database for current price

    synthetic_candles = generate_synthetic_candles(current_price, volatility=0.03, limit=limit)
    stats = calculate_price_stats(synthetic_candles)

    return ChartHistoryResponse(
        market_id=market_id,
        outcome=outcome,
        resolution=resolution,
        candles=synthetic_candles,
        labels=[datetime.fromtimestamp(c.timestamp / 1000).isoformat() for c in synthetic_candles],
        prices=[c.close for c in synthetic_candles],
        first_price=stats["first_price"],
        last_price=stats["last_price"],
        price_change=stats["price_change"],
        cached=False,
        source="synthetic"
    )


@router.get("/{market_id}/stats", response_model=ChartStatsResponse)
async def get_market_chart_stats(
    market_id: str,
    outcome: str = Query(default="Yes", description="Outcome name"),
    db: Session = Depends(get_db)
):
    """
    Get chart statistics for a market

    Returns 24h price change, high/low, volume
    """
    # Fetch last 24h of hourly candles
    raw_candles = fetch_polymarket_candles(market_id, outcome, "hour", 24)

    if not raw_candles or len(raw_candles) == 0:
        raise HTTPException(status_code=404, detail="No chart data available")

    candles = parse_candle_data(raw_candles)
    stats = calculate_price_stats(candles)

    # Get current price from DB
    event = db.query(Event).filter(Event.polymarket_id == market_id).first()
    current_price = 0.5

    if event and event.event_options:
        for option in event.event_options:
            if outcome.lower() in option.option_text.lower():
                current_price = option.current_price
                break

    # Calculate 24h change
    price_24h_ago = stats["first_price"] if candles else current_price
    price_change_24h = ((current_price - price_24h_ago) / price_24h_ago * 100) if price_24h_ago > 0 else 0

    return ChartStatsResponse(
        market_id=market_id,
        outcome=outcome,
        current_price=current_price,
        price_24h_ago=price_24h_ago,
        price_change_24h=round(price_change_24h, 2),
        high_24h=stats["high"],
        low_24h=stats["low"],
        volume_24h=stats["volume"],
        candles_count=len(candles)
    )


@router.get("/{market_id}/compare")
async def compare_outcomes(
    market_id: str,
    resolution: str = Query(default="hour", description="Resolution"),
    limit: int = Query(default=168, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Compare multiple outcomes from the same market

    Returns chart data for all outcomes side by side
    """
    # Get event from DB to find all outcomes
    event = db.query(Event).filter(Event.polymarket_id == market_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Market not found in database")

    outcomes_data = {}

    for option in event.event_options:
        outcome_name = option.option_text

        # Fetch candles for this outcome
        raw_candles = fetch_polymarket_candles(market_id, outcome_name, resolution, limit)

        if raw_candles:
            candles = parse_candle_data(raw_candles)
            outcomes_data[outcome_name] = {
                "prices": [c.close for c in candles],
                "labels": [datetime.fromtimestamp(c.timestamp / 1000).isoformat() for c in candles],
                "current_price": option.current_price
            }

    if not outcomes_data:
        raise HTTPException(status_code=404, detail="No chart data for any outcome")

    return {
        "market_id": market_id,
        "resolution": resolution,
        "outcomes": outcomes_data
    }


@router.post("/{market_id}/cache/update")
async def update_market_chart_cache(
    market_id: str,
    db: Session = Depends(get_db)
):
    """
    Manually update chart cache for a market

    Fetches latest candles and stores in PriceHistory table
    """
    event = db.query(Event).filter(Event.polymarket_id == market_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Market not found")

    updated_count = 0

    for option in event.event_options:
        outcome = option.option_text

        # Fetch latest candles
        raw_candles = fetch_polymarket_candles(market_id, outcome, "hour", 24)

        if not raw_candles:
            continue

        candles = parse_candle_data(raw_candles)

        # Store in PriceHistory
        for candle in candles[-12:]:  # Last 12 hours
            price_history = PriceHistory(
                event_id=event.id,
                option_index=option.option_index,
                price=candle.close,
                volume=candle.volume,
                timestamp=datetime.fromtimestamp(candle.timestamp / 1000)
            )
            db.add(price_history)
            updated_count += 1

    db.commit()

    return {
        "success": True,
        "market_id": market_id,
        "records_updated": updated_count
    }


@router.get("/health")
async def get_chart_health():
    """
    Check Polymarket candles API health
    """
    try:
        # Test with a known market
        test_market = "polymarket-test"  # Would use real market ID in production

        response = requests.get(
            POLYMARKET_CANDLES_URL,
            params={"market": test_market, "outcome": "Yes", "resolution": "hour", "limit": 1},
            headers=POLYMARKET_HEADERS,
            timeout=5
        )

        # Even 404 is OK - means API is responding
        if response.status_code in [200, 404]:
            return {
                "status": "healthy",
                "api": "polymarket_candles",
                "endpoint": POLYMARKET_CANDLES_URL
            }

    except Exception as e:
        return {
            "status": "degraded",
            "api": "polymarket_candles",
            "error": str(e)
        }

    return {
        "status": "unhealthy",
        "api": "polymarket_candles"
    }
