# Тесты для EventPredict API

## Запуск тестов

### Установка зависимостей

```bash
pip install -r api/requirements.txt
```

### Запуск всех тестов

```bash
pytest api/tests/ -v
```

### Запуск конкретных тестов

```bash
# Тесты определения категорий
pytest api/tests/test_api.py::TestCategoryDetection -v

# Тесты Polymarket API
pytest api/tests/test_api.py::TestPolymarketAPI -v

# Тесты синхронизации
pytest api/tests/test_api.py::TestSyncPolymarket -v

# Тесты API endpoints
pytest api/tests/test_api.py::TestAPIEndpoints -v

# Тесты прогнозов
pytest api/tests/test_api.py::TestUserPrediction -v

# Тесты граничных случаев
pytest api/tests/test_api.py::TestEdgeCases -v
```

### Запуск с покрытием кода

```bash
pytest api/tests/ -v --cov=api --cov-report=html
```

Отчёт будет в `htmlcov/index.html`.

## Структура тестов

| Класс тестов | Описание | Статус |
|-------------|----------|--------|
| `TestCategoryDetection` | Тесты определения категории событий | ✅ 8 тестов |
| `TestPolymarketAPI` | Тесты получения данных из Polymarket API | ✅ 3 теста |
| `TestSyncPolymarket` | Тесты синхронизации событий | ⚠️ 2 теста (требуют доработки) |
| `TestAPIEndpoints` | Тесты API endpoints | ⚠️ 5 тестов (требуют доработки) |
| `TestUserPrediction` | Тесты создания прогнозов | ⚠️ 2 теста (требуют доработки) |
| `TestEdgeCases` | Тесты граничных случаев | ✅ 3 теста |

## Примечания

### Переменные окружения для тестов

- `TEST_DB_PATH` — путь к тестовой БД (по умолчанию `./test_events.db`)
- `DISABLE_SCHEDULER` — отключает планировщик при старте (устанавливается в `1` автоматически в тестах)

### Известные проблемы

1. **Тесты синхронизации** — требуют исправления работы с datetime (timezone-aware vs naive)
2. **Тесты с TestClient** — проблемы с event loop при инициализации scheduler

### Рекомендации

Для быстрой проверки работоспособности запускайте:

```bash
pytest api/tests/test_api.py::TestCategoryDetection api/tests/test_api.py::TestPolymarketAPI api/tests/test_api.py::TestEdgeCases -v
```

Это 14 стабильных тестов которые проверяют:
- Определение категорий событий
- Получение данных из Polymarket API
- Обработку граничных случаев
