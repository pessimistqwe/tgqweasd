from fastapi import FastAPI, HTTPException, Depends, Query, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from datetime import datetime, timedelta
import json
import requests
from typing import List, Optional
import os
import asyncio
import logging
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlsplit
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Rate limiting
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware

# Импорт моделей
try:
    from .models import (
        get_db, User, Event, EventOption, UserPrediction,
        Transaction, TransactionType, TransactionStatus, PriceHistory,
        EventComment, BetHistory
    )
except ImportError:
    from models import (
        get_db, User, Event, EventOption, UserPrediction,
        Transaction, TransactionType, TransactionStatus, PriceHistory,
        EventComment, BetHistory
    )

# Импорт betting engine
try:
    from .betting_routes import router as betting_router
    from .telegram_auth import init_telegram_validator
    from .betting_resolver import start_resolver_worker, stop_resolver_worker
    from .volatility_routes import router as volatility_router
    from .volatility_service import start_volatility_service, stop_volatility_service
    from .admin_routes import router as admin_router
    from .chart_routes import router as chart_router
    from .polymarket_routes import router as polymarket_router
    from .leaderboard_routes import router as leaderboard_router
    from .polymarket_chart_routes import router as polymarket_chart_router
    from .polymarket_price_routes import router as polymarket_price_router
    from .cache_service import create_cache_routes, get_cache_stats
    from .websocket_service import create_websocket_routes, init_websocket_service, stop_websocket_service
    from .analytics_routes import router as analytics_router
    HISTORICAL_AVAILABLE = True
except ImportError:
    from betting_routes import router as betting_router
    from telegram_auth import init_telegram_validator
    from betting_resolver import start_resolver_worker, stop_resolver_worker
    from volatility_routes import router as volatility_router
    from volatility_service import start_volatility_service, stop_volatility_service
    from admin_routes import router as admin_router
    from chart_routes import router as chart_router
    from polymarket_routes import router as polymarket_router
    from leaderboard_routes import router as leaderboard_router
    from polymarket_chart_routes import router as polymarket_chart_router
    from polymarket_price_routes import router as polymarket_price_router
    from cache_service import create_cache_routes, get_cache_stats
    from websocket_service import create_websocket_routes, init_websocket_service, stop_websocket_service
    from analytics_routes import router as analytics_router
    HISTORICAL_AVAILABLE = True

# Импорт historical routes (опционально)
historical_router = None
try:
    from .historical_routes import router as historical_router
except ImportError:
    try:
        from historical_routes import router as historical_router
    except ImportError:
        historical_router = None

app = FastAPI(title="EventPredict API")

# ==================== Rate Limiting ====================
# Лимитер для защиты от злоупотреблений
limiter = Limiter(
    key_func=get_remote_address,  # Используем IP для идентификации
    default_limits=["100/minute"]  # По умолчанию 100 запросов в минуту
)

# Добавляем middleware
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# Подключаем betting routes
app.include_router(betting_router)

# Подключаем volatility routes
app.include_router(volatility_router)

# Подключаем admin routes
app.include_router(admin_router)

# Подключаем chart routes
app.include_router(chart_router)

# Подключаем polymarket routes
app.include_router(polymarket_router)

# Подключаем polymarket chart routes
app.include_router(polymarket_chart_router)

# Подключаем polymarket price routes
app.include_router(polymarket_price_router)

# Подключаем leaderboard routes
app.include_router(leaderboard_router)

# Подключаем analytics routes
app.include_router(analytics_router)

# Подключаем historical routes (если доступны)
if historical_router:
    app.include_router(historical_router)

# Подключаем cache routes (если доступны)
cache_router = create_cache_routes()
if cache_router:
    app.include_router(cache_router)

# Подключаем websocket routes (если доступны)
websocket_router = create_websocket_routes()
if websocket_router:
    app.include_router(websocket_router)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Binance API для реальных цен криптовалют
BINANCE_WS_URL = "wss://stream.binance.com:9443/ws"
BINANCE_API_URL = "https://api.binance.com/api/v3"

# Mapping событий на Binance символы
CRYPTO_SYMBOLS = {
    'bitcoin': 'BTCUSDT',
    'btc': 'BTCUSDT',
    'ethereum': 'ETHUSDT',
    'eth': 'ETHUSDT',
    'solana': 'SOLUSDT',
    'sol': 'SOLUSDT',
    'ton': 'TONUSDT',
    'bnb': 'BNBUSDT',
    'xrp': 'XRPUSDT',
    'cardano': 'ADAUSDT',
    'dogecoin': 'DOGEUSDT',
    'doge': 'DOGEUSDT',
    'polkadot': 'DOTUSDT',
    'dot': 'DOTUSDT',
    'avalanche': 'AVAXUSDT',
    'avax': 'AVAXUSDT',
}

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# CORS для работы с frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Vercel routes keep the "/api" prefix; strip it so FastAPI routes match.
@app.middleware("http")
async def strip_api_prefix(request, call_next):
    path = request.scope.get("path", "")
    if path == "/api":
        request.scope["path"] = "/"
    elif path.startswith("/api/"):
        request.scope["path"] = path[4:] or "/"
    return await call_next(request)

# ==================== POLYMARKET API INTEGRATION ====================

POLYMARKET_API_URL = "https://gamma-api.polymarket.com"
# Интервал синхронизации: 2 часа (7200 секунд) для экономии кредитов Railway
POLYMARKET_SYNC_INTERVAL_SECONDS = int(os.getenv("POLYMARKET_SYNC_INTERVAL", "7200"))
last_polymarket_sync = datetime.min
sync_stats = {"total_synced": 0, "last_sync": None, "last_error": None}
POLYMARKET_VERBOSE_LOGS = os.getenv("POLYMARKET_VERBOSE_LOGS", "0") == "1"

# Исторические данные: используем candles API для реальных данных
POLYMARKET_CANDLES_URL = "https://gamma-api.polymarket.com/candles"

# Поддерживаемые разрешения для candles API
POLYMARKET_CANDLES_RESOLUTIONS = {
    '1m': 1,       # 1 минута
    '5m': 5,       # 5 минут
    '15m': 15,     # 15 минут
    '30m': 30,     # 30 минут
    '1h': 60,      # 1 час
    '2h': 120,     # 2 часа
    '4h': 240,     # 4 часа
    '6h': 360,     # 6 часов
    '12h': 720,    # 12 часов
    '1d': 1440,    # 1 день
    '3d': 4320,    # 3 дня
    '1w': 10080,   # 1 неделя
    '1M': 43200    # 1 месяц (30 дней)
}

# Лимиты для разных разрешений
POLYMARKET_CANDLES_LIMITS = {
    '1m': 100,     # 100 минут
    '5m': 500,     # ~41 час
    '15m': 500,    # ~5 дней
    '30m': 500,    # ~10 дней
    '1h': 168,     # 7 дней
    '2h': 336,     # 28 дней
    '4h': 168,     # 28 дней
    '6h': 112,     # 28 дней
    '12h': 56,     # 28 дней
    '1d': 90,      # 90 дней
    '3d': 30,      # 90 дней
    '1w': 52,      # 1 год
    '1M': 24       # 2 года
}

# Лимит API запросов при синхронизации истории цен (для защиты от rate limit)
PRICE_HISTORY_SYNC_LIMIT = 10  # Максимум 10 событий за раз

# Инициализация планировщика
scheduler = AsyncIOScheduler()

# Admin Telegram ID
ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "1972885597"))

# CORS proxy для изображений Polymarket
POLYMARKET_IMAGE_PROXY = os.getenv("POLYMARKET_IMAGE_PROXY", "https://gamma-api.polymarket.com")

