# 🚨 EventPredict — Production Error Report

## Дата: 18 февраля 2026

---

## ❌ Проблема: 502 Bad Gateway

**URL:** https://eventpredict-production.up.railway.app  
**Статус:** 502 Bad Gateway  
**Время возникновения:** После деплоя коммита `3f5c211`

---

## 📋 Что было сделано в последнем деплое

### Коммиты:
1. `00bdf2d` — feat: умный перевод событий и реальные данные графиков
2. `3f5c211` — docs: добавлен отчёт об исправлениях

### Изменения в коде:

#### api/index.py
- Добавлена функция `fetch_polymarket_price_history()` для получения истории цен
- Обновлена функция `upsert_polymarket_event()` с вызовом новой функции
- Добавлена константа `POLYMARKET_CANDLES_URL`

#### frontend/script.js
- Переписана функция `translateEventText()` с новой логикой
- Добавлена функция `translateQuestionPatterns()`
- Обновлена функция `renderEventChart()`

#### Новые файлы тестов:
- `test_translation.py` (370 строк)
- `test_charts.py` (285 строк)

---

## 🔍 Возможные причины ошибки 502

### 1. Ошибка импорта в api/index.py
```python
# Проверить что все импорты корректны
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # Есть ли эта библиотека?
```

### 2. Ошибка при старте приложения
```python
@app.on_event("startup")
async def startup_event():
    # Возможно ошибка в инициализации планировщика или БД
```

### 3. Нехватка памяти/ресурсов на Railway
- Функция `fetch_polymarket_price_history()` делает много запросов к API
- При синхронизации 300 событий × 2 исхода = 600 API запросов

### 4. Ошибка в БД
- Миграции таблиц могли не примениться корректно
- Проблема с SQLite и concurrent requests

### 5. Таймаут при синхронизации
- Polymarket API может отвечать медленно
- Railway убивает процесс при превышении времени старта

---

## 🛠️ Что проверить для исправления

### 1. Логи Railway
```bash
# В панели Railway посмотреть логи приложения
# Искать ошибки при старте:
# - ImportError
# - Exception in startup_event
# - Database errors
```

### 2. Проверить requirements.txt
```bash
# Убедиться что все зависимости установлены:
pip install apscheduler
```

### 3. Проверить код на синтаксические ошибки
```bash
# Запустить локально:
python -m py_compile api/index.py
```

### 4. Проверить логи Polymarket API вызовов
```python
# Возможно API вернул ошибку и код упал
# Добавить try/except в fetch_polymarket_price_history()
```

### 5. Откатиться на предыдущую версию
```bash
# Если проблема критична:
git revert 3f5c211
git revert 00bdf2d
git push origin main
```

---

## 📝 Промт для следующего чата

