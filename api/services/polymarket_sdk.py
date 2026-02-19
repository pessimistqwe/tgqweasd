"""
Polymarket SDK Wrapper Module

Этот модуль предоставляет обёртку над официальным Python SDK Polymarket CLOB.
Статус: Prepared for Integration (требуется API key для активации)

Установка зависимостей:
    pip install py-clob-client

Требуемые переменные окружения:
    POLYMARKET_API_KEY - API ключ от Polymarket
    POLYMARKET_SECRET - API секрет
    POLYMARKET_PASSPHRASE - API passphrase
    POLYMARKET_PRIVATE_KEY - Приватный ключ кошелька (для подписи)
    POLYMARKET_CHAIN_ID - ID сети (137 для Polygon mainnet)

Пример использования:
    from api.services.polymarket_sdk import PolymarketSDK
    
    sdk = PolymarketSDK()
    if sdk.is_configured():
        markets = sdk.get_markets()
        order = sdk.place_order(token_id="123", price=0.5, size=10, side="BUY")
"""

import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Попытка импорта py-clob-client
try:
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import OrderArgs, OrderType, ApiCreds
    from py_clob_client.order_builder.constants import BUY, SELL
    PY_CLOB_AVAILABLE = True
    logger.info("✅ py-clob-client imported successfully")
except ImportError:
    PY_CLOB_AVAILABLE = False
    logger.warning("⚠️ py-clob-client not installed. Run: pip install py-clob-client")


class PolymarketSDKError(Exception):
    """Базовое исключение для Polymarket SDK"""
    pass


class PolymarketNotConfiguredError(PolymarketSDKError):
    """Исключение когда SDK не настроен (нет API ключей)"""
    pass


