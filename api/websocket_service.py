"""
WebSocket Service - WebSocket клиент для Polymarket CLOB

Функционал:
- Подключение к wss://clob.polymarket.com/ws
- Подписка на каналы l2:{token_id}, trades:{token_id}
- Автообновление цен в БД
- Автоматический переподключение при разрыве
- Обработка ордеров (L2) и сделок (trades)

Использование:
    service = PolymarketWebSocketService()
    await service.connect()
    await service.subscribe_to_market("market_id")
"""

import asyncio
import json
import logging
from typing import Optional, Dict, List, Callable, Any, Set
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ==================== Configuration ====================

POLYMARKET_WS_URL = "wss://clob.polymarket.com/ws"
RECONNECT_DELAY_SECONDS = 5
MAX_RECONNECT_ATTEMPTS = 10
HEARTBEAT_INTERVAL_SECONDS = 30


# ==================== Data Classes ====================

@dataclass
class OrderBookUpdate:
    """Обновление стакана ордеров"""
    token_id: str
    bids: List[Dict[str, Any]] = field(default_factory=list)
    asks: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def best_bid(self) -> Optional[float]:
        """Лучшая цена покупки"""
        return float(self.bids[0]["price"]) if self.bids else None

    @property
    def best_ask(self) -> Optional[float]:
        """Лучшая цена продажи"""
        return float(self.asks[0]["price"]) if self.asks else None

    @property
    def mid_price(self) -> Optional[float]:
        """Средняя цена"""
        if self.best_bid and self.best_ask:
            return (self.best_bid + self.best_ask) / 2
        return None


@dataclass
class TradeUpdate:
    """Обновление о сделке"""
    token_id: str
    price: float
    size: float
    side: str  # "buy" или "sell"
    timestamp: datetime = field(default_factory=datetime.utcnow)


# ==================== WebSocket Service ====================

