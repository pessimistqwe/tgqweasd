# Core Betting Engine — Документация

## Обзор

Core Betting Engine — это модульная система для управления ставками в Telegram Mini App. Поддерживает два типа рынков:

1. **Polymarket Style (EVENT)** — ставки на события с исходами Yes/No
2. **Binance Style (PRICE)** — ставки на цену с плечом Long/Short
3. **Price Predictions** — краткосрочные прогнозы на 5 минут

## Архитектура

```
api/
├── betting_models.py       # SQLAlchemy модели (Bet, PricePrediction)
├── betting_repository.py   # Repository слой для работы с БД
├── betting_service.py      # Бизнес-логика (placeBet, settleBet, cancelBet)
├── betting_resolver.py     # Фоновый воркер для авто-расчёта ставок
├── betting_routes.py       # FastAPI endpoints
├── telegram_auth.py        # Валидация Telegram initData
└── index.py                # Интеграция (обновлён)

frontend/
├── betting.js              # JS модуль (usePlaceBet, BetModal)
├── styles.css              # CSS стили для модальных окон
└── index.html              # Подключён betting.js
```

## Быстрый старт

### 1. Настройка переменных окружения

Добавьте в `.env`:

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
```

### 2. Запуск приложения

```bash
cd api
uvicorn index:app --reload --host 0.0.0.0 --port 8000
```

### 3. Миграции БД

Миграции выполняются автоматически при старте. Создаются таблицы:
- `bets` — основные ставки
- `price_predictions` — краткосрочные прогнозы

## Backend API

### Разместить ставку на событие (Polymarket)

```http
POST /api/betting/event/place
Content-Type: application/json
X-Telegram-Init-Data: <initData от Telegram>

{
    "market_id": 1,
    "option_index": 0,
    "amount": "10.00",
    "direction": "yes"
}
```

**Ответ:**
```json
{
    "success": true,
    "data": {
        "bet_id": 123,
        "shares": "20.00000000",
        "entry_price": "0.50000000",
        "potential_payout": "20.00000000",
        "status": "open"
    }
}
```

### Разместить ставку на цену (Binance Long/Short)

```http
POST /api/betting/price/place
Content-Type: application/json
X-Telegram-Init-Data: <initData>

{
    "market_id": 1,
    "direction": "long",
    "amount": "100.00",
    "leverage": "10",
    "entry_price": "50000.00",
    "symbol": "BTCUSDT",
    "take_profit_price": "55000.00",
    "stop_loss_price": "48000.00"
}
```

**Ответ:**
```json
{
    "success": true,
    "data": {
        "bet_id": 124,
        "position_size": "1000.00000000",
        "leverage": "10.00",
        "liquidation_price": "45000.00000000",
        "potential_payout": "100.00000000",
        "status": "open"
    }
}
```

### Разместить краткосрочный прогноз (5 минут)

```http
POST /api/betting/prediction/place
Content-Type: application/json
X-Telegram-Init-Data: <initData>

{
    "market_id": 1,
    "direction": "long",
    "amount": "10.00",
    "odds": "1.95",
    "entry_price": "50000.00",
    "symbol": "BTCUSDT",
    "duration_seconds": 300
}
```

### Получить мои ставки

```http
GET /api/betting/my-bets?status=open&bet_type=event&limit=50&offset=0
X-Telegram-Init-Data: <initData>
```

### Отменить ставку

```http
POST /api/betting/cancel
Content-Type: application/json
X-Telegram-Init-Data: <initData>

{
    "bet_id": 123
}
```

## Frontend Integration

### Использование usePlaceBet hook

```javascript
// Создаём хук
const betting = usePlaceBet();

// Настраиваем callbacks
betting.setCallbacks({
    onSuccess: (result) => {
        console.log('Ставка размещена:', result);
        updateBalance(); // Обновляем UI баланса
    },
    onError: (error) => {
        console.error('Ошибка:', error.message);
        showError(error.message);
    },
    onLoadingChange: (loading) => {
        setButtonDisabled(loading);
    }
});

// Размещаем ставку на событие
await betting.placeEventBet({
    marketId: 1,
    optionIndex: 0,
    amount: 10.00,
    direction: 'yes'
});

// Размещаем прогноз
await betting.placePricePrediction({
    marketId: 1,
    direction: 'long',
    amount: 10.00,
    odds: 1.95,
    entryPrice: 50000,
    symbol: 'BTCUSDT'
});
```

### Использование BetModal

```javascript
// Открываем модальное окно для ставки на событие
betModal.open({
    type: 'event',
    marketId: 1,
    optionIndex: 0,
    optionText: 'Yes',
    currentPrice: 0.5,
    balance: 100.00,
    direction: 'yes',
    onSuccess: () => {
        // Обновляем UI после успешной ставки
        loadUserBalance();
    }
});

