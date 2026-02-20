# 🚀 Деплой на Zeabur — Инструкция

## Проблема "Removed"

Если деплой показывает статус "Removed", это означает что Zeabur не может запустить приложение.

## Решение

### 1. Проверьте конфигурационные файлы

#### Dockerfile
Убедитесь что Dockerfile содержит:
```dockerfile
CMD ["uvicorn", "api.index:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### zeabur.json
Должен содержать:
```json
{
  "build": {
    "dockerfile": "Dockerfile",
    "context": "."
  },
  "start": {
    "command": "uvicorn api.index:app --host 0.0.0.0 --port 8000"
  }
}
```

### 2. Проверьте переменные окружения на Zeabur

Зайдите в панель управления Zeabur → Project → Variables и добавьте:

```
PORT=8000
TEST_DB_PATH=/tmp/events.db
DATABASE_URL=
PYTHONUNBUFFERED=1
PYTHONPATH=/app:/app/api
POLYMARKET_SYNC_INTERVAL=7200
CRYPTOBOT_API_TOKEN=
ADMIN_TELEGRAM_IDS=
```

### 3. Перезапустите деплой

1. Зайдите на https://zeabur.com
2. Выберите проект `eventpredict`
3. Нажмите "Redeploy" или "Restart"

### 4. Проверьте логи

В панели Zeabur:
1. Project → Deployments
2. Выберите последний деплой
3. Нажмите "View Logs"

Ищите ошибки:
- `ModuleNotFoundError` — проблема с импортами
- `Address already in use` — порт занят
- `Health check failed` — приложение не отвечает

## Проверка работы

После успешного деплоя проверьте:

1. **Health endpoint:**
   ```
   https://your-app.zeabur.app/health
   ```
   Должен вернуть: `{"status": "healthy", ...}`

2. **API endpoints:**
   ```
   https://your-app.zeabur.app/api/polymarket/trending
   https://your-app.zeabur.app/api/leaderboard
   https://your-app.zeabur.app/categories
   ```

3. **Frontend:**
   ```
   https://your-app.zeabur.app
   ```

## Частые проблемы

### 1. "ModuleNotFoundError: No module named 'xxx'"

**Решение:** Добавьте модуль в `api/requirements-minimal.txt` и запушите изменения.

### 2. "Health check failed"

**Причина:** Health endpoint не отвечает в течение 30 секунд.

**Решение:**
- Проверьте что `/health` endpoint существует
- Увеличьте timeout в zeabur.json
- Проверьте логи на ошибки при старте

### 3. "Address already in use"

**Причина:** Порт 8000 уже используется.

**Решение:** Убедитесь что в Dockerfile указано:
```dockerfile
CMD ["uvicorn", "api.index:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 4. Деплой застревает на "Building"

**Причина:** Долгая установка зависимостей.

**Решение:**
- Проверьте `requirements-minimal.txt` на лишние пакеты
- Используйте кэширование в Zeabur

## Локальная проверка Docker

Перед деплоем проверьте Docker локально:

```bash
# Сборка образа
docker build -t eventpredict-test .

# Запуск
docker run -p 8000:8000 eventpredict-test

# Проверка
curl http://localhost:8000/health
```

## Контакты поддержки Zeabur

- Discord: https://discord.gg/zeabur
- GitHub: https://github.com/Zeabur
