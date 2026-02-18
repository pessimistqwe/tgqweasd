"""
Модели данных для Core Betting Engine

Поддерживает два типа рынков:
1. Polymarket Style (события): Outcome Yes/No, Shares, Price per share
2. Binance Style (цены): Direction Long/Short, Entry Price, Liquidation Price, Leverage

Все финансовые вычисления используют Decimal для точности.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum, DECIMAL, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from decimal import Decimal

# Импортируем Base из основных моделей
try:
    from .models import Base
except ImportError:
    from models import Base


class BetType(str, enum.Enum):
    """Тип рынка"""
    EVENT = "event"  # Polymarket-style (события)
    PRICE = "price"  # Binance-style (прогноз цены)


class BetDirection(str, enum.Enum):
    """Направление ставки"""
    # Для событий (Polymarket)
    YES = "yes"
    NO = "no"
    # Для цен (Binance)
    LONG = "long"  # Ставка на рост
    SHORT = "short"  # Ставка на падение


class BetStatus(str, enum.Enum):
    """Статус ставки"""
    OPEN = "open"  # Активная ставка
    CLOSED = "closed"  # Закрыта (результат определён)
    WON = "won"  # Выигрышная
    LOST = "lost"  # Проигрышная
    CANCELLED = "cancelled"  # Отменена (возврат средств)
    PENDING = "pending"  # Ожидает подтверждения (холдирование средств)


class Bet(Base):
    """
    Основная таблица ставок
    
    Универсальная схема для обоих типов рынков:
    - EVENT: direction = yes/no, amount = сумма ставки, shares = количество акций
    - PRICE: direction = long/short, amount = сумма, leverage = плечо, entry_price = цена входа
    """
    __tablename__ = "bets"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # === Идентификация ===
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    market_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    
    # === Тип ставки ===
    bet_type = Column(Enum(BetType), nullable=False, default=BetType.EVENT)
    direction = Column(Enum(BetDirection), nullable=False)  # yes/no для событий, long/short для цен
    
    # === Финансовые параметры ===
    # Сумма ставки в USDT (используем DECIMAL для точности)
    amount = Column(DECIMAL(20, 8), nullable=False)
    
    # Для EVENT: количество акций (shares)
    # Для PRICE: размер позиции с учётом плеча (amount * leverage)
    shares = Column(DECIMAL(20, 8), default=Decimal("0"))
    
    # Цена за акцию (EVENT) или цена входа (PRICE)
    entry_price = Column(DECIMAL(20, 8), nullable=False)
    
    # Для PRICE: кредитное плечо (1x, 5x, 10x и т.д.)
    leverage = Column(DECIMAL(10, 2), default=Decimal("1"))
    
    # Цена ликвидации (для PRICE short/long)
    liquidation_price = Column(DECIMAL(20, 8), nullable=True)
    
    # Цена выхода (когда ставка закрывается)
    exit_price = Column(DECIMAL(20, 8), nullable=True)
    
    # Потенциальный выигрыш (рассчитывается при размещении)
    potential_payout = Column(DECIMAL(20, 8), default=Decimal("0"))
    
    # Фактический выигрыш (после расчёта)
    actual_payout = Column(DECIMAL(20, 8), default=Decimal("0"))
    
    # === Статус ===
    status = Column(Enum(BetStatus), nullable=False, default=BetStatus.PENDING)
    
    # === Временные метки ===
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    resolved_at = Column(DateTime, nullable=True)  # Когда ставка была рассчитана
    
    # === Метаданные ===
    # Для PRICE: символ торгуемого актива (BTCUSDT, ETHUSDT и т.д.)
    symbol = Column(String(50), nullable=True)
    
    # Для PRICE: цена тейк-профита
    take_profit_price = Column(DECIMAL(20, 8), nullable=True)
    
    # Для PRICE: цена стоп-лосса
    stop_loss_price = Column(DECIMAL(20, 8), nullable=True)
    
    # Комментарий или примечание
    comment = Column(Text, nullable=True)
    
    # === Relationships ===
    user = relationship("User", back_populates="bets")
    market = relationship("Event", back_populates="bets")
    
    # === Индексы для производительности ===
    __table_args__ = (
        Index('idx_bet_user_status', 'user_id', 'status'),
        Index('idx_bet_market_status', 'market_id', 'status'),
        Index('idx_bet_created_at', 'created_at'),
        Index('idx_bet_resolved_at', 'resolved_at'),
    )
    
    def __repr__(self):
        return f"<Bet(id={self.id}, user_id={self.user_id}, type={self.bet_type}, direction={self.direction}, amount={self.amount})>"
    
    def to_dict(self) -> dict:
        """Конвертация в словарь для API ответов"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "market_id": self.market_id,
            "bet_type": self.bet_type.value,
            "direction": self.direction.value,
            "amount": str(self.amount),
            "shares": str(self.shares),
            "entry_price": str(self.entry_price),
            "leverage": str(self.leverage),
            "liquidation_price": str(self.liquidation_price) if self.liquidation_price else None,
            "exit_price": str(self.exit_price) if self.exit_price else None,
            "potential_payout": str(self.potential_payout),
            "actual_payout": str(self.actual_payout),
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "symbol": self.symbol,
            "take_profit_price": str(self.take_profit_price) if self.take_profit_price else None,
            "stop_loss_price": str(self.stop_loss_price) if self.stop_loss_price else None,
            "comment": self.comment,
        }


