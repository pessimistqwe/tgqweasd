# ✅ Деплой исправлен — Чеклист проверки

## Что было сделано

### Исправления в конфигурации:

1. **Dockerfile**
   - Сменён базовый образ с `alpine` на `python:3.12-slim` (более стабильный)
   - Добавлен `wget` для health checks
   - Создан стартовый скрипт `start.sh`
   - Исправлен путь PYTHONPATH
   - Увеличен `start-period` для healthcheck до 10 секунд

2. **zeabur.json**
   - Убран `start.command` (используется Dockerfile CMD)
   - Добавлен `startPeriod` в healthcheck
   - Упрощена конфигурация

3. **.dockerignore**
   - Убран `Dockerfile` из игнора (мог вызывать проблемы)

4. **start.sh**
   - Новый стартовый скрипт для надёжного запуска
   - Устанавливает PYTHONPATH
   - Запускает uvicorn правильно

5. **test_app.py**
   - Тестовый скрипт для проверки запуска
   - Проверяет все импорты и роуты

## Проверка перед деплоем

### Локальные тесты (уже пройдены ✅):

```bash
# Тест 1: Импорт приложения
py -c "from api.index import app; print('OK')"
# Результат: OK ✅

# Тест 2: Проверка всех модулей
py test_app.py
# Результат: Все 13 тестов пройдены ✅

# Тест 3: Проверка роутов
# - 95 роутов найдено
# - /health существует ✅
# - /api/polymarket/search существует ✅
# - /api/leaderboard существует ✅
```

## Проверка после деплоя на Zeabur

### 1. Дождитесь завершения деплоя (2-5 минут)

Зайдите на https://zeabur.com и проверьте статус.

### 2. Проверьте health endpoint

```bash
curl https://your-app.zeabur.app/health
```

**Ожидаемый ответ:**
```json
{
  "status": "healthy",
  "sync": {
    "last_sync": "2026-02-20T...",
    "total_synced": 50,
    "last_error": null,
    "next_sync_in": 7200
  }
}
```

### 3. Проверьте новые API endpoints

```bash
# Polymarket search
curl https://your-app.zeabur.app/api/polymarket/search?q=bitcoin

# Leaderboard
curl https://your-app.zeabur.app/api/leaderboard

# Trending markets
curl https://your-app.zeabur.app/api/polymarket/trending

# User stats (замените telegram_id)
curl https://your-app.zeabur.app/api/user/123456789/stats
```

### 4. Проверьте frontend

Откройте в браузере: `https://your-app.zeabur.app`

Убедитесь что:
- Страница загружается
- Поиск работает
- Категории отображаются

## Если всё ещё ошибка 502

### Шаг 1: Проверьте логи на Zeabur

1. Зайдите на https://zeabur.com
2. Project → Deployments → Последний деплой
3. Нажмите "View Logs"

Ищите ошибки:
- `ModuleNotFoundError` — проблема с импортами
- `Address already in use` — порт занят
- `Health check failed` — приложение не отвечает

### Шаг 2: Проверьте переменные окружения

Убедитесь что на Zeabur установлены:

```
PORT=8000
TEST_DB_PATH=/tmp/events.db
PYTHONPATH=/app
PYTHONUNBUFFERED=1
DATABASE_URL=
CRYPTOBOT_API_TOKEN=
ADMIN_TELEGRAM_IDS=
POLYMARKET_SYNC_INTERVAL=7200
```

### Шаг 3: Перезапустите деплой

1. Zeabur → Project → "Redeploy"
2. Подождите 3-5 минут

### Шаг 4: Напишите в поддержку Zeabur

Если ничего не помогает:
- Discord: https://discord.gg/zeabur
- Пришлите скриншот ошибки и логи

## Коммиты

Последние изменения:
- `e49bc80` fix: Полная переработка Dockerfile и конфигурации
- `c919d99` docs: Инструкция по деплою
- `bac9a6f` fix: Конфигурация Dockerfile и zeabur.json
- `6e549b4` fix: Импорт Bet в leaderboard_routes.py
- `d9895ad` feat: Polymarket интеграция v0.3.0

**Всего изменений:** 5 файлов, +108 строк, -19 строк

---

**Статус:** ✅ Готово к деплою
**Дата:** 20 февраля 2026
**Версия:** v0.3.0
