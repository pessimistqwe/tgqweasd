"""
VolatilityService - Сервис для расчета коэффициентов на основе реальной волатильности

Особенности:
1. Берет реальные цены за последние 5 минут из Binance API
2. Рассчитывает волатильность: std_dev(prices) / mean(prices) * 100
3. Рассчитывает коэффициент на основе волатильности:
   - Низкая волатильность (< 0.5%) → коэффициент ~1.90x–1.95x
   - Средняя волатильность (0.5%–2%) → коэффициент ~1.80x–1.90x
   - Высокая волатильность (> 2%) → коэффициент ~1.50x–1.80x
4. Обновляет коэффициент каждые 30 секунд
5. НЕ зависит от таймфрейма графика
6. Обработка ошибки 451 (Binance блокировка) с fallback на кэш
7. Failover между зеркалами Binance API
8. Retry логика с экспоненциальной задержкой
"""

import asyncio
import logging
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
from decimal import Decimal, ROUND_HALF_UP
import statistics

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

# Binance API endpoints (failover список)
BINANCE_ENDPOINTS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://api4.binance.com",
]

# Текущий активный endpoint (переключается при ошибках)
CURRENT_ENDPOINT_INDEX = 0

# Headers для запросов (обход простых блокировок)
BINANCE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
}

# Mapping событий на Binance символы
CRYPTO_SYMBOLS = {
    'bitcoin': 'BTCUSDT',
    'btc': 'BTCUSDT',
    'ethereum': 'ETHUSDT',
    'eth': 'ETHUSDT',
    'solana': 'SOLUSDT',
    'sol': 'SOLUSDT',
    'ton': 'TONUSDT',
    'bnb': 'BNBUSDT',
    'xrp': 'XRPUSDT',
    'cardano': 'ADAUSDT',
    'dogecoin': 'DOGEUSDT',
    'doge': 'DOGEUSDT',
    'polkadot': 'DOTUSDT',
    'dot': 'DOTUSDT',
    'avalanche': 'AVAXUSDT',
    'avax': 'AVAXUSDT',
}

# Глобальный кэш последних данных (для fallback)
# Формат: {symbol: {"prices": [...], "timestamp": datetime, "odds": Decimal, "volatility": Decimal}}
PRICE_CACHE: Dict[str, Dict] = {}
CACHE_TTL_SECONDS = 300  # 5 минут


class BinanceAPIError(Exception):
    """Ошибка Binance API"""
    pass


class BinanceBlockedError(Exception):
    """Binance заблокировал запрос (451)"""
    pass


def get_current_endpoint() -> str:
    """Получить текущий активный endpoint"""
    global CURRENT_ENDPOINT_INDEX
    return BINANCE_ENDPOINTS[CURRENT_ENDPOINT_INDEX % len(BINANCE_ENDPOINTS)]


def switch_to_next_endpoint():
    """Переключиться на следующий endpoint"""
    global CURRENT_ENDPOINT_INDEX
    CURRENT_ENDPOINT_INDEX += 1
    logger.warning(f"🔄 Switched to Binance endpoint: {get_current_endpoint()}")


def get_from_cache(symbol: str) -> Optional[Dict]:
    """
    Получить данные из кэша
    
    Args:
        symbol: Торговая пара
        
    Returns:
        Dict с данными или None если кэш устарел/отсутствует
    """
    if symbol not in PRICE_CACHE:
        return None
    
    cached = PRICE_CACHE[symbol]
    age = (datetime.utcnow() - cached["timestamp"]).total_seconds()
    
    if age > CACHE_TTL_SECONDS:
        logger.warning(f"⚠️ Cache expired for {symbol} (age: {age:.0f}s)")
        return None
    
    return cached


