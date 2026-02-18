"""
Resolver Worker - фоновый воркер для автоматического расчёта ставок

Периодически проверяет:
1. Для Polymarket событий: статус события в API -> если resolved, закрыть ставки
2. Для Binance цен: текущую цену -> если достигнут тейк-профит/стоп-лосс/ликвидация, закрыть
3. Для Price Predictions: истёк срок прогноза -> рассчитать результат

Воркер запускается в фоне через APScheduler и работает асинхронно.
"""

import asyncio
import logging
import requests
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

try:
    from .betting_models import Bet, BetType, BetDirection, BetStatus, PricePrediction
    from .betting_service import BettingService
    from .betting_repository import BettingRepository
    from .models import Event, get_db
except ImportError:
    from betting_models import Bet, BetType, BetDirection, BetStatus, PricePrediction
    from betting_service import BettingService
    from betting_repository import BettingRepository
    from models import Event, get_db

logger = logging.getLogger(__name__)

# Polymarket API
POLYMARKET_API_URL = "https://gamma-api.polymarket.com"

# Binance API для получения актуальных цен
BINANCE_API_URL = "https://api.binance.com/api/v3"

# Интервалы проверки (в секундах)
CHECK_INTERVAL_SECONDS = 60  # Проверка каждые 60 секунд
PRICE_CHECK_INTERVAL_SECONDS = 10  # Проверка цен каждые 10 секунд (для price predictions)
POLYMARKET_CHECK_INTERVAL_SECONDS = 300  # Проверка Polymarket каждые 5 минут


