"""
Cache Service - Сервис кэширования для API запросов

Функционал:
- In-memory кэширование с TTL
- Декоратор @cache_result для автоматического кэширования
- Поддержка namespaces для разных типов данных
- Статистика кэша (hit/miss ratio)
- Очистка кэша по namespace или полностью

Использование:
    @cache_result(namespace=CacheNamespace.POLYMARKET, ttl_seconds=300)
    async def get_market_data(market_id: str):
        ...
"""

from functools import wraps
from typing import Any, Optional, Dict, Callable, TypeVar
from datetime import datetime, timedelta
import logging
import hashlib
import json

logger = logging.getLogger(__name__)

# ==================== Types ====================

T = TypeVar('T')


class CacheNamespace:
    """Пространства имен для кэша"""
    POLYMARKET = "polymarket"
    BINANCE = "binance"
    USER_DATA = "user_data"
    EVENTS = "events"
    ADMIN = "admin"
    GENERAL = "general"


# ==================== Cache Entry ====================

class CacheEntry:
    """Элемент кэша"""

    def __init__(self, data: Any, ttl_seconds: int):
        self.data = data
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(seconds=ttl_seconds)
        self.ttl_seconds = ttl_seconds

    def is_expired(self) -> bool:
        """Проверить истечение срока"""
        return datetime.utcnow() > self.expires_at

    def age_seconds(self) -> float:
        """Возраст кэша в секундах"""
        return (datetime.utcnow() - self.created_at).total_seconds()

    def remaining_ttl(self) -> float:
        """Оставшееся время жизни"""
        remaining = (self.expires_at - datetime.utcnow()).total_seconds()
        return max(0, remaining)


# ==================== Cache Service ====================