class PolymarketSDK:
    """
    Wrapper над официальным Polymarket CLOB SDK
    
    Предоставляет методы для:
    - Получения данных рынков (markets, events, prices)
    - Размещения и отмены ордеров
    - Получения информации о позициях пользователя
    - Подписи транзакций (через Builder SDK)
    - Безгазовых транзакций (через Relayer SDK)
    
    Статус: Prepared for Integration
    Для активации необходимо настроить переменные окружения
    """
    
    def __init__(self, host: str = "https://clob.polymarket.com"):
        """
        Инициализация SDK
        
        Args:
            host: URL CLOB API (по умолчанию production)
        """
        self.host = host
        self.client: Optional[ClobClient] = None
        self._configured = False
        
        # Загрузка конфигурации из env
        self.api_key = os.getenv("POLYMARKET_API_KEY")
        self.api_secret = os.getenv("POLYMARKET_SECRET")
        self.api_passphrase = os.getenv("POLYMARKET_PASSPHRASE")
        self.private_key = os.getenv("POLYMARKET_PRIVATE_KEY")
        self.chain_id = int(os.getenv("POLYMARKET_CHAIN_ID", "137"))
        self.signature_type = int(os.getenv("POLYMARKET_SIGNATURE_TYPE", "0"))
        self.funder = os.getenv("POLYMARKET_FUNDER")
        
        # Проверяем конфигурацию
        self._check_configuration()
    
    def _check_configuration(self) -> None:
        """Проверяет наличие необходимых API ключей"""
        has_keys = all([
            self.api_key,
            self.api_secret,
            self.api_passphrase,
            self.private_key
        ])
        
        if has_keys and PY_CLOB_AVAILABLE:
            self._configured = True
            logger.info("✅ PolymarketSDK configured successfully")
        else:
            self._configured = False
            if not PY_CLOB_AVAILABLE:
                logger.warning("⚠️ py-clob-client package not installed")
            else:
                logger.warning("⚠️ Polymarket API keys not configured")
    
    def is_configured(self) -> bool:
        """
        Проверяет настроено ли SDK
        
        Returns:
            bool: True если SDK готов к работе
        """
        return self._configured
    
    def _ensure_configured(self) -> None:
        """Гарантирует что SDK настроен, иначе выбрасывает исключение"""
        if not self._configured:
            raise PolymarketNotConfiguredError(
                "Polymarket SDK not configured. "
                "Please set POLYMARKET_API_KEY, POLYMARKET_SECRET, "
                "POLYMARKET_PASSPHRASE, and POLYMARKET_PRIVATE_KEY environment variables."
            )
    
    def _get_client(self) -> ClobClient:
        """
        Получает или создаёт CLOB клиента
        
        Returns:
            ClobClient: Настроенный клиент
            
        Raises:
            PolymarketNotConfiguredError: Если SDK не настроен
        """
        self._ensure_configured()
        
        if self.client is None:
            try:
                from py_clob_client.client import ClobClient
                
                self.client = ClobClient(
                    host=self.host,
                    key=self.private_key,
                    chain_id=self.chain_id,
                    signature_type=self.signature_type,
                    funder=self.funder if self.signature_type != 0 else None
                )
                
                # Устанавливаем API credentials
                api_creds = ApiCreds(
                    api_key=self.api_key,
                    api_secret=self.api_secret,
                    api_passphrase=self.api_passphrase
                )
                self.client.set_api_creds(api_creds)
                
                logger.info(f"✅ ClobClient initialized for chain_id={self.chain_id}")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize ClobClient: {e}")
                raise PolymarketSDKError(f"Failed to initialize client: {e}")
        
        return self.client
    
    # ==================== MARKET DATA ====================
    
    def get_markets(self, limit: int = 100, active: bool = True) -> List[Dict[str, Any]]:
        """
        Получить список рынков
        
        Args:
            limit: Максимальное количество рынков
            active: Только активные рынки
            
        Returns:
            Список словарей с данными рынков
            
        Raises:
            PolymarketNotConfiguredError: Если SDK не настроен
        """
        self._ensure_configured()
        
        try:
            client = self._get_client()
            markets = client.get_markets()
            
            # Фильтрация
            if active:
                markets = [m for m in markets if m.get('active', True)]
            
            return markets[:limit]
            
        except Exception as e:
            logger.error(f"❌ Error fetching markets: {e}")
            raise PolymarketSDKError(f"Failed to fetch markets: {e}")
    
    def get_market(self, market_id: str) -> Optional[Dict[str, Any]]:
        """
        Получить данные конкретного рынка
        
        Args:
            market_id: ID рынка
            
        Returns:
            Данные рынка или None
        """
        self._ensure_configured()
        
        try:
            client = self._get_client()
            return client.get_market(market_id)
        except Exception as e:
            logger.error(f"❌ Error fetching market {market_id}: {e}")
            return None
    
    def get_orderbook(self, token_id: str) -> Dict[str, Any]:
        """
        Получить стакан заявок для токена
        
        Args:
            token_id: ID токена
            
        Returns:
            Стакан с bids и asks
        """
        self._ensure_configured()
        
        try:
            client = self._get_client()
            return client.get_orderbook(token_id)
        except Exception as e:
            logger.error(f"❌ Error fetching orderbook for {token_id}: {e}")
            return {"bids": [], "asks": []}
    
    def get_price(self, token_id: str) -> Optional[float]:
        """
        Получить текущую цену токена
        
        Args:
            token_id: ID токена
            
        Returns:
            Цена токена или None
        """
        self._ensure_configured()
        
        try:
            client = self._get_client()
            return client.get_price(token_id)
        except Exception as e:
            logger.error(f"❌ Error fetching price for {token_id}: {e}")
            return None
    
    def get_prices_history(self, token_id: str, resolution: str = "hour", limit: int = 168) -> List[Dict]:
        """
        Получить историю цен
        
        Args:
            token_id: ID токена
            resolution: Разрешение ('minute', 'hour', 'day', 'week')
            limit: Количество точек данных
            
        Returns:
            Список свечей [timestamp, open, high, low, close, volume]
        """
        self._ensure_configured()
        
        try:
            client = self._get_client()
            return client.get_prices_history(token_id, resolution, limit)
        except Exception as e:
            logger.error(f"❌ Error fetching price history for {token_id}: {e}")
            return []
    
    # ==================== ORDERS ====================
    
    def place_order(
        self,
        token_id: str,
        price: float,
        size: float,
        side: str = "BUY",
        order_type: str = "GTC"
    ) -> Optional[Dict[str, Any]]:
        """
        Разместить ордер
        
        Args:
            token_id: ID токена
            price: Цена ордера (0.0 - 1.0)
            size: Размер ордера (количество токенов)
            side: Сторона ордера ('BUY' или 'SELL')
            order_type: Тип ордера ('GTC', 'GTD', 'FOK')
            
        Returns:
            Данные размещённого ордера или None
            
        Raises:
            PolymarketNotConfiguredError: Если SDK не настроен
        """
        self._ensure_configured()
        
        try:
            client = self._get_client()
            
            # Определяем сторону
            clob_side = BUY if side.upper() == "BUY" else SELL
            
            # Создаём аргументы ордера
            order_args = OrderArgs(
                price=price,
                size=size,
                side=clob_side,
                token_id=token_id
            )
            
            # Подписываем ордер
            signed_order = client.create_order(order_args)
            
            # Определяем тип ордера
            clob_order_type = OrderType.GTC
            if order_type.upper() == "GTD":
                clob_order_type = OrderType.GTD
            elif order_type.upper() == "FOK":
                clob_order_type = OrderType.FOK
            
            # Размещаем ордер
            resp = client.post_order(signed_order, clob_order_type)
            
            logger.info(f"✅ Order placed: {resp.get('orderID', 'unknown')}")
            return resp
            
        except Exception as e:
            logger.error(f"❌ Error placing order: {e}")
            raise PolymarketSDKError(f"Failed to place order: {e}")
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Отменить ордер
        
        Args:
            order_id: ID ордера
            
        Returns:
            True если успешно
        """
        self._ensure_configured()
        
        try:
            client = self._get_client()
            resp = client.cancel_order(order_id)
            logger.info(f"✅ Order cancelled: {order_id}")
            return resp.get('success', False)
        except Exception as e:
            logger.error(f"❌ Error cancelling order {order_id}: {e}")
            return False
    
    def cancel_all_orders(self) -> int:
        """
        Отменить все ордера
        
        Returns:
            Количество отменённых ордеров
        """
        self._ensure_configured()
        
        try:
            client = self._get_client()
            resp = client.cancel_all()
            cancelled = len(resp.get('orderIDs', []))
            logger.info(f"✅ Cancelled {cancelled} orders")
            return cancelled
        except Exception as e:
            logger.error(f"❌ Error cancelling all orders: {e}")
            return 0
    
    def get_orders(self, market_id: Optional[str] = None) -> List[Dict]:
        """
        Получить ордера пользователя
        
        Args:
            market_id: Опционально фильтр по рынку
            
        Returns:
            Список ордеров
        """
        self._ensure_configured()
        
        try:
            client = self._get_client()
            orders = client.get_orders()
            
            if market_id:
                orders = [o for o in orders if o.get('market') == market_id]
            
            return orders
        except Exception as e:
            logger.error(f"❌ Error fetching orders: {e}")
            return []
    
    # ==================== POSITIONS ====================
    
    def get_positions(self) -> List[Dict]:
        """
        Получить текущие позиции пользователя
        
        Returns:
            Список позиций
        """
        self._ensure_configured()
        
        try:
            client = self._get_client()
            return client.get_positions()
        except Exception as e:
            logger.error(f"❌ Error fetching positions: {e}")
            return []
    
    def get_balance(self, token_id: Optional[str] = None) -> Dict[str, float]:
        """
        Получить баланс пользователя
        
        Args:
            token_id: Опционально ID токена
            
        Returns:
            Словарь с балансами {token_id: amount}
        """
        self._ensure_configured()
        
        try:
            client = self._get_client()
            balances = client.get_balances()
            
            if token_id:
                return {token_id: balances.get(token_id, 0.0)}
            
            return balances
        except Exception as e:
            logger.error(f"❌ Error fetching balances: {e}")
            return {}
    
    # ==================== UTILITY ====================
    
    def get_server_time(self) -> Optional[datetime]:
        """
        Получить время сервера
        
        Returns:
            Время сервера или None
        """
        try:
            client = self._get_client() if self._configured else None
            if client:
                return client.get_time()
            return None
        except Exception as e:
            logger.error(f"❌ Error fetching server time: {e}")
            return None
    
    def get_fee_rate(self) -> float:
        """
        Получить текущую ставку комиссии
        
        Returns:
            Ставка комиссии (в bps)
        """
        try:
            client = self._get_client() if self._configured else None
            if client:
                return client.get_fee_rate()
            return 0.0
        except Exception as e:
            logger.error(f"❌ Error fetching fee rate: {e}")
            return 0.0
    
    def get_tick_size(self, token_id: str) -> float:
        """
        Получить размер шага цены для токена
        
        Args:
            token_id: ID токена
            
        Returns:
            Tick size
        """
        try:
            client = self._get_client() if self._configured else None
            if client:
                return client.get_tick_size(token_id)
            return 0.01
        except Exception as e:
            logger.error(f"❌ Error fetching tick size for {token_id}: {e}")
            return 0.01
    
    # ==================== BUILDER SDK (Placeholder) ====================
    
    def sign_transaction(self, transaction: Dict) -> Optional[str]:
        """
        Подписать транзакцию через Builder Signing SDK
        
        Args:
            transaction: Данные транзакции
            
        Returns:
            Подпись транзакции или None
            
        Note:
            Требуется установка py-builder-signing-sdk
        """
        logger.warning("⚠️ sign_transaction() requires py-builder-signing-sdk (not installed)")
        return None
    
    def submit_gasless_transaction(self, transaction: Dict, signature: str) -> Optional[str]:
        """
        Отправить безгазовую транзакцию через Relayer SDK
        
        Args:
            transaction: Данные транзакции
            signature: Подпись транзакции
            
        Returns:
            Хэш транзакции или None
            
        Note:
            Требуется установка py-builder-relayer-client
        """
        logger.warning("⚠️ submit_gasless_transaction() requires py-builder-relayer-client (not installed)")
        return None
    
    def get_builder_volume(self) -> float:
        """
        Получить объём билдера за день
        
        Returns:
            Объём в USDC
        """
        logger.warning("⚠️ get_builder_volume() requires Builder SDK (not installed)")
        return 0.0


# ==================== GLOBAL INSTANCE ====================

# Глобальный экземпляр SDK (ленивая инициализация)
_polymarket_sdk: Optional[PolymarketSDK] = None


def get_polymarket_sdk() -> PolymarketSDK:
    """
    Получить глобальный экземпляр PolymarketSDK
    
    Returns:
        PolymarketSDK: Настроенный экземпляр SDK
    """
    global _polymarket_sdk
    if _polymarket_sdk is None:
        _polymarket_sdk = PolymarketSDK()
    return _polymarket_sdk


def is_polymarket_configured() -> bool:
    """
    Проверить настроен ли Polymarket SDK
    
    Returns:
        bool: True если настроен
    """
    sdk = get_polymarket_sdk()
    return sdk.is_configured()
