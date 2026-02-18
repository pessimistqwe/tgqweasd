"""
PriceFeedService - Сервис получения цен из Binance WebSocket

Реализует:
- WebSocket подключение к Binance Stream
- Автоматическое переподключение при обрыве
- Кэширование последних цен в Redis (опционально)
- Подписка на несколько символов одновременно

Документация Binance WebSocket:
https://binance-docs.github.io/apidocs/spot/en/#kline-candlestick-streams
"""

import asyncio
import json
import logging
import websockets
from decimal import Decimal
from datetime import datetime
from typing import Dict, Optional, Callable, List, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class PriceUpdate:
    """Обновление цены"""
    symbol: str
    price: Decimal
    timestamp: datetime
    volume_24h: Optional[Decimal] = None
    price_change_24h: Optional[Decimal] = None
    price_change_pct_24h: Optional[Decimal] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "price": str(self.price),
            "timestamp": self.timestamp.isoformat(),
            "volume_24h": str(self.volume_24h) if self.volume_24h else None,
            "price_change_24h": str(self.price_change_24h) if self.price_change_24h else None,
            "price_change_pct_24h": str(self.price_change_pct_24h) if self.price_change_pct_24h else None,
        }


class BinanceWebSocketError(Exception):
    """Ошибка Binance WebSocket"""
    pass