def save_to_cache(symbol: str, prices: List[float], odds: Decimal, volatility: Decimal):
    """
    Сохранить данные в кэш
    
    Args:
        symbol: Торговая пара
        prices: Список цен
        odds: Коэффициент
        volatility: Волатильность
    """
    PRICE_CACHE[symbol] = {
        "prices": prices,
        "timestamp": datetime.utcnow(),
        "odds": odds,
        "volatility": volatility,
    }
    logger.debug(f"💾 Cached data for {symbol}: {len(prices)} prices, odds={odds}")


def get_fallback_data(symbol: str) -> Dict:
    """
    Получить fallback данные если Binance недоступен
    
    Args:
        symbol: Торговая пара
        
    Returns:
        Dict с данными (из кэша или дефолтные)
    """
    logger.warning(f"⚠️ Using fallback data for {symbol}")
    
    # Попытка получить из кэша
    cached = get_from_cache(symbol)
    if cached:
        logger.info(f"✅ Fallback from cache for {symbol}: odds={cached['odds']}")
        return {
            "symbol": symbol,
            "volatility": float(cached["volatility"]),
            "odds": float(cached["odds"]),
            "cached": True,
            "from_cache": True,
            "timestamp": cached["timestamp"].isoformat(),
            "price_count": len(cached["prices"]),
            "min_price": min(cached["prices"]) if cached["prices"] else 0,
            "max_price": max(cached["prices"]) if cached["prices"] else 0,
            "current_price": cached["prices"][-1] if cached["prices"] else 0,
        }
    
    # Дефолтные данные если кэша нет
    default_odds = Decimal("1.90")
    logger.warning(f"⚠️ No cache for {symbol}, using default odds={default_odds}")
    
    return {
        "symbol": symbol,
        "volatility": 0.0,
        "odds": float(default_odds),
        "cached": False,
        "from_cache": False,
        "error": "Data temporarily unavailable",
        "timestamp": datetime.utcnow().isoformat(),
        "price_count": 0,
        "min_price": 0,
        "max_price": 0,
        "current_price": 0,
    }


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.exceptions.RequestException, BinanceAPIError)),
    reraise=True
)
def fetch_binance_prices(symbol: str, endpoint: str) -> List[float]:
    """
    Получить цены из Binance API с retry логикой
    
    Args:
        symbol: Торговая пара
        endpoint: Binance endpoint
        
    Returns:
        Список цен закрытия
        
    Raises:
        BinanceBlockedError: Если Binance вернул 451
        BinanceAPIError: Если другая ошибка API
    """
    url = f"{endpoint}/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": "1m",
        "limit": 6  # 5 минут = 5-6 свечей
    }
    
    logger.info(f"📡 Fetching prices for {symbol} from {endpoint}")
    
    try:
        response = requests.get(url, params=params, headers=BINANCE_HEADERS, timeout=10)
        
        # Обработка ошибки 451
        if response.status_code == 451:
            logger.error(f"🚫 Binance blocked request (451) for {symbol} from {endpoint}")
            raise BinanceBlockedError(f"Binance returned 451 for {symbol}")
        
        # Обработка других HTTP ошибок
        if response.status_code != 200:
            logger.error(f"❌ Binance API error {response.status_code} for {symbol}: {response.text[:200]}")
            raise BinanceAPIError(f"Binance API error: {response.status_code}")
        
        data = response.json()
        
        if not isinstance(data, list) or len(data) == 0:
            logger.warning(f"⚠️ Empty response from Binance for {symbol}")
            return []
        
        # Извлекаем цены закрытия (индекс 4 в свече)
        prices = []
        for candle in data:
            if len(candle) >= 5:
                try:
                    prices.append(float(candle[4]))
                except (ValueError, TypeError):
                    continue
        
        logger.info(f"✅ Received {len(prices)} prices for {symbol}")
        return prices
        
    except requests.exceptions.Timeout:
        logger.error(f"⏱️ Timeout fetching prices for {symbol} from {endpoint}")
        raise
    except requests.exceptions.ConnectionError as e:
        logger.error(f"🔌 Connection error fetching prices for {symbol}: {e}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Request error fetching prices for {symbol}: {e}")
        raise