class CacheService:
    """
    In-memory сервис кэширования

    Thread-safe, поддерживает:
    - TTL для каждого ключа
    - Namespaces для группировки
    - Статистику hit/miss
    - Автоматическую очистку expired entries
    """

    def __init__(self, max_size: int = 10000):
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._hits = 0
        self._misses = 0
        self._namespace_keys: Dict[str, set] = {
            CacheNamespace.POLYMARKET: set(),
            CacheNamespace.BINANCE: set(),
            CacheNamespace.USER_DATA: set(),
            CacheNamespace.EVENTS: set(),
            CacheNamespace.ADMIN: set(),
            CacheNamespace.GENERAL: set(),
        }

    def _make_key(self, namespace: str, key: str) -> str:
        """Создать уникальный ключ"""
        return f"{namespace}:{key}"

    def _extract_key(self, func: Callable, args: tuple, kwargs: dict) -> str:
        """
        Извлечь ключ из аргументов функции

        Создает хэш из всех аргументов для уникальности
        """
        key_parts = []

        # Позиционные аргументы
        for arg in args:
            if isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
            elif hasattr(arg, '__dict__'):
                key_parts.append(str(arg.__dict__))
            else:
                try:
                    key_parts.append(json.dumps(arg, sort_keys=True))
                except (TypeError, ValueError):
                    key_parts.append(str(arg))

        # Именованные аргументы
        for k, v in sorted(kwargs.items()):
            if isinstance(v, (str, int, float, bool)):
                key_parts.append(f"{k}={v}")
            elif hasattr(v, '__dict__'):
                key_parts.append(f"{k}={v.__dict__}")
            else:
                try:
                    key_parts.append(f"{k}={json.dumps(v, sort_keys=True)}")
                except (TypeError, ValueError):
                    key_parts.append(f"{k}={str(v)}")

        # Создаем хэш для длинных ключей
        key_string = "|".join(key_parts)
        if len(key_string) > 100:
            key_hash = hashlib.md5(key_string.encode()).hexdigest()[:16]
            return key_hash

        return key_string

    def get(self, namespace: str, key: str) -> Optional[Any]:
        """
        Получить значение из кэша

        Args:
            namespace: Пространство имен
            key: Ключ

        Returns:
            Значение или None если не найдено/истекло
        """
        full_key = self._make_key(namespace, key)

        entry = self._cache.get(full_key)
        if not entry:
            self._misses += 1
            return None

        if entry.is_expired():
            self.delete(namespace, key)
            self._misses += 1
            return None

        self._hits += 1
        return entry.data

    def set(self, namespace: str, key: str, value: Any, ttl_seconds: int = 300):
        """
        Сохранить значение в кэш

        Args:
            namespace: Пространство имен
            key: Ключ
            value: Значение
            ttl_seconds: Время жизни в секундах
        """
        full_key = self._make_key(namespace, key)

        # Проверка на переполнение
        if len(self._cache) >= self._max_size:
            self._cleanup_expired()
            # Если все еще полно, удаляем oldest
            if len(self._cache) >= self._max_size:
                oldest_key = min(
                    self._cache.keys(),
                    key=lambda k: self._cache[k].created_at
                )
                del self._cache[oldest_key]

        entry = CacheEntry(value, ttl_seconds)
        self._cache[full_key] = entry

        # Добавляем в namespace
        if namespace in self._namespace_keys:
            self._namespace_keys[namespace].add(full_key)

        logger.debug(f"💾 Cached {full_key} (TTL: {ttl_seconds}s)")

    def delete(self, namespace: str, key: str) -> bool:
        """
        Удалить значение из кэша

        Returns:
            True если удалено, False если не найдено
        """
        full_key = self._make_key(namespace, key)

        if full_key in self._cache:
            del self._cache[full_key]
            if namespace in self._namespace_keys:
                self._namespace_keys[namespace].discard(full_key)
            return True

        return False

    def clear_namespace(self, namespace: str) -> int:
        """
        Очистить все кэши в namespace

        Returns:
            Количество удаленных записей
        """
        if namespace not in self._namespace_keys:
            return 0

        keys_to_delete = self._namespace_keys[namespace].copy()
        count = 0

        for key in keys_to_delete:
            if key in self._cache:
                del self._cache[key]
                count += 1

        self._namespace_keys[namespace].clear()
        logger.info(f"🧹 Cleared {count} entries from namespace '{namespace}'")

        return count

    def clear_all(self) -> int:
        """
        Очистить весь кэш

        Returns:
            Количество удаленных записей
        """
        count = len(self._cache)
        self._cache.clear()
        for keys in self._namespace_keys.values():
            keys.clear()

        logger.info(f"🧹 Cleared all cache ({count} entries)")
        return count

    def _cleanup_expired(self):
        """Очистить expired entries"""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug(f"🧹 Cleaned up {len(expired_keys)} expired entries")

    def get_stats(self) -> Dict[str, Any]:
        """
        Получить статистику кэша

        Returns:
            Dict со статистикой
        """
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0

        # Статистика по namespace
        namespace_stats = {}
        for ns, keys in self._namespace_keys.items():
            active_keys = [k for k in keys if k in self._cache and not self._cache[k].is_expired()]
            namespace_stats[ns] = len(active_keys)

        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_percent": round(hit_rate, 2),
            "namespaces": namespace_stats,
        }

    def cleanup_expired(self) -> int:
        """
        Публичный метод для очистки expired entries

        Returns:
            Количество удаленных записей
        """
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]

        for key in expired_keys:
            del self._cache[key]
            # Удаляем из namespace
            for ns_keys in self._namespace_keys.values():
                key.discard(key)

        return len(expired_keys)


# ==================== Global Cache Instance ====================

# Глобальный экземпляр кэша
cache = CacheService(max_size=5000)


# ==================== Decorator ====================

