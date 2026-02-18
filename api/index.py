from fastapi import FastAPI, HTTPException, Depends, Query
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
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Импорт моделей
try:
    from .models import (
        get_db, User, Event, EventOption, UserPrediction,
        Transaction, TransactionType, TransactionStatus, PriceHistory
    )
except ImportError:
    from models import (
        get_db, User, Event, EventOption, UserPrediction,
        Transaction, TransactionType, TransactionStatus, PriceHistory
    )

app = FastAPI(title="EventPredict API")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

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

def fetch_polymarket_price_history(condition_id: str, outcome: str, resolution: str = 'hour', limit: int = 168):
    """
    Получает исторические данные о ценах из Polymarket candles API

    Args:
        condition_id: ID условия (рынка) из Polymarket
        outcome: Название исхода (например, "Yes", "No")
        resolution: Разрешение ('minute', 'hour', 'day', 'week')
        limit: Количество точек данных (максимум 168 для часов)

    Returns:
        Список кортежей (timestamp, price, volume)
    """
    try:
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

        response = requests.get(url, params=params, headers=headers, timeout=10)

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
                close_price = candle[4] / 100  # Polymarket использует 0-100, нам нужно 0-1
                volume = candle[5]
                history.append((timestamp, close_price, volume))

        if POLYMARKET_VERBOSE_LOGS:
            print(f"   Fetched {len(history)} price history points for {condition_id} / {outcome}")

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