class ResolverWorker:
    """
    Фоновый воркер для автоматического расчёта ставок
    
    Работает в нескольких потоках:
    1. Проверка краткосрочных прогнозов (каждые 10 сек)
    2. Проверка price bets (каждые 60 сек)
    3. Проверка Polymarket событий (каждые 5 мин)
    """
    
    def __init__(self):
        self._running = False
        self._tasks: List[asyncio.Task] = []
    
    async def start(self):
        """Запуск воркера"""
        logger.info("🚀 Starting Resolver Worker...")
        self._running = True
        
        # Запускаем задачи в фоне
        self._tasks = [
            asyncio.create_task(self._run_price_predictions_checker()),
            asyncio.create_task(self._run_price_bets_checker()),
            asyncio.create_task(self._run_polymarket_checker()),
        ]
        
        logger.info("✅ Resolver Worker started")
    
    async def stop(self):
        """Остановка воркера"""
        logger.info("🛑 Stopping Resolver Worker...")
        self._running = False
        
        # Отменяем все задачи
        for task in self._tasks:
            task.cancel()
        
        # Ждём завершения
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
        
        logger.info("✅ Resolver Worker stopped")
    
    async def _run_price_predictions_checker(self):
        """Проверка краткосрочных прогнозов (каждые 10 сек)"""
        logger.info("📊 Starting price predictions checker loop")
        
        while self._running:
            try:
                await asyncio.sleep(PRICE_CHECK_INTERVAL_SECONDS)
                await self._check_price_predictions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in price predictions checker: {e}")
                await asyncio.sleep(5)  # Pause before retry
    
    async def _run_price_bets_checker(self):
        """Проверка price bets (каждые 60 сек)"""
        logger.info("📈 Starting price bets checker loop")
        
        while self._running:
            try:
                await asyncio.sleep(CHECK_INTERVAL_SECONDS)
                await self._check_price_bets()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in price bets checker: {e}")
                await asyncio.sleep(10)
    
    async def _run_polymarket_checker(self):
        """Проверка Polymarket событий (каждые 5 мин)"""
        logger.info("🏛️ Starting Polymarket checker loop")
        
        while self._running:
            try:
                await asyncio.sleep(POLYMARKET_CHECK_INTERVAL_SECONDS)
                await self._check_polymarket_events()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Polymarket checker: {e}")
                await asyncio.sleep(30)
    
    async def _check_price_predictions(self):
        """
        Проверка краткосрочных прогнозов
        
        1. Получаем все активные прогнозы
        2. Для каждого проверяем не истёк ли срок
        3. Если истёк - получаем текущую цену и рассчитываем
        """
        db = next(get_db())
        try:
            repository = BettingRepository(db)
            service = BettingService(db)
            
            # Получаем все активные прогнозы
            predictions = repository.get_pending_price_predictions()
            
            now = datetime.utcnow()
            settled_count = 0
            
            for prediction in predictions:
                # Проверяем истёк ли срок
                expires_at = prediction.created_at + timedelta(seconds=prediction.duration_seconds)
                
                if now >= expires_at:
                    try:
                        # Получаем текущую цену актива
                        exit_price = await self._get_binance_price(prediction.symbol)
                        
                        if exit_price:
                            # Рассчитываем прогноз
                            result = service.settle_price_prediction(prediction.id, exit_price)
                            settled_count += 1
                            
                            logger.info(
                                f"📊 Settled prediction {prediction.id}: "
                                f"won={result['won']}, payout={result['payout']}"
                            )
                        else:
                            logger.warning(f"Could not get price for {prediction.symbol}")
                    
                    except Exception as e:
                        logger.error(f"Error settling prediction {prediction.id}: {e}")
                        continue
            
            if settled_count > 0:
                logger.info(f"✅ Settled {settled_count} price predictions")
            
            db.commit()
        
        except Exception as e:
            logger.error(f"Error in price predictions check: {e}")
            db.rollback()
        
        finally:
            db.close()
    
    async def _check_price_bets(self):
        """
        Проверка price bets (Long/Short позиции)
        
        1. Получаем все открытые price bets
        2. Для каждой получаем текущую цену
        3. Проверяем условия закрытия:
           - Достигнут тейк-профит
           - Достигнут стоп-лосс
           - Достигнута цена ликвидации
        4. Если условие выполнено - закрываем ставку
        """
        db = next(get_db())
        try:
            repository = BettingRepository(db)
            service = BettingService(db)
            
            # Получаем все открытые price bets
            open_bets = repository.get_open_bets(bet_type=BetType.PRICE)
            
            closed_count = 0
            
            for bet in open_bets:
                try:
                    # Получаем текущую цену
                    current_price = await self._get_binance_price(bet.symbol)
                    
                    if not current_price:
                        continue
                    
                    current_price = Decimal(str(current_price))
                    entry_price = bet.entry_price
                    liquidation_price = bet.liquidation_price if bet.liquidation_price else None
                    take_profit = bet.take_profit_price if bet.take_profit_price else None
                    stop_loss = bet.stop_loss_price if bet.stop_loss_price else None
                    
                    should_close = False
                    close_reason = ""
                    
                    # Проверка ликвидации
                    if liquidation_price:
                        if bet.direction == BetDirection.LONG and current_price <= liquidation_price:
                            should_close = True
                            close_reason = "liquidation"
                        elif bet.direction == BetDirection.SHORT and current_price >= liquidation_price:
                            should_close = True
                            close_reason = "liquidation"
                    
                    # Проверка тейк-профита
                    if take_profit and not should_close:
                        if bet.direction == BetDirection.LONG and current_price >= take_profit:
                            should_close = True
                            close_reason = "take_profit"
                        elif bet.direction == BetDirection.SHORT and current_price <= take_profit:
                            should_close = True
                            close_reason = "take_profit"
                    
                    # Проверка стоп-лосса
                    if stop_loss and not should_close:
                        if bet.direction == BetDirection.LONG and current_price <= stop_loss:
                            should_close = True
                            close_reason = "stop_loss"
                        elif bet.direction == BetDirection.SHORT and current_price >= stop_loss:
                            should_close = True
                            close_reason = "stop_loss"
                    
                    # Закрываем ставку если условие выполнено
                    if should_close:
                        result = service.settle_price_bet(bet.id, current_price)
                        closed_count += 1
                        
                        logger.info(
                            f"📈 Closed price bet {bet.id}: reason={close_reason}, "
                            f"pnl={result['pnl']}"
                        )
                
                except Exception as e:
                    logger.error(f"Error checking bet {bet.id}: {e}")
                    continue
            
            if closed_count > 0:
                logger.info(f"✅ Closed {closed_count} price bets")
            
            db.commit()
        
        except Exception as e:
            logger.error(f"Error in price bets check: {e}")
            db.rollback()
        
        finally:
            db.close()
    
    async def _check_polymarket_events(self):
        """
        Проверка Polymarket событий
        
        1. Получаем все открытые event bets
        2. Для каждого события проверяем статус в Polymarket API
        3. Если событие resolved - закрываем все ставки по нему
        """
        db = next(get_db())
        try:
            repository = BettingRepository(db)
            service = BettingService(db)
            
            # Получаем все открытые event bets
            open_bets = repository.get_open_bets(bet_type=BetType.EVENT)
            
            # Группируем по market_id
            market_ids = set(bet.market_id for bet in open_bets)
            
            settled_count = 0
            
            for market_id in market_ids:
                try:
                    # Получаем событие из БД
                    event = repository.get_event_by_id(market_id)
                    if not event or not event.polymarket_id:
                        continue
                    
                    # Проверяем статус в Polymarket API
                    pm_status = await self._get_polymarket_event_status(event.polymarket_id)
                    
                    if pm_status and pm_status.get("resolved", False):
                        # Получаем выигрышный опцион
                        winning_outcome = pm_status.get("winning_outcome")
                        
                        if winning_outcome:
                            # Маппинг outcome на option_index
                            # Polymarket возвращает название исхода (Yes/No)
                            winning_index = 0 if winning_outcome.lower() == "yes" else 1
                            
                            # Закрываем все ставки по этому рынку
                            market_bets = repository.get_market_bets(market_id, status=BetStatus.OPEN)
                            
                            for bet in market_bets:
                                try:
                                    result = service.settle_event_bet(bet.id, winning_index)
                                    settled_count += 1
                                    
                                    logger.info(
                                        f"🏛️ Settled bet {bet.id}: won={result['won']}, "
                                        f"payout={result['payout']}"
                                    )
                                except Exception as e:
                                    logger.error(f"Error settling bet {bet.id}: {e}")
                                    continue
                        
                        # Обновляем событие в БД
                        event.is_resolved = True
                        event.resolution_time = datetime.utcnow()
                
                except Exception as e:
                    logger.error(f"Error checking market {market_id}: {e}")
                    continue
            
            if settled_count > 0:
                logger.info(f"✅ Settled {settled_count} Polymarket bets")
            
            db.commit()
        
        except Exception as e:
            logger.error(f"Error in Polymarket check: {e}")
            db.rollback()
        
        finally:
            db.close()
    
    async def _get_binance_price(self, symbol: str) -> Optional[Decimal]:
        """
        Получить текущую цену из Binance API
        
        Args:
            symbol: Символ актива (BTCUSDT, ETHUSDT и т.д.)
            
        Returns:
            Decimal или None если ошибка
        """
        try:
            symbol = symbol.upper()
            if not symbol.endswith('USDT'):
                symbol = symbol + 'USDT'
            
            response = requests.get(
                f"{BINANCE_API_URL}/ticker/price",
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
    
    async def _get_polymarket_event_status(self, condition_id: str) -> Optional[Dict[str, Any]]:
        """
        Получить статус события из Polymarket API
        
        Args:
            condition_id: ID условия из Polymarket
            
        Returns:
            Dict со статусом или None
        """
        try:
            response = requests.get(
                f"{POLYMARKET_API_URL}/markets/{condition_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Polymarket возвращает информацию о рынке
                return {
                    "resolved": data.get("resolved", False),
                    "winning_outcome": data.get("winningOutcome"),
                }
            
            return None
        
        except Exception as e:
            logger.warning(f"Error getting Polymarket status for {condition_id}: {e}")
            return None


# Глобальный экземпляр воркера
resolver_worker: Optional[ResolverWorker] = None


async def start_resolver_worker():
    """Запустить воркер"""
    global resolver_worker
    resolver_worker = ResolverWorker()
    await resolver_worker.start()


async def stop_resolver_worker():
    """Остановить воркер"""
    global resolver_worker
    if resolver_worker:
        await resolver_worker.stop()
        resolver_worker = None


# Функция для интеграции с APScheduler (если нужен sync подход)
def run_resolver_sync():
    """
    Синхронная обёртка для запуска воркера
    
    Используется если нет возможности запустить asyncio event loop
    """
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    worker = ResolverWorker()
    
    # Запускаем один цикл проверки
    async def run_once():
        await worker._check_price_predictions()
        await worker._check_price_bets()
        await worker._check_polymarket_events()
    
    loop.run_until_complete(run_once())
