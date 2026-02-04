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
                "volume": float