class PricePrediction(Base):
    """
    Таблица для краткосрочных прогнозов цены (5-минутные ставки)
    
    Отдельная таблица для быстрых прогнозов направления цены:
    - Угадайте направление цены за 5 минут
    - Коэффициент зависит от волатильности рынка
    """
    __tablename__ = "price_predictions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # === Идентификация ===
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    market_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    
    # === Параметры прогноза ===
    direction = Column(Enum(BetDirection), nullable=False)  # LONG (вверх) или SHORT (вниз)
    
    # Символ актива (BTCUSDT, ETHUSDT и т.д.)
    symbol = Column(String(50), nullable=False)
    
    # === Финансовые параметры ===
    amount = Column(DECIMAL(20, 8), nullable=False)  # Сумма ставки в USDT
    
    # Коэффициент (odds) на момент размещения
    odds = Column(DECIMAL(10, 4), nullable=False)  # Например, 1.95x
    
    # Цена входа (когда открыли прогноз)
    entry_price = Column(DECIMAL(20, 8), nullable=False)
    
    # Цена выхода (когда закрыли прогноз)
    exit_price = Column(DECIMAL(20, 8), nullable=True)
    
    # Потенциальный выигрыш (amount * odds)
    potential_payout = Column(DECIMAL(20, 8), nullable=False)
    
    # Фактический выигрыш
    actual_payout = Column(DECIMAL(20, 8), default=Decimal("0"))
    
    # === Статус ===
    status = Column(Enum(BetStatus), nullable=False, default=BetStatus.PENDING)
    
    # === Временные метки ===
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    resolved_at = Column(DateTime, nullable=True)  # Когда прогноз рассчитан
    
    # === Длительность прогноза (в секундах) ===
    duration_seconds = Column(Integer, default=300)  # По умолчанию 5 минут
    
    # === Relationships ===
    user = relationship("User", back_populates="price_predictions")
    market = relationship("Event", back_populates="price_predictions")
    
    # === Индексы ===
    __table_args__ = (
        Index('idx_price_pred_user_status', 'user_id', 'status'),
        Index('idx_price_pred_created_at', 'created_at'),
        Index('idx_price_pred_resolved_at', 'resolved_at'),
    )
    
    def __repr__(self):
        return f"<PricePrediction(id={self.id}, user_id={self.user_id}, symbol={self.symbol}, direction={self.direction}, amount={self.amount})>"
    
    def to_dict(self) -> dict:
        """Конвертация в словарь для API ответов"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "market_id": self.market_id,
            "direction": self.direction.value,
            "symbol": self.symbol,
            "amount": str(self.amount),
            "odds": str(self.odds),
            "entry_price": str(self.entry_price),
            "exit_price": str(self.exit_price) if self.exit_price else None,
            "potential_payout": str(self.potential_payout),
            "actual_payout": str(self.actual_payout),
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "duration_seconds": self.duration_seconds,
        }


# Добавляем relationships в существующие модели
# Это нужно сделать в models.py, но здесь определяем для ясности
"""
В models.py добавить:

class User(Base):
    # ... existing fields ...
    bets = relationship("Bet", back_populates="user")
    price_predictions = relationship("PricePrediction", back_populates="user")

class Event(Base):
    # ... existing fields ...
    bets = relationship("Bet", back_populates="market")
    price_predictions = relationship("PricePrediction", back_populates="market")
"""
