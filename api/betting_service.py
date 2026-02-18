"""
BettingService - сервисный слой для Core Betting Engine

Реализует основную бизнес-логику:
- Размещение ставок (placeBet)
- Расчёт ставок (settleBet)
- Отмена ставок (cancelBet)

Все операции используют Decimal для точности и выполняются
внутри DB-транзакций для обеспечения ACID.
"""

from sqlalchemy.orm import Session
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any, List
import logging

try:
    from .betting_models import Bet, BetType, BetDirection, BetStatus, PricePrediction
    from .betting_repository import BettingRepository
    from .models import TransactionType, TransactionStatus
except ImportError:
    from betting_models import Bet, BetType, BetDirection, BetStatus, PricePrediction
    from betting_repository import BettingRepository
    from models import TransactionType, TransactionStatus

logger = logging.getLogger(__name__)


class BettingError(Exception):
    """Базовое исключение для ошибок betting engine"""
    pass


class InsufficientBalanceError(BettingError):
    """Недостаточно средств на балансе"""
    pass


class InvalidBetAmountError(BettingError):
    """Некорректная сумма ставки"""
    pass


class MarketNotFoundError(BettingError):
    """Рынок не найден"""
    pass


class BetNotFoundError(BettingError):
    """Ставка не найдена"""
    pass


class InvalidOddsError(BettingError):
    """Некорректные коэффициенты"""
    pass


