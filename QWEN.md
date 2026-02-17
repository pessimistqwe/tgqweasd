# EventPredict — Проект предсказательных рынков

## Обзор проекта

**EventPredict** — это веб-приложение для торговли предсказаниями (prediction market), интегрированное с Telegram WebApp и API Polymarket. Пользователи могут делать прогнозы на события из различных категорий (политика, спорт, крипто, поп-культура, бизнес, наука) используя виртуальные очки (USDT).

### Архитектура

```
tgqweasd/
├── api/                    # Backend (FastAPI + SQLAlchemy)
│   ├── index.py           # Основной файл приложения (API endpoints + Polymarket integration)
│   ├── models.py          # SQLAlchemy модели (User, Event, EventOption, UserPrediction, Transaction)
│   ├── main.py            # Точка входа для некоторых платформ
│   └── requirements*.txt  # Зависимости Python
├── frontend/              # Frontend (Vanilla JS + CSS)
│   ├── index.html         # Главная страница
│   ├── styles.css         # Стили
│   └── script.js          # Клиентская логика (Telegram WebApp integration)
├── Dockerfile             # Multi-stage Docker образ (Alpine Linux)
├── fly.toml              # Конфигурация для Fly.io
├── railway.json          # Конфигурация для Railway.app
├── render.yaml           # Конфигурация для Render.com
├── vercel.json           # Конфигурация для Vercel
└── zbpack.json           # Конфигурация для ZBpack
```

### Технологический стек

| Компонент | Технология |
|-----------|------------|
| **Backend** | Python 3.12, FastAPI 0.109, SQLAlchemy 2.0, Pydantic 2.9 |
| **Frontend** | Vanilla JavaScript, CSS3, Telegram WebApp SDK |
| **База данных** | SQLite (для production совместима с PostgreSQL) |
| **Контейнеризация** | Docker (multi-stage build на Alpine) |
| **Внешние API** | Polymarket Gamma API |

### Ключевые возможности

- **Интеграция с Polymarket**: Автоматическая синхронизация событий из Polymarket API (интервал настраивается через `POLYMARKET_SYNC_INTERVAL`)
- **Категоризация событий**: Автоматическое определение категории события по ключевым словам
- **Telegram WebApp**: Полная интеграция с Telegram (темизация, HapticFeedback, уведомления)
- **Система балансов**: Депозиты/выводы через CryptoBot
- **Админ-панель**: Управление выводами, ручная синхронизация событий
- **Мультиплатформенный деплой**: Поддержка Railway, Render, Fly.io, Vercel, Zeabur

---

## Сборка и запуск

### Локальная разработка

```bash
# Установка зависимостей
pip install -r api/requirements.txt

# Запуск сервера разработки
uvicorn api.index:app --reload --host 0.0.0.0 --port 8000

# Или для production-подобного запуска
uvicorn index:app --host 0.0.0.0 --port 8000 --app-dir api
```

### Docker

```bash
# Сборка образа
docker build -t eventpredict .

# Запуск контейнера
docker run -p 8000:8000 -e PORT=8000 eventpredict
```

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `PORT` | Порт сервера | `8000` |
| `POLYMARKET_SYNC_INTERVAL` | Интервал синхронизации Polymarket (секунды) | `3600` |
| `CRYPTOBOT_API_TOKEN` | Токен CryptoBot для платежей | — |
| `ADMIN_TELEGRAM_IDS` | Список Telegram ID администраторов | — |

---

## API Endpoints

