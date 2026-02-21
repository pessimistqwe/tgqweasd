"""
Polymarket Price Service - Сервис для получения реальных цен из Polymarket

Features:
1. Получение цен через Polymarket Gamma API
2. Кэширование цен для снижения нагрузки
3. Массовый запрос цен для нескольких token_id
4. Интеграция с локальной БД для синхронизации

API Endpoints:
- GET /price?token_id={id} - Цена для одного токена
- GET /prices?token_ids={id1,id2,...} - Массовый запрос
- GET /last-trade-price?token_id={id} - Последняя сделка
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import requests
import logging
from functools import lru_cache
import time

logger = logging.getLogger(__name__)

# ==================== Configuration ====================

POLYMARKET_GAMMA_URL = "https://gamma-api.polymarket.com"
POLYMARKET_CLOB_URL = "https://clob.polymarket.com"

# Timeout для запросов
REQUEST_TIMEOUT = 10

# Headers
POLYMARKET_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# Rate limiting
MAX_REQUESTS_PER_MINUTE = 100
request_timestamps: List[float] = []

# ==================== Rate Limiting ====================

def check_rate_limit():
    """Проверка rate limit (100 запросов в минуту)"""
    global request_timestamps
    
    now = time.time()
    # Удаляем запросы старше 1 минуты
    request_timestamps = [ts for ts in request_timestamps if now - ts < 60]
    
    if len(request_timestamps) >= MAX_REQUESTS_PER_MINUTE:
        raise Exception(f"Rate limit exceeded. Try again in {60 - (now - request_timestamps[0]):.0f} seconds")
    
    request_timestamps.append(now)

# ==================== Price Data Models ====================

class PolymarketPrice:
    """Модель цены Polymarket"""
    def __init__(self, token_id: str, price: float, bid: float = None, ask: float = None, 
                 last_trade: float = None, volume_24h: float = None, change_24h: float = None):
        self.token_id = token_id
        self.price = price  # 0-1 format (0.65 = 65%)
        self.bid = bid
        self.ask = ask
        self.last_trade = last_trade
        self.volume_24h = volume_24h
        self.change_24h = change_24h
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "token_id": self.token_id,
            "price": self.price,
            "price_percent": round(self.price * 100, 2),
            "bid": self.bid,
            "ask": self.ask,
            "last_trade": self.last_trade,
            "volume_24h": self.volume_24h,
            "change_24h": self.change_24h,
            "timestamp": self.timestamp.isoformat()
        }

# ==================== Cache ====================

# Простой in-memory кэш
price_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 30  # 30 секунд TTL для цен

def get_cached_price(token_id: str) -> Optional[PolymarketPrice]:
    """Получить цену из кэша"""
    if token_id not in price_cache:
        return None
    
    cached = price_cache[token_id]
    age = (datetime.utcnow() - cached["timestamp"]).total_seconds()
    
    if age > CACHE_TTL_SECONDS:
        logger.debug(f"Cache expired for {token_id}")
        del price_cache[token_id]
        return None
    
    return PolymarketPrice(**cached["data"])

def save_to_cache(price: PolymarketPrice):
    """Сохранить цену в кэш"""
    price_cache[price.token_id] = {
        "data": {
            "token_id": price.token_id,
            "price": price.price,
            "bid": price.bid,
            "ask": price.ask,
            "last_trade": price.last_trade,
            "volume_24h": price.volume_24h,
            "change_24h": price.change_24h
        },
        "timestamp": price.timestamp
    }

# ==================== API Functions ====================

def get_price(token_id: str, use_cache: bool = True) -> Optional[PolymarketPrice]:
    """
    Получить цену для одного токена
    
    Args:
        token_id: Polymarket token ID
        use_cache: Использовать ли кэш
    
    Returns:
        PolymarketPrice или None при ошибке
    """
    # Проверяем кэш
    if use_cache:
        cached = get_cached_price(token_id)
        if cached:
            logger.debug(f"Cache hit for {token_id}")
            return cached
    
    try:
        check_rate_limit()
        
        url = f"{POLYMARKET_GAMMA_URL}/price"
        params = {"token_id": token_id}
        
        response = requests.get(url, params=params, headers=POLYMARKET_HEADERS, timeout=REQUEST_TIMEOUT)
        
        if response.status_code == 404:
            logger.warning(f"Price not found for token {token_id}")
            return None
        
        if response.status_code != 200:
            logger.error(f"Price API error {response.status_code} for {token_id}")
            return None
        
        data = response.json()
        
        if not data or "price" not in data:
            return None
        
        price = PolymarketPrice(
            token_id=token_id,
            price=float(data["price"]) / 100,  # Конвертируем 0-100 в 0-1
            bid=float(data.get("bid", 0) or 0) / 100,
            ask=float(data.get("ask", 0) or 0) / 100,
            last_trade=float(data.get("last_trade", 0) or 0) / 100,
            volume_24h=float(data.get("volume_24h", 0) or 0),
            change_24h=float(data.get("change_24h", 0) or 0)
        )
        
        save_to_cache(price)
        logger.info(f"✅ Fetched price for {token_id}: {price.price:.4f} ({price.price_percent:.2f}%)")
        
        return price
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching price for {token_id}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error for {token_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error for {token_id}: {e}")
        return None


def get_prices(token_ids: List[str], use_cache: bool = True) -> Dict[str, PolymarketPrice]:
    """
    Массовый запрос цен для нескольких токенов
    
    Args:
        token_ids: Список token ID
        use_cache: Использовать ли кэш
    
    Returns:
        Dict[token_id, PolymarketPrice]
    """
    results = {}
    to_fetch = []
    
    # Проверяем кэш
    if use_cache:
        for token_id in token_ids:
            cached = get_cached_price(token_id)
            if cached:
                results[token_id] = cached
            else:
                to_fetch.append(token_id)
    else:
        to_fetch = token_ids
    
    if not to_fetch:
        logger.debug(f"All {len(token_ids)} prices from cache")
        return results
    
    # Массовый запрос через /prices endpoint
    try:
        check_rate_limit()
        
        url = f"{POLYMARKET_GAMMA_URL}/prices"
        params = {"token_ids": ",".join(to_fetch)}
        
        response = requests.get(url, params=params, headers=POLYMARKET_HEADERS, timeout=REQUEST_TIMEOUT)
        
        if response.status_code != 200:
            logger.error(f"Prices API error {response.status_code}")
            # Fallback: индивидуальные запросы
            for token_id in to_fetch:
                price = get_price(token_id, use_cache=False)
                if price:
                    results[token_id] = price
            return results
        
        data = response.json()
        
        for item in data:
            token_id = item.get("token_id")
            if not token_id or "price" not in item:
                continue
            
            price = PolymarketPrice(
                token_id=token_id,
                price=float(item["price"]) / 100,
                bid=float(item.get("bid", 0) or 0) / 100,
                ask=float(item.get("ask", 0) or 0) / 100,
                volume_24h=float(item.get("volume_24h", 0) or 0),
                change_24h=float(item.get("change_24h", 0) or 0)
            )
            
            results[token_id] = price
            save_to_cache(price)
        
        logger.info(f"✅ Fetched {len(results)} prices")
        return results
        
    except Exception as e:
        logger.error(f"Error fetching prices: {e}")
        # Fallback: индивидуальные запросы
        for token_id in to_fetch:
            price = get_price(token_id, use_cache=False)
            if price:
                results[token_id] = price
        return results


def get_last_trade_price(token_id: str) -> Optional[float]:
    """
    Получить цену последней сделки
    
    Args:
        token_id: Polymarket token ID
    
    Returns:
        Цена последней сделки или None
    """
    try:
        check_rate_limit()
        
        url = f"{POLYMARKET_GAMMA_URL}/last-trade-price"
        params = {"token_id": token_id}
        
        response = requests.get(url, params=params, headers=POLYMARKET_HEADERS, timeout=REQUEST_TIMEOUT)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        return float(data.get("price", 0)) / 100
        
    except Exception as e:
        logger.error(f"Error fetching last trade price: {e}")
        return None


def get_market_prices(market_id: str) -> Dict[str, PolymarketPrice]:
    """
    Получить цены для всех исходов рынка
    
    Args:
        market_id: Polymarket market ID (conditionId)
    
    Returns:
        Dict[outcome_name, PolymarketPrice]
    """
    try:
        # Сначала получаем детали рынка для получения token_id
        market_info = get_market_info(market_id)
        
        if not market_info:
            return {}
        
        token_ids = []
        outcomes = market_info.get("outcomes", [])
        tokens = market_info.get("tokens", [])
        
        # Собираем token_id из tokens
        for token in tokens:
            if "token_id" in token:
                token_ids.append(token["token_id"])
        
        if not token_ids:
            return {}
        
        # Получаем цены
        prices = get_prices(token_ids)
        
        # Маппим на названия исходов
        result = {}
        for token in tokens:
            token_id = token.get("token_id")
            outcome = token.get("outcome", "")
            
            if token_id in prices:
                result[outcome] = prices[token_id]
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching market prices: {e}")
        return {}


def get_market_info(market_id: str) -> Optional[Dict[str, Any]]:
    """
    Получить информацию о рынке
    
    Args:
        market_id: Polymarket market ID
    
    Returns:
        Dict с информацией о рынке или None
    """
    try:
        url = f"{POLYMARKET_GAMMA_URL}/markets"
        params = {"ids": market_id}
        
        response = requests.get(url, params=params, headers=POLYMARKET_HEADERS, timeout=REQUEST_TIMEOUT)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        markets = data.get("markets", data.get("events", []))
        
        if not markets:
            return None
        
        return markets[0]
        
    except Exception as e:
        logger.error(f"Error fetching market info: {e}")
        return None

# ==================== Sync Functions ====================

def sync_prices_to_db(db_session, limit: int = 50):
    """
    Синхронизировать цены из Polymarket в локальную БД
    
    Args:
        db_session: SQLAlchemy session
        limit: Количество событий для синхронизации
    """
    try:
        from .models import Event, EventOption
        
        # Получаем последние активные события с Polymarket ID
        events = db_session.query(Event).filter(
            Event.polymarket_id.isnot(None),
            Event.is_active == True
        ).order_by(Event.id.desc()).limit(limit).all()
        
        updated_count = 0
        
        for event in events:
            try:
                # Получаем цены для всех исходов
                prices = get_market_prices(event.polymarket_id)
                
                if not prices:
                    continue
                
                # Обновляем EventOption
                options = db_session.query(EventOption).filter(
                    EventOption.event_id == event.id
                ).all()
                
                for option in options:
                    outcome_name = option.option_text
                    
                    if outcome_name in prices:
                        price = prices[outcome_name]
                        option.current_price = price.price
                        
                        # Сохраняем token_id если есть
                        if hasattr(option, 'polymarket_token_id') and price.token_id:
                            option.polymarket_token_id = price.token_id
                        
                        updated_count += 1
                
            except Exception as e:
                logger.warning(f"Error syncing prices for event {event.id}: {e}")
                continue
        
        db_session.commit()
        logger.info(f"✅ Synced prices for {updated_count} options")
        
    except Exception as e:
        logger.error(f"Error in sync_prices_to_db: {e}")
        if db_session:
            db_session.rollback()


def get_cache_stats() -> Dict[str, Any]:
    """Получить статистику кэша"""
    return {
        "cached_prices": len(price_cache),
        "cache_ttl_seconds": CACHE_TTL_SECONDS,
        "rate_limit": {
            "max_requests_per_minute": MAX_REQUESTS_PER_MINUTE,
            "current_requests": len(request_timestamps),
            "reset_in_seconds": 60 - (time.time() - request_timestamps[0]) if request_timestamps else 0
        }
    }


def clear_cache():
    """Очистить кэш"""
    price_cache.clear()
    logger.info("🧹 Price cache cleared")
