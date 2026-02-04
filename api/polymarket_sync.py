"""
Polymarket synchronization module - Crypto events only
"""
import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict

GAMMA_API_URL = "https://gamma-api.polymarket.com"

# Ключевые слова для crypto событий
CRYPTO_KEYWORDS = ['bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'cryptocurrency', 
                   'blockchain', 'token', 'defi', 'nft', 'solana', 'sol', 'cardano', 'ada']

def is_crypto_event(event: Dict) -> bool:
    """Проверяем, относится ли событие к криптовалютам"""
    text = f"{event.get('title', '')} {event.get('description', '')}".lower()
    return any(keyword in text for keyword in CRYPTO_KEYWORDS)

def get_polymarket_events(limit: int = 50) -> List[Dict]:
    """Получить события с Polymarket"""
    query = """
    query GetActiveEvents {
        events(where: {isResolved: false, isActive: true}, first: %d, orderBy: volume, orderDirection: desc) {
            id
            slug
            title
            description
            endDate
            liquidity
            volume
            markets {
                id
                slug
                question
                outcomes
                outcomePrices
                volume
            }
        }
    }
    """ % limit
    
    try:
        response = requests.post(
            f"{GAMMA_API_URL}/graphql",
            json={"query": query},
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        
        events = []
        for event in data.get("data", {}).get("events", []):
            # Фильтруем только crypto события
            if not is_crypto_event(event):
                continue
            
            markets = event.get("markets", [])
            if not markets:
                continue
            
            market = markets[0]
            outcomes = market.get("outcomes", [])
            if isinstance(outcomes, str):
                outcomes = json.loads(outcomes)
            
            events.append({
                "polymarket_id": event["id"],
                "slug": event["slug"],
                "title": event["title"],
                "description": event.get("description", market.get("question", "")),
                "end_date": event.get("endDate"),
                "liquidity": float(event.get("liquidity", 0)),
                "volume": float(event.get("volume", 0)),
                "question": market.get("question"),
                "outcomes": outcomes,
                "outcome_prices": market.get("outcomePrices", "[]"),
                "market_id": market["id"]
            })
        
        return events
    except Exception as e:
        print(f"Error fetching Polymarket events: {e}")
        return []

def sync_polymarket_events(db_session):
    """Синхронизировать crypto события Polymarket с локальной БД"""
    from models import Event, EventOption
    
    try:
        events = get_polymarket_events(limit=30)
        print(f"Found {len(events)} crypto events")
        
        created_count = 0
        for pm_event in events:
            # Проверяем, есть ли уже
            existing = db_session.query(Event).filter(
                Event.polymarket_id == pm_event["polymarket_id"]
            ).first()
            
            if existing:
                # Обновляем объёмы
                existing.total_pool = pm_event["volume"]
                continue
            
            # Парсим дату
            try:
                end_time = datetime.fromisoformat(pm_event["end_date"].replace("Z", "+00:00"))
            except:
                end_time = datetime.utcnow() + timedelta(days=7)
            
            # Не добавляем просроченные
            if end_time < datetime.utcnow():
                continue
            
            # Создаём событие
            event = Event(
                polymarket_id=pm_event["polymarket_id"],
                title=pm_event["title"],
                description=pm_event.get("description", "")[:500],
                end_time=end_time,
                is_moderated=True,
                is_active=True,
                total_pool=pm_event["volume"]
            )
            db_session.add(event)
            db_session.flush()
            
            # Добавляем исходы
            outcomes = pm_event.get("outcomes", ["Yes", "No"])
            for idx, outcome in enumerate(outcomes):
                option = EventOption(
                    event_id=event.id,
                    option_index=idx,
                    option_text=str(outcome)[:100],
                    total_stake=0.0
                )
                db_session.add(option)
            
            created_count += 1
        
        db_session.commit()
        print(f"Created {created_count} new crypto events")
        return {"synced": len(events), "created": created_count}
        
    except Exception as e:
        db_session.rollback()
        print(f"Sync error: {e}")
        raise e

if __name__ == "__main__":
    events = get_polymarket_events()
    print(f"Found {len(events)} crypto events")
    for e in events[:3]:
        print(f"- {e['title'][:60]}...")