```
# EventPredict — Исправление 502 ошибки и полный контроль работоспособности

## Контекст

Проект: EventPredict (prediction market с интеграцией Polymarket и Telegram WebApp)
URL: https://eventpredict-production.up.railway.app
GitHub: https://github.com/pessimistqwe/tgqweasd

## Проблема

После последнего деплоя (коммиты 00bdf2d, 3f5c211) сайт возвращает 502 Bad Gateway.

## Что было сделано в последнем деплое

### Изменения в api/index.py:
1. Добавлена функция fetch_polymarket_price_history() для получения истории цен из Polymarket candles API
2. Обновлена upsert_polymarket_event() — теперь вызывает fetch_polymarket_price_history() при каждом обновлении события
3. Добавлена константа POLYMARKET_CANDLES_URL = "https://gamma-api.polymarket.com/candles"

### Изменения в frontend/script.js:
1. Полностью переписана translateEventText() с PRESERVE_PATTERNS и PRESERVE_TERMS
2. Добавлена translateQuestionPatterns() для умного перевода вопросов
3. Обновлена renderEventChart() с улучшенным стилем

### Новые файлы:
- test_translation.py (370 строк)
- test_charts.py (285 строк)
- FIX_REPORT.md

## Задачи

### Задача 1: Диагностика 502 ошибки

1. Проверить логи Railway на ошибки при старте приложения
2. Проверить что все импорты в api/index.py корректны
3. Проверить requirements.txt на наличие всех зависимостей:
   - apscheduler
   - fastapi
   - uvicorn
   - sqlalchemy
   - requests
   - pydantic

4. Проверить нет ли ошибок в коде:
   ```bash
   python -m py_compile api/index.py
   ```

5. Проверить не превышает ли время старта лимит Railway (30 секунд)
6. Проверить не вызывает ли fetch_polymarket_price_history() слишком много API запросов при старте

### Задача 2: Исправление ошибки

Варианты исправления (по приоритету):

1. **Добавить обработку ошибок в fetch_polymarket_price_history():**
   ```python
   def fetch_polymarket_price_history(...):
       try:
           # ... код
       except Exception as e:
           logger.error(f"Price history fetch error: {e}")
           return []  # Вернуть пустой список вместо падения
   ```

2. **Отложить синхронизацию истории цен:**
   - Не вызывать fetch_polymarket_price_history() при upsert_polymarket_event()
   - Создать отдельный endpoint для ручной синхронизации истории
   - Или запускать синхронизацию истории в фоне через планировщик

3. **Добавить лимиты на API запросы:**
   - Максимум 10-20 событий с историей за одну синхронизацию
   - Rate limiting для Polymarket API

4. **Проверить и исправить импорты:**
   ```python
   # Убедиться что все импорты корректны
   from apscheduler.schedulers.asyncio import AsyncIOScheduler
   ```

5. **Проверить БД:**
   - Убедиться что таблица price_history существует
   - Проверить миграции

### Задача 3: Добавить comprehensive тесты

Создать test_comprehensive.py который проверяет:

#### 3.1 Backend API Tests:
```python
def test_health_endpoint():
    """Проверка что приложение живо"""
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_api_imports():
    """Проверка что все импорты в api/index.py корректны"""
    import api.index
    assert hasattr(api.index, 'app')
    assert hasattr(api.index, 'fetch_polymarket_price_history')

def test_database_connection():
    """Проверка подключения к БД"""
    response = requests.get(f"{BASE_URL}/admin/stats")
    assert response.status_code == 200

def test_all_endpoints():
    """Проверка всех API endpoints"""
    endpoints = [
        ("/", 200),
        ("/categories", 200),
        ("/events", 200),
        ("/health", 200),
        ("/admin/stats", 200),
    ]
    for endpoint, expected_status in endpoints:
        response = requests.get(f"{BASE_URL}{endpoint}")
        assert response.status_code == expected_status
```

#### 3.2 Startup Tests:
```python
def test_startup_no_errors():
    """Проверка что приложение стартует без ошибок"""
    # Запустить uvicorn локально
    # Проверить что нет ImportError, Exception в логах
    pass

def test_scheduler_initialization():
    """Проверка инициализации планировщика"""
    # Проверить что AsyncIOScheduler корректно инициализируется
    pass
```

#### 3.3 Integration Tests:
```python
def test_polymarket_api_connection():
    """Проверка подключения к Polymarket API"""
    response = requests.get("https://gamma-api.polymarket.com/markets", timeout=10)
    assert response.status_code == 200

def test_price_history_function():
    """Проверка функции fetch_polymarket_price_history()"""
    # Вызвать функцию с тестовыми данными
    # Убедиться что не падает с исключением
    history = fetch_polymarket_price_history("test", "Yes")
    assert isinstance(history, list)  # Может быть пустым, но не None
```

#### 3.4 Frontend Tests:
```python
def test_frontend_loads():
    """Проверка что frontend загружается"""
    response = requests.get(f"{BASE_URL}")
    assert response.status_code == 200
    assert "index.html" in response.text or "EventPredict" in response.text

def test_script_js_syntax():
    """Проверка синтаксиса frontend/script.js"""
    import subprocess
    result = subprocess.run(
        ["node", "--check", "frontend/script.js"],
        capture_output=True
    )
    assert result.returncode == 0
```

#### 3.5 Database Tests:
```python
def test_database_tables_exist():
    """Проверка что все таблицы БД существуют"""
    # Проверить наличие таблиц:
    # - users
    # - events
    # - event_options
    # - price_history
    # - user_predictions
    # - transactions
    pass

def test_price_history_migration():
    """Проверка миграции price_history"""
    # Убедиться что таблица price_history создана
    pass