class BettingService:
    """
    Сервис для управления ставками
    
    Все публичные методы:
    1. Используют транзакции для целостности данных
    2. Работают с Decimal для точности вычислений
    3. Возвращают результат и ошибки через исключения
    """
    
    # Константы для валидации
    MIN_BET_AMOUNT = Decimal("0.01")  # Минимальная ставка 0.01 USDT
    MAX_BET_AMOUNT = Decimal("10000")  # Максимальная ставка 10000 USDT
    MAX_LEVERAGE = Decimal("100")  # Максимальное плечо 100x
    
    def __init__(self, db: Session):
        """
        Инициализация сервиса
        
        Args:
            db: Сессия SQLAlchemy
        """
        self.db = db
        self.repository = BettingRepository(db)
    
    # ==================== Public API ====================
    
    def place_event_bet(
        self,
        user_id: int,
        market_id: int,
        option_index: int,
        amount: Decimal,
        direction: BetDirection,
    ) -> Dict[str, Any]:
        """
        Разместить ставку на событие (Polymarket-style)
        
        Логика:
        1. Проверка баланса пользователя
        2. Получение текущей цены опциона
        3. Расчёт количества акций (shares = amount / price)
        4. Расчёт потенциального выигрыша (shares * 1.0)
        5. Блокировка средств (списание с баланса)
        6. Сохранение ставки в БД
        
        Args:
            user_id: ID пользователя
            market_id: ID рынка (события)
            option_index: Индекс выбранного опциона
            amount: Сумма ставки в USDT
            direction: Направление (YES или NO)
            
        Returns:
            Dict с информацией о ставке:
            {
                "bet_id": int,
                "shares": Decimal,
                "entry_price": Decimal,
                "potential_payout": Decimal,
                "status": str
            }
            
        Raises:
            InsufficientBalanceError: Недостаточно средств
            InvalidBetAmountError: Некорректная сумма
            MarketNotFoundError: Рынок не найден
        """
        # === Валидация суммы ===
        self._validate_bet_amount(amount)
        
        # === Получаем информацию о рынке ===
        event = self.repository.get_event_by_id(market_id)
        if not event:
            raise MarketNotFoundError(f"Event with id={market_id} not found")
        
        # === Получаем цену опциона ===
        entry_price = self.repository.get_event_option_price(market_id, option_index)
        if entry_price is None or entry_price <= 0:
            raise InvalidOddsError(f"Invalid price for option {option_index}")
        
        # === Проверка баланса ===
        if not self.repository.check_user_balance(user_id, amount):
            balance = self.repository.get_user_balance(user_id)
            raise InsufficientBalanceError(
                f"Insufficient balance: required {amount}, has {balance}"
            )
        
        # === Расчёт параметров ставки ===
        # Количество акций = сумма / цена за акцию
        shares = (amount / entry_price).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
        
        # Потенциальный выигрыш = shares * 1.0 (если выиграет, получает $1 за акцию)
        potential_payout = shares * Decimal("1.0")
        
        # === Списываем средства с баланса ===
        # Используем транзакцию для атомарности
        success, new_balance = self.repository.update_user_balance(
            user_id=user_id,
            amount_change=-amount,  # Списание
            create_transaction=True,
            transaction_type=TransactionType.BET_PLACED,
        )
        
        if not success:
            raise InsufficientBalanceError("Failed to deduct balance")
        
        # === Создаём ставку ===
        bet = self.repository.create_bet(
            user_id=user_id,
            market_id=market_id,
            bet_type=BetType.EVENT,
            direction=direction,
            amount=amount,
            entry_price=entry_price,
            shares=shares,
            potential_payout=potential_payout,
        )
        
        # === Коммитим транзакцию ===
        # Ставка переводится в статус OPEN после успешного создания
        bet.status = BetStatus.OPEN
        
        logger.info(
            f"✅ Event bet placed: bet_id={bet.id}, user={user_id}, "
            f"amount={amount}, shares={shares}, price={entry_price}"
        )
        
        return {
            "bet_id": bet.id,
            "shares": str(shares),
            "entry_price": str(entry_price),
            "potential_payout": str(potential_payout),
            "status": bet.status.value,
            "created_at": bet.created_at.isoformat(),
        }
    
    def place_price_bet(
        self,
        user_id: int,
        market_id: int,
        direction: BetDirection,
        amount: Decimal,
        leverage: Decimal,
        entry_price: Decimal,
        symbol: str,
        take_profit_price: Optional[Decimal] = None,
        stop_loss_price: Optional[Decimal] = None,
    ) -> Dict[str, Any]:
        """
        Разместить ставку на цену (Binance-style)
        
        Логика:
        1. Проверка баланса пользователя
        2. Валидация параметров (плечо, цена)
        3. Расчёт размера позиции (amount * leverage)
        4. Расчёт цены ликвидации
        5. Блокировка средств
        6. Сохранение ставки в БД
        
        Args:
            user_id: ID пользователя
            market_id: ID рынка
            direction: Направление (LONG или SHORT)
            amount: Сумма ставки в USDT (маржа)
            leverage: Кредитное плечо (например, 10x)
            entry_price: Цена входа
            symbol: Символ актива (BTCUSDT)
            take_profit_price: Цена тейк-профита (опционально)
            stop_loss_price: Цена стоп-лосса (опционально)
            
        Returns:
            Dict с информацией о ставке:
            {
                "bet_id": int,
                "position_size": Decimal,
                "leverage": Decimal,
                "liquidation_price": Decimal,
                "potential_payout": Decimal,
                "status": str
            }
            
        Raises:
            InsufficientBalanceError: Недостаточно средств
            InvalidBetAmountError: Некорректная сумма или плечо
            MarketNotFoundError: Рынок не найден
        """
        # === Валидация суммы ===
        self._validate_bet_amount(amount)
        
        # === Валидация плеча ===
        self._validate_leverage(leverage)
        
        # === Проверка баланса ===
        if not self.repository.check_user_balance(user_id, amount):
            balance = self.repository.get_user_balance(user_id)
            raise InsufficientBalanceError(
                f"Insufficient balance: required {amount}, has {balance}"
            )
        
        # === Расчёт параметров ставки ===
        # Размер позиции = маржа * плечо
        position_size = (amount * leverage).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
        
        # Расчёт цены ликвидации
        liquidation_price = self._calculate_liquidation_price(
            entry_price=entry_price,
            leverage=leverage,
            direction=direction,
        )
        
        # Потенциальный выигрыш (расчётный, зависит от движения цены)
        # Для простоты: potential = amount * leverage * 0.1 (10% движение)
        potential_payout = amount * leverage * Decimal("0.1")
        
        # === Списываем средства с баланса (холдирование) ===
        success, new_balance = self.repository.update_user_balance(
            user_id=user_id,
            amount_change=-amount,  # Списываем маржу
            create_transaction=True,
            transaction_type=TransactionType.BET_PLACED,
        )
        
        if not success:
            raise InsufficientBalanceError("Failed to deduct balance")
        
        # === Создаём ставку ===
        bet = self.repository.create_bet(
            user_id=user_id,
            market_id=market_id,
            bet_type=BetType.PRICE,
            direction=direction,
            amount=amount,
            entry_price=entry_price,
            shares=position_size,  # Размер позиции
            leverage=leverage,
            liquidation_price=liquidation_price,
            potential_payout=potential_payout,
            symbol=symbol,
            take_profit_price=take_profit_price,
            stop_loss_price=stop_loss_price,
        )
        
        # === Коммитим транзакцию ===
        bet.status = BetStatus.OPEN
        
        logger.info(
            f"✅ Price bet placed: bet_id={bet.id}, user={user_id}, "
            f"symbol={symbol}, direction={direction.value}, amount={amount}, "
            f"leverage={leverage}, liq_price={liquidation_price}"
        )
        
        return {
            "bet_id": bet.id,
            "position_size": str(position_size),
            "leverage": str(leverage),
            "liquidation_price": str(liquidation_price),
            "potential_payout": str(potential_payout),
            "status": bet.status.value,
            "created_at": bet.created_at.isoformat(),
        }
    
    def place_price_prediction(
        self,
        user_id: int,
        market_id: int,
        direction: BetDirection,
        amount: Decimal,
        odds: Decimal,
        entry_price: Decimal,
        symbol: str,
        duration_seconds: int = 300,
    ) -> Dict[str, Any]:
        """
        Разместить краткосрочный прогноз цены (5 минут)
        
        Логика:
        1. Проверка баланса
        2. Валидация коэффициента
        3. Расчёт потенциального выигрыша (amount * odds)
        4. Списывание средств
        5. Создание прогноза
        
        Args:
            user_id: ID пользователя
            market_id: ID рынка
            direction: Направление (LONG=вверх или SHORT=вниз)
            amount: Сумма ставки в USDT
            odds: Коэффициент (например, 1.95x)
            entry_price: Текущая цена актива
            symbol: Символ актива (BTCUSDT)
            duration_seconds: Длительность прогноза в секундах
            
        Returns:
            Dict с информацией о прогнозе:
            {
                "prediction_id": int,
                "odds": Decimal,
                "potential_payout": Decimal,
                "status": str
            }
        """
        # === Валидация суммы ===
        self._validate_bet_amount(amount)
        
        # === Валидация коэффициента ===
        if odds <= 1:
            raise InvalidOddsError(f"Odds must be greater than 1, got {odds}")
        
        # === Проверка баланса ===
        if not self.repository.check_user_balance(user_id, amount):
            balance = self.repository.get_user_balance(user_id)
            raise InsufficientBalanceError(
                f"Insufficient balance: required {amount}, has {balance}"
            )
        
        # === Расчёт потенциального выигрыша ===
        potential_payout = (amount * odds).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
        
        # === Списываем средства ===
        success, new_balance = self.repository.update_user_balance(
            user_id=user_id,
            amount_change=-amount,
            create_transaction=True,
            transaction_type=TransactionType.BET_PLACED,
        )
        
        if not success:
            raise InsufficientBalanceError("Failed to deduct balance")
        
        # === Создаём прогноз ===
        prediction = self.repository.create_price_prediction(
            user_id=user_id,
            market_id=market_id,
            direction=direction,
            symbol=symbol,
            amount=amount,
            odds=odds,
            entry_price=entry_price,
            potential_payout=potential_payout,
            duration_seconds=duration_seconds,
        )
        
        prediction.status = BetStatus.OPEN
        
        logger.info(
            f"✅ Price prediction placed: id={prediction.id}, user={user_id}, "
            f"symbol={symbol}, direction={direction.value}, amount={amount}, odds={odds}"
        )
        
        return {
            "prediction_id": prediction.id,
            "odds": str(odds),
            "potential_payout": str(potential_payout),
            "status": prediction.status.value,
            "created_at": prediction.created_at.isoformat(),
            "resolves_at": (
                prediction.created_at + timedelta(seconds=duration_seconds)
            ).isoformat(),
        }
    
    def settle_event_bet(
        self,
        bet_id: int,
        winning_option_index: int,
    ) -> Dict[str, Any]:
        """
        Рассчитать ставку на событие
        
        Вызывается когда событие завершилось и определён победивший исход.
        
        Логика:
        1. Получить ставку
        2. Проверить соответствует ли ставка выигрышному опциону
        3. Если выиграл - начислить payout на баланс
        4. Обновить статус ставки
        
        Args:
            bet_id: ID ставки
            winning_option_index: Индекс выигрышного опциона
            
        Returns:
            Dict с результатом:
            {
                "bet_id": int,
                "won": bool,
                "payout": Decimal,
                "status": str
            }
        """
        # === Получаем ставку с блокировкой ===
        bet = self.repository.get_bet_with_lock(bet_id)
        if not bet:
            raise BetNotFoundError(f"Bet with id={bet_id} not found")
        
        # === Проверка что ставка открыта ===
        if bet.status not in [BetStatus.OPEN, BetStatus.PENDING]:
            raise BettingError(f"Bet {bet_id} is already settled (status={bet.status.value})")
        
        # === Определяем выигрыш ===
        # Для Polymarket-style: если опцион совпадает - выигрыш = shares * 1.0
        won = False
        payout = Decimal("0")
        
        # Получаем индекс опциона на который сделана ставка
        # direction YES -> option_index 0, NO -> option_index 1 (упрощённо)
        # В реальности нужно мапить direction на option_index
        bet_option_index = 0 if bet.direction == BetDirection.YES else 1
        
        if bet_option_index == winning_option_index:
            # Ставка выиграла
            won = True
            payout = bet.potential_payout
            
            # === Начисляем выигрыш на баланс ===
            self.repository.update_user_balance(
                user_id=bet.user_id,
                amount_change=payout,
                create_transaction=True,
                transaction_type=TransactionType.BET_WON,
            )
            
            logger.info(
                f"🎉 Bet WON: bet_id={bet_id}, user={bet.user_id}, payout={payout}"
            )
        else:
            # Ставка проиграла
            logger.info(f"❌ Bet LOST: bet_id={bet_id}, user={bet.user_id}")
        
        # === Обновляем статус ===
        if won:
            self.repository.update_bet_status(bet_id, BetStatus.WON)
            self.repository.update_bet_payout(bet_id, payout)
        else:
            self.repository.update_bet_status(bet_id, BetStatus.LOST)
        
        return {
            "bet_id": bet_id,
            "won": won,
            "payout": str(payout),
            "status": BetStatus.WON.value if won else BetStatus.LOST.value,
        }
    
    def settle_price_bet(
        self,
        bet_id: int,
        exit_price: Decimal,
    ) -> Dict[str, Any]:
        """
        Рассчитать ставку на цену
        
        Вызывается когда:
        - Достигнута цена тейк-профита
        - Достигнута цена стоп-лосса
        - Достигнута цена ликвидации
        - Пользователь закрыл позицию вручную
        
        Логика:
        1. Получить ставку
        2. Рассчитать PnL (Profit and Loss)
        3. Начислить результат на баланс
        4. Обновить статус
        
        Args:
            bet_id: ID ставки
            exit_price: Цена выхода
            
        Returns:
            Dict с результатом:
            {
                "bet_id": int,
                "pnl": Decimal,
                "exit_price": Decimal,
                "status": str
            }
        """
        # === Получаем ставку с блокировкой ===
        bet = self.repository.get_bet_with_lock(bet_id)
        if not bet:
            raise BetNotFoundError(f"Bet with id={bet_id} not found")
        
        if bet.status not in [BetStatus.OPEN, BetStatus.PENDING]:
            raise BettingError(f"Bet {bet_id} is already settled")
        
        # === Расчёт PnL ===
        # PnL = (exit_price - entry_price) / entry_price * position_size * direction
        entry_price = bet.entry_price
        position_size = bet.shares  # Это amount * leverage
        direction_multiplier = Decimal("1") if bet.direction == BetDirection.LONG else Decimal("-1")
        
        # Процент изменения цены
        price_change_pct = (exit_price - entry_price) / entry_price
        
        # PnL в USDT
        pnl = (price_change_pct * position_size * direction_multiplier).quantize(
            Decimal("0.00000001"), rounding=ROUND_HALF_UP
        )
        
        # Ограничиваем убыток размером маржи (не может потерять больше чем поставил)
        if pnl < -bet.amount:
            pnl = -bet.amount
        
        # === Начисляем результат ===
        # Возвращаем маржу + PnL (или - убыток)
        total_change = bet.amount + pnl
        
        self.repository.update_user_balance(
            user_id=bet.user_id,
            amount_change=total_change,
            create_transaction=True,
            transaction_type=TransactionType.BET_WON if pnl > 0 else TransactionType.BET_PLACED,
        )
        
        # === Обновляем статус ===
        self.repository.update_bet_status(bet_id, BetStatus.CLOSED)
        self.repository.update_bet_payout(bet_id, total_change, exit_price)
        
        result_status = BetStatus.WON if pnl > 0 else BetStatus.LOST
        
        logger.info(
            f"{'✅' if pnl > 0 else '❌'} Price bet settled: bet_id={bet_id}, "
            f"user={bet.user_id}, pnl={pnl}, exit_price={exit_price}"
        )
        
        return {
            "bet_id": bet_id,
            "pnl": str(pnl),
            "exit_price": str(exit_price),
            "total_payout": str(total_change),
            "status": result_status.value,
        }
    
    def settle_price_prediction(
        self,
        prediction_id: int,
        exit_price: Decimal,
    ) -> Dict[str, Any]:
        """
        Рассчитать краткосрочный прогноз цены
        
        Логика:
        1. Получить прогноз
        2. Сравнить направление с фактическим движением цены
        3. Если угадал - начислить amount * odds
        4. Если нет - ставка сгорает
        
        Args:
            prediction_id: ID прогноза
            exit_price: Цена в момент расчёта
            
        Returns:
            Dict с результатом
        """
        # === Получаем прогноз ===
        prediction = self.repository.get_price_prediction_with_lock(prediction_id)
        if not prediction:
            raise BetNotFoundError(f"Prediction with id={prediction_id} not found")
        
        if prediction.status not in [BetStatus.OPEN, BetStatus.PENDING]:
            raise BettingError(f"Prediction {prediction_id} is already settled")
        
        # === Определяем результат ===
        entry_price = prediction.entry_price
        direction = prediction.direction
        
        # Определяем фактическое направление
        actual_up = exit_price > entry_price
        predicted_up = direction == BetDirection.LONG
        
        won = (actual_up and predicted_up) or (not actual_up and not predicted_up)
        
        payout = Decimal("0")
        if won:
            payout = prediction.potential_payout
            
            # === Начисляем выигрыш ===
            self.repository.update_user_balance(
                user_id=prediction.user_id,
                amount_change=payout,
                create_transaction=True,
                transaction_type=TransactionType.BET_WON,
            )
            
            logger.info(
                f"🎉 Prediction WON: id={prediction_id}, user={prediction.user_id}, payout={payout}"
            )
        else:
            logger.info(f"❌ Prediction LOST: id={prediction_id}, user={prediction.user_id}")
        
        # === Обновляем статус ===
        status = BetStatus.WON if won else BetStatus.LOST
        self.repository.update_price_prediction_status(
            prediction_id,
            status,
            exit_price=exit_price,
            actual_payout=payout,
        )
        
        return {
            "prediction_id": prediction_id,
            "won": won,
            "exit_price": str(exit_price),
            "payout": str(payout),
            "status": status.value,
        }
    
    def cancel_bet(self, bet_id: int) -> Dict[str, Any]:
        """
        Отменить ставку и вернуть средства
        
        Можно отменить только ставки в статусе PENDING или OPEN
        (пока рынок не принял ставку или не началось событие)
        
        Args:
            bet_id: ID ставки
            
        Returns:
            Dict с результатом
            
        Raises:
            BetNotFoundError: Ставка не найдена
            BettingError: Нельзя отменить
        """
        # === Получаем ставку ===
        bet = self.repository.get_bet_with_lock(bet_id)
        if not bet:
            raise BetNotFoundError(f"Bet with id={bet_id} not found")
        
        # === Проверка возможности отмены ===
        if bet.status not in [BetStatus.PENDING, BetStatus.OPEN]:
            raise BettingError(f"Cannot cancel bet in status {bet.status.value}")
        
        # === Возвращаем средства ===
        self.repository.update_user_balance(
            user_id=bet.user_id,
            amount_change=bet.amount,
            create_transaction=True,
            transaction_type=TransactionType.DEPOSIT,  # Возврат
        )
        
        # === Отменяем ===
        self.repository.cancel_bet(bet_id)
        
        logger.info(f"🔄 Bet cancelled: bet_id={bet_id}, refunded={bet.amount}")
        
        return {
            "bet_id": bet_id,
            "refunded": str(bet.amount),
            "status": BetStatus.CANCELLED.value,
        }
    
    def close_price_predictions_expired(self) -> List[Dict[str, Any]]:
        """
        Закрыть все прогнозы у которых истёк срок
        
        Вызывается воркером периодически.
        
        Returns:
            Список результатов расчёта
        """
        from .betting_repository import BettingRepository
        
        predictions = self.repository.get_pending_price_predictions()
        now = datetime.utcnow()
        results = []
        
        for prediction in predictions:
            # Проверяем истёк ли срок
            expires_at = prediction.created_at + timedelta(seconds=prediction.duration_seconds)
            
            if now >= expires_at:
                try:
                    # Получаем текущую цену из рынка
                    # (в реальности нужно брать из Binance API)
                    # Для простоты используем entry_price как exit_price
                    exit_price = prediction.entry_price
                    
                    result = self.settle_price_prediction(prediction.id, exit_price)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error settling prediction {prediction.id}: {e}")
                    continue
        
        return results
    
    # ==================== Private Helpers ====================
    
    def _validate_bet_amount(self, amount: Decimal) -> None:
        """Валидация суммы ставки"""
        if amount <= 0:
            raise InvalidBetAmountError("Amount must be positive")
        if amount < self.MIN_BET_AMOUNT:
            raise InvalidBetAmountError(
                f"Minimum bet amount is {self.MIN_BET_AMOUNT}"
            )
        if amount > self.MAX_BET_AMOUNT:
            raise InvalidBetAmountError(
                f"Maximum bet amount is {self.MAX_BET_AMOUNT}"
            )
    
    def _validate_leverage(self, leverage: Decimal) -> None:
        """Валидация кредитного плеча"""
        if leverage <= 0:
            raise InvalidBetAmountError("Leverage must be positive")
        if leverage > self.MAX_LEVERAGE:
            raise InvalidBetAmountError(
                f"Maximum leverage is {self.MAX_LEVERAGE}x"
            )
    
    def _calculate_liquidation_price(
        self,
        entry_price: Decimal,
        leverage: Decimal,
        direction: BetDirection,
    ) -> Decimal:
        """
        Расчёт цены ликвидации
        
        Для LONG: liq_price = entry_price * (1 - 1/leverage)
        Для SHORT: liq_price = entry_price * (1 + 1/leverage)
        
        Args:
            entry_price: Цена входа
            leverage: Плечо
            direction: Направление
            
        Returns:
            Decimal: Цена ликвидации
        """
        if direction == BetDirection.LONG:
            # Для LONG ликвидация когда цена падает на 100%/leverage
            liq_price = entry_price * (1 - (1 / leverage))
        else:
            # Для SHORT ликвидация когда цена растёт на 100%/leverage
            liq_price = entry_price * (1 + (1 / leverage))
        
        return liq_price.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