def fetch_polymarket_events(limit: int = 50, category: str = None):
    """Получает активные события из Polymarket API"""
    try:
        print(f"=== fetch_polymarket_events START ===")
        print(f"Limit: {limit}, Category: {category}")
        
        # На практике /markets чаще содержит все нужные поля (включая исходы)
        primary_url = "https://gamma-api.polymarket.com/markets"
        secondary_url = "https://gamma-api.polymarket.com/events"

        # Заголовки (важно: НЕ запрашиваем brotli 'br', т.к. requests без доп. пакетов может не декодировать)
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

        # Параметры (для /markets и /events)
        params = {
            "order": "id",
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
                print("   No question/title/description found")
                continue
            
            # Получаем исходы/опции из разных возможных структур
            tokens = event.get("tokens")
            outcomes = event.get("outcomes")
            outcome_prices = event.get("outcomePrices") or event.get("outcome_prices")

            options = []
            volumes = []

            # Парсим outcomes если это JSON строка
            if isinstance(outcomes, str):
                try:
                    outcomes = json.loads(outcomes)
                except Exception:
                    pass

            # 1) tokens (новый формат)
            if isinstance(tokens, list) and tokens:
                for token in tokens:
                    outcome = token.get("outcome", "")
                    if not outcome:
                        continue
                    price = float(token.get("price", 0.5) or 0.5)
                    options.append(outcome)
                    volumes.append(price * 1000)

            # 2) outcomes + outcomePrices (частый формат /markets)
            elif isinstance(outcomes, list) and outcomes:
                options = [str(o) for o in outcomes]
                if isinstance(outcome_prices, list) and len(outcome_prices) == len(options):
                    for p in outcome_prices:
                        try:
                            volumes.append(float(p) * 1000)
                        except Exception:
                            volumes.append(500.0)
                else:
                    volumes = [500.0 for _ in options]

            if not options:
                # Нечего синкать
                continue
            
            if POLYMARKET_VERBOSE_LOGS:
                print(f"   Found question: {question}")
                print(f"   Found {len(tokens)} tokens")
            
            # Формируем структуру события
            title = question
            description = event.get('description', '')
            detected_category = detect_category(title, description)

            if category and category != 'all' and detected_category != category:
                print(f"   Skipping - category {detected_category} != {category}")
                continue

            if POLYMARKET_VERBOSE_LOGS:
                print(f"   Options: {options}")
            
            # Получаем ID события
            event_id = event.get('conditionId') or event.get('id') or str(idx)
            
            event_data = {
                'polymarket_id': event_id,
                'title': title,
                'description': description,
                'category': detected_category,
                'image_url': event.get('image', ''),
                'end_time': event.get('endDate', '') or event.get('end_date', ''),
                'options': options,
                'volumes': volumes
            }
            
            events.append(event_data)
            if POLYMARKET_VERBOSE_LOGS:
                print(f"   Created event data: {title}")
        
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
    print(f"Upserting event: {pm_event.get('title', 'No title')}")
    
    end_time = parse_polymarket_end_time(pm_event.get('end_time'))
    is_active = end_time > datetime.utcnow()
    options = pm_event.get('options', [])
    volumes = pm_event.get('volumes', [])
    
    print(f"   - Parsed end time: {end_time}")
    print(f"   - Is active: {is_active}")
    print(f"   - Options count: {len(options)}")
    print(f"   - Volumes: {volumes}")

    polymarket_id = pm_event.get('polymarket_id', '')
    if not polymarket_id:
        print("   No polymarket_id - skipping")
        return False

    existing = db.query(Event).filter(
        Event.polymarket_id == polymarket_id
    ).first()

    if existing:
        print(f"   Updating existing event (ID: {existing.id})")
        existing.title = pm_event['title'][:500]
        existing.description = pm_event['description'][:1000] if pm_event['description'] else None
        existing.category = pm_event.get('category', existing.category)
        existing.image_url = pm_event.get('image_url', '')
        existing.end_time = end_time
        existing.is_active = is_active
        existing.options = json.dumps(options)

        existing_options = {
            opt.option_index: opt
            for opt in db.query(EventOption).filter(EventOption.event_id == existing.id).all()
        }

        for idx, (option_text, volume) in enumerate(zip(options, volumes)):
            option = existing_options.get(idx)
            if option:
                option.option_text = option_text
                option.market_stake = volume
                # Сохраняем историю цен
                price = volume / (sum(volumes) or 1)
                option.current_price = price

                # Пытаемся получить реальные исторические данные из Polymarket
                # ПРИМЕЧАНИЕ: Загрузка истории цен перенесена в фоновую задачу
                # чтобы не замедлять синхронизацию событий
                condition_id = pm_event.get('polymarket_id', '')
                # История будет загружена отдельно через sync_polymarket_price_history()

                print(f"   Updated option {idx}: {option_text}, price: {price:.2%}")
            else:
                new_option = EventOption(
                    event_id=existing.id,
                    option_index=idx,
                    option_text=option_text,
                    total_stake=0.0,
                    market_stake=volume,
                    current_price=volume / (sum(volumes) or 1)
                )
                db.add(new_option)
                print(f"   Added option {idx}: {option_text}")

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
        is_active=is_active,
        is_moderated=True,
        total_pool=sum(volumes)
    )
    db.add(new_event)
    db.flush()
    print(f"   Created event with ID: {new_event.id}")

    for idx, (option_text, volume) in enumerate(zip(options, volumes)):
        new_option = EventOption(
            event_id=new_event.id,
            option_index=idx,
            option_text=option_text,
            total_stake=0.0,
            market_stake=volume,
            current_price=volume / (sum(volumes) or 1)
        )
        db.add(new_option)

        # ПРИМЕЧАНИЕ: Загрузка истории цен перенесена в фоновую задачу
        # чтобы не замедлять синхронизацию событий
        # История будет загружена отдельно через sync_polymarket_price_history()

        print(f"   Added option {idx}: {option_text}")

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
        
        logger.info(f"📈 Starting Polymarket price history sync (limit: {limit} events)...")
        
        # Получаем последние активные события
        events = db.query(Event).filter(
            Event.is_active == True,
            Event.end_time > datetime.utcnow()
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
        logger.info(f"✅ Price history sync completed: {total_history_points} new points")
        
    except Exception as e:
        logger.error(f"❌ Price history sync error: {e}")
        if db:
            db.rollback()


def sync_polymarket_events(db: Session = None):
    """Синхронизирует события из Polymarket в БД"""
    try:
        logger.info("🔄 Starting Polymarket sync...")
        
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
            logger.info(f"  {'✅ Added' if created else '🔄 Updated'}: {pm_event['title'][:50]}...")

        db.commit()
        
        # Обновляем статистику
        sync_stats["total_synced"] = synced_count
        sync_stats["last_sync"] = datetime.utcnow()
        sync_stats["last_error"] = None
        
        logger.info(f"✅ Sync completed: {synced_count} events ({added_count} new, {updated_count} updated)")
        return synced_count
    except Exception as e:
        logger.error(f"❌ Error syncing events: {e}")
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

@app.on_event("startup")
async def startup_event():
    """Инициализация при старте приложения"""
    logger.info("🚀 Starting EventPredict API...")

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
        
        scheduler.start()
        logger.info(f"⏰ Scheduler started (events: {POLYMARKET_SYNC_INTERVAL_SECONDS}s, history: 21600s)")

        # Первая синхронизация событий при старте (в фоне, не блокируем запуск)
        try:
            db = next(get_db())
            # Запускаем синхронизацию в отдельном потоке чтобы не блокировать старт
            import threading
            sync_thread = threading.Thread(target=sync_polymarket_events, args=(db,))
            sync_thread.start()
            logger.info("📊 Initial event sync started in background...")
        except Exception as e:
            logger.error(f"Initial sync error: {e}")
    else:
        logger.info("🧪 Test mode: scheduler disabled")


@app.on_event("shutdown")
async def shutdown_event():
    """Остановка при завершении работы"""
    logger.info("🛑 Shutting down EventPredict API...")
    if not os.getenv("DISABLE_SCHEDULER"):
        scheduler.shutdown(wait=False)

# ==================== PYDANTIC MODELS ====================

class PredictionRequest(BaseModel):
    telegram_id: int
    event_id: int
    option_index: int
    points: float

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
            {"id": "all", "name": "All", "icon": "🔥", "name_ru": "Все"},
            {"id": "politics", "name": "Politics", "icon": "🏛️", "name_ru": "Политика"},
            {"id": "sports", "name": "Sports", "icon": "⚽", "name_ru": "Спорт"},
            {"id": "crypto", "name": "Crypto", "icon": "₿", "name_ru": "Крипто"},
            {"id": "pop_culture", "name": "Pop Culture", "icon": "🎬", "name_ru": "Поп-культура"},
            {"id": "business", "name": "Business", "icon": "📈", "name_ru": "Бизнес"},
            {"id": "science", "name": "Science", "icon": "🔬", "name_ru": "Наука"},
            {"id": "other", "name": "Other", "icon": "📌", "name_ru": "Другое"}
        ]
    }