class PriceFeedService:
    """
    Сервис для получения реальных цен из Binance

    Поддерживает:
    - Kline/Candlestick streams для исторических данных
    - Trade streams для реальных сделок
    - Ticker streams для тикеров 24h

    Пример использования:
        service = PriceFeedService()
        await service.start()
        price = await service.get_price("BTCUSDT")
    """

    # Binance WebSocket endpoints
    WS_BASE_URL = "wss://stream.binance.com:9443/ws"
    WS_TESTNET_URL = "wss://testnet.binance.vision/ws"

    # Реактивные параметры
    RECONNECT_DELAY = 5  # Задержка перед переподключением (сек)
    MAX_RECONNECT_ATTEMPTS = 10  # Максимум попыток переподключения
    PING_INTERVAL = 180  # Интервал ping (сек)
    MESSAGE_TIMEOUT = 30  # Таймаут получения сообщения (сек)

    def __init__(
        self,
        use_testnet: bool = False,
        cache_enabled: bool = True,
    ):
        """
        Инициализация сервиса

        Args:
            use_testnet: Использовать тестовую сеть
            cache_enabled: Включить кэширование цен
        """
        self.use_testnet = use_testnet
        self.cache_enabled = cache_enabled

        # Кэш цен: symbol -> PriceUpdate
        self._price_cache: Dict[str, PriceUpdate] = {}

        # WebSocket соединение
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._running = False
        self._reconnect_attempts = 0

        # Подписки: список символов
        self._subscriptions: List[str] = []

        # Callback для обработки обновлений
        self._on_price_update: Optional[Callable[[PriceUpdate], None]] = None

        # Задачи
        self._receive_task: Optional[asyncio.Task] = None
        self._ping_task: Optional[asyncio.Task] = None

    # ==================== Public API ====================

    async def start(self) -> None:
        """Запустить WebSocket подключение"""
        logger.info("🚀 Starting PriceFeedService...")
        self._running = True

        # Подключаемся
        await self._connect()

        # Запускаем задачу получения сообщений
        self._receive_task = asyncio.create_task(self._receive_loop())

        # Запускаем задачу ping
        self._ping_task = asyncio.create_task(self._ping_loop())

        logger.info("✅ PriceFeedService started")

    async def stop(self) -> None:
        """Остановить WebSocket подключение"""
        logger.info("🛑 Stopping PriceFeedService...")
        self._running = False

        # Отменяем задачи
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        if self._ping_task:
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass

        # Закрываем WebSocket
        if self._ws:
            await self._ws.close()

        logger.info("✅ PriceFeedService stopped")

    def set_on_price_update(self, callback: Callable[[PriceUpdate], None]) -> None:
        """
        Установить callback для обработки обновлений цен

        Args:
            callback: Функция которая вызывается при обновлении цены
        """
        self._on_price_update = callback

    async def subscribe(self, symbols: List[str]) -> None:
        """
        Подписаться на обновления цен

        Args:
            symbols: Список символов (например, ["BTCUSDT", "ETHUSDT"])
        """
        # Нормализуем символы (верхний регистр)
        symbols = [s.upper() for s in symbols]

        # Добавляем новые символы
        for symbol in symbols:
            if symbol not in self._subscriptions:
                self._subscriptions.append(symbol)

        # Переподключаемся с новыми подписками
        if self._ws:
            await self._resubscribe()

        logger.info(f"📡 Subscribed to: {symbols}")

    async def unsubscribe(self, symbols: List[str]) -> None:
        """
        Отписаться от обновлений цен

        Args:
            symbols: Список символов
        """
        symbols = [s.upper() for s in symbols]

        for symbol in symbols:
            if symbol in self._subscriptions:
                self._subscriptions.remove(symbol)

        logger.info(f"📡 Unsubscribed from: {symbols}")

    def get_price(self, symbol: str) -> Optional[PriceUpdate]:
        """
        Получить последнюю цену из кэша

        Args:
            symbol: Символ (например, "BTCUSDT")

        Returns:
            PriceUpdate или None если цена не найдена
        """
        symbol = symbol.upper()
        return self._price_cache.get(symbol)

    def get_price_decimal(self, symbol: str) -> Optional[Decimal]:
        """
        Получить цену как Decimal

        Args:
            symbol: Символ

        Returns:
            Decimal цена или None
        """
        price_update = self.get_price(symbol)
        return price_update.price if price_update else None

    def get_all_prices(self) -> Dict[str, PriceUpdate]:
        """
        Получить все цены из кэша

        Returns:
            Dict symbol -> PriceUpdate
        """
        return self._price_cache.copy()

    # ==================== Private Methods ====================

    async def _connect(self) -> None:
        """Подключиться к Binance WebSocket"""
        base_url = self.WS_TESTNET_URL if self.use_testnet else self.WS_BASE_URL

        # Формируем URL для подписок
        # Для нескольких символов используем комбинированный стрим
        if self._subscriptions:
            streams = [f"{s.lower()}@trade" for s in self._subscriptions]
            stream_path = "/".join(streams)
            ws_url = f"{base_url}/stream?streams={stream_path}"
        else:
            # Подписка на все трейды (не рекомендуется для production)
            ws_url = f"{base_url}"

        logger.info(f"🔌 Connecting to Binance WebSocket: {ws_url}")

        try:
            self._ws = await websockets.connect(
                ws_url,
                ping_interval=self.PING_INTERVAL,
                ping_timeout=10,
                close_timeout=5,
            )
            self._reconnect_attempts = 0
            logger.info("✅ Connected to Binance WebSocket")
        except Exception as e:
            logger.error(f"❌ Connection error: {e}")
            raise BinanceWebSocketError(f"Failed to connect: {e}")

    async def _resubscribe(self) -> None:
        """Переподписаться после переподключения"""
        if not self._ws or not self._subscriptions:
            return

        # Отправляем подписку
        streams = [f"{s.lower()}@trade" for s in self._subscriptions]

        subscribe_message = {
            "method": "SUBSCRIBE",
            "params": streams,
            "id": 1,
        }

        await self._ws.send(json.dumps(subscribe_message))
        logger.info(f"📡 Resubscribed to {len(streams)} streams")

    async def _receive_loop(self) -> None:
        """Цикл получения сообщений"""
        logger.info("📥 Starting receive loop")

        while self._running:
            try:
                if not self._ws:
                    await asyncio.sleep(1)
                    continue

                # Получаем сообщение с таймаутом
                try:
                    message = await asyncio.wait_for(
                        self._ws.recv(),
                        timeout=self.MESSAGE_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    # Нормальная ситуация - просто продолжаем
                    continue

                # Обрабатываем сообщение
                await self._handle_message(message)

            except asyncio.CancelledError:
                logger.info("📥 Receive loop cancelled")
                break
            except websockets.ConnectionClosed as e:
                logger.warning(f"📡 WebSocket connection closed: {e}")
                await self._reconnect()
            except Exception as e:
                logger.error(f"❌ Error in receive loop: {e}")
                await asyncio.sleep(1)

    async def _handle_message(self, message: str) -> None:
        """
        Обработать полученное сообщение

        Args:
            message: JSON сообщение от Binance
        """
        try:
            data = json.loads(message)

            # Binance может возвращать разные форматы:
            # 1. Комбинированный стрим: {"stream": "<name>", "data": {...}}
            # 2. Прямой стрим: {...}

            if "stream" in data and "data" in data:
                # Комбинированный стрим
                stream_data = data["data"]
            else:
                # Прямой стрим
                stream_data = data

            # Проверяем тип сообщения
            if "e" not in stream_data:
                # Неизвестный формат
                return

            event_type = stream_data["e"]

            if event_type == "trade":
                # Trade update
                await self._handle_trade(stream_data)
            elif event_type == "kline":
                # Kline/Candlestick update
                await self._handle_kline(stream_data)
            elif event_type == "24hrTicker":
                # 24hr Ticker update
                await self._handle_ticker(stream_data)

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse message: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def _handle_trade(self, data: Dict[str, Any]) -> None:
        """
        Обработать trade update

        Формат:
        {
            "e": "trade",
            "s": "BTCUSDT",
            "t": 12345,
            "p": "0.001",
            "q": "100",
            "T": 1234567890,
            "m": true
        }
        """
        symbol = data.get("s", "").upper()
        price_str = data.get("p", "0")
        timestamp_ms = data.get("T", 0)

        if not symbol or not price_str:
            return

        price = Decimal(price_str)
        timestamp = datetime.utcfromtimestamp(timestamp_ms / 1000)

        # Создаем обновление цены
        update = PriceUpdate(
            symbol=symbol,
            price=price,
            timestamp=timestamp,
        )

        # Обновляем кэш
        if self.cache_enabled:
            self._price_cache[symbol] = update

        # Вызываем callback
        if self._on_price_update:
            self._on_price_update(update)

    async def _handle_kline(self, data: Dict[str, Any]) -> None:
        """
        Обработать kline/candlestick update

        Формат:
        {
            "e": "kline",
            "s": "BTCUSDT",
            "k": {
                "t": 1234567890000,
                "T": 1234567895000,
                "s": "BTCUSDT",
                "i": "1m",
                "c": "0.001",
                "v": "1000"
            }
        }
        """
        kline = data.get("k", {})
        symbol = data.get("s", "").upper()
        price_str = kline.get("c", "0")  # Close price
        timestamp_ms = kline.get("t", 0)
        volume_str = kline.get("v", "0")

        if not symbol or not price_str:
            return

        price = Decimal(price_str)
        timestamp = datetime.utcfromtimestamp(timestamp_ms / 1000)
        volume = Decimal(volume_str) if volume_str else None

        update = PriceUpdate(
            symbol=symbol,
            price=price,
            timestamp=timestamp,
            volume_24h=volume,
        )

        if self.cache_enabled:
            self._price_cache[symbol] = update

        if self._on_price_update:
            self._on_price_update(update)

    async def _handle_ticker(self, data: Dict[str, Any]) -> None:
        """
        Обработать 24hr ticker update

        Формат:
        {
            "e": "24hrTicker",
            "s": "BTCUSDT",
            "c": "0.001",
            "v": "1000",
            "P": "2.5",
            "p": "0.000025"
        }
        """
        symbol = data.get("s", "").upper()
        price_str = data.get("c", "0")  # Close price
        volume_str = data.get("v", "0")
        change_pct_str = data.get("P", "0")  # Price change percent

        if not symbol or not price_str:
            return

        price = Decimal(price_str)
        volume = Decimal(volume_str) if volume_str else None
        change_pct = Decimal(change_pct_str) if change_pct_str else None

        update = PriceUpdate(
            symbol=symbol,
            price=price,
            timestamp=datetime.utcnow(),
            volume_24h=volume,
            price_change_pct_24h=change_pct,
        )

        if self.cache_enabled:
            self._price_cache[symbol] = update

        if self._on_price_update:
            self._on_price_update(update)

    async def _reconnect(self) -> None:
        """Переподключиться к WebSocket"""
        if not self._running:
            return

        if self._reconnect_attempts >= self.MAX_RECONNECT_ATTEMPTS:
            logger.error("❌ Max reconnection attempts reached")
            self._running = False
            return

        self._reconnect_attempts += 1

        logger.info(
            f"🔄 Reconnecting (attempt {self._reconnect_attempts}/{self.MAX_RECONNECT_ATTEMPTS})..."
        )

        # Ждём перед переподключением
        await asyncio.sleep(self.RECONNECT_DELAY)

        # Закрываем старое соединение
        if self._ws:
            await self._ws.close()

        # Подключаемся заново
        try:
            await self._connect()
            await self._resubscribe()
            logger.info("✅ Reconnected successfully")
        except Exception as e:
            logger.error(f"❌ Reconnection failed: {e}")

    async def _ping_loop(self) -> None:
        """Отправлять ping для поддержания соединения"""
        logger.info("🏓 Starting ping loop")

        while self._running:
            try:
                await asyncio.sleep(self.PING_INTERVAL)

                if self._ws and self._ws.open:
                    # Отправляем ping
                    pong = await self._ws.ping()
                    await asyncio.wait_for(pong, timeout=10)
                    logger.debug("🏓 Ping/Pong OK")

            except asyncio.CancelledError:
                break
            except asyncio.TimeoutError:
                logger.warning("⚠️ Ping timeout - connection may be stale")
                await self._reconnect()
            except Exception as e:
                logger.error(f"❌ Ping error: {e}")


# ==================== Helper Functions ====================

async def get_binance_price(symbol: str, use_testnet: bool = False) -> Optional[Decimal]:
    """
    Быстро получить цену актива (REST API)

    Args:
        symbol: Символ (например, "BTCUSDT")
        use_testnet: Использовать тестовую сеть

    Returns:
        Decimal цена или None
    """
    import requests

    base_url = "https://testnet.binance.vision" if use_testnet else "https://api.binance.com"

    try:
        symbol = symbol.upper()
        if not symbol.endswith('USDT'):
            symbol = symbol + 'USDT'

        response = requests.get(
            f"{base_url}/api/v3/ticker/price",
            params={"symbol": symbol},
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            price = Decimal(data.get('price', '0'))
            return price if price > 0 else None

        return None

    except Exception as e:
        logger.warning(f"Error getting Binance price for {symbol}: {e}")
        return None


# ==================== Singleton ====================

# Глобальный экземпляр сервиса
_price_feed_service: Optional[PriceFeedService] = None


def get_price_feed_service() -> Optional[PriceFeedService]:
    """Получить глобальный экземпляр сервиса"""
    return _price_feed_service


async def init_price_feed_service(
    symbols: List[str] = None,
    use_testnet: bool = False,
) -> PriceFeedService:
    """
    Инициализировать и запустить глобальный сервис

    Args:
        symbols: Список символов для подписки
        use_testnet: Использовать тестовую сеть

    Returns:
        PriceFeedService
    """
    global _price_feed_service

    if _price_feed_service:
        await _price_feed_service.stop()

    _price_feed_service = PriceFeedService(use_testnet=use_testnet)
    await _price_feed_service.start()

    if symbols:
        await _price_feed_service.subscribe(symbols)

    return _price_feed_service