### Публичные

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/` | Главная страница (frontend) |
| `GET` | `/categories` | Список категорий |
| `GET` | `/events?category={}` | Получить события (фильтр по категории) |
| `GET` | `/user/{telegram_id}` | Информация о пользователе |
| `GET` | `/health` | Health check |

### Аутентифицированные

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `POST` | `/predict` | Сделать прогноз |
| `GET` | `/wallet/balance/{telegram_id}` | Баланс пользователя |
| `POST` | `/wallet/deposit` | Создать депозит |
| `POST` | `/wallet/withdraw` | Запросить вывод |

### Админские

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `POST` | `/admin/sync-polymarket` | Ручная синхронизация Polymarket |
| `GET` | `/admin/check/{telegram_id}` | Проверка прав администратора |
| `GET` | `/admin/stats` | Статистика платформы |
| `GET` | `/admin/withdrawals` | Список выводов |
| `POST` | `/admin/withdrawal/action` | Одобрить/отклонить вывод |

---

## Структура базы данных

### Таблицы

- **users** — пользователи (telegram_id, баланс USDT/TON, статусы)
- **events** — события (Polymarket ID, категория, время окончания, пул)
- **event_options** — варианты исходов (текст, ставки, market_stake от Polymarket)
- **user_predictions** — прогнозы пользователей (связь user-event-option)
- **transactions** — транзакции (депозиты, выводы, ставки)

### Особенности

- Используется SQLite с путем `/tmp/events.db` для совместимости с serverless (Vercel)
- Автоматическая миграция: добавление колонки `market_stake` в `event_options` при старте

---

## Деплой

### Рекомендуемые платформы (бесплатные тарифы)

1. **Railway.app** ⭐ — $5 кредитов/мес, автоматический деплой из GitHub
2. **Render.com** — free tier с sleep после 15 мин бездействия
3. **Fly.io** — 3 shared-cpu-1x VM бесплатно
4. **Vercel** — serverless функции для Python

### Инструкции

См. файл [`DEPLOY.md`](./DEPLOY.md) с подробными инструкциями по деплою на каждую платформу.

---

## Конвенции разработки

### Код

- **Python**: PEP 8, type hints через Pydantic модели
- **JavaScript**: ES6+, async/await для асинхронных операций
- **Именование**: snake_case для Python, camelCase для JavaScript

### Тестирование

- Ручное тестирование через Telegram WebApp
- API endpoints можно проверять через `/docs` (Swagger UI) или `/redoc`

### Git

- Ветка по умолчанию: `main`
- Коммиты: conventional commits (опционально)

---

## Frontend структура

### Секции приложения

1. **Markets** (`#events-section`) — список событий с фильтрацией по категориям
2. **Wallet** (`#wallet-section`) — баланс, депозиты, выводы, история транзакций
3. **Profile** (`#profile-section`) — профиль пользователя, статистика, навигация
4. **Admin** (`#admin-section`) — админ-панель (только для администраторов)

### Навигация

- Bottom navigation bar с переключением между секциями
- Автообновление событий каждые 30 секунд (только в активной секции Markets)
- Telegram theme integration (автоматическая темизация)

---

## Polymarket интеграция

### Категории и ключевые слова

| Категория | Ключевые слова |
|-----------|----------------|
| `politics` | trump, biden, election, putin, zelensky, russia, ukraine... |
| `sports` | nba, nfl, soccer, football, basketball, tennis, ufc... |
| `crypto` | bitcoin, btc, ethereum, eth, defi, nft, solana... |
| `pop_culture` | movie, oscar, grammy, celebrity, netflix, marvel... |
| `business` | stock, tesla, apple, google, ai, fed, inflation... |
| `science` | nasa, spacex, climate, vaccine, research, gpt... |

### Синхронизация

- Автоматическая: каждые `POLYMARKET_SYNC_INTERVAL` секунд
- Ручная: через админ-панель или кнопку "Load from Polymarket"

---

## Файлы конфигурации

| Файл | Назначение |
|------|------------|
| `Dockerfile` | Multi-stage сборка (Alpine + minimal dependencies) |
| `fly.toml` | Конфигурация Fly.io (порт 8080, auto-start/stop) |
| `railway.json` | Railway: Dockerfile builder, start command |
| `render.yaml` | Render: build/start commands |
| `vercel.json` | Vercel: routes для Python + static files |
| `.dockerignore` | Исключения для Docker (`.env`, `__pycache__`, `node_modules`) |

---

## Контакты и поддержка

- Документация по деплою: [`DEPLOY.md`](./DEPLOY.md)
- API документация: `/docs` (Swagger) или `/redoc` после запуска