# Ключевые слова для определения категорий
CATEGORY_KEYWORDS = {
    'politics': ['trump', 'biden', 'election', 'president', 'congress', 'senate', 'vote', 'democrat', 'republican', 'political', 'government', 'minister', 'parliament', 'putin', 'zelensky', 'ukraine', 'russia', 'china', 'nato', 'white house', 'kremlin', 'prime minister', 'governor', 'mayor', 'policy', 'legislation', 'bill', 'veto', 'impeachment', 'sanction', 'tariff', 'embassy', 'ambassador', 'summit', 'treaty', 'alliance', 'coalition', 'party', 'campaign', 'debate', 'poll', 'ballot', 'referendum'],
    'sports': ['nba', 'nfl', 'mlb', 'soccer', 'football', 'basketball', 'baseball', 'tennis', 'golf', 'ufc', 'boxing', 'f1', 'formula', 'championship', 'world cup', 'super bowl', 'olympics', 'game', 'match', 'team', 'player', 'league', 'tournament', 'finals', 'playoffs', 'coach', 'athlete', 'sport', 'win', 'loss', 'score', 'goal', 'touchdown', 'home run'],
    'crypto': ['bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'blockchain', 'defi', 'nft', 'token', 'coin', 'binance', 'coinbase', 'solana', 'dogecoin', 'altcoin', 'mining', 'web3', 'metamask', 'wallet', 'exchange', 'trading', 'hodl', 'bull', 'bear', 'market cap', 'altseason', 'layer 2', 'staking', 'yield', 'farm'],
    'pop_culture': ['movie', 'film', 'oscar', 'grammy', 'emmy', 'celebrity', 'music', 'album', 'artist', 'actor', 'actress', 'tv show', 'netflix', 'disney', 'marvel', 'star wars', 'taylor swift', 'beyonce', 'kanye', 'pop', 'rock', 'hip hop', 'rap', 'country', 'jazz', 'concert', 'tour', 'award', 'red carpet', 'premiere', 'streaming', 'youtube', 'tiktok', 'instagram', 'influencer', 'viral', 'trending', 'meme'],
    'business': ['stock', 'market', 'company', 'ceo', 'ipo', 'merger', 'earnings', 'revenue', 'tesla', 'apple', 'google', 'amazon', 'microsoft', 'nvidia', 'ai', 'layoff', 'startup', 'fed', 'interest rate', 'inflation', 'economy', 'gdp', 'recession', 'bull market', 'bear market', 'dividend', 'bond', 'etf', 'mutual fund', 'hedge fund', 'private equity', 'venture capital', 'acquisition', 'spinoff', 'bankruptcy', 'restructuring', 'layoffs', 'hiring', 'job', 'career', 'salary', 'bonus'],
    'science': ['nasa', 'spacex', 'rocket', 'mars', 'moon', 'climate', 'vaccine', 'fda', 'research', 'discovery', 'scientist', 'study', 'experiment', 'technology', 'ai model', 'gpt', 'openai', 'physics', 'chemistry', 'biology', 'medicine', 'health', 'disease', 'treatment', 'drug', 'clinical trial', 'gene', 'dna', 'crispr', 'telescope', 'satellite', 'asteroid', 'comet', 'galaxy', 'universe', 'quantum', 'particle', 'atom', 'energy', 'renewable', 'solar', 'wind', 'fusion', 'fission']
}

# Ключевые слова для CIS сортировки (приоритет для СНГ)
CIS_KEYWORDS = [
    'россия', 'russia', 'путин', 'putin', 'украина', 'ukraine', 'казахстан', 'kazakhstan',
    'минск', 'minsk', 'рубль', 'ruble', 'нефть', 'oil', 'газ', 'gas', 'gazprom',
    'роснефть', 'rosneft', 'лукойл', 'lukoil', 'яндекс', 'yandex', 'сбербанк', 'sberbank',
    'зеленский', 'zelensky', 'кремль', 'kremlin', 'москва', 'moscow', 'киев', 'kyiv',
    'астана', 'astana', 'алматы', 'almaty', 'тон', 'toncoin', 'telegram'
]

# Крипто ключевые слова (второй приоритет)
CRYPTO_PRIORITY_KEYWORDS = [
    'bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'binance', 'solana', 'sol',
    'dogecoin', 'doge', 'xrp', 'cardano', 'ada', 'polkadot', 'dot', 'avalanche', 'avax',
    'bnb', 'ton', 'tron', 'trx', 'matic', 'polygon', 'chainlink', 'link'
]

# Спорт ключевые слова (третий приоритет)
SPORT_PRIORITY_KEYWORDS = [
    'football', 'soccer', 'hockey', 'ufc', 'champion', 'nba', 'nfl', 'mlb',
    'теннис', 'tennis', 'футбол', 'хоккей', 'баскетбол', 'basketball'
]

# США локальные события (пониженный приоритет)
US_LOCAL_KEYWORDS = [
    'governor', 'senate', 'congress', 'sheriff', 'california', 'texas', 'florida',
    'new york', 'illinois', 'ohio', 'pennsylvania', 'georgia', 'michigan', 'arizona',
    'nevada', 'wisconsin', 'minnesota', 'colorado', 'oregon', 'washington state'
]

def calculate_relevance_score(event_title: str, event_description: str = '') -> int:
    """
    Рассчитывает релевантность события для СНГ аудитории
    
    Args:
        event_title: Заголовок события
        event_description: Описание события
    
    Returns:
        Score релевантности (чем выше, тем приоритетнее)
    """
    score = 0
    text = (event_title + ' ' + (event_description or '')).lower()
    
    # CIS события - высший приоритет (+100 за каждое совпадение)
    for keyword in CIS_KEYWORDS:
        if keyword in text:
            score += 100
    
    # Крипто события - высокий приоритет (+50 за каждое совпадение)
    for keyword in CRYPTO_PRIORITY_KEYWORDS:
        if keyword in text:
            score += 50
    
    # Спорт события - средний приоритет (+30 за каждое совпадение)
    for keyword in SPORT_PRIORITY_KEYWORDS:
        if keyword in text:
            score += 30
    
    # США локальные события - пониженный приоритет (-20 за каждое совпадение)
    for keyword in US_LOCAL_KEYWORDS:
        if keyword in text:
            score -= 20
    
    return score

def detect_category(title: str, description: str = '') -> str:
    """Определяет категорию события по заголовку и описанию"""
    text = (title + ' ' + (description or '')).lower()

    category_scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in text)
        if score > 0:
            category_scores[category] = score

    if category_scores:
        return max(category_scores, key=category_scores.get)
    return 'other'

def fetch_polymarket_price_history(
    condition_id: str,
    outcome: str,
    resolution: str = '1h',
    limit: int = None
):
    """
    Получает исторические данные о ценах из Polymarket candles API

    Args:
        condition_id: ID условия (рынка) из Polymarket
        outcome: Название исхода (например, "Yes", "No")
        resolution: Разрешение ('1m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d', '3d', '1w', '1M')
        limit: Количество точек данных (если None, используется лимит по умолчанию для resolution)

    Returns:
        Список кортежей (timestamp, price, volume, open, high, low)
    """
    try:
        # Проверяем валидность resolution
        if resolution not in POLYMARKET_CANDLES_RESOLUTIONS:
            valid_resolutions = list(POLYMARKET_CANDLES_RESOLUTIONS.keys())
            print(f"Invalid resolution: {resolution}. Valid options: {valid_resolutions}")
            return []
        
        # Используем лимит по умолчанию для resolution если не указан
        if limit is None:
            limit = POLYMARKET_CANDLES_LIMITS.get(resolution, 168)
        else:
            # Ограничиваем максимальный лимит для resolution
            max_limit = POLYMARKET_CANDLES_LIMITS.get(resolution, 200)
            limit = min(limit, max_limit)

        # Polymarket candles API endpoint
        url = f"{POLYMARKET_CANDLES_URL}"

        params = {
            "market": condition_id,
            "outcome": outcome,
            "resolution": resolution,
            "limit": limit
        }

        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept-Language": "en-US,en;q=0.9",
        }

        if POLYMARKET_VERBOSE_LOGS:
            print(f"   Fetching price history: {condition_id} / {outcome} / {resolution} / limit={limit}")

        response = requests.get(url, params=params, headers=headers, timeout=15)

        if response.status_code != 200:
            if POLYMARKET_VERBOSE_LOGS:
                print(f"   Price history API error: {response.status_code}")
            return []

        data = response.json()

        # Polymarket возвращает массив свечей: [timestamp, open, high, low, close, volume]
        if not isinstance(data, list) or len(data) == 0:
            if POLYMARKET_VERBOSE_LOGS:
                print(f"   No price history data for {condition_id} / {outcome}")
            return []

        history = []
        for candle in data:
            if len(candle) >= 6:
                timestamp = datetime.utcfromtimestamp(candle[0] / 1000)  # ms → seconds
                open_price = candle[1] / 100  # Polymarket использует 0-100, нам нужно 0-1
                high_price = candle[2] / 100
                low_price = candle[3] / 100
                close_price = candle[4] / 100
                volume = candle[5]
                # Возвращаем полные данные свечи
                history.append((timestamp, close_price, volume, open_price, high_price, low_price))

        if POLYMARKET_VERBOSE_LOGS:
            print(f"   Fetched {len(history)} price history points for {condition_id} / {outcome} / {resolution}")

        return history

    except requests.exceptions.Timeout:
        if POLYMARKET_VERBOSE_LOGS:
            print(f"   Timeout fetching price history for {condition_id} / {outcome}")
        return []
    except requests.exceptions.RequestException as e:
        if POLYMARKET_VERBOSE_LOGS:
            print(f"   Request error fetching price history: {e}")
        return []
    except Exception as e:
        if POLYMARKET_VERBOSE_LOGS:
            print(f"   Error fetching price history: {e}")
        return []

