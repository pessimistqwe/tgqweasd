# Polymarket API Reference

Полный справочник по API Polymarket CLOB (Central Limit Order Book).

**Документация:** https://docs.polymarket.com/  
**CLOB API:** https://clob.polymarket.com  
**Gamma API:** https://gamma-api.polymarket.com

---

## 📦 Официальные SDK

### CLOB Clients (основные)

| Язык | Пакет | Установка | Репозиторий |
|------|-------|-----------|-------------|
| **TypeScript** | `@polymarket/clob-client` | `npm install @polymarket/clob-client ethers@5` | [GitHub](https://github.com/Polymarket/clob-client) |
| **Python** | `py-clob-client` | `pip install py-clob-client` | [GitHub](https://github.com/Polymarket/py-clob-client) |
| **Rust** | `polymarket-client-sdk` | `cargo add polymarket-client-sdk` | [GitHub](https://github.com/Polymarket/rs-clob-client) |

### Builder SDK (для Builder Program)

| Язык | Пакет | Репозиторий |
|------|-------|-------------|
| **TypeScript** | `@polymarket/builder-signing-sdk` | [GitHub](https://github.com/Polymarket/builder-signing-sdk) |
| **Python** | `py-builder-signing-sdk` | [GitHub](https://github.com/Polymarket/py-builder-signing-sdk) |

### Relayer SDK (безгазовые транзакции)

| Язык | Пакет | Репозиторий |
|------|-------|-------------|
| **TypeScript** | `@polymarket/builder-relayer-client` | [GitHub](https://github.com/Polymarket/builder-relayer-client) |
| **Python** | `py-builder-relayer-client` | [GitHub](https://github.com/Polymarket/py-builder-relayer-client) |

---

## 🔐 Аутентификация

### Типы подписи

| Тип | Значение | Описание |
|-----|----------|----------|
| **EOA** | `0` | Прямой трейдинг с кошелька (MetaMask, Ledger) |
| **Magic Link / Email** | `1` | Аккаунты через Magic Link или Email |
| **Web3 Wallet** | `2` | Браузерные кошельки через Polymarket Proxy |

### Получение API ключей

1. **Поделиться ключом:** https://reveal.polymarket.com
2. **Импортировать из кошелька:** Экспортировать приватный ключ
3. **Создать API credentials:** Через SDK метод `create_or_derive_api_creds()`

### Инициализация клиента

#### Python
```python
from py_clob_client.client import ClobClient

host = "https://clob.polymarket.com"
key = "your_private_key"
chain_id = 137  # Polygon mainnet

# Для Email/Magic аккаунтов
client = ClobClient(
    host, 
    key=key, 
    chain_id=chain_id, 
    signature_type=1, 
    funder="POLYMARKET_PROXY_ADDRESS"
)

# Для EOA кошельков
client = ClobClient(
    host, 
    key=key, 
    chain_id=chain_id
)

# Установка API credentials
client.set_api_creds(client.create_or_derive_api_creds())
```

#### TypeScript
```typescript
import { ClobClient } from "@polymarket/clob-client";
import { Wallet } from "ethers";

const host = "https://clob.polymarket.com";
const chainId = 137;
const signer = new Wallet("your_private_key");

const client = new ClobClient(host, chainId, signer, apiCreds);
```

---

## 🔑 Настройка разрешений (Allowances)

**Требуется только для EOA/Web3 кошельков!** Для Email/Magic allowances настраиваются автоматически.

### Токены и Spender адреса (Polygon Mainnet)

| Токен | Адрес токена | Spender адрес | Описание |
|-------|--------------|---------------|----------|
| **USDC** | `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174` | `0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E` | CTF Exchange |
| **USDC** | `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174` | `0xC5d563A36AE78145C45a50134d48A1215220f80a` | Neg Risk CTF Exchange |
| **USDC** | `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174` | `0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296` | Neg Risk Adapter |
| **Conditional Tokens** | `0x4D97DCd97eC945f40cF65F87097ACe5EA0476045` | `0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E` | CTF Exchange |
| **Conditional Tokens** | `0x4D97DCd97eC945f40cF65F87097ACe5EA0476045` | `0xC5d563A36AE78145C45a50134d48A1215220f80a` | Neg Risk CTF Exchange |
| **Conditional Tokens** | `0x4D97DCd97eC945f40cF65F87097ACe5EA0476045` | `0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296` | Neg Risk Adapter |

---

## 📡 API Endpoints

### Base URLs

| API | URL | Назначение |
|-----|-----|------------|
| **CLOB API** | `https://clob.polymarket.com` | Торговля, ордера, позиции |
| **Gamma API** | `https://gamma-api.polymarket.com` | Данные рынков, события |
| **Candles API** | `https://gamma-api.polymarket.com/candles` | Исторические данные цен |

---

### 📊 Events (События)

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/events` | Список всех событий |
| `GET` | `/events/{id}` | Получить событие по ID |
| `GET` | `/events/slug/{slug}` | Получить событие по slug |
| `GET` | `/events/tags` | Теги событий |

**Пример запроса:**
```bash
curl "https://gamma-api.polymarket.com/events?order=volume&ascending=false&closed=false"
```

---

### 🏛 Markets (Рынки)

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/markets` | Список всех рынков |
| `GET` | `/markets/{id}` | Получить рынок по ID |
| `GET` | `/markets/slug/{slug}` | Получить рынок по slug |
| `GET` | `/markets/tags/{id}` | Теги рынка |
| `GET` | `/markets/top-holders` | Топ держатели для рынка |
| `GET` | `/markets/open-interest` | Открытый интерес |
| `GET` | `/markets/volume/{eventId}` | Объём торгов для события |

**Пример запроса:**
```bash
curl "https://gamma-api.polymarket.com/markets?order=volume&ascending=false&active=true"
```

**Пример ответа:**
```json
{
  "markets": [
    {
      "id": "market_id_123",
      "question": "Will Bitcoin reach $100,000?",
      "outcomes": ["Yes", "No"],
      "outcomePrices": ["0.65", "0.35"],
      "volume": 1250000,
      "endDate": "2025-12-31T23:59:59Z"
    }
  ]
}
```

---

### 📈 Orderbook & Pricing (Стакан и цены)

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/book?token_id={id}` | Получить стакан заявок |
| `POST` | `/order-books` | Получить несколько стаканов |
| `GET` | `/price?token_id={id}` | Получить цену рынка |
| `GET` | `/prices` | Получить цены (query params) |
| `POST` | `/prices` | Получить цены (body) |
| `GET` | `/midpoint?token_id={id}` | Средняя цена |
| `GET` | `/midpoints` | Несколько средних цен |
| `GET` | `/spread?token_id={id}` | Спред |
| `POST` | `/spreads` | Несколько спредов |
| `GET` | `/last-trade-price?token_id={id}` | Последняя цена сделки |
| `GET` | `/last-trades-prices` | Последние цены сделок |
| `GET` | `/prices/history?token_id={id}` | История цен |
| `GET` | `/fee-rate` | Текущая комиссия |
| `GET` | `/tick-size?token_id={id}` | Размер шага цены |
| `GET` | `/time` | Время сервера |

**Пример запроса истории цен:**
```bash
curl "https://gamma-api.polymarket.com/candles?market=market_id_123&outcome=Yes&resolution=hour&limit=168"
```

**Пример ответа:**
```json
[
  [1707436800000, 65, 70, 63, 68, 12500],
  [1707440400000, 68, 72, 67, 71, 15000]
]
```
Формат: `[timestamp, open, high, low, close, volume]` (цена в центах 0-100)

---

### 📝 Orders (Ордера)

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `POST` | `/order` | Разместить новый ордер |
| `DELETE` | `/order/{id}` | Отменить ордер |
| `GET` | `/order/{id}` | Получить ордер по ID |
| `POST` | `/orders` | Разместить несколько ордеров |
| `GET` | `/orders` | Получить ордера пользователя |
| `DELETE` | `/orders` | Отменить несколько ордеров |
| `DELETE` | `/orders/all` | Отменить все ордера |
| `DELETE` | `/orders/market/{id}` | Отменить ордера для рынка |
| `POST` | `/order/score` | Проверка скоринга ордера |
| `POST` | `/heartbeat` | Heartbeat сигнал |

**Пример создания ордера (Python):**
```python
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY

# Создание ордера
order_args = OrderArgs(
    price=0.50,      # Цена 50¢
    size=10.0,       # Размер 10 токенов
    side=BUY,        # BUY или SELL
    token_id="12345" # ID токена
)

# Подписание
signed_order = client.create_order(order_args)

# Размещение GTC ордера (до отмены)
resp = client.post_order(signed_order, OrderType.GTC)
```

---

### 💼 Trades (Сделки)

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/trades` | Получить сделки |
| `GET` | `/trades/builder` | Сделки билдеров |
| `GET` | `/trades/user/{address}` | Сделки пользователя |
| `GET` | `/trades/market/{id}` | Сделки для рынка |

---

### 👤 Profile (Профиль пользователя)

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/profile/{address}` | Публичный профиль |
| `GET` | `/positions` | Текущие позиции |
| `GET` | `/positions/closed` | Закрытые позиции |
| `GET` | `/activity` | Активность пользователя |
| `GET` | `/value` | Общая стоимость позиций |
| `GET` | `/positions/market/{id}` | Позиции для рынка |
| `GET` | `/accounting` | Скачать accounting snapshot (ZIP) |

---

### 🏆 Leaderboard (Таблица лидеров)

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/leaderboard` | Трейдеры (топ) |
| `GET` | `/builders/leaderboard` | Билдеры (агрегированный) |
| `GET` | `/builders/volume` | Объём билдеров (time-series) |

---

### 🔍 Search (Поиск)

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/search?q={query}` | Поиск рынков, событий, профилей |

---

### 🏷 Tags (Теги)

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/tags` | Список тегов |
| `GET` | `/tags/{id}` | Тег по ID |
| `GET` | `/tags/slug/{slug}` | Тег по slug |
| `GET` | `/tags/{id}/related` | Связанные теги |

---

### 📺 Series (Серии)

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/series` | Список серий |
| `GET` | `/series/{id}` | Серия по ID |

---

### 💬 Comments (Комментарии)

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/comments?market_id={id}` | Комментарии для рынка |
| `GET` | `/comments/{comment_id}` | Комментарий по ID |
| `GET` | `/comments/user/{address}` | Комментарии пользователя |

---

### ⚽ Sports (Спорт)

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/sports` | Sports metadata |
| `GET` | `/sports/types` | Valid market types |
| `GET` | `/teams` | Список команд |

---

### 🌉 Bridge (Мост)

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/bridge/assets` | Поддерживаемые активы |
| `POST` | `/bridge/deposit` | Создать депозит адрес |
| `POST` | `/bridge/quote` | Получить quote |
| `GET` | `/bridge/status/{txHash}` | Статус транзакции |
| `POST` | `/bridge/withdraw` | Создать withdrawal адрес |

---

## ⚠️ Rate Limits

| Endpoint | Лимит |
|----------|-------|
| **Public API** (GET) | ~100 запросов/минуту |
| **Private API** (POST/DELETE) | ~300 запросов/минуту |
| **WebSocket** | 10 подключений/IP |

**Рекомендации:**
- Использовать кэширование для public endpoints
- Избегать polling чаще 1 раза в секунду
- Для production запросить увеличение лимитов

---

## 📊 Типы ордеров

| Тип | Описание | SDK Constant |
|-----|----------|--------------|
| **GTC** | Good-Till-Cancelled (действует до отмены) | `OrderType.GTC` |
| **GTD** | Good-Till-Date (действует до даты) | `OrderType.GTD` |
| **FOK** | Fill-Or-Kill (заполнить или отменить) | `OrderType.FOK` |

---

## 💰 Комиссии

### Текущие ставки (2025)

| Тип | Maker | Taker |
|-----|-------|-------|
| **Базовая ставка** | 0 bps | 0 bps |

**Формула расчёта:**

Для продажи результат токенов (base → quote):
```
feeQuote = baseRate × min(price, 1 - price) × size
```

Для покупки результат токенов (quote → base):
```
feeBase = baseRate × min(price, 1 - price) × (size / price)
```

> Платформа оставляет за собой право изменять комиссии.

---

## 🔌 WebSocket

### Подключение

```
wss://clob.polymarket.com/ws
```

### Подписки

| Канал | Описание |
|-------|----------|
| `l2:{token_id}` | Orderbook updates |
| `trades:{token_id}` | Сделки в реальном времени |
| `prices:{token_id}` | Обновления цен |

**Пример подписки:**
```json
{
  "type": "subscribe",
  "channels": ["l2:12345", "trades:12345"]
}
```

---

## 🎯 Примеры использования

### 1. Получить список рынков

```python
import requests

response = requests.get(
    "https://gamma-api.polymarket.com/markets",
    params={"order": "volume", "active": "true", "limit": 10}
)
markets = response.json()
```

### 2. Разместить ордер

```python
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY

client = ClobClient("https://clob.polymarket.com", key=key, chain_id=137)
client.set_api_creds(client.create_or_derive_api_creds())

order = client.create_order(OrderArgs(
    price=0.55,
    size=100,
    side=BUY,
    token_id="12345"
))

resp = client.post_order(order, OrderType.GTC)
print(f"Order placed: {resp}")
```

### 3. Получить историю цен

```python
import requests

response = requests.get(
    "https://gamma-api.polymarket.com/candles",
    params={
        "market": "market_id_123",
        "outcome": "Yes",
        "resolution": "hour",
        "limit": 168
    }
)
candles = response.json()
# Формат: [timestamp, open, high, low, close, volume]
```

### 4. Получить позиции пользователя

```python
positions = client.get_positions()
for pos in positions:
    print(f"Market: {pos['market']}, Size: {pos['size']}, PnL: {pos['pnl']}")
```

---

## 📝 Глоссарий

| Термин | Описание |
|--------|----------|
| **CLOB** | Central Limit Order Book (централизованный стакан) |
| **Maker** | Создатель ордера (добавляет ликвидность) |
| **Taker** | Исполнитель ордера (забирает ликвидность) |
| **CTF** | Conditional Tokens Framework (ERC1155) |
| **USDCe** | Bridged USDC на Polygon |
| **EIP-712** | Стандарт подписи структурированных данных |
| **GTC** | Good-Till-Cancelled |
| **GTD** | Good-Till-Date |
| **FOK** | Fill-Or-Kill |

---

## 🔗 Полезные ссылки

- **Основная документация:** https://docs.polymarket.com/
- **CLOB API Reference:** https://docs.polymarket.com/api-reference
- **GitHub Organization:** https://github.com/Polymarket
- **Discord:** https://discord.gg/polymarket
- **Builder Program:** https://docs.polymarket.com/builders

---

**Последнее обновление:** Февраль 2026  
**Версия API:** v1 (Gamma)