def cache_result(namespace: str = CacheNamespace.GENERAL, ttl_seconds: int = 300):
    """
    Декоратор для автоматического кэширования результатов async функций

    Args:
        namespace: Пространство имен для кэша
        ttl_seconds: Время жизни кэша в секундах

    Example:
        @cache_result(namespace=CacheNamespace.POLYMARKET, ttl_seconds=300)
        async def get_market_data(market_id: str):
            return {"data": "..."}
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Извлекаем ключ из аргументов
            cache_key = cache._extract_key(func, args, kwargs)

            # Пробуем получить из кэша
            cached_value = cache.get(namespace, cache_key)
            if cached_value is not None:
                logger.debug(f"✅ Cache hit: {func.__name__}:{cache_key}")
                return cached_value

            logger.debug(f"❌ Cache miss: {func.__name__}:{cache_key}")

            # Вызываем функцию
            try:
                result = await func(*args, **kwargs) if hasattr(func, '__await__') else func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in cached function {func.__name__}: {e}")
                raise

            # Сохраняем в кэш (если результат не None)
            if result is not None:
                cache.set(namespace, cache_key, result, ttl_seconds)

            return result

        return wrapper

    return decorator


# ==================== Helper Functions ====================

def get_cached(namespace: str, key: str) -> Optional[Any]:
    """
    Получить значение из кэша

    Args:
        namespace: Пространство имен
        key: Ключ

    Returns:
        Значение или None
    """
    return cache.get(namespace, key)


def set_cached(namespace: str, key: str, value: Any, ttl_seconds: int = 300):
    """
    Сохранить значение в кэш

    Args:
        namespace: Пространство имен
        key: Ключ
        value: Значение
        ttl_seconds: Время жизни в секундах
    """
    cache.set(namespace, key, value, ttl_seconds)


def invalidate_cached(namespace: str, key: str) -> bool:
    """
    Удалить значение из кэша

    Args:
        namespace: Пространство имен
        key: Ключ

    Returns:
        True если удалено
    """
    return cache.delete(namespace, key)


def clear_cache_namespace(namespace: str) -> int:
    """
    Очистить весь namespace

    Args:
        namespace: Пространство имен

    Returns:
        Количество удаленных записей
    """
    return cache.clear_namespace(namespace)


def get_cache_stats() -> Dict[str, Any]:
    """
    Получить статистику кэша

    Returns:
        Dict со статистикой
    """
    return cache.get_stats()


# ==================== Cache Routes (для админки) ====================

def create_cache_routes():
    """
    Создать FastAPI routes для управления кэшем

    Returns:
        APIRouter с endpoints для управления кэшем
    """
    try:
        from fastapi import APIRouter, Query, Depends
        from fastapi.responses import JSONResponse
        import os

        router = APIRouter(prefix="/api/cache", tags=["Cache"])

        # Admin Telegram ID
        ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "1972885597"))

        def check_admin(telegram_id: int):
            if telegram_id != ADMIN_TELEGRAM_ID:
                from fastapi import HTTPException
                raise HTTPException(status_code=403, detail="Admin only")
            return True

        @router.get("/stats")
        async def get_cache_statistics(
            telegram_id: int = Query(..., description="Telegram ID администратора")
        ):
            """Получить статистику кэша"""
            check_admin(telegram_id)
            return get_cache_stats()

        @router.post("/clear")
        async def clear_cache(
            namespace: Optional[str] = Query(None, description="Namespace для очистки"),
            telegram_id: int = Query(..., description="Telegram ID администратора")
        ):
            """Очистить кэш"""
            check_admin(telegram_id)

            if namespace:
                count = clear_cache_namespace(namespace)
                return {"cleared": count, "namespace": namespace}
            else:
                count = cache.clear_all()
                return {"cleared": count, "namespace": "all"}

        @router.delete("/invalidate")
        async def invalidate_cache_entry(
            namespace: str = Query(..., description="Namespace"),
            key: str = Query(..., description="Ключ для удаления"),
            telegram_id: int = Query(..., description="Telegram ID администратора")
        ):
            """Удалить конкретную запись из кэша"""
            check_admin(telegram_id)

            success = invalidate_cached(namespace, key)
            return {"success": success, "namespace": namespace, "key": key}

        return router

    except ImportError:
        logger.warning("FastAPI not available, skipping cache routes creation")
        return None