class VolatilityService:
    """Сервис для расчета волатильности и коэффициентов"""

    # Интервал обновления коэффициентов (секунды)
    UPDATE_INTERVAL_SECONDS = 30

    # Период для расчета волатильности (5 минут)
    VOLATILITY_PERIOD_MINUTES = 5

    # Минутный интервал для получения данных
    BINANCE_INTERVAL = '1m'

    # Количество свечей для анализа (5 минут = 5 свечей по 1 минуте)
    CANDLE_LIMIT = 6  # Берем с запасом

    # Базовые коэффициенты
    BASE_ODDS_LOW_VOLATILITY = Decimal("1.95")    # < 0.5%
    BASE_ODDS_MEDIUM_VOLATILITY = Decimal("1.85")  # 0.5% - 2%
    BASE_ODDS_HIGH_VOLATILITY = Decimal("1.65")    # > 2%

    # Пороги волатильности (в процентах)
    LOW_VOLATILITY_THRESHOLD = Decimal("0.5")
    HIGH_VOLATILITY_THRESHOLD = Decimal("2.0")

    # Минимальный и максимальный коэффициент
    MIN_ODDS = Decimal("1.50")
    MAX_ODDS = Decimal("1.95")

    def __init__(self):
        # Кэш последних рассчитанных коэффициентов
        self._odds_cache: Dict[str, Tuple[Decimal, Decimal, datetime]] = {}
        # Задача для фонового обновления
        self._background_task: Optional[asyncio.Task] = None
        # Флаг остановки
        self._stop_event: Optional[asyncio.Event] = None
        # Счётчик ошибок для каждого символа
        self._error_counts: Dict[str, int] = {}

    def calculate_volatility(self, prices: list) -> Decimal:
        """
        Рассчитывает волатильность по списку цен

        Формула: (std_dev / mean) * 100

        Args:
            prices: Список цен (float или Decimal)

        Returns:
            Волатильность в процентах (Decimal)
        """
        if len(prices) < 2:
            return Decimal("0")

        # Конвертируем в Decimal для точности
        decimal_prices = [Decimal(str(p)) for p in prices]

        # Среднее значение
        mean_price = sum(decimal_prices) / len(decimal_prices)

        if mean_price == 0:
            return Decimal("0")

        # Стандартное отклонение
        if len(decimal_prices) < 2:
            return Decimal("0")

        variance = statistics.variance([float(p) for p in decimal_prices])
        std_dev = Decimal(str(variance ** 0.5))

        # Волатильность в процентах
        volatility = (std_dev / mean_price) * Decimal("100")

        return volatility.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    def calculate_odds_from_volatility(self, volatility: Decimal) -> Decimal:
        """
        Рассчитывает коэффициент на основе волатильности

        Args:
            volatility: Волатильность в процентах

        Returns:
            Коэффициент (например, 1.95)
        """
        if volatility < self.LOW_VOLATILITY_THRESHOLD:
            # Низкая волатильность - высокий коэффициент
            # 1.90x - 1.95x
            base = self.BASE_ODDS_LOW_VOLATILITY
            # Немного уменьшаем коэффициент при приближении к порогу
            adjustment = volatility / self.LOW_VOLATILITY_THRESHOLD * Decimal("0.05")
            odds = base - adjustment
        elif volatility < self.HIGH_VOLATILITY_THRESHOLD:
            # Средняя волатильность
            # 1.80x - 1.90x
            range_volatility = self.HIGH_VOLATILITY_THRESHOLD - self.LOW_VOLATILITY_THRESHOLD
            position = (volatility - self.LOW_VOLATILITY_THRESHOLD) / range_volatility
            odds = self.BASE_ODDS_LOW_VOLATILITY - Decimal("0.15") - (position * Decimal("0.10"))
        else:
            # Высокая волатильность - низкий коэффициент
            # 1.50x - 1.80x
            # Чем выше волатильность, тем ниже коэффициент
            excess = volatility - self.HIGH_VOLATILITY_THRESHOLD
            # Ограничиваем влияние избыточной волатильности
            excess = min(excess, Decimal("5.0"))  # Максимум 5% избытка
            odds = self.BASE_ODDS_HIGH_VOLATILITY - (excess / Decimal("5.0") * Decimal("0.15"))

        # Ограничиваем мин/макс
        odds = max(self.MIN_ODDS, min(self.MAX_ODDS, odds))

        return odds.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    async def fetch_recent_prices(self, symbol: str) -> List[float]:
        """
        Получает последние цены за последние 5 минут из Binance API
        с обработкой ошибки 451 и failover между зеркалами

        Args:
            symbol: Торговая пара (например, 'BTCUSDT')

        Returns:
            Список цен закрытия
        """
        # Пробуем каждый endpoint из списка
        endpoints_to_try = [get_current_endpoint()] + [
            ep for ep in BINANCE_ENDPOINTS if ep != get_current_endpoint()
        ]
        
        for i, endpoint in enumerate(endpoints_to_try[:3]):  # Максимум 3 попытки
            try:
                logger.info(f"🔄 Attempt {i+1}: Trying endpoint {endpoint}")
                
                # Используем sync функцию в async контексте
                loop = asyncio.get_event_loop()
                prices = await loop.run_in_executor(
                    None,
                    lambda ep=endpoint: fetch_binance_prices(symbol, ep)
                )
                
                if prices and len(prices) >= 2:
                    logger.info(f"✅ Successfully fetched {len(prices)} prices from {endpoint}")
                    return prices
                else:
                    logger.warning(f"⚠️ Got insufficient data from {endpoint}: {len(prices)} prices")
                    
            except BinanceBlockedError as e:
                logger.error(f"🚫 Endpoint {endpoint} blocked (451): {e}")
                switch_to_next_endpoint()
                continue
                
            except BinanceAPIError as e:
                logger.error(f"❌ API error from {endpoint}: {e}")
                switch_to_next_endpoint()
                continue
                
            except requests.exceptions.Timeout:
                logger.error(f"⏱️ Timeout from {endpoint}")
                switch_to_next_endpoint()
                continue
                
            except Exception as e:
                logger.error(f"❌ Unexpected error from {endpoint}: {e}")
                switch_to_next_endpoint()
                continue
        
        # Все endpoints не сработали
        logger.error(f"🚫 All Binance endpoints failed for {symbol}")
        return []

    async def calculate_odds_for_symbol(self, symbol: str) -> Dict:
        """
        Рассчитывает волатильность и коэффициент для символа
        с обработкой ошибки 451 и fallback на кэш

        Args:
            symbol: Торговая пара

        Returns:
            Dict с волатильностью и коэффициентом
        """
        logger.info(f"1️⃣ Starting market load for {symbol}")
        
        # Проверяем кэш (не старше 30 секунд)
        if symbol in self._odds_cache:
            odds, volatility, timestamp = self._odds_cache[symbol]
            if (datetime.utcnow() - timestamp).total_seconds() < self.UPDATE_INTERVAL_SECONDS:
                logger.info(f"2️⃣ Using cached odds for {symbol}: {odds}")
                return {
                    "symbol": symbol,
                    "volatility": float(volatility),
                    "odds": float(odds),
                    "cached": True,
                    "timestamp": timestamp.isoformat()
                }

        # Получаем цены с обработкой 451
        logger.info(f"2️⃣ Fetching from Binance: {symbol}")
        prices = await self.fetch_recent_prices(symbol)

        if not prices or len(prices) < 2:
            logger.warning(f"⚠️ No price data for {symbol}, using fallback")
            # Возвращаем fallback данные
            return get_fallback_data(symbol)

        logger.info(f"3️⃣ Received {len(prices)} candles for {symbol}")
        
        # Рассчитываем волатильность
        volatility = self.calculate_volatility(prices)

        # Рассчитываем коэффициент
        odds = self.calculate_odds_from_volatility(volatility)

        # Сохраняем в кэш
        save_to_cache(symbol, prices, odds, volatility)
        self._odds_cache[symbol] = (odds, volatility, datetime.utcnow())

        logger.info(
            f"4️⃣ Volatility calculated for {symbol}: "
            f"volatility={volatility}%, odds={odds}x"
        )

        return {
            "symbol": symbol,
            "volatility": float(volatility),
            "odds": float(odds),
            "cached": False,
            "timestamp": datetime.utcnow().isoformat(),
            "price_count": len(prices),
            "min_price": min(prices),
            "max_price": max(prices),
            "current_price": prices[-1]
        }

    def get_cached_odds(self, symbol: str) -> Optional[Dict]:
        """
        Получает закэшированные коэффициенты

        Args:
            symbol: Торговая пара

        Returns:
            Dict с данными или None
        """
        if symbol not in self._odds_cache:
            return None

        odds, volatility, timestamp = self._odds_cache[symbol]
        return {
            "symbol": symbol,
            "volatility": float(volatility),
            "odds": float(odds),
            "timestamp": timestamp.isoformat()
        }

    async def start_background_updates(self):
        """Запускает фоновое обновление коэффициентов"""
        if self._background_task is not None:
            logger.warning("Background updates already running")
            return

        self._stop_event = asyncio.Event()
        self._background_task = asyncio.create_task(self._background_update_loop())
        logger.info("Started volatility background updates")

    async def stop_background_updates(self):
        """Останавливает фоновое обновление"""
        if self._stop_event:
            self._stop_event.set()

        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass

        self._background_task = None
        self._stop_event = None
        logger.info("Stopped volatility background updates")

    async def _background_update_loop(self):
        """Фоновый цикл обновления коэффициентов"""
        while not self._stop_event.is_set():
            try:
                # Обновляем для всех популярных символов
                for symbol in list(CRYPTO_SYMBOLS.values())[:10]:  # Топ 10
                    try:
                        await self.calculate_odds_for_symbol(symbol)
                    except Exception as e:
                        logger.error(f"Error updating {symbol}: {e}")
                        # Увеличиваем счётчик ошибок
                        self._error_counts[symbol] = self._error_counts.get(symbol, 0) + 1

                # Ждем следующий интервал обновления
                await asyncio.sleep(self.UPDATE_INTERVAL_SECONDS)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in background update loop: {e}")
                await asyncio.sleep(5)  # Пауза при ошибке

    def detect_symbol_from_text(self, text: str) -> Optional[str]:
        """
        Определяет Binance символ из текста события

        Args:
            text: Текст события (title + description)

        Returns:
            Символ (например, 'BTCUSDT') или None
        """
        if not text:
            return None

        text_lower = text.lower()

        for key, symbol in CRYPTO_SYMBOLS.items():
            if key in text_lower:
                return symbol

        return None


# Глобальный экземпляр сервиса
volatility_service = VolatilityService()


# Функции для использования в других модулях
async def get_volatility_odds(symbol: str) -> Dict:
    """
    Получает коэффициент для символа

    Args:
        symbol: Торговая пара

    Returns:
        Dict с волатильностью и коэффициентом
    """
    return await volatility_service.calculate_odds_for_symbol(symbol)


def get_cached_volatility_odds(symbol: str) -> Optional[Dict]:
    """
    Получает закэшированный коэффициент

    Args:
        symbol: Торговая пара

    Returns:
        Dict с данными или None
    """
    return volatility_service.get_cached_odds(symbol)


async def start_volatility_service():
    """Запускает сервис волатильности"""
    await volatility_service.start_background_updates()


async def stop_volatility_service():
    """Останавливает сервис волатильности"""
    await volatility_service.stop_background_updates()
