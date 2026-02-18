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
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
import statistics

import requests

logger = logging.getLogger(__name__)

# Binance API для получения реальных цен
BINANCE_API_URL = "https://api.binance.com/api/v3"

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
    
    async def fetch_recent_prices(self, symbol: str) -> list:
        """
        Получает последние цены за последние 5 минут из Binance API
        
        Args:
            symbol: Торговая пара (например, 'BTCUSDT')
            
        Returns:
            Список цен закрытия
        """
        try:
            url = f"{BINANCE_API_URL}/klines"
            params = {
                "symbol": symbol,
                "interval": self.BINANCE_INTERVAL,
                "limit": self.CANDLE_LIMIT
            }
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.get(url, params=params, timeout=10)
            )
            
            if response.status_code != 200:
                logger.warning(f"Binance API error: {response.status_code}")
                return []
            
            data = response.json()
            
            # Извлекаем цены закрытия (индекс 4 в свече)
            prices = [float(candle[4]) for candle in data]
            
            return prices
            
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching prices for {symbol}")
            return []
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error fetching prices: {e}")
            return []
        except Exception as e:
            logger.warning(f"Error fetching prices: {e}")
            return []
    
    async def calculate_odds_for_symbol(self, symbol: str) -> Dict:
        """
        Рассчитывает волатильность и коэффициент для символа
        
        Args:
            symbol: Торговая пара
            
        Returns:
            Dict с волатильностью и коэффициентом
        """
        # Проверяем кэш (не старше 30 секунд)
        if symbol in self._odds_cache:
            odds, volatility, timestamp = self._odds_cache[symbol]
            if (datetime.utcnow() - timestamp).total_seconds() < self.UPDATE_INTERVAL_SECONDS:
                return {
                    "symbol": symbol,
                    "volatility": volatility,
                    "odds": odds,
                    "cached": True,
                    "timestamp": timestamp.isoformat()
                }
        
        # Получаем цены
        prices = await self.fetch_recent_prices(symbol)
        
        if not prices or len(prices) < 2:
            # Возвращаем дефолтный коэффициент если нет данных
            default_odds = Decimal("1.90")
            result = {
                "symbol": symbol,
                "volatility": Decimal("0"),
                "odds": default_odds,
                "cached": False,
                "error": "No price data"
            }
            # Кэшируем на 10 секунд
            self._odds_cache[symbol] = (default_odds, Decimal("0"), datetime.utcnow())
            return result
        
        # Рассчитываем волатильность
        volatility = self.calculate_volatility(prices)
        
        # Рассчитываем коэффициент
        odds = self.calculate_odds_from_volatility(volatility)
        
        # Кэшируем результат
        self._odds_cache[symbol] = (odds, volatility, datetime.utcnow())
        
        logger.info(
            f"Volatility calculated for {symbol}: "
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