def fetch_polymarket_events(limit: int = 100, category: str = None):
    """
    Получает активные события из Polymarket API
    
    Args:
        limit: Количество событий для загрузки (по умолчанию 100 для запаса)
        category: Фильтр по категории (None = все категории)
    
    Returns:
        Список словарей с данными событий
    """
    try:
        print(f"=== fetch_polymarket_events START ===")
        print(f"Limit: {limit}, Category: {category or 'all'}")

        # Используем /markets endpoint — он содержит все нужные поля
        primary_url = "https://gamma-api.polymarket.com/markets"
        secondary_url = "https://gamma-api.polymarket.com/events"

        # Заголовки
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

        # Параметры — загружаем больше событий для запаса
        params = {
            "order": "volume",
            "ascending": "false",
            "closed": "false",
            "active": "true",
            "limit": limit,
        }

        def _do_get(url: str):
            if POLYMARKET_VERBOSE_LOGS:
                print(f"Fetching from Polymarket: {url}")
                print(f"Params: {params}")
            resp = requests.get(url, params=params, headers=headers, timeout=30)
            print(f"Response: status={resp.status_code}, content-length={len(resp.content)}")
            return resp

        response = _do_get(primary_url)

        if POLYMARKET_VERBOSE_LOGS:
            print(f"Response status: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type', 'unknown')}")

        if response.status_code != 200:
            print(f"HTTP error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            # fallback to /events
            response = _do_get(secondary_url)

        if response.status_code != 200:
            print(f"HTTP error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return []

        # Проверяем Content-Type
        content_type = response.headers.get('content-type', '').lower()
        if 'application/json' not in content_type:
            print(f"Wrong content-type: {content_type}")
            print(f"Response preview: {response.text[:200]}")
            return []

        if POLYMARKET_VERBOSE_LOGS:
            print(f"Response preview (first 1000 chars): {response.text[:1000]}")

        try:
            events_data = response.json()
        except ValueError as e:
            print(f"JSON parsing error: {e}")
            print(f"Response preview: {response.text[:200]}")
            return []

        # API может вернуть список, либо объект вида {"events": [...]}/{"markets": [...]}
        events_list = None
        if isinstance(events_data, list):
            events_list = events_data
        elif isinstance(events_data, dict):
            if isinstance(events_data.get("events"), list):
                events_list = events_data.get("events")
            elif isinstance(events_data.get("markets"), list):
                events_list = events_data.get("markets")
            elif isinstance(events_data.get("data"), list):
                events_list = events_data.get("data")
            elif isinstance(events_data.get("results"), list):
                events_list = events_data.get("results")

        if events_list is None:
            print(f"Unexpected Polymarket response shape: {type(events_data)}")
            if POLYMARKET_VERBOSE_LOGS:
                print(f"Response preview: {str(events_data)[:1000]}")
            return []

        print(f"Received {len(events_list)} events from Polymarket")

        # Обрабатываем рынки/события
        events = []
        for idx, event in enumerate(events_list):
            if POLYMARKET_VERBOSE_LOGS:
                print(f"Processing event #{idx}: {str(event)[:200]}...")

            # Пробуем разные поля для вопроса
            question = event.get('question') or event.get('title') or event.get('description')
            if not question:
                print("   No question/title/description found - skipping")
                continue

            # Получаем исходы/опции из разных возможных структур
            tokens = event.get("tokens")
            outcomes = event.get("outcomes")
            outcome_prices = event.get("outcomePrices") or event.get("outcome_prices")
            
            # Получаем volume для фильтра
            volume = event.get('volume', 0) or event.get('liquidity', 0) or 0

            options = []
            volumes = []
            probabilities = []  # Сохраняем probabilities из Polymarket

            # Парсим outcomes если это JSON строка
            if isinstance(outcomes, str):
                try:
                    outcomes = json.loads(outcomes)
                except Exception:
                    pass

            # 1) tokens (новый формат Polymarket) — содержит price для probability
            if isinstance(tokens, list) and tokens:
                for token in tokens:
                    outcome = token.get("outcome", "")
                    if not outcome:
                        continue
                    # Price в Polymarket = probability (0.70 = 70%)
                    price = float(token.get("price", 0.5) or 0.5)
                    options.append(outcome)
                    volumes.append(price * 1000)  # Для совместимости
                    probabilities.append(round(price * 100, 1))  # Конвертируем в проценты

            # 2) outcomes + outcomePrices (частый формат /markets)
            elif isinstance(outcomes, list) and outcomes:
                options = [str(o) for o in outcomes]
                if isinstance(outcome_prices, list) and len(outcome_prices) == len(options):
                    for p in outcome_prices:
                        try:
                            price = float(p)
                            volumes.append(price * 1000)
                            probabilities.append(round(price * 100, 1))
                        except Exception:
                            volumes.append(500.0)
                            probabilities.append(50.0)
                else:
                    volumes = [500.0 for _ in options]
                    probabilities = [50.0 for _ in options]

            if not options:
                # Нечего синкать
                print(f"   No options found - skipping")
                continue

            if POLYMARKET_VERBOSE_LOGS:
                print(f"   Found question: {question}")
                print(f"   Found {len(options)} options: {options}")
                print(f"   Probabilities: {probabilities}")

            # Формируем структуру события
            title = question
            description = event.get('description', '')
            detected_category = detect_category(title, description)

            # НЕ фильтруем по категории здесь — фильтр будет в get_events
            # Это позволяет загружать все события в БД

            if POLYMARKET_VERBOSE_LOGS:
                print(f"   Category: {detected_category}")

            # Получаем ID события
            event_id = event.get('conditionId') or event.get('id') or str(idx)

            # Получаем время окончания
            end_time = event.get('endDate', '') or event.get('end_date', '')

            event_data = {
                'polymarket_id': event_id,
                'title': title,
                'description': description,
                'category': detected_category,
                'image_url': event.get('image', ''),
                'end_time': end_time,
                'options': options,
                'volumes': volumes,
                'probabilities': probabilities,  # Сохраняем probabilities
                'volume_24h': volume,  # Сохраняем volume для фильтра
                'tokens': tokens  # Сохраняем tokens для token_id
            }

            events.append(event_data)
            if POLYMARKET_VERBOSE_LOGS:
                print(f"   Created event data: {title[:50]}...")

        print(f"Processed {len(events)} valid events")
        print(f"=== fetch_polymarket_events END ===")
        return events

    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        print(f"=== fetch_polymarket_events ERROR ===")
        return []
    except Exception as e:
        print(f"Error fetching Polymarket events: {e}")
        import traceback
        traceback.print_exc()
        print(f"=== fetch_polymarket_events ERROR ===")
        return []

def parse_polymarket_end_time(end_time: str) -> datetime:
    if not end_time:
        return datetime.utcnow() + timedelta(days=7)
    try:
        # Parse with timezone and convert to naive UTC
        dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        return dt.replace(tzinfo=None)  # Convert to naive UTC
    except Exception as e:
        print(f"Error parsing end time: {e}")
        return datetime.utcnow() + timedelta(days=7)

def update_event_total_pool(db: Session, event: Event) -> None:
    options = db.query(EventOption).filter(EventOption.event_id == event.id).all()
    event.total_pool = sum(
        (opt.total_stake or 0.0) + (opt.market_stake or 0.0)
        for opt in options
    )

def upsert_polymarket_event(db: Session, pm_event: dict) -> bool:
    """
    Сохраняет событие из Polymarket в базу данных

    Args:
        db: Сессия базы данных
        pm_event: Данные события из Polymarket

    Returns:
        True если создано новое событие, False если обновлено существующее
    """
    # print(f"Upserting event: {pm_event.get('title', 'No title')}")

    end_time = parse_polymarket_end_time(pm_event.get('end_time'))
    is_active = end_time > datetime.utcnow()
    options = pm_event.get('options', [])
    volumes = pm_event.get('volumes', [])
    probabilities = pm_event.get('probabilities', [])  # Получаем probabilities
    tokens = pm_event.get('tokens', [])  # Получаем tokens для token_id

    # Если probabilities не переданы, рассчитываем из volumes
    if not probabilities and volumes:
        total_volume = sum(volumes)
        probabilities = [round((v / total_volume) * 100, 1) if total_volume > 0 else 50.0 for v in volumes]

    # print(f"   - Parsed end time: {end_time}")
    # print(f"   - Is active: {is_active}")
    # print(f"   - Options count: {len(options)}")

    polymarket_id = pm_event.get('polymarket_id', '')
    if not polymarket_id:
        print("   No polymarket_id - skipping")
        return False

    existing = db.query(Event).filter(
        Event.polymarket_id == polymarket_id
    ).first()

    if existing:
        # print(f"   Updating existing event (ID: {existing.id})")
        existing.title = pm_event['title'][:500]
        existing.description = pm_event['description'][:1000] if pm_event['description'] else None
        existing.category = pm_event.get('category', existing.category)
        existing.image_url = pm_event.get('image_url', '')
        existing.end_time = end_time
        existing.is_active = end_time > datetime.now()
        existing.options = json.dumps(options)
        existing.has_chart = True  # Polymarket events have charts

        existing_options = {
            opt.option_index: opt
            for opt in db.query(EventOption).filter(EventOption.event_id == existing.id).all()
        }

        for idx, (option_text, volume, probability) in enumerate(zip(options, volumes, probabilities)):
            option = existing_options.get(idx)
            
            # Получаем token_id из tokens если доступно
            token_id = None
            if tokens and idx < len(tokens):
                token_id = tokens[idx].get("token_id") or tokens[idx].get("tokenId")
            
            if option:
                option.option_text = option_text
                option.market_stake = volume
                # Используем probability из Polymarket если доступно
                option.current_price = probability / 100.0  # Конвертируем процент в 0-1
                
                # Сохраняем token_id если есть
                if token_id:
                    option.polymarket_token_id = token_id
                    print(f"   Updated option {idx}: {option_text}, token_id: {token_id}")

                print(f"   Updated option {idx}: {option_text}, probability: {probability}%")
            else:
                new_option = EventOption(
                    event_id=existing.id,
                    option_index=idx,
                    option_text=option_text,
                    total_stake=0.0,
                    market_stake=volume,
                    current_price=probability / 100.0,  # Конвертируем процент в 0-1
                    polymarket_token_id=token_id  # Сохраняем token_id
                )
                db.add(new_option)
                print(f"   Added option {idx}: {option_text}, probability: {probability}%, token_id: {token_id}")

        for idx, option in existing_options.items():
            if idx >= len(options):
                db.delete(option)
                print(f"   Deleted option {idx}")

        update_event_total_pool(db, existing)
        print("   Event updated successfully")
        return False

    print("   Creating new event")
    new_event = Event(
        polymarket_id=polymarket_id,
        title=pm_event['title'][:500],
        description=pm_event['description'][:1000] if pm_event['description'] else None,
        category=pm_event.get('category', 'other'),
        image_url=pm_event.get('image_url', ''),
        options=json.dumps(options),
        end_time=end_time,
        is_active=end_time > datetime.now(),
        is_moderated=True,
        has_chart=True,  # Polymarket events have charts
        total_pool=sum(volumes)
    )
    db.add(new_event)
    db.flush()
    print(f"   Created event with ID: {new_event.id}")

    for idx, (option_text, volume, probability) in enumerate(zip(options, volumes, probabilities)):
        new_option = EventOption(
            event_id=new_event.id,
            option_index=idx,
            option_text=option_text,
            total_stake=0.0,
            market_stake=volume,
            current_price=probability / 100.0  # Конвертируем процент в 0-1
        )
        db.add(new_option)

        print(f"   Added option {idx}: {option_text}, probability: {probability}%")

    print(f"   New event created successfully")
    return True


def sync_polymarket_price_history(db: Session = None, limit: int = PRICE_HISTORY_SYNC_LIMIT):
    """
    Синхронизирует историю цен для последних событий
    
    Args:
        db: Сессия базы данных
        limit: Максимальное количество событий для синхронизации за один раз
    """
    try:
        if db is None:
            db = next(get_db())
        
        logger.info(f"[UP] Starting Polymarket price history sync (limit: {limit} events)...")
        
        # Получаем последние активные события
        events = db.query(Event).filter(
            Event.is_active == True,
            Event.end_time > datetime.now()
        ).order_by(Event.id.desc()).limit(limit).all()
        
        total_history_points = 0
        
        for event in events:
            try:
                options = db.query(EventOption).filter(
                    EventOption.event_id == event.id
                ).all()
                
                for option in options:
                    try:
                        # Получаем историю цен
                        history_data = fetch_polymarket_price_history(
                            event.polymarket_id,
                            option.option_text,
                            'hour',
                            168
                        )
                        
                        if history_data:
                            # Сохраняем исторические данные
                            for hist_timestamp, hist_price, hist_volume in history_data:
                                existing_hist = db.query(PriceHistory).filter(
                                    PriceHistory.event_id == event.id,
                                    PriceHistory.option_index == option.option_index,
                                    PriceHistory.timestamp == hist_timestamp
                                ).first()
                                if not existing_hist:
                                    new_history = PriceHistory(
                                        event_id=event.id,
                                        option_index=option.option_index,
                                        price=hist_price,
                                        volume=hist_volume,
                                        timestamp=hist_timestamp
                                    )
                                    db.add(new_history)
                                    total_history_points += 1
                            
                            logger.info(f"  Added {len(history_data)} history points for {event.title[:30]} / {option.option_text}")
                        
                        # Небольшая задержка между запросами для защиты от rate limit
                        import time
                        time.sleep(0.2)
                        
                    except Exception as e:
                        logger.warning(f"  Error syncing history for option {option.option_index}: {e}")
                        continue
                
            except Exception as e:
                logger.warning(f"  Error syncing history for event {event.id}: {e}")
                continue
        
        db.commit()
        logger.info(f"[OK] Price history sync completed: {total_history_points} new points")
        
    except Exception as e:
        logger.error(f"[ERROR] Price history sync error: {e}")
        if db:
            db.rollback()


def sync_polymarket_events(db: Session = None):
    """Синхронизирует события из Polymarket в БД"""
    try:
        logger.info("[SYNC] Starting Polymarket sync...")
        
        # Получаем сессию БД если не передана
        if db is None:
            db = next(get_db())
        
        polymarket_events = fetch_polymarket_events(limit=300)
        synced_count = 0
        added_count = 0
        updated_count = 0

        for pm_event in polymarket_events:
            created = upsert_polymarket_event(db, pm_event)
            if created:
                added_count += 1
            else:
                updated_count += 1
            synced_count += 1
            # logger.info(f"  {'[ADDED]' if created else '[UPDATED]'}")

        db.commit()
        
        # Обновляем статистику
        sync_stats["total_synced"] = synced_count
        sync_stats["last_sync"] = datetime.now()
        sync_stats["last_error"] = None
        
        logger.info(f"[SYNC] Sync completed: {synced_count} events ({added_count} new, {updated_count} updated)")
        return synced_count
    except Exception as e:
        logger.error(f"[ERROR] Error syncing events: {e}")
        if db:
            try:
                db.rollback()
            except Exception:
                pass
        sync_stats["last_error"] = str(e)
        return 0


def scheduled_sync():
    """Обёртка для планировщика - синхронизация событий"""
    try:
        sync_polymarket_events()
    except Exception as e:
        logger.error(f"Scheduled sync error: {e}")

def scheduled_price_history_sync():
    """Обёртка для планировщика - синхронизация истории цен"""
    try:
        db = next(get_db())
        sync_polymarket_price_history(db, limit=PRICE_HISTORY_SYNC_LIMIT)
    except Exception as e:
        logger.error(f"Scheduled price history sync error: {e}")

def scheduled_polymarket_price_sync():
    """Обёртка для планировщика - синхронизация реальных цен Polymarket"""
    try:
        # Используем try/except для импорта чтобы работало из разных мест
        try:
            from .polymarket_price_service import sync_prices_to_db
        except ImportError:
            from polymarket_price_service import sync_prices_to_db
        
        db = next(get_db())
        sync_prices_to_db(db, limit=100)
        logger.info("[OK] Polymarket price sync completed")
    except Exception as e:
        logger.error(f"Scheduled Polymarket price sync error: {e}")

@app.on_event("startup")
async def startup_event():
    """Инициализация при старте приложения"""
    logger.info("[START] Starting EventPredict API...")

    # Инициализация Telegram валидатора
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if bot_token:
        init_telegram_validator(bot_token)
        logger.info("[OK] Telegram auth validator initialized")
    else:
        logger.warning("[WARN] TELEGRAM_BOT_TOKEN not set, Telegram auth disabled")

    # Запуск Resolver Worker
    try:
        await start_resolver_worker()
        logger.info("[OK] Resolver Worker started")
    except Exception as e:
        logger.error(f"Failed to start Resolver Worker: {e}")

    # Запуск сервиса волатильности для расчета коэффициентов
    try:
        await start_volatility_service()
        logger.info("[OK] Volatility Service started (coefficients based on real market volatility)")
    except Exception as e:
        logger.error(f"Failed to start Volatility Service: {e}")

    # Миграция: добавляем поле polymarket_token_id если его нет
    # Выполняем в фоне чтобы не блокировать старт
    def run_migration():
        try:
            import time
            time.sleep(2)  # Ждем пока БД полностью инициализируется
            
            from sqlalchemy import inspect, text
            db = next(get_db())
            # Проверяем существует ли колонка
            inspector = inspect(db.bind)
            columns = [col['name'] for col in inspector.get_columns('event_options')]
            
            if 'polymarket_token_id' not in columns:
                logger.info("[FIX] Adding polymarket_token_id column to event_options...")
                db.execute(text("ALTER TABLE event_options ADD COLUMN polymarket_token_id VARCHAR(255)"))
                db.commit()
                logger.info("[OK] Migration completed: polymarket_token_id added")
            else:
                logger.info("[OK] Column polymarket_token_id already exists")
        except Exception as e:
            logger.warning(f"[WARN] Migration check skipped: {e}")
    
    # Запускаем миграцию в фоне
    import threading
    migration_thread = threading.Thread(target=run_migration)
    migration_thread.start()

    # Отключаем scheduler в тестовом режиме
    if not os.getenv("DISABLE_SCHEDULER"):
        # Запускаем планировщик
        scheduler.add_job(
            scheduled_sync,
            'interval',
            seconds=POLYMARKET_SYNC_INTERVAL_SECONDS,
            id='polymarket_sync',
            replace_existing=True
        )
        
        # Добавляем задачу для синхронизации истории цен (каждые 6 часов)
        scheduler.add_job(
            scheduled_price_history_sync,
            'interval',
            seconds=21600,  # 6 часов
            id='price_history_sync',
            replace_existing=True
        )

        # Добавляем задачу для синхронизации реальных цен Polymarket (каждые 5 минут)
        scheduler.add_job(
            scheduled_polymarket_price_sync,
            'interval',
            seconds=300,  # 5 минут
            id='polymarket_price_sync',
            replace_existing=True
        )

        scheduler.start()
        logger.info(f"⏰ Scheduler started (events: {POLYMARKET_SYNC_INTERVAL_SECONDS}s, history: 21600s, prices: 300s)")

        # Первая синхронизация событий при старте (в фоне, не блокируем запуск)
        try:
            db = next(get_db())
            # Запускаем синхронизацию в отдельном потоке чтобы не блокировать старт
            import threading
            sync_thread = threading.Thread(target=sync_polymarket_events, args=(db,))
            sync_thread.start()
            logger.info("[STATS] Initial event sync started in background...")
        except Exception as e:
            logger.error(f"Initial sync error: {e}")
    else:
        logger.info("🧪 Test mode: scheduler disabled")


@app.on_event("shutdown")
async def shutdown_event():
    """Остановка при завершении работы"""
    logger.info("🛑 Shutting down EventPredict API...")

    # Остановка Resolver Worker
    try:
        await stop_resolver_worker()
        logger.info("[OK] Resolver Worker stopped")
    except Exception as e:
        logger.error(f"Error stopping Resolver Worker: {e}")

    # Остановка сервиса волатильности
    try:
        await stop_volatility_service()
        logger.info("[OK] Volatility Service stopped")
    except Exception as e:
        logger.error(f"Error stopping Volatility Service: {e}")

    if not os.getenv("DISABLE_SCHEDULER"):
        scheduler.shutdown(wait=False)

# ==================== PYDANTIC MODELS ====================

class PredictionRequest(BaseModel):
    telegram_id: int
    event_id: int
    option_index: int
    points: float

class SellRequest(BaseModel):
    telegram_id: int
    event_id: int
    option_index: int
    shares: float  # Количество акций для продажи (0 для продажи всех)

class CreateEventRequest(BaseModel):
    telegram_id: int
    title: str
    description: str
    category: str
    image_url: str
    end_time: str
    options: list[str]

class AdminStats(BaseModel):
    total_users: int
    total_events: int
    pending_events: int
    total_volume: float
    total_transactions: int

class UserResponse(BaseModel):
    telegram_id: int
    username: Optional[str]
    points: float
    stats: dict


class AddBalanceRequest(BaseModel):
    admin_telegram_id: int
    user_telegram_id: int
    amount: float
    asset: str = "USDT"
    comment: Optional[str] = None


# ==================== API ENDPOINTS ====================
@app.get("/", include_in_schema=False)
async def root():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"status": "ok", "message": "EventPredict API"}

@app.get("/categories")
async def get_categories():
    """Получить список категорий"""
    return {
        "categories": [
            {"id": "all", "name": "All", "icon": "[HOT]", "name_ru": "Все"},
            {"id": "politics", "name": "Politics", "icon": "🏛️", "name_ru": "Политика"},
            {"id": "sports", "name": "Sports", "icon": "⚽", "name_ru": "Спорт"},
            {"id": "crypto", "name": "Crypto", "icon": "₿", "name_ru": "Крипто"},
            {"id": "pop_culture", "name": "Pop Culture", "icon": "🎬", "name_ru": "Поп-культура"},
            {"id": "business", "name": "Business", "icon": "[UP]", "name_ru": "Бизнес"},
            {"id": "science", "name": "Science", "icon": "🔬", "name_ru": "Наука"},
            {"id": "other", "name": "Other", "icon": "[PIN]", "name_ru": "Другое"}
        ]
    }

@app.get("/events")
async def get_events(category: str = None, db: Session = Depends(get_db)):
    """Получить события с фильтрацией по категории и CIS сортировкой"""
    try:
        print(f"Getting events with category filter: {category}")

        global last_polymarket_sync
        now = datetime.utcnow()
        if (now - last_polymarket_sync).total_seconds() >= POLYMARKET_SYNC_INTERVAL_SECONDS:
            print("Triggering automatic sync...")
            sync_polymarket_events(db)
            last_polymarket_sync = datetime.utcnow()

        if category and category != 'all':
            # Получаем события выбранной категории
            events = db.query(Event).filter(
                Event.is_active == True,
                Event.end_time > datetime.utcnow(),
                Event.category == category
            ).all()
            print(f"   Found {len(events)} events for category: {category}")
        else:
            # Получаем все активные события
            events = db.query(Event).filter(
                Event.is_active == True,
                Event.end_time > datetime.utcnow()
            ).all()
            print(f"   Found {len(events)} events in database")

        result = []
        for event in events:
            # Получаем опции
            options = db.query(EventOption).filter(
                EventOption.event_id == event.id
            ).all()

            # Парсим опции из JSON если нет в EventOption
            if not options and event.options:
                try:
                    options_list = json.loads(event.options)
                    print(f"      - Creating {len(options_list)} options from JSON")
                    for idx, opt_text in enumerate(options_list):
                        opt = EventOption(
                            event_id=event.id,
                            option_index=idx,
                            option_text=opt_text,
                            total_stake=0.0,
                            market_stake=0.0
                        )
                        db.add(opt)
                    db.commit()
                    options = db.query(EventOption).filter(
                        EventOption.event_id == event.id
                    ).all()
                    print(f"      - Created {len(options)} options successfully")
                except Exception as e:
                    print(f"      - Error creating options from JSON: {e}")
                    pass

            # Вычисляем оставшееся время
            time_left = int((event.end_time - datetime.utcnow()).total_seconds())
            total_stakes = sum(
                (opt.total_stake or 0.0) + (opt.market_stake or 0.0)
                for opt in options
            ) or 1

            # Рассчитываем релевантность для СНГ
            relevance_score = calculate_relevance_score(event.title, event.description or '')

            event_data = {
                "id": event.id,
                "polymarket_id": event.polymarket_id,
                "title": event.title,
                "description": event.description,
                "category": event.category or "other",
                "image_url": event.image_url,
                "end_time": event.end_time.isoformat(),
                "time_left": max(0, time_left),
                "total_pool": event.total_pool,
                "has_chart": event.has_chart or False,
                "relevance_score": relevance_score,  # Для сортировки
                "options": [
                    {
                        "index": opt.option_index,
                        "text": opt.option_text,
                        "total_points": (opt.total_stake or 0.0) + (opt.market_stake or 0.0),
                        # Используем current_price из БД (probability из Polymarket) если доступно
                        # Иначе рассчитываем из total_stakes
                        "probability": round((opt.current_price or 0) * 100, 1) if opt.current_price and opt.current_price > 0 else round(((opt.total_stake or 0.0) + (opt.market_stake or 0.0)) / total_stakes * 100, 1)
                    }
                    for opt in options
                ]
            }

            result.append(event_data)
        
        # Сортировка: сначала по relevance_score (убывание), затем по total_pool (убывание)
        result.sort(key=lambda x: (x['relevance_score'], x['total_pool']), reverse=True)

        # Лимит 50 событий
        result = result[:50]

        print(f"Returning {len(result)} events to frontend (sorted by CIS relevance)")
        return {"events": result}
    except Exception as e:
        print(f"Error loading events: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/events/search")
async def search_events(
    q: str = Query(..., min_length=2, description="Поисковый запрос"),
    limit: int = Query(default=50, ge=1, le=100, description="Максимум результатов"),
    category: str = Query(default=None, description="Фильтр по категории"),
    db: Session = Depends(get_db)
):
    """
    Поиск событий по названию и описанию
    
    Ищет по локальной базе данных с поддержкой категории
    """
    try:
        print(f"[SEARCH] Поиск: '{q}', категория: {category}, лимит: {limit}")
        
        # Базовый запрос
        query = db.query(Event).filter(
            Event.is_active == True,
            Event.end_time > datetime.utcnow()
        )
        
        # Фильтр по категории если указан
        if category and category != 'all':
            query = query.filter(Event.category == category)
        
        # Поиск по названию и описанию
        search_term = f"%{q}%"
        query = query.filter(
            (Event.title.ilike(search_term)) | 
            (Event.description.ilike(search_term))
        )
        
        # Получаем результаты
        events = query.limit(limit).all()
        print(f"[SEARCH] Найдено событий: {len(events)}")
        
        result = []
        for event in events:
            options = db.query(EventOption).filter(
                EventOption.event_id == event.id
            ).all()
            
            time_left = int((event.end_time - datetime.utcnow()).total_seconds())
            total_stakes = sum(
                (opt.total_stake or 0.0) + (opt.market_stake or 0.0)
                for opt in options
            ) or 1
            
            relevance_score = calculate_relevance_score(event.title, event.description or '')
            
            event_data = {
                "id": event.id,
                "polymarket_id": event.polymarket_id,
                "title": event.title,
                "description": event.description,
                "category": event.category or "other",
                "image_url": event.image_url,
                "end_time": event.end_time.isoformat(),
                "time_left": max(0, time_left),
                "total_pool": event.total_pool,
                "has_chart": event.has_chart or False,
                "relevance_score": relevance_score,
                "options": [
                    {
                        "index": opt.option_index,
                        "text": opt.option_text,
                        "total_points": (opt.total_stake or 0.0) + (opt.market_stake or 0.0),
                        "probability": round((opt.current_price or 0) * 100, 1) if opt.current_price and opt.current_price > 0 else round(((opt.total_stake or 0.0) + (opt.market_stake or 0.0)) / total_stakes * 100, 1)
                    }
                    for opt in options
                ]
            }
            result.append(event_data)
        
        # Сортировка: сначала по релевантности (убывание), затем по пулу (убывание)
        result.sort(key=lambda x: (x['relevance_score'], x['total_pool']), reverse=True)
        
        return {"events": result, "total": len(result)}
        
    except Exception as e:
        print(f"[SEARCH] Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/events/{event_id}")
async def get_event(event_id: int, db: Session = Depends(get_db)):
    """Get single event by ID"""
    try:
        print(f"[API] Loading event {event_id}...")
        
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            print(f"[API] Event {event_id} not found")
            raise HTTPException(status_code=404, detail="Event not found")

        options = db.query(EventOption).filter(EventOption.event_id == event_id).all()
        print(f"[API] Found {len(options)} options for event {event_id}")
        
        time_left = int((event.end_time - datetime.utcnow()).total_seconds())
        total_stakes = sum(
            (opt.total_stake or 0.0) + (opt.market_stake or 0.0)
            for opt in options
        ) or 1

        # Формируем options с probability
        options_data = []
        for opt in options:
            # Используем current_price из БД если доступно, иначе рассчитываем из stakes
            if opt.current_price and opt.current_price > 0:
                probability = round(opt.current_price * 100, 1)
            else:
                opt_total = (opt.total_stake or 0.0) + (opt.market_stake or 0.0)
                probability = round(opt_total / total_stakes * 100, 1)
            
            options_data.append({
                "index": opt.option_index,
                "text": opt.option_text,
                "total_points": (opt.total_stake or 0.0) + (opt.market_stake or 0.0),
                "probability": probability
            })
            # print(f"   - Option {opt.option_index}: probability: {probability}%")

        response_data = {
            "id": event.id,
            "title": event.title,
            "description": event.description,
            "category": event.category or "other",
            "image_url": event.image_url,
            "end_time": event.end_time.isoformat(),
            "time_left": max(0, time_left),
            "total_pool": event.total_pool,
            "has_chart": event.has_chart or False,
            "options": options_data
        }
        
        print(f"[API] Event {event_id} loaded successfully")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] Error loading event {event_id}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/events/{event_id}/price-history")