@app.get("/events")
async def get_events(category: str = None, db: Session = Depends(get_db)):
    """Получить события с фильтрацией по категории"""
    try:
        print(f"Getting events with category filter: {category}")
        
        global last_polymarket_sync
        now = datetime.utcnow()
        if (now - last_polymarket_sync).total_seconds() >= POLYMARKET_SYNC_INTERVAL_SECONDS:
            print("Triggering automatic sync...")
            sync_polymarket_events(db)
            last_polymarket_sync = datetime.utcnow()
        
        query = db.query(Event).filter(
            Event.is_active == True,
            Event.end_time > datetime.utcnow()
        )

        if category and category != 'all':
            # Получаем события выбранной категории
            query = db.query(Event).filter(
                Event.is_active == True,
                Event.end_time > datetime.utcnow(),
                Event.category == category
            )
            events = query.order_by(Event.total_pool.desc()).limit(50).all()
            print(f"   Found {len(events)} events for category: {category}")
        else:
            query = db.query(Event).filter(
                Event.is_active == True,
                Event.end_time > datetime.utcnow()
            )
            events = query.order_by(Event.total_pool.desc()).limit(50).all()
            print(f"   Found {len(events)} events in database")
        
        result = []
        for event in events:
            print(f"   Processing event: {event.title} (ID: {event.id})")
            
            # Получаем опции
            options = db.query(EventOption).filter(
                EventOption.event_id == event.id
            ).all()
            
            print(f"      - Found {len(options)} options in database")
            
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
                "options": [
                    {
                        "index": opt.option_index,
                        "text": opt.option_text,
                        "total_points": (opt.total_stake or 0.0) + (opt.market_stake or 0.0),
                        "probability": round(((opt.total_stake or 0.0) + (opt.market_stake or 0.0)) / total_stakes * 100, 1)
                    }
                    for opt in options
                ]
            }
            
            result.append(event_data)
            print(f"      Added event to result: {len(event_data['options'])} options")
        
        print(f"Returning {len(result)} events to frontend")
        return {"events": result}
    except Exception as e:
        print(f"Error loading events: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/events/{event_id}")