// Открываем модальное окно для прогноза
betModal.open({
    type: 'prediction',
    marketId: 1,
    direction: 'long',
    odds: 1.95,
    entryPrice: 50000,
    symbol: 'BTCUSDT',
    balance: 100.00
});
```

## Resolver Worker

Фоновый воркер автоматически рассчитывает ставки:

### Проверка краткосрочных прогнозов (каждые 10 сек)
- Получает все активные `PricePrediction`
- Проверяет истёк ли срок (5 минут)
- Получает текущую цену из Binance API
- Рассчитывает выигрыш

### Проверка Price Bets (каждые 60 сек)
- Получает все открытые `Bet` типа `PRICE`
- Проверяет текущую цену из Binance
- Закрывает если:
  - Достигнут тейк-профит
  - Достигнут стоп-лосс
  - Достигнута цена ликвидации

### Проверка Polymarket событий (каждые 5 мин)
- Получает все открытые `Bet` типа `EVENT`
- Проверяет статус события в Polymarket API
- Если событие resolved — рассчитывает ставки

## Бизнес-логика

### Расчёт для EVENT ставок (Polymarket)

```python
# Количество акций = сумма / цена за акцию
shares = amount / entry_price

# Потенциальный выигрыш = shares * $1.00
potential_payout = shares * 1.0

# Если выиграл:
profit = potential_payout - amount
roi = (profit / amount) * 100
```

### Расчёт для PRICE ставок (Binance)

```python
# Размер позиции = маржа * плечо
position_size = amount * leverage

# Цена ликвидации:
# LONG: liq = entry * (1 - 1/leverage)
# SHORT: liq = entry * (1 + 1/leverage)

# PnL при закрытии:
price_change_pct = (exit_price - entry_price) / entry_price
pnl = price_change_pct * position_size * direction_multiplier
# direction_multiplier: +1 для LONG, -1 для SHORT
```

### Расчёт для Price Predictions

```python
# Потенциальный выигрыш = сумма * коэффициент
potential_payout = amount * odds

# Если угадал направление:
profit = potential_payout - amount
```

## Валидация Telegram initData

Все API endpoints требуют заголовок `X-Telegram-Init-Data`.

### Как получить initData на frontend:

```javascript
const initData = window.Telegram.WebApp.initData;
```

### Валидация на backend:

```python
from telegram_auth import validate_telegram_init_data

try:
    user_data = validate_telegram_init_data(init_data)
    telegram_id = user_data['user']['id']
except TelegramAuthError as e:
    # Неверные данные
    pass
```

## Обработка ошибок

### Backend исключения:

```python
from betting_service import (
    BettingError,
    InsufficientBalanceError,
    InvalidBetAmountError,
    MarketNotFoundError,
    BetNotFoundError,
    InvalidOddsError,
)
```

### Frontend ошибки:

```javascript
try {
    await betting.placeEventBet({...});
} catch (error) {
    if (error instanceof InsufficientBalanceError) {
        // Показать "Недостаточно средств"
    } else if (error instanceof ValidationError) {
        // Показать ошибку валидации
    } else {
        // Общая ошибка
    }
}
```

## Тестирование

### 1. Создать тестового пользователя

```bash
curl -X POST http://localhost:8000/api/user/create \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": 123456789, "username": "testuser"}'
```

### 2. Начислить баланс

```bash
curl -X POST http://localhost:8000/api/admin/add-balance \
  -H "Content-Type: application/json" \
  -d '{
    "admin_telegram_id": 1972885597,
    "user_telegram_id": 123456789,
    "amount": 1000,
    "asset": "USDT"
  }'
```

### 3. Разместить ставку

```bash
curl -X POST http://localhost:8000/api/betting/event/place \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Init-Data: <initData>" \
  -d '{
    "market_id": 1,
    "option_index": 0,
    "amount": "10.00",
    "direction": "yes"
  }'
```

## Безопасность

1. **ACID транзакции** — все операции с балансом в транзакциях
2. **Row locking** — блокировка строк при обновлении (FOR UPDATE)
3. **Decimal вычисления** — никаких float для денег
4. **Telegram аутентификация** — валидация initData через HMAC-SHA256
5. **Rate limiting** — защита от злоупотреблений (реализуется отдельно)

## Расширение

### Добавить новый тип ставок:

1. Создать модель в `betting_models.py`
2. Добавить методы в `BettingRepository`
3. Добавить бизнес-логику в `BettingService`
4. Создать API endpoint в `betting_routes.py`
5. Добавить frontend компонент в `betting.js`

## Поддержка

Вопросы и предложения: создайте issue в репозитории.