async def get_price_history(event_id: int, db: Session = Depends(get_db)):
    """Get price history for event chart"""
    try:
        # Get last 48 hours of price history
        history = db.query(PriceHistory).filter(
            PriceHistory.event_id == event_id
        ).order_by(PriceHistory.timestamp.desc()).limit(100).all()

        return [
            {
                "event_id": h.event_id,
                "option_index": h.option_index,
                "price": h.price,
                "volume": h.volume,
                "timestamp": h.timestamp.isoformat()
            }
            for h in history
        ]
    except Exception as e:
        print(f"Error loading price history: {e}")
        return []

@app.get("/events/{event_id}/bet-history")
async def get_bet_history(event_id: int, db: Session = Depends(get_db)):
    """Get bet history for sports/politics events"""
    try:
        # Get last 50 bets
        history = db.query(BetHistory).filter(
            BetHistory.event_id == event_id
        ).order_by(BetHistory.timestamp.desc()).limit(50).all()

        return [
            {
                "id": h.id,
                "telegram_id": h.telegram_id,
                "username": h.username or f"User{h.telegram_id}",
                "option_index": h.option_index,
                "amount": h.amount,
                "shares": h.shares,
                "price": h.price,
                "timestamp": h.timestamp.isoformat()
            }
            for h in history
        ]
    except Exception as e:
        print(f"Error loading bet history: {e}")
        return []