async def get_event(event_id: int, db: Session = Depends(get_db)):
    """Get single event by ID"""
    try:
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        options = db.query(EventOption).filter(EventOption.event_id == event_id).all()
        time_left = int((event.end_time - datetime.utcnow()).total_seconds())
        total_stakes = sum(
            (opt.total_stake or 0.0) + (opt.market_stake or 0.0)
            for opt in options
        ) or 1

        return {
            "id": event.id,
            "title": event.title,
            "description": event.description,
            "category": event.category or "other",
            "image_url": event.image_url,
            "end_time": event.end_time.isoformat(),
            "time_left": max(0, time_left),
            "total_pool": event.total_pool,
            "options": [
                {
                    "index": opt.option_index,
                    "text": opt.option_text,
                    "total_points": (opt.total_stake or 0.0) + (opt.market_stake or 0.0),
                    "probability": round(((opt.total_stake or 0.0) + (opt.market_stake or 0.0)) / total_stakes * 100, 1)
                }
                for opt in options
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error loading event: {e}")
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

@app.get("/proxy/image")
async def proxy_image(url: str):
    """Проксирует изображение для обхода CORS"""
    try:
        if not url:
            raise HTTPException(status_code=400, detail="URL required")
        
        # Проверяем что URL с Polymarket
        if not url.startswith('https://gamma-api.polymarket.com'):
            # Разрешаем только Polymarket images
            if not any(domain in url for domain in ['polymarket.com', 'polygon.com']):
                raise HTTPException(status_code=400, detail="Only Polymarket images allowed")
        
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
        return Response(
            content=response.content,
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=86400",  # Кэш на 24 часа
                "Access-Control-Allow-Origin": "*"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Proxy image error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/{telegram_id}")
async def get_user(telegram_id: int, db: Session = Depends(get_db)):
    """Получить информацию о пользователе"""
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
        UserPrediction.is_winner == None
    ).count()
    
    return {
        "telegram_id": user.telegram_id,
        "username": user.username,
        "points": user.balance_usdt,
        "stats": {
            "active_predictions": active_predictions,
            "total_won": 0,
            "total_lost": 0
        }
    }

@app.post("/predict")
async def make_prediction(request: PredictionRequest, db: Session = Depends(get_db)):
    """Сделать прогноз"""
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
        
        # Списываем средства
        user.balance_usdt -= request.points
        
        # Создаём прогноз
        prediction = UserPrediction(
            user_id=user.id,
            event_id=event.id,
            option_index=request.option_index,
            amount=request.points,
            asset="USDT"
        )
        db.add(prediction)
        
        # Обновляем статистику опции
        option = db.query(EventOption).filter(
            EventOption.event_id == event.id,
            EventOption.option_index == request.option_index
        ).first()
        
        if option:
            option.total_stake += request.points
        
        # Обновляем общий пул
        event.total_pool += request.points
        
        db.commit()
        
        return {
            "success": True,
            "message": "Прогноз принят",
            "new_balance": user.balance_usdt
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error making prediction: {e}")
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


if os.path.isdir(FRONTEND_DIR):
    app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")


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
