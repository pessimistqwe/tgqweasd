"""
BettingRepository - слой доступа к данным для Core Betting Engine

Реализует паттерн Repository для инкапсуляции работы с базой данных.
Все операции используют Decimal для точных финансовых вычислений.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, update
from decimal import Decimal
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any

try:
    from .betting_models import Bet, BetType, BetDirection, BetStatus, PricePrediction
    from .models import User, Event, EventOption, Transaction, TransactionType, TransactionStatus
except ImportError:
    from betting_models import Bet, BetType, BetDirection, BetStatus, PricePrediction
    from models import User, Event, EventOption, Transaction, TransactionType, TransactionStatus


class BettingRepository:
    """
    Repository для управления ставками
    
    Все методы возвращают данные и не коммитят транзакцию -
    это позволяет сервисному слою управлять транзакциями.
    """
    
    def __init__(self, db: Session):
        """
        Инициализация репозитория
        
        Args:
            db: Сессия SQLAlchemy
        """
        self.db = db
    
    # ==================== Bet Operations ====================
    
    def create_bet(
        self,
        user_id: int,
        market_id: int,
        bet_type: BetType,
        direction: BetDirection,
        amount: Decimal,
        entry_price: Decimal,
        shares: Decimal = Decimal("0"),
        leverage: Decimal = Decimal("1"),
        liquidation_price: Optional[Decimal] = None,
        potential_payout: Decimal = Decimal("0"),
        symbol: Optional[str] = None,
        take_profit_price: Optional[Decimal] = None,
        stop_loss_price: Optional[Decimal] = None,
        comment: Optional[str] = None,
    ) -> Bet:
        """
        Создать новую ставку в БД
        
        Args:
            user_id: ID пользователя
            market_id: ID рынка (события)
            bet_type: Тип ставки (event/price)
            direction: Направление (yes/no/long/short)
            amount: Сумма ставки в USDT
            entry_price: Цена входа
            shares: Количество акций (для EVENT)
            leverage: Кредитное плечо (для PRICE)
            liquidation_price: Цена ликвидации (для PRICE)
            potential_payout: Потенциальный выигрыш
            symbol: Символ актива (для PRICE)
            take_profit_price: Цена тейк-профита
            stop_loss_price: Цена стоп-лосса
            comment: Комментарий
            
        Returns:
            Bet: Созданный объект ставки
        """
        bet = Bet(
            user_id=user_id,
            market_id=market_id,
            bet_type=bet_type,
            direction=direction,
            amount=amount,
            entry_price=entry_price,
            shares=shares,
            leverage=leverage,
            liquidation_price=liquidation_price,
            potential_payout=potential_payout,
            symbol=symbol,
            take_profit_price=take_profit_price,
            stop_loss_price=stop_loss_price,
            comment=comment,
            status=BetStatus.PENDING,  # Начальный статус - ожидание
        )
        self.db.add(bet)
        self.db.flush()  # Получаем ID ставки
        return bet
    
    def get_bet_by_id(self, bet_id: int) -> Optional[Bet]:
        """
        Получить ставку по ID
        
        Args:
            bet_id: ID ставки
            
        Returns:
            Bet или None если не найдено
        """
        return self.db.query(Bet).filter(Bet.id == bet_id).first()
    
    def get_bet_with_lock(self, bet_id: int) -> Optional[Bet]:
        """
        Получить ставку с блокировкой строки (FOR UPDATE)
        
        Используется для предотвращения race conditions при обновлении.
        
        Args:
            bet_id: ID ставки
            
        Returns:
            Bet или None если не найдено
        """
        return self.db.query(Bet).filter(
            Bet.id == bet_id
        ).with_for_update().first()
    
    def get_user_bets(
        self,
        user_id: int,
        status: Optional[BetStatus] = None,
        bet_type: Optional[BetType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Bet]:
        """
        Получить ставки пользователя с фильтрацией
        
        Args:
            user_id: ID пользователя
            status: Фильтр по статусу (опционально)
            bet_type: Фильтр по типу (опционально)
            limit: Лимит записей
            offset: Смещение
            
        Returns:
            Список ставок
        """
        query = self.db.query(Bet).filter(Bet.user_id == user_id)
        
        if status:
            query = query.filter(Bet.status == status)
        if bet_type:
            query = query.filter(Bet.bet_type == bet_type)
        
        return query.order_by(
            Bet.created_at.desc()
        ).offset(offset).limit(limit).all()
    
    def get_open_bets(self, bet_type: Optional[BetType] = None) -> List[Bet]:
        """
        Получить все открытые ставки
        
        Args:
            bet_type: Фильтр по типу (опционально)
            
        Returns:
            Список открытых ставок
        """
        query = self.db.query(Bet).filter(
            Bet.status.in_([BetStatus.OPEN, BetStatus.PENDING])
        )
        
        if bet_type:
            query = query.filter(Bet.bet_type == bet_type)
        
        return query.all()
    
    def get_market_bets(
        self,
        market_id: int,
        status: Optional[BetStatus] = None,
    ) -> List[Bet]:
        """
        Получить все ставки по рынку
        
        Args:
            market_id: ID рынка
            status: Фильтр по статусу (опционально)
            
        Returns:
            Список ставок
        """
        query = self.db.query(Bet).filter(Bet.market_id == market_id)
        
        if status:
            query = query.filter(Bet.status == status)
        
        return query.all()
    
    def update_bet_status(
        self,
        bet_id: int,
        status: BetStatus,
        resolved_at: Optional[datetime] = None,
    ) -> bool:
        """
        Обновить статус ставки
        
        Args:
            bet_id: ID ставки
            status: Новый статус
            resolved_at: Время расчёта (опционально)
            
        Returns:
            bool: True если обновлено, False если не найдено
        """
        result = self.db.execute(
            update(Bet)
            .where(Bet.id == bet_id)
            .values(
                status=status,
                resolved_at=resolved_at or datetime.utcnow(),
            )
        )
        return result.rowcount > 0
    
    def update_bet_payout(
        self,
        bet_id: int,
        actual_payout: Decimal,
        exit_price: Optional[Decimal] = None,
    ) -> bool:
        """
        Обновить фактический выигрыш ставки
        
        Args:
            bet_id: ID ставки
            actual_payout: Фактический выигрыш
            exit_price: Цена выхода (опционально)
            
        Returns:
            bool: True если обновлено, False если не найдено
        """
        result = self.db.execute(
            update(Bet)
            .where(Bet.id == bet_id)
            .values(
                actual_payout=actual_payout,
                exit_price=exit_price,
            )
        )
        return result.rowcount > 0
    
    def cancel_bet(self, bet_id: int) -> bool:
        """
        Отменить ставку (возврат в статус CANCELLED)
        
        Args:
            bet_id: ID ставки
            
        Returns:
            bool: True если отменено, False если не найдено или нельзя отменить
        """
        bet = self.get_bet_with_lock(bet_id)
        if not bet or bet.status not in [BetStatus.PENDING, BetStatus.OPEN]:
            return False
        
        bet.status = BetStatus.CANCELLED
        bet.resolved_at = datetime.utcnow()
        return True
    
    # ==================== PricePrediction Operations ====================
    
    def create_price_prediction(
        self,
        user_id: int,
        market_id: int,
        direction: BetDirection,
        symbol: str,
        amount: Decimal,
        odds: Decimal,
        entry_price: Decimal,
        potential_payout: Decimal,
        duration_seconds: int = 300,
    ) -> PricePrediction:
        """
        Создать краткосрочный прогноз цены
        
        Args:
            user_id: ID пользователя
            market_id: ID рынка
            direction: Направление (long=вверх, short=вниз)
            symbol: Символ актива (BTCUSDT и т.д.)
            amount: Сумма ставки в USDT
            odds: Коэффициент
            entry_price: Цена входа
            potential_payout: Потенциальный выигрыш
            duration_seconds: Длительность в секундах
            
        Returns:
            PricePrediction: Созданный объект прогноза
        """
        prediction = PricePrediction(
            user_id=user_id,
            market_id=market_id,
            direction=direction,
            symbol=symbol,
            amount=amount,
            odds=odds,
            entry_price=entry_price,
            potential_payout=potential_payout,
            duration_seconds=duration_seconds,
            status=BetStatus.PENDING,
        )
        self.db.add(prediction)
        self.db.flush()
        return prediction
    
    def get_price_prediction_by_id(self, prediction_id: int) -> Optional[PricePrediction]:
        """
        Получить прогноз по ID
        
        Args:
            prediction_id: ID прогноза
            
        Returns:
            PricePrediction или None если не найдено
        """
        return self.db.query(PricePrediction).filter(
            PricePrediction.id == prediction_id
        ).first()
    
    def get_price_prediction_with_lock(self, prediction_id: int) -> Optional[PricePrediction]:
        """
        Получить прогноз с блокировкой строки (FOR UPDATE)
        
        Args:
            prediction_id: ID прогноза
            
        Returns:
            PricePrediction или None если не найдено
        """
        return self.db.query(PricePrediction).filter(
            PricePrediction.id == prediction_id
        ).with_for_update().first()
    
    def get_user_price_predictions(
        self,
        user_id: int,
        status: Optional[BetStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[PricePrediction]:
        """
        Получить прогнозы пользователя с фильтрацией
        
        Args:
            user_id: ID пользователя
            status: Фильтр по статусу (опционально)
            limit: Лимит записей
            offset: Смещение
            
        Returns:
            Список прогнозов
        """
        query = self.db.query(PricePrediction).filter(
            PricePrediction.user_id == user_id
        )
        
        if status:
            query = query.filter(PricePrediction.status == status)
        
        return query.order_by(
            PricePrediction.created_at.desc()
        ).offset(offset).limit(limit).all()
    
    def get_pending_price_predictions(self) -> List[PricePrediction]:
        """
        Получить все активные прогнозы, ожидающие расчёта
        
        Returns:
            Список активных прогнозов
        """
        now = datetime.utcnow()
        return self.db.query(PricePrediction).filter(
            PricePrediction.status.in_([BetStatus.PENDING, BetStatus.OPEN]),
            # Прогноз активен если время ещё не вышло
            PricePrediction.created_at != None,
        ).all()
    
    def update_price_prediction_status(
        self,
        prediction_id: int,
        status: BetStatus,
        resolved_at: Optional[datetime] = None,
        exit_price: Optional[Decimal] = None,
        actual_payout: Decimal = Decimal("0"),
    ) -> bool:
        """
        Обновить статус прогноза
        
        Args:
            prediction_id: ID прогноза
            status: Новый статус
            resolved_at: Время расчёта (опционально)
            exit_price: Цена выхода (опционально)
            actual_payout: Фактический выигрыш (опционально)
            
        Returns:
            bool: True если обновлено, False если не найдено
        """
        result = self.db.execute(
            update(PricePrediction)
            .where(PricePrediction.id == prediction_id)
            .values(
                status=status,
                resolved_at=resolved_at or datetime.utcnow(),
                exit_price=exit_price,
                actual_payout=actual_payout,
            )
        )
        return result.rowcount > 0
    
    # ==================== User Balance Operations ====================
    
    def get_user_balance(self, user_id: int) -> Decimal:
        """
        Получить баланс пользователя в USDT
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Decimal: Баланс в USDT
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return Decimal("0")
        # Конвертируем Float в Decimal для точности
        return Decimal(str(user.balance_usdt or 0))
    
    def update_user_balance(
        self,
        user_id: int,
        amount_change: Decimal,
        create_transaction: bool = True,
        transaction_type: TransactionType = TransactionType.BET_PLACED,
    ) -> Tuple[bool, Decimal]:
        """
        Обновить баланс пользователя
        
        Args:
            user_id: ID пользователя
            amount_change: Изменение баланса (положительное = начисление, отрицательное = списание)
            create_transaction: Создать запись транзакции
            transaction_type: Тип транзакции
            
        Returns:
            Tuple[bool, Decimal]: (успех, новый баланс)
        """
        user = self.db.query(User).filter(User.id == user_id).with_for_update().first()
        if not user:
            return False, Decimal("0")
        
        # Обновляем баланс
        current_balance = Decimal(str(user.balance_usdt or 0))
        new_balance = current_balance + amount_change
        
        # Проверка на отрицательный баланс (не должно происходить)
        if new_balance < 0:
            return False, current_balance
        
        user.balance_usdt = float(new_balance)
        
        # Создаём транзакцию если нужно
        if create_transaction:
            transaction = Transaction(
                user_id=user_id,
                type=transaction_type,
                amount=abs(float(amount_change)),
                asset="USDT",
                status=TransactionStatus.COMPLETED,
            )
            self.db.add(transaction)
        
        return True, new_balance
    
    def check_user_balance(self, user_id: int, required_amount: Decimal) -> bool:
        """
        Проверить достаточно ли средств у пользователя
        
        Args:
            user_id: ID пользователя
            required_amount: Требуемая сумма
            
        Returns:
            bool: True если средств достаточно
        """
        balance = self.get_user_balance(user_id)
        return balance >= required_amount
    
    # ==================== Event/Market Operations ====================
    
    def get_event_option_price(self, event_id: int, option_index: int) -> Optional[Decimal]:
        """
        Получить текущую цену опциона события
        
        Args:
            event_id: ID события
            option_index: Индекс опциона
            
        Returns:
            Decimal: Цена опциона или None если не найдено
        """
        option = self.db.query(EventOption).filter(
            and_(
                EventOption.event_id == event_id,
                EventOption.option_index == option_index,
            )
        ).first()
        
        if not option:
            return None
        
        return Decimal(str(option.current_price or Decimal("0.5")))
    
    def get_event_by_id(self, event_id: int) -> Optional[Event]:
        """
        Получить событие по ID
        
        Args:
            event_id: ID события
            
        Returns:
            Event или None если не найдено
        """
        return self.db.query(Event).filter(Event.id == event_id).first()
    
    # ==================== Statistics ====================
    
    def get_user_betting_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Получить статистику ставок пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Dict со статистикой
        """
        # Общая сумма ставок
        total_bets = self.db.query(func.count(Bet.id)).filter(
            Bet.user_id == user_id
        ).scalar() or 0
        
        # Активные ставки
        active_bets = self.db.query(func.count(Bet.id)).filter(
            Bet.user_id == user_id,
            Bet.status.in_([BetStatus.OPEN, BetStatus.PENDING]),
        ).scalar() or 0
        
        # Выигрышные ставки
        won_bets = self.db.query(func.count(Bet.id)).filter(
            Bet.user_id == user_id,
            Bet.status == BetStatus.WON,
        ).scalar() or 0
        
        # Общая сумма выигрышей
        total_winnings = self.db.query(func.sum(Bet.actual_payout)).filter(
            Bet.user_id == user_id,
            Bet.status == BetStatus.WON,
        ).scalar() or Decimal("0")
        
        return {
            "total_bets": total_bets,
            "active_bets": active_bets,
            "won_bets": won_bets,
            "total_winnings": str(total_winnings),
        }
    
    def get_market_stats(self, market_id: int) -> Dict[str, Any]:
        """
        Получить статистику рынка
        
        Args:
            market_id: ID рынка
            
        Returns:
            Dict со статистикой
        """
        # Общая сумма ставок на рынке
        total_volume = self.db.query(func.sum(Bet.amount)).filter(
            Bet.market_id == market_id,
        ).scalar() or Decimal("0")
        
        # Количество ставок
        total_bets = self.db.query(func.count(Bet.id)).filter(
            Bet.market_id == market_id,
        ).scalar() or 0
        
        # Активные ставки
        active_bets = self.db.query(func.count(Bet.id)).filter(
            Bet.market_id == market_id,
            Bet.status.in_([BetStatus.OPEN, BetStatus.PENDING]),
        ).scalar() or 0
        
        return {
            "total_volume": str(total_volume),
            "total_bets": total_bets,
            "active_bets": active_bets,
        }