@app.get("/market/price/{symbol}")
async def get_crypto_price(symbol: str):
    """Get real-time crypto price from Binance"""
    try:
        symbol_upper = symbol.upper()
        if not symbol_upper.endswith('USDT'):
            symbol_upper = symbol_upper + 'USDT'
        
        response = requests.get(
            f"{BINANCE_API_URL}/ticker/price",
            params={"symbol": symbol_upper},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            price = float(data.get('price', 0))
            return {
                "symbol": symbol_upper,
                "price": price,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            # Fallback: try alternative endpoint
            response = requests.get(
                f"{BINANCE_API_URL}/ticker/24hr",
                params={"symbol": symbol_upper},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                price = float(data.get('lastPrice', 0))
                return {
                    "symbol": symbol_upper,
                    "price": price,
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        return {"symbol": symbol_upper, "price": 0, "error": "Not found"}
    except Exception as e:
        print(f"Error fetching price: {e}")
        return {"symbol": symbol, "price": 0, "error": str(e)}

@app.get("/market/prices")
async def get_crypto_prices():
    """Get real-time prices for multiple cryptocurrencies"""
    try:
        symbols = list(set(CRYPTO_SYMBOLS.values()))
        prices = {}
        
        for symbol in symbols:
            try:
                response = requests.get(
                    f"{BINANCE_API_URL}/ticker/price",
                    params={"symbol": symbol},
                    timeout=3
                )
                if response.status_code == 200:
                    data = response.json()
                    prices[symbol] = float(data.get('price', 0))
            except:
                pass
        
        return {
            "prices": prices,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        print(f"Error fetching prices: {e}")
        return {"prices": {}, "error": str(e)}


# ==================== COMMENTS API ====================

# Pydantic модели для комментариев
class CommentCreate(BaseModel):
    comment_text: str
    telegram_id: int
    username: Optional[str] = None


class CommentResponse(BaseModel):
    id: int
    event_id: int
    telegram_id: int
    username: Optional[str]
    comment_text: str
    created_at: str
    is_deleted: bool
    is_hidden: bool


# Стоп-слова для модерации (оскорбления)
PROFANITY_LIST = [
    "идиот", "дурак", "дебил", "кретин", "придурок", "тупой", "глупый",
    "сука", "блядь", "нахуй", "пиздец", "хуй", "пизда", "ебать", "мудак",
    "scum", "bitch", "fuck", "shit", "asshole", "damn", "bastard",
    "stupid", "idiot", "retard", "moron"
]

# URL паттерны для блокировки ссылок
import re
URL_PATTERN = re.compile(r'https?://\S+|www\.\S+', re.IGNORECASE)


def check_comment_content(text: str) -> dict:
    """
    Проверка комментария на запрещённый контент
    
    Returns:
        dict: {"valid": bool, "reason": str}
    """
    # Проверка длины
    if len(text) > 1000:
        return {"valid": False, "reason": "Comment too long (max 1000 characters)"}
    
    # Проверка на ссылки
    if URL_PATTERN.search(text):
        return {"valid": False, "reason": "Links are not allowed"}
    
    # Проверка на оскорбления
    text_lower = text.lower()
    for word in PROFANITY_LIST:
        if word.lower() in text_lower:
            return {"valid": False, "reason": "Inappropriate language detected"}
    
    return {"valid": True, "reason": ""}


# Rate limiting для комментариев (простая реализация в памяти)
comment_rate_limit = {}  # telegram_id -> list of timestamps


def check_rate_limit(telegram_id: int, max_per_minute: int = 3) -> bool:
    """Проверка rate limiting для комментариев"""
    import time
    current_time = time.time()
    
    if telegram_id not in comment_rate_limit:
        comment_rate_limit[telegram_id] = []
    
    # Удаляем старые записи (старше 1 минуты)
    comment_rate_limit[telegram_id] = [
        ts for ts in comment_rate_limit[telegram_id]
        if current_time - ts < 60
    ]
    
    # Проверяем лимит
    if len(comment_rate_limit[telegram_id]) >= max_per_minute:
        return False
    
    # Добавляем текущую запись
    comment_rate_limit[telegram_id].append(current_time)
    return True


@app.get("/events/{event_id}/comments")
async def get_event_comments(
    event_id: int,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Получить комментарии к событию"""
    try:
        # Проверяем существование события
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Получаем комментарии (только не скрытые и не удалённые)
        comments = db.query(EventComment).filter(
            EventComment.event_id == event_id,
            EventComment.is_deleted == False,
            EventComment.is_hidden == False
        ).order_by(EventComment.created_at.desc()).limit(limit).all()
        
        return [
            {
                "id": c.id,
                "event_id": c.event_id,
                "telegram_id": c.telegram_id,
                "username": c.username,
                "comment_text": c.comment_text,
                "created_at": c.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "is_deleted": c.is_deleted,
                "is_hidden": c.is_hidden
            }
            for c in comments
        ]
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting comments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/events/{event_id}/comments")
async def create_event_comment(
    event_id: int,
    comment_data: CommentCreate,
    db: Session = Depends(get_db)
):
    """Добавить комментарий к событию"""
    try:
        # Проверяем существование события
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Проверка rate limiting
        if not check_rate_limit(comment_data.telegram_id):
            raise HTTPException(
                status_code=429,
                detail="Too many comments. Please wait a minute."
            )
        
        # Проверка контента
        content_check = check_comment_content(comment_data.comment_text)
        if not content_check["valid"]:
            raise HTTPException(
                status_code=400,
                detail=content_check["reason"]
            )
        
        # Создаём комментарий
        new_comment = EventComment(
            event_id=event_id,
            telegram_id=comment_data.telegram_id,
            username=comment_data.username,
            comment_text=comment_data.comment_text,
            is_hidden=False  # Публикуется автоматически если контент чистый
        )
        
        db.add(new_comment)
        db.commit()
        db.refresh(new_comment)
        
        return {
            "success": True,
            "comment": {
                "id": new_comment.id,
                "event_id": new_comment.event_id,
                "telegram_id": new_comment.telegram_id,
                "username": new_comment.username,
                "comment_text": new_comment.comment_text,
                "created_at": new_comment.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "is_deleted": new_comment.is_deleted,
                "is_hidden": new_comment.is_hidden
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/admin/comments/{comment_id}")
async def delete_comment(
    comment_id: int,
    telegram_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Удалить комментарий (только для администраторов)"""
    try:
        # Проверяем права администратора
        if telegram_id != ADMIN_TELEGRAM_ID:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Находим комментарий
        comment = db.query(EventComment).filter(EventComment.id == comment_id).first()
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")
        
        # Мягкое удаление
        comment.is_deleted = True
        db.commit()
        
        return {"success": True, "message": "Comment deleted"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/proxy/image")
async def proxy_image(url: str, telegram_webapp: Optional[str] = Query(None, alias="telegram_webapp")):
    """
    Проксирует изображение для обхода CORS
    Специальный режим для Telegram WebApp с правильными заголовками
    """
    try:
        if not url:
            raise HTTPException(status_code=400, detail="URL required")

        # Проверяем что URL с Polymarket
        # Разрешаем gamma-api.polymarket.com, polymarket-upload.s3.*.amazonaws.com, polymarket.com, polygon.com
        allowed_domains = [
            'gamma-api.polymarket.com',
            'polymarket.com',
            'polygon.com',
            'polymarket-upload.s3.'
        ]
        if not any(domain in url for domain in allowed_domains):
            raise HTTPException(status_code=400, detail="Only Polymarket images allowed")

        # User-Agent для Telegram WebApp - используем TelegramBot для лучшей совместимости
        if telegram_webapp == "1":
            headers = {
                "User-Agent": "TelegramBot/1.0",
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }
        else:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }

        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="Image not found")

        # Определяем content-type
        content_type = response.headers.get('content-type', 'image/jpeg')
        if not content_type.startswith('image/'):
            content_type = 'image/jpeg'

        from fastapi.responses import Response
        
        # Формируем заголовки для ответа
        response_headers = {
            "Cache-Control": "public, max-age=86400",  # Кэш на 24 часа
            "Access-Control-Allow-Origin": "*",
            "Cross-Origin-Resource-Policy": "cross-origin",
            "Access-Control-Allow-Headers": "Content-Type",
        }
        
        return Response(
            content=response.content,
            media_type=content_type,
            headers=response_headers
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Proxy image error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/{telegram_id}")
async def get_user(telegram_id: int, db: Session = Depends(get_db)):
    """Получить информацию о пользователе с позициями"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()

    if not user:
        # Создаём нового пользователя с начальными очками
        user = User(
            telegram_id=telegram_id,
            balance_usdt=1000.0  # Стартовые очки
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Статистика
    active_predictions = db.query(UserPrediction).filter(
        UserPrediction.user_id == user.id,
        UserPrediction.shares > 0
    ).count()

    # Получаем активные позиции (акции)
    positions = db.query(UserPrediction).filter(
        UserPrediction.user_id == user.id,
        UserPrediction.shares > 0
    ).all()
    
    positions_data = []
    for pred in positions:
        event = db.query(Event).filter(Event.id == pred.event_id).first()
        option = db.query(EventOption).filter(
            EventOption.event_id == pred.event_id,
            EventOption.option_index == pred.option_index
        ).first()
        
        if event and option:
            current_value = pred.shares * option.current_price
            profit_loss = current_value - (pred.shares * pred.average_price)
            profit_loss_percent = (profit_loss / (pred.shares * pred.average_price) * 100) if pred.average_price > 0 else 0
            
            positions_data.append({
                "event_id": event.id,
                "event_title": event.title[:50],
                "option_index": pred.option_index,
                "option_text": option.option_text,
                "shares": pred.shares,
                "average_price": pred.average_price,
                "current_price": option.current_price,
                "current_value": current_value,
                "profit_loss": profit_loss,
                "profit_loss_percent": profit_loss_percent,
                "end_time": event.end_time.isoformat()
            })

    return {
        "telegram_id": user.telegram_id,
        "username": user.username,
        "points": user.balance_usdt,
        "stats": {
            "active_predictions": active_predictions,
            "total_won": 0,
            "total_lost": 0
        },
        "positions": positions_data
    }


# ==================== PROFILE API ====================

class ProfileUpdateRequest(BaseModel):
    custom_username: Optional[str] = None
    avatar_url: Optional[str] = None


class ProfileResponse(BaseModel):
    telegram_id: int
    username: Optional[str]
    custom_username: Optional[str]
    avatar_url: Optional[str]
    balance_usdt: float
    balance_ton: float


@app.get("/user/{telegram_id}/profile")
async def get_user_profile(telegram_id: int, db: Session = Depends(get_db)):
    """Получить профиль пользователя"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()

    if not user:
        # Создаём нового пользователя
        user = User(
            telegram_id=telegram_id,
            balance_usdt=1000.0,
            balance_ton=0.0
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return {
        "telegram_id": user.telegram_id,
        "username": user.username,
        "custom_username": user.custom_username,
        "avatar_url": user.avatar_url,
        "balance_usdt": user.balance_usdt,
        "balance_ton": user.balance_ton
    }


@app.post("/user/profile/update")
async def update_user_profile(
    request: ProfileUpdateRequest,
    telegram_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Обновить профиль пользователя"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Обновляем custom_username если предоставлен
    if request.custom_username is not None:
        if len(request.custom_username) > 50:
            raise HTTPException(
                status_code=400,
                detail="Username too long (max 50 characters)"
            )
        user.custom_username = request.custom_username

    # Обновляем avatar_url если предоставлен
    if request.avatar_url is not None:
        if len(request.avatar_url) > 500:
            raise HTTPException(
                status_code=400,
                detail="Avatar URL too long (max 500 characters)"
            )
        user.avatar_url = request.avatar_url

    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "profile": {
            "telegram_id": user.telegram_id,
            "username": user.username,
            "custom_username": user.custom_username,
            "avatar_url": user.avatar_url
        }
    }


# Папка для загрузки аватаров
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
AVATARS_DIR = os.path.join(UPLOAD_DIR, "avatars")

# Создаём директорию если не существует
os.makedirs(AVATARS_DIR, exist_ok=True)


@app.post("/user/profile/upload-avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    telegram_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Загрузить аватар пользователя"""
    try:
        # Проверяем пользователя
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Валидация типа файла
        allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
            )

        # Читаем файл
        file_content = await file.read()
        file_size = len(file_content)

        # Проверка размера (максимум 5MB)
        max_size = 5 * 1024 * 1024  # 5MB
        if file_size > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large (max {max_size / 1024 / 1024}MB)"
            )

        # Генерируем уникальное имя файла
        import time
        filename = f"{telegram_id}_{int(time.time())}_{file.filename}"
        filepath = os.path.join(AVATARS_DIR, filename)

        # Сохраняем файл
        with open(filepath, "wb") as f:
            f.write(file_content)

        # Формируем URL
        # В production замените на реальный URL вашего сервера
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        avatar_url = f"{base_url}/uploads/avatars/{filename}"

        # Сохраняем URL в базу
        user.avatar_url = avatar_url
        db.commit()

        return {
            "success": True,
            "avatar_url": avatar_url
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error uploading avatar: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/predict")
async def make_prediction(request: PredictionRequest, db: Session = Depends(get_db)):
    """Купить акции (Buy shares) - Polymarket style"""
    try:
        # Получаем пользователя
        user = db.query(User).filter(User.telegram_id == request.telegram_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        # Проверяем баланс
        if user.balance_usdt < request.points:
            raise HTTPException(status_code=400, detail="Недостаточно средств")

        # Проверяем событие
        event = db.query(Event).filter(Event.id == request.event_id).first()
        if not event or not event.is_active:
            raise HTTPException(status_code=404, detail="Событие не найдено")

        if event.end_time <= datetime.utcnow():
            raise HTTPException(status_code=400, detail="Событие завершено")

        # Получаем опцию и её текущую цену
        option = db.query(EventOption).filter(
            EventOption.event_id == event.id,
            EventOption.option_index == request.option_index
        ).first()
        
        if not option:
            raise HTTPException(status_code=404, detail="Опция не найдена")
        
        # Цена за акцию (0.01 - 0.99)
        share_price = max(0.01, min(0.99, option.current_price))
        
        # Вычисляем количество акций
        shares_to_buy = request.points / share_price

        # Проверяем существующую позицию
        existing_prediction = db.query(UserPrediction).filter(
            UserPrediction.user_id == user.id,
            UserPrediction.event_id == event.id,
            UserPrediction.option_index == request.option_index,
            UserPrediction.shares > 0
        ).first()

        if existing_prediction:
            # Усредняем цену при покупке дополнительных акций
            total_shares = existing_prediction.shares + shares_to_buy
            total_cost = (existing_prediction.shares * existing_prediction.average_price) + request.points
            new_average_price = total_cost / total_shares
            
            existing_prediction.shares = total_shares
            existing_prediction.average_price = new_average_price
            existing_prediction.amount += request.points
            prediction = existing_prediction
        else:
            # Создаём новую позицию
            prediction = UserPrediction(
                user_id=user.id,
                event_id=event.id,
                option_index=request.option_index,
                shares=shares_to_buy,
                average_price=share_price,
                amount=request.points,
                asset="USDT"
            )
            db.add(prediction)

        # Списываем средства
        user.balance_usdt -= request.points

        # Обновляем статистику опции
        option.total_stake += request.points
        option.current_price = share_price  # Обновляем текущую цену

        # Обновляем общий пул
        event.total_pool += request.points

        # Записываем в историю ставок
        bet = BetHistory(
            event_id=event.id,
            user_id=user.id,
            telegram_id=user.telegram_id,
            username=user.username or user.display_name,
            option_index=request.option_index,
            amount=request.points,
            shares=shares_to_buy,
            price=share_price
        )
        db.add(bet)

        db.commit()

        return {
            "success": True,
            "message": f"Куплено {shares_to_buy:.2f} акций по цене {share_price:.2f} USDT",
            "new_balance": user.balance_usdt,
            "shares": prediction.shares,
            "average_price": prediction.average_price
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error making prediction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sell")
async def sell_shares(request: SellRequest, db: Session = Depends(get_db)):
    """Продать акции (Sell shares) - Polymarket style"""
    try:
        # Получаем пользователя
        user = db.query(User).filter(User.telegram_id == request.telegram_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        # Проверяем событие
        event = db.query(Event).filter(Event.id == request.event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Событие не найдено")

        # Получаем опцию и её текущую цену
        option = db.query(EventOption).filter(
            EventOption.event_id == event.id,
            EventOption.option_index == request.option_index
        ).first()
        
        if not option:
            raise HTTPException(status_code=404, detail="Опция не найдена")
        
        # Получаем позицию пользователя
        prediction = db.query(UserPrediction).filter(
            UserPrediction.user_id == user.id,
            UserPrediction.event_id == event.id,
            UserPrediction.option_index == request.option_index,
            UserPrediction.shares > 0
        ).first()
        
        if not prediction:
            raise HTTPException(status_code=400, detail="У вас нет акций этой опции")
        
        # Определяем количество акций для продажи
        shares_to_sell = request.shares if request.shares > 0 else prediction.shares
        shares_to_sell = min(shares_to_sell, prediction.shares)  # Не больше чем есть
        
        # Текущая цена за акцию
        current_price = max(0.01, min(0.99, option.current_price))
        
        # Сумма к получению
        payout = shares_to_sell * current_price
        
        # Вычисляем прибыль/убыток
        cost_basis = shares_to_sell * prediction.average_price
        profit_loss = payout - cost_basis
        
        # Обновляем позицию
        prediction.shares -= shares_to_sell
        
        if prediction.shares < 0.01:
            # Закрываем позицию если осталось мало акций
            prediction.shares = 0
            prediction.average_price = 0
        
        # Начисляем средства пользователю
        user.balance_usdt += payout

        # Обновляем статистику опции
        option.total_stake -= shares_to_sell * current_price

        # Обновляем общий пул
        event.total_pool -= shares_to_sell * current_price

        db.commit()

        return {
            "success": True,
            "message": f"Продано {shares_to_sell:.2f} акций по цене {current_price:.2f} USDT",
            "new_balance": user.balance_usdt,
            "payout": payout,
            "profit_loss": profit_loss,
            "remaining_shares": prediction.shares
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error selling shares: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/sync-polymarket")
async def manual_sync(db: Session = Depends(get_db)):
    """Ручная синхронизация событий из Polymarket"""
    try:
        count = sync_polymarket_events(db)
        return {
            "success": True,
            "message": f"Синхронизировано событий: {count}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/force-sync")
async def force_sync_polymarket(
    admin_telegram_id: int = Query(None),
    db: Session = Depends(get_db)
):
    """Принудительная синхронизация с Polymarket"""
    try:
        count = sync_polymarket_events(db)
        global last_polymarket_sync
        last_polymarket_sync = datetime.utcnow()
        return {
            "success": True,
            "synced_events": count,
            "message": f"Successfully synced {count} events from Polymarket"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/debug-sync")
async def debug_sync(db: Session = Depends(get_db)):
    """Debug sync endpoint with detailed output"""
    import io
    import sys
    
    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = buffer = io.StringIO()
    
    try:
        # Call fetch directly
        events = fetch_polymarket_events(limit=5)
        
        # Get captured output
        sys.stdout = old_stdout
        logs = buffer.getvalue()
        
        return {
            "success": True,
            "events_count": len(events),
            "events": events[:2] if events else [],
            "logs": logs[:2000] if logs else "No logs captured"
        }
    except Exception as e:
        sys.stdout = old_stdout
        logs = buffer.getvalue()
        return {
            "success": False,
            "error": str(e),
            "logs": logs[:2000] if logs else "No logs captured"
        }

# ==================== ADMIN ENDPOINTS ====================

@app.get("/admin/check/{telegram_id}")
async def check_admin(telegram_id: int):
    """Check if user is admin"""
    return {"is_admin": telegram_id == ADMIN_TELEGRAM_ID}

@app.get("/admin/stats")
async def get_admin_stats(db: Session = Depends(get_db)):
    """Get admin statistics"""
    total_users = db.query(User).count()
    total_events = db.query(Event).filter(Event.is_moderated == True).count()
    pending_events = db.query(Event).filter(Event.is_moderated == False).count()
    total_volume = db.query(Event).filter(
        Event.is_moderated == True
    ).with_entities(func.sum(Event.total_pool)).scalar() or 0.0
    total_transactions = db.query(Transaction).count()

    return {
        "total_users": total_users,
        "total_events": total_events,
        "pending_events": pending_events,
        "total_volume": round(total_volume, 2),
        "total_transactions": total_transactions
    }

@app.get("/admin/pending-events")
async def get_pending_events(db: Session = Depends(get_db)):
    """Get events pending moderation"""
    events = db.query(Event).filter(Event.is_moderated == False).all()
    return {
        "events": [
            {
                "id": e.id,
                "title": e.title,
                "category": e.category,
                "created_by": e.creator_id,
                "end_time": e.end_time.isoformat()
            }
            for e in events
        ]
    }

@app.post("/admin/event/action")
async def moderate_event(
    event_id: int,
    action: str,  # "approve" or "reject"
    telegram_id: int,
    db: Session = Depends(get_db)
):
    """Approve or reject event"""
    if telegram_id != ADMIN_TELEGRAM_ID:
        raise HTTPException(status_code=403, detail="Not authorized")

    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if action == "approve":
        event.is_moderated = True
        db.commit()
        return {"success": True, "message": "Event approved"}
    elif action == "reject":
        db.delete(event)
        db.commit()
        return {"success": True, "message": "Event rejected"}
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

@app.get("/admin/user/{telegram_id}")
async def get_user_admin(telegram_id: int, db: Session = Depends(get_db)):
    """Get user info for admin"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    transactions = db.query(Transaction).filter(
        Transaction.user_id == user.id
    ).order_by(Transaction.created_at.desc()).limit(20).all()

    return {
        "telegram_id": user.telegram_id,
        "username": user.username,
        "balance_usdt": user.balance_usdt,
        "balance_ton": user.balance_ton,
        "is_blocked": user.is_blocked,
        "created_at": user.created_at.isoformat(),
        "transactions": [
            {
                "id": t.id,
                "type": t.type,
                "amount": t.amount,
                "status": t.status,
                "created_at": t.created_at.isoformat()
            }
            for t in transactions
        ]
    }

@app.post("/admin/user/balance")
async def update_user_balance(
    telegram_id: int,
    amount: float,
    action: str,  # "add" or "set"
    admin_telegram_id: int,
    db: Session = Depends(get_db)
):
    """Update user balance (admin only)"""
    if admin_telegram_id != ADMIN_TELEGRAM_ID:
        raise HTTPException(status_code=403, detail="Not authorized")

    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if action == "add":
        user.balance_usdt += amount
    elif action == "set":
        user.balance_usdt = amount

    db.commit()
    return {"success": True, "new_balance": user.balance_usdt}


@app.get("/admin/users")
async def get_all_users(admin_telegram_id: int, db: Session = Depends(get_db)):
    """Get all users with their balances (admin only)"""
    if admin_telegram_id != ADMIN_TELEGRAM_ID:
        raise HTTPException(status_code=403, detail="Not authorized")

    users = db.query(User).order_by(User.balance_usdt.desc()).all()
    
    return {
        "users": [
            {
                "telegram_id": u.telegram_id,
                "username": u.username,
                "balance_usdt": u.balance_usdt,
                "balance_ton": u.balance_ton,
                "created_at": u.created_at.isoformat() if u.created_at else None
            }
            for u in users
        ]
    }


@app.post("/admin/add-balance")
async def admin_add_balance(request: AddBalanceRequest, db: Session = Depends(get_db)):
    """Add balance to user account (admin only)"""
    if request.admin_telegram_id != ADMIN_TELEGRAM_ID:
        raise HTTPException(status_code=403, detail="Not authorized")

    user = db.query(User).filter(User.telegram_id == request.user_telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Add balance
    old_balance = user.balance_usdt
    user.balance_usdt += request.amount

    # Create transaction record
    transaction = Transaction(
        user_id=user.id,
        transaction_type="deposit",
        amount=request.amount,
        asset=request.asset,
        status="completed",
        description=f"Admin deposit: {request.comment}" if request.comment else "Admin deposit"
    )
    db.add(transaction)

    # Log the action
    print(f"Admin {request.admin_telegram_id} added {request.amount} {request.asset} to user {request.user_telegram_id}")
    print(f"  Old balance: {old_balance}, New balance: {user.balance_usdt}")

    db.commit()
    
    return {
        "success": True,
        "new_balance": user.balance_usdt,
        "added_amount": request.amount
    }


@app.post("/events/create")
async def create_event(request: CreateEventRequest, db: Session = Depends(get_db)):
    """Create a new event (requires moderation)"""
    try:
        # Check if user has enough balance for creation (min $10)
        user = db.query(User).filter(User.telegram_id == request.telegram_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.balance_usdt < 10:
            raise HTTPException(status_code=400, detail="Insufficient balance. Minimum $10 required to create event")

        # Parse end time
        try:
            end_time = datetime.fromisoformat(request.end_time.replace('Z', '+00:00'))
        except:
            end_time = datetime.utcnow() + timedelta(days=7)

        # Create event (not moderated by default)
        new_event = Event(
            polymarket_id=f"user_{request.telegram_id}_{int(datetime.utcnow().timestamp())}",
            title=request.title[:500],
            description=request.description[:1000] if request.description else None,
            category=request.category or 'other',
            image_url=request.image_url or '',
            options=json.dumps(request.options),
            end_time=end_time,
            is_active=True,
            is_moderated=False,  # Requires moderation
            is_resolved=False,
            total_pool=0.0,
            creator_id=user.id
        )
        db.add(new_event)
        db.flush()

        # Create options
        for idx, option_text in enumerate(request.options):
            new_option = EventOption(
                event_id=new_event.id,
                option_index=idx,
                option_text=option_text[:255],
                total_stake=0.0,
                market_stake=0.0
            )
            db.add(new_option)

        db.commit()
        db.refresh(new_event)

        return {
            "success": True,
            "event_id": new_event.id,
            "message": "Event created and sent for moderation"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "sync": {
            "last_sync": sync_stats["last_sync"].isoformat() if sync_stats["last_sync"] else None,
            "total_synced": sync_stats["total_synced"],
            "last_error": sync_stats["last_error"],
            "next_sync_in": POLYMARKET_SYNC_INTERVAL_SECONDS
        }
    }

# Debug endpoint для проверки графиков
@app.get("/debug/chart/{symbol}")
async def debug_chart(symbol: str):
    """
    Debug endpoint для проверки что графики разные для разных символов
    
    Пример:
    - /debug/chart/BTC → возвращает свечи для BTCUSDT
    - /debug/chart/ETH → возвращает свечи для ETHUSDT
    """
    try:
        # Нормализация символа
        symbol = symbol.upper()
        if not symbol.endswith('USDT'):
            symbol = symbol + 'USDT'
        
        # Запрос к Binance API
        binance_url = f"{BINANCE_API_URL}/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": "5m",
            "limit": 100
        }
        
        import requests
        response = requests.get(binance_url, params=params, timeout=10)
        
        if response.status_code != 200:
            return {
                "error": f"Binance API error: {response.status_code}",
                "symbol": symbol,
                "data": []
            }
        
        data = response.json()
        
        # Преобразуем в читаемый формат
        candles = []
        for candle in data:
            candles.append({
                "timestamp": candle[0],
                "open": float(candle[1]),
                "high": float(candle[2]),
                "low": float(candle[3]),
                "close": float(candle[4]),
                "volume": float(candle[5])
            })
        
        # Статистика для проверки
        prices = [c["close"] for c in candles]
        unique_prices = len(set(prices))
        
        return {
            "symbol": symbol,
            "candles_count": len(candles),
            "unique_prices": unique_prices,
            "first_price": prices[0] if prices else 0,
            "last_price": prices[-1] if prices else 0,
            "min_price": min(prices) if prices else 0,
            "max_price": max(prices) if prices else 0,
            "data": candles,
            "check": f"Если видите это для {symbol} — данные РЕАЛЬНЫЕ из Binance [OK]"
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "symbol": symbol,
            "data": []
        }


if os.path.isdir(FRONTEND_DIR):
    app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")

# Mount для загруженных аватаров
if os.path.isdir(UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/{file_path:path}", include_in_schema=False)
async def serve_frontend_assets(file_path: str):
    # Игнорируем API-маршруты и встроенную документацию
    reserved_prefixes = ("api/", "docs", "redoc", "openapi.json")
    if file_path.startswith(reserved_prefixes):
        raise HTTPException(status_code=404, detail="Not found")

    candidate = os.path.join(FRONTEND_DIR, file_path)
    if os.path.isfile(candidate):
        return FileResponse(candidate)

    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Frontend not found")

class handler(BaseHTTPRequestHandler):
    def _run_app(self):
        body_length = int(self.headers.get("content-length", 0) or 0)
        body = self.rfile.read(body_length) if body_length > 0 else b""

        url = urlsplit(self.path)
        headers = [
            (key.lower().encode("latin-1"), value.encode("latin-1"))
            for key, value in self.headers.items()
        ]

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": self.request_version.replace("HTTP/", ""),
            "method": self.command,
            "scheme": "https",
            "path": url.path,
            "raw_path": url.path.encode("utf-8"),
            "query_string": url.query.encode("utf-8"),
            "headers": headers,
            "client": self.client_address,
            "server": (self.server.server_address[0], self.server.server_address[1]),
        }

        response = {"status": 500, "headers": [], "body": b""}

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            if message["type"] == "http.response.start":
                response["status"] = message["status"]
                response["headers"] = message.get("headers", [])
            elif message["type"] == "http.response.body":
                response["body"] += message.get("body", b"")

        async def app_runner():
            await app(scope, receive, send)

        asyncio.run(app_runner())

        self.send_response(response["status"])
        for key, value in response["headers"]:
            self.send_header(key.decode("latin-1"), value.decode("latin-1"))
        self.end_headers()
        self.wfile.write(response["body"])

    def do_GET(self):
        self._run_app()

    def do_POST(self):
        self._run_app()

    def do_PUT(self):
        self._run_app()

    def do_PATCH(self):
        self._run_app()

    def do_DELETE(self):
        self._run_app()

    def do_OPTIONS(self):
        self._run_app()