class PolymarketWebSocketService:
    """
    WebSocket клиент для Polymarket CLOB

    Поддерживает:
    - Подключение к CLOB WebSocket
    - Подписку на L2 (стакан) и trades (сделки)
    - Автоматический переподключение
    - Колбэки для обновлений
    """

    def __init__(self, db_session_factory=None):
        """
        Инициализация сервиса

        Args:
            db_session_factory: Фабрика сессий БД для обновления цен
        """
        self.db_session_factory = db_session_factory
        self.ws = None
        self.is_connected = False
        self.is_running = False
        self.subscribed_tokens: Set[str] = set()
        self.reconnect_attempts = 0
        self.last_message_time: Optional[datetime] = None

        # Колбэки
        self.on_orderbook_update: Optional[Callable[[OrderBookUpdate], None]] = None
        self.on_trade_update: Optional[Callable[[TradeUpdate], None]] = None
        self.on_price_change: Optional[Callable[[str, float], None]] = None

        # Задачи
        self._receive_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None

        # Статистика
        self.messages_received = 0
        self.errors_count = 0

    async def connect(self):
        """
        Подключиться к WebSocket

        Raises:
            Exception: Если не удалось подключиться
        """
        try:
            # Импортируем websockets только при необходимости
            import websockets
            from websockets.exceptions import ConnectionClosed, InvalidURI

            logger.info(f"🔌 Connecting to Polymarket WebSocket: {POLYMARKET_WS_URL}")

            self.ws = await websockets.connect(
                POLYMARKET_WS_URL,
                ping_interval=HEARTBEAT_INTERVAL_SECONDS,
                ping_timeout=10,
                close_timeout=5,
            )

            self.is_connected = True
            self.reconnect_attempts = 0
            self.last_message_time = datetime.utcnow()

            logger.info("✅ Connected to Polymarket WebSocket")

            # Запускаем heartbeat
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        except ImportError:
            logger.error("❌ websockets library not installed. Run: pip install websockets")
            raise
        except Exception as e:
            logger.error(f"❌ WebSocket connection error: {e}")
            self.is_connected = False
            raise

    async def disconnect(self):
        """Отключиться от WebSocket"""
        self.is_running = False
        self.is_connected = False

        # Отменяем задачи
        for task in [self._receive_task, self._heartbeat_task, self._reconnect_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Закрываем соединение
        if self.ws:
            await self.ws.close()
            self.ws = None

        logger.info("🔌 Disconnected from Polymarket WebSocket")

    async def subscribe_to_market(self, token_id: str):
        """
        Подписаться на обновления рынка

        Args:
            token_id: ID токена (рынка)
        """
        if not self.is_connected:
            logger.warning("⚠️ Cannot subscribe: not connected")
            return

        if token_id in self.subscribed_tokens:
            logger.debug(f"Already subscribed to {token_id}")
            return

        # Подписка на L2 (стакан ордеров)
        l2_channel = f"l2:{token_id}"
        await self._send_message({
            "event": "sub",
            "topic": l2_channel,
        })

        # Подписка на trades (сделки)
        trades_channel = f"trades:{token_id}"
        await self._send_message({
            "event": "sub",
            "topic": trades_channel,
        })

        self.subscribed_tokens.add(token_id)
        logger.info(f"📡 Subscribed to market: {token_id} (channels: {l2_channel}, {trades_channel})")

    async def unsubscribe_from_market(self, token_id: str):
        """
        Отписаться от обновлений рынка

        Args:
            token_id: ID токена
        """
        if not self.is_connected:
            return

        # Отписка от L2
        l2_channel = f"l2:{token_id}"
        await self._send_message({
            "event": "unsub",
            "topic": l2_channel,
        })

        # Отписка от trades
        trades_channel = f"trades:{token_id}"
        await self._send_message({
            "event": "unsub",
            "topic": trades_channel,
        })

        self.subscribed_tokens.discard(token_id)
        logger.info(f"🚫 Unsubscribed from market: {token_id}")

    async def start(self, token_ids: List[str]):
        """
        Запустить WebSocket клиент

        Args:
            token_ids: Список ID токенов для подписки
        """
        self.is_running = True

        # Подключаемся
        try:
            await self.connect()
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return

        # Подписываемся на все токены
        for token_id in token_ids:
            await self.subscribe_to_market(token_id)

        # Запускаем получение сообщений
        self._receive_task = asyncio.create_task(self._receive_loop())

        logger.info(f"🚀 WebSocket service started with {len(token_ids)} markets")

    async def _send_message(self, message: Dict[str, Any]):
        """Отправить сообщение в WebSocket"""
        if not self.ws or not self.is_connected:
            return

        try:
            await self.ws.send(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending message: {e}")

    async def _receive_loop(self):
        """Цикл получения сообщений"""
        if not self.ws:
            return

        try:
            async for message in self.ws:
                if not self.is_running:
                    break

                self.last_message_time = datetime.utcnow()
                self.messages_received += 1

                try:
                    await self._handle_message(message)
                except Exception as e:
                    self.errors_count += 1
                    logger.error(f"Error handling message: {e}", exc_info=True)

        except asyncio.CancelledError:
            logger.info("Receive loop cancelled")
        except Exception as e:
            logger.error(f"Receive loop error: {e}", exc_info=True)
            self.errors_count += 1

            # Пытаемся переподключиться
            if self.reconnect_attempts < MAX_RECONNECT_ATTEMPTS:
                await self._reconnect()

    async def _handle_message(self, raw_message: str):
        """
        Обработать полученное сообщение

        Args:
            raw_message: Сырое сообщение от WebSocket
        """
        try:
            data = json.loads(raw_message)

            # Определяем тип сообщения
            event_type = data.get("event")
            topic = data.get("topic", "")

            # L2 update (стакан ордеров)
            if event_type == "l2" or topic.startswith("l2:"):
                await self._handle_l2_update(data, topic)

            # Trade update (сделка)
            elif event_type == "trade" or topic.startswith("trades:"):
                await self._handle_trade_update(data, topic)

            # Subscription confirmation
            elif event_type == "sub" or event_type == "unsub":
                logger.debug(f"Subscription update: {data}")

            # Heartbeat/pong
            elif event_type == "pong":
                logger.debug("Received pong")

            else:
                logger.debug(f"Unknown message type: {event_type}")

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
        except Exception as e:
            logger.error(f"Message handling error: {e}", exc_info=True)

    async def _handle_l2_update(self, data: Dict[str, Any], topic: str):
        """
        Обработать обновление стакана

        Args:
            data: Данные сообщения
            topic: Топик (l2:{token_id})
        """
        # Извлекаем token_id из топика
        token_id = topic.split(":")[1] if ":" in topic else data.get("token_id")

        if not token_id:
            return

        # Получаем bids и asks
        bids = data.get("bids", data.get("data", {}).get("bids", []))
        asks = data.get("asks", data.get("data", {}).get("asks", []))

        if not bids and not asks:
            return

        update = OrderBookUpdate(
            token_id=token_id,
            bids=bids if isinstance(bids, list) else [],
            asks=asks if isinstance(asks, list) else [],
        )

        # Вызываем колбэк
        if self.on_orderbook_update:
            self.on_orderbook_update(update)

        # Обновляем цену в БД
        if update.mid_price and self.db_session_factory:
            await self._update_price_in_db(token_id, update.mid_price)

        # Колбэк на изменение цены
        if self.on_price_change and update.mid_price:
            self.on_price_change(token_id, update.mid_price)

    async def _handle_trade_update(self, data: Dict[str, Any], topic: str):
        """
        Обзовать обновление о сделке

        Args:
            data: Данные сообщения
            topic: Топик (trades:{token_id})
        """
        # Извлекаем token_id
        token_id = topic.split(":")[1] if ":" in topic else data.get("token_id")

        if not token_id:
            return

        # Получаем данные о сделке
        trades_data = data.get("data", data)
        price = float(trades_data.get("price", 0))
        size = float(trades_data.get("size", 0))
        side = trades_data.get("side", "unknown")

        if price <= 0:
            return

        update = TradeUpdate(
            token_id=token_id,
            price=price,
            size=size,
            side=side,
        )

        # Вызываем колбэк
        if self.on_trade_update:
            self.on_trade_update(update)

        # Обновляем цену в БД (по последней сделке)
        if self.db_session_factory:
            await self._update_price_in_db(token_id, price)

        # Колбэк на изменение цены
        if self.on_price_change:
            self.on_price_change(token_id, price)

    async def _update_price_in_db(self, token_id: str, price: float):
        """
        Обновить цену в базе данных

        Args:
            token_id: ID токена (рынка)
            price: Новая цена
        """
        if not self.db_session_factory:
            return

        try:
            # Импортируем модели
            try:
                from .models import Event, EventOption
            except ImportError:
                from models import Event, EventOption

            db = self.db_session_factory()

            # Находим событие по polymarket_id
            event = db.query(Event).filter(Event.polymarket_id == token_id).first()

            if event and event.event_options:
                # Обновляем цену первого опциона (Yes)
                option = event.event_options[0]
                old_price = option.current_price

                # Конвертируем цену из формата Polymarket (0-100) в наш (0-1)
                normalized_price = price / 100 if price > 1 else price
                option.current_price = normalized_price

                db.commit()

                price_change = ((normalized_price - old_price) / old_price * 100) if old_price > 0 else 0

                logger.debug(
                    f"💾 Updated price for event {event.id}: "
                    f"{old_price:.4f} → {normalized_price:.4f} ({price_change:+.2f}%)"
                )

            db.close()

        except Exception as e:
            logger.error(f"Error updating price in DB: {e}", exc_info=True)

    async def _heartbeat_loop(self):
        """Цикл отправки heartbeat"""
        while self.is_running and self.is_connected:
            try:
                await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)

                # Проверяем таймаут
                if self.last_message_time:
                    time_since_last = (datetime.utcnow() - self.last_message_time).total_seconds()
                    if time_since_last > HEARTBEAT_INTERVAL_SECONDS * 3:
                        logger.warning(f"⚠️ No messages for {time_since_last:.0f}s, reconnecting...")
                        await self._reconnect()
                        continue

                # Отправляем ping
                await self._send_message({"event": "ping"})

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

    async def _reconnect(self):
        """Переподключиться к WebSocket"""
        if self._reconnect_task and not self._reconnect_task.done():
            return

        self._reconnect_task = asyncio.create_task(self._do_reconnect())

    async def _do_reconnect(self):
        """Выполнить переподключение"""
        while self.is_running and self.reconnect_attempts < MAX_RECONNECT_ATTEMPTS:
            self.reconnect_attempts += 1

            logger.info(
                f"🔄 Reconnecting... (attempt {self.reconnect_attempts}/{MAX_RECONNECT_ATTEMPTS})"
            )

            try:
                await asyncio.sleep(RECONNECT_DELAY_SECONDS)
                await self.connect()

                # Восстанавливаем подписки
                for token_id in list(self.subscribed_tokens):
                    await self.subscribe_to_market(token_id)

                logger.info("✅ Reconnected successfully")
                return

            except Exception as e:
                logger.error(f"Reconnect attempt {self.reconnect_attempts} failed: {e}")

        logger.error("❌ Max reconnect attempts reached")
        self.is_connected = False
        self.is_running = False

    def get_stats(self) -> Dict[str, Any]:
        """
        Получить статистику сервиса

        Returns:
            Dict со статистикой
        """
        return {
            "is_connected": self.is_connected,
            "is_running": self.is_running,
            "subscribed_tokens": list(self.subscribed_tokens),
            "messages_received": self.messages_received,
            "errors_count": self.errors_count,
            "reconnect_attempts": self.reconnect_attempts,
            "last_message_time": self.last_message_time.isoformat() if self.last_message_time else None,
        }


# ==================== Global Service Instance ====================

# Глобальный экземпляр сервиса
_ws_service: Optional[PolymarketWebSocketService] = None


def get_websocket_service() -> Optional[PolymarketWebSocketService]:
    """Получить глобальный экземпляр сервиса"""
    return _ws_service


async def init_websocket_service(db_session_factory=None, token_ids: Optional[List[str]] = None):
    """
    Инициализировать и запустить WebSocket сервис

    Args:
        db_session_factory: Фабрика сессий БД
        token_ids: Список токенов для подписки
    """
    global _ws_service

    if _ws_service and _ws_service.is_running:
        logger.warning("WebSocket service already running")
        return

    _ws_service = PolymarketWebSocketService(db_session_factory)

    if token_ids:
        await _ws_service.start(token_ids)


async def stop_websocket_service():
    """Остановить WebSocket сервис"""
    global _ws_service

    if _ws_service:
        await _ws_service.disconnect()
        _ws_service = None
        logger.info("WebSocket service stopped")


# ==================== FastAPI Routes (для админки) ====================

def create_websocket_routes():
    """
    Создать FastAPI routes для управления WebSocket

    Returns:
        APIRouter с endpoints
    """
    try:
        from fastapi import APIRouter, Query, HTTPException
        import os

        router = APIRouter(prefix="/api/websocket", tags=["WebSocket"])

        # Admin Telegram ID
        ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "1972885597"))

        def check_admin(telegram_id: int):
            if telegram_id != ADMIN_TELEGRAM_ID:
                raise HTTPException(status_code=403, detail="Admin only")
            return True

        @router.get("/stats")
        async def get_websocket_stats(
            telegram_id: int = Query(..., description="Telegram ID администратора")
        ):
            """Получить статистику WebSocket сервиса"""
            check_admin(telegram_id)

            service = get_websocket_service()
            if not service:
                return {"status": "not_running"}

            return {
                "status": "running",
                **service.get_stats()
            }

        @router.post("/subscribe")
        async def subscribe_to_token(
            token_id: str = Query(..., description="Token ID для подписки"),
            telegram_id: int = Query(..., description="Telegram ID администратора")
        ):
            """Подписаться на обновления токена"""
            check_admin(telegram_id)

            service = get_websocket_service()
            if not service or not service.is_connected:
                raise HTTPException(status_code=503, detail="WebSocket not connected")

            await service.subscribe_to_market(token_id)
            return {"success": True, "token_id": token_id}

        @router.post("/unsubscribe")
        async def unsubscribe_from_token(
            token_id: str = Query(..., description="Token ID для отписки"),
            telegram_id: int = Query(..., description="Telegram ID администратора")
        ):
            """Отписаться от обновлений токена"""
            check_admin(telegram_id)

            service = get_websocket_service()
            if not service or not service.is_connected:
                raise HTTPException(status_code=503, detail="WebSocket not connected")

            await service.unsubscribe_from_market(token_id)
            return {"success": True, "token_id": token_id}

        return router

    except ImportError:
        logger.warning("FastAPI not available, skipping websocket routes creation")
        return None