```

### Задача 4: Автоматический деплой тест

Создать test_deployment_comprehensive.py:
```python
def test_full_deployment():
    """Полная проверка работоспособности после деплоя"""
    
    # 1. Проверка что сайт доступен
    response = requests.get(BASE_URL, timeout=30)
    assert response.status_code == 200, "Site not accessible"
    
    # 2. Проверка API endpoints
    endpoints = ["/health", "/categories", "/events"]
    for endpoint in endpoints:
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        assert response.status_code == 200, f"Endpoint {endpoint} failed"
    
    # 3. Проверка что события загружаются
    events_response = requests.get(f"{BASE_URL}/events", timeout=10)
    events = events_response.json().get("events", [])
    assert len(events) > 0, "No events loaded"
    
    # 4. Проверка что есть изображения
    events_with_images = sum(1 for e in events if e.get("image_url"))
    assert events_with_images > 0, "No events with images"
    
    # 5. Проверка переводов (если русский язык)
    # ...
    
    # 6. Проверка графиков
    if events:
        event_id = events[0]["id"]
        history_response = requests.get(
            f"{BASE_URL}/events/{event_id}/price-history",
            timeout=10
        )
        assert history_response.status_code == 200
    
    print("✅ All deployment checks passed!")
```

### Задача 5: CI/CD улучшения

1. **Добавить pre-commit хуки:**
   ```bash
   # Проверка синтаксиса Python перед коммитом
   python -m py_compile api/index.py
   python -m py_compile api/models.py
   ```

2. **Добавить post-deploy тесты:**
   - Автоматический запуск test_deployment_comprehensive.py после деплоя
   - Отправка уведомления если тесты не прошли

3. **Добавить health checks:**
   - Periodic проверка /health endpoint
   - Автоматический rollback если 502 ошибка

## Критерии приёмки

### 1. 502 ошибка исправлена:
- [ ] Сайт доступен по https://eventpredict-production.up.railway.app
- [ ] /health endpoint возвращает 200
- [ ] /events endpoint возвращает события
- [ ] Frontend загружается корректно

### 2. Все тесты проходят:
- [ ] test_translation.py (8/8 тестов)
- [ ] test_charts.py (9/9 тестов)
- [ ] test_frontend_features.py (9/9 тестов)
- [ ] test_comprehensive.py (все новые тесты)
- [ ] test_deployment_comprehensive.py (все проверки)

### 3. Логи чистые:
- [ ] Нет ImportError при старте
- [ ] Нет Exception в логах Railway
- [ ] Polymarket API вызовы логируются корректно

### 4. Функционал работает:
- [ ] События загружаются из Polymarket
- [ ] Перевод работает (сохраняет имена, криптовалюты)
- [ ] Графики отображаются
- [ ] Админ-панель доступна

## Формат ответа

1. **Диагностика** — анализ логов, выявление причины 502
2. **Исправление** — код фиксов с объяснением
3. **Тесты** — новые comprehensive тесты
4. **Проверка** — запуск всех тестов, ручная проверка
5. **Документация** — обновление FIX_REPORT.md

## Важно

- Не делать слишком много API запросов к Polymarket при старте
- Обрабатывать все исключения в fetch_polymarket_price_history()
- Проверять что все импорты корректны перед деплоем
- Запускать full deployment test перед каждым деплоем
```

---

## 📊 Приоритеты исправлений

| Приоритет | Задача | Время |
|-----------|--------|-------|
| 🔴 P0 | Исправить 502 ошибку | 30 мин |
| 🔴 P0 | Проверить логи Railway | 10 мин |
| 🟡 P1 | Добавить обработку ошибок | 30 мин |
| 🟡 P1 | Создать comprehensive тесты | 1 час |
| 🟢 P2 | Оптимизировать API запросы | 1 час |
| 🟢 P2 | Добавить CI/CD проверки | 1 час |

---

## 🔗 Полезные ссылки

- **Railway Dashboard:** https://railway.app/dashboard
- **Railway Logs:** https://railway.app/project/logs
- **GitHub Repo:** https://github.com/pessimistqwe/tgqweasd
- **Polymarket API Docs:** https://polymarket.github.io/docs/

---

**Следующий шаг:** Использовать промт выше для нового чата и исправить 502 ошибку.
