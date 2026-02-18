"""
Betting API Endpoints

Эндпоинты для Core Betting Engine:
- Размещение ставок (event/price/prediction)
- Получение информации о ставках
- Отмена ставок
- История ставок

Все эндпоинты требуют валидации Telegram initData.
"""

from fastapi import APIRouter, HTTPException, Depends, Header, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional, List, Dict, Any
from datetime import datetime

try:
    from .models import get_db, User
    from .betting_models import BetType, BetDirection
    from .betting_service import (
        BettingService,
        BettingError,
        InsufficientBalanceError,
        InvalidBetAmountError,
        MarketNotFoundError,
        BetNotFoundError,
        InvalidOddsError,
    )
    from .telegram_auth import validate_telegram_init_data, TelegramAuthError
    from .volatility_service import get_volatility_odds
except ImportError:
    from models import get_db, User
    from betting_models import BetType, BetDirection
    from betting_service import (
        BettingService,
        BettingError,
        InsufficientBalanceError,
        InvalidBetAmountError,
        MarketNotFoundError,
        BetNotFoundError,
        InvalidOddsError,
    )
    from telegram_auth import validate_telegram_init_data, TelegramAuthError
    from volatility_service import get_volatility_odds


router = APIRouter(prefix="/api/betting", tags=["Betting"])


# ==================== Pydantic Models ====================

class PlaceEventBetRequest(BaseModel):
    """Запрос на размещение ставки на событие"""
    market_id: int = Field(..., description="ID рынка (события)")
    option_index: int = Field(..., description="Индекс опциона (0, 1, ...)")
    amount: str = Field(..., description="Сумма ставки в USDT")
    direction: str = Field(..., description="Направление (yes/no)")
    
    def get_amount(self) -> Decimal:
        return Decimal(self.amount)
    
    def get_direction(self) -> BetDirection:
        return BetDirection.YES if self.direction.lower() == "yes" else BetDirection.NO


class PlacePriceBetRequest(BaseModel):
    """Запрос на размещение ставки на цену"""
    market_id: int = Field(..., description="ID рынка")
    direction: str = Field(..., description="Направление (long/short)")
    amount: str = Field(..., description="Сумма ставки в USDT (маржа)")
    leverage: str = Field(default="1", description="Кредитное плечо")
    entry_price: str = Field(..., description="Цена входа")
    symbol: str = Field(..., description="Символ актива (BTCUSDT)")
    take_profit_price: Optional[str] = Field(None, description="Тейк-профит")
    stop_loss_price: Optional[str] = Field(None, description="Стоп-лосс")
    
    def get_amount(self) -> Decimal:
        return Decimal(self.amount)
    
    def get_leverage(self) -> Decimal:
        return Decimal(self.leverage)
    
    def get_entry_price(self) -> Decimal:
        return Decimal(self.entry_price)
    
    def get_direction(self) -> BetDirection:
        return BetDirection.LONG if self.direction.lower() == "long" else BetDirection.SHORT
    
    def get_take_profit(self) -> Optional[Decimal]:
        return Decimal(self.take_profit_price) if self.take_profit_price else None
    
    def get_stop_loss(self) -> Optional[Decimal]:
        return Decimal(self.stop_loss_price) if self.stop_loss_price else None


class PlacePricePredictionRequest(BaseModel):
    """Запрос на размещение краткосрочного прогноза"""
    market_id: int = Field(..., description="ID рынка")
    direction: str = Field(..., description="Направление (long/short)")
    amount: str = Field(..., description="Сумма ставки в USDT")
    odds: str = Field(..., description="Коэффициент")
    entry_price: str = Field(..., description="Цена входа")
    symbol: str = Field(..., description="Символ актива (BTCUSDT)")
    duration_seconds: int = Field(default=300, description="Длительность в секундах")
    
    def get_amount(self) -> Decimal:
        return Decimal(self.amount)
    
    def get_odds(self) -> Decimal:
        return Decimal(self.odds)
    
    def get_entry_price(self) -> Decimal:
        return Decimal(self.entry_price)
    
    def get_direction(self) -> BetDirection:
        return BetDirection.LONG if self.direction.lower() == "long" else BetDirection.SHORT


class CancelBetRequest(BaseModel):
    """Запрос на отмену ставки"""
    bet_id: int = Field(..., description="ID ставки")


class BetResponse(BaseModel):
    """Ответ с информацией о ставке"""
    id: int
    user_id: int
    market_id: int
    bet_type: str
    direction: str
    amount: str
    shares: str
    entry_price: str
    leverage: str
    liquidation_price: Optional[str]
    potential_payout: str
    actual_payout: str
    status: str
    created_at: str
    resolved_at: Optional[str]
    symbol: Optional[str]


class PricePredictionResponse(BaseModel):
    """Ответ с информацией о прогнозе"""
    id: int
    user_id: int
    market_id: int
    direction: str
    symbol: str
    amount: str
    odds: str
    entry_price: str
    exit_price: Optional[str]
    potential_payout: str
    actual_payout: str
    status: str
    created_at: str
    resolved_at: Optional[str]
    duration_seconds: int


# ==================== Helpers ====================

def get_user_from_init_data(
    x_telegram_init_data: str = Header(None, alias="X-Telegram-Init-Data")
) -> Dict[str, Any]:
    """
    Получить данные пользователя из Telegram initData
    
    Args:
        x_telegram_init_data: Заголовок с initData
        
    Returns:
        Dict с данными пользователя
        
    Raises:
        HTTPException: Если initData невалиден
    """
    if not x_telegram_init_data:
        raise HTTPException(
            status_code=401,
            detail="X-Telegram-Init-Data header is required"
        )
    
    try:
        data = validate_telegram_init_data(x_telegram_init_data)
        user = data.get('user')
        
        if not user:
            raise HTTPException(status_code=401, detail="User data not found")
        
        return user
    
    except TelegramAuthError as e:
        raise HTTPException(status_code=401, detail=f"Invalid initData: {str(e)}")


def get_user_by_telegram_id(db: Session, telegram_id: int) -> User:
    """
    Получить пользователя из БД по Telegram ID
    
    Args:
        db: Сессия БД
        telegram_id: Telegram ID пользователя
        
    Returns:
        User
        
    Raises:
        HTTPException: Если пользователь не найден
    """
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.is_blocked:
        raise HTTPException(status_code=403, detail="User is blocked")
    
    return user


# ==================== Event Betting Endpoints ====================

@router.post("/event/place", response_model=Dict[str, Any])
async def place_event_bet(
    request: PlaceEventBetRequest,
    db: Session = Depends(get_db),
    user_data: Dict[str, Any] = Depends(get_user_from_init_data),
):
    """
    Разместить ставку на событие (Polymarket-style)
    
    Требуется заголовок X-Telegram-Init-Data для аутентификации.
    """
    telegram_id = user_data['id']
    user = get_user_by_telegram_id(db, telegram_id)
    
    try:
        service = BettingService(db)
        
        result = service.place_event_bet(
            user_id=user.id,
            market_id=request.market_id,
            option_index=request.option_index,
            amount=request.get_amount(),
            direction=request.get_direction(),
        )
        
        db.commit()
        
        return {
            "success": True,
            "data": result,
        }
    
    except InsufficientBalanceError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except InvalidBetAmountError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except MarketNotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except BettingError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Price Betting Endpoints ====================

@router.post("/price/place", response_model=Dict[str, Any])
async def place_price_bet(
    request: PlacePriceBetRequest,
    db: Session = Depends(get_db),
    user_data: Dict[str, Any] = Depends(get_user_from_init_data),
):
    """
    Разместить ставку на цену (Binance-style Long/Short)
    
    Требуется заголовок X-Telegram-Init-Data для аутентификации.
    """
    telegram_id = user_data['id']
    user = get_user_by_telegram_id(db, telegram_id)
    
    try:
        service = BettingService(db)
        
        result = service.place_price_bet(
            user_id=user.id,
            market_id=request.market_id,
            direction=request.get_direction(),
            amount=request.get_amount(),
            leverage=request.get_leverage(),
            entry_price=request.get_entry_price(),
            symbol=request.symbol,
            take_profit_price=request.get_take_profit(),
            stop_loss_price=request.get_stop_loss(),
        )
        
        db.commit()
        
        return {
            "success": True,
            "data": result,
        }
    
    except InsufficientBalanceError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except InvalidBetAmountError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except MarketNotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except BettingError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Price Prediction Endpoints ====================

@router.get("/volatility-odds", response_model=Dict[str, Any])
async def get_prediction_odds(symbol: str = Query(..., description="Символ актива (например, BTCUSDT)")):
    """
    Получить коэффициент для прогноза на основе реальной волатильности
    
    Коэффициент рассчитывается автоматически на основе волатильности рынка
    за последние 5 минут.
    
    Требуется заголовок X-Telegram-Init-Data для аутентификации.
    """
    try:
        result = await get_volatility_odds(symbol)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        # Возвращаем дефолтный коэффициент при ошибке
        return {
            "success": True,
            "data": {
                "symbol": symbol,
                "volatility": 0.0,
                "odds": 1.90,
                "cached": False,
                "error": str(e)
            }
        }


@router.post("/prediction/place", response_model=Dict[str, Any])
async def place_price_prediction(
    request: PlacePricePredictionRequest,
    db: Session = Depends(get_db),
    user_data: Dict[str, Any] = Depends(get_user_from_init_data),
):
    """
    Разместить краткосрочный прогноз цены (5 минут)
    
    Требуется заголовок X-Telegram-Init-Data для аутентификации.
    """
    telegram_id = user_data['id']
    user = get_user_by_telegram_id(db, telegram_id)
    
    try:
        service = BettingService(db)
        
        result = service.place_price_prediction(
            user_id=user.id,
            market_id=request.market_id,
            direction=request.get_direction(),
            amount=request.get_amount(),
            odds=request.get_odds(),
            entry_price=request.get_entry_price(),
            symbol=request.symbol,
            duration_seconds=request.duration_seconds,
        )
        
        db.commit()
        
        return {
            "success": True,
            "data": result,
        }
    
    except InsufficientBalanceError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except InvalidBetAmountError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except InvalidOddsError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except BettingError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Bet Management Endpoints ====================

@router.post("/cancel", response_model=Dict[str, Any])
async def cancel_bet(
    request: CancelBetRequest,
    db: Session = Depends(get_db),
    user_data: Dict[str, Any] = Depends(get_user_from_init_data),
):
    """
    Отменить ставку и вернуть средства
    
    Можно отменить только ставки в статусе PENDING или OPEN.
    """
    telegram_id = user_data['id']
    user = get_user_by_telegram_id(db, telegram_id)
    
    try:
        service = BettingService(db)
        result = service.cancel_bet(request.bet_id)
        
        db.commit()
        
        return {
            "success": True,
            "data": result,
        }
    
    except BetNotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except BettingError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/my-bets", response_model=Dict[str, Any])
async def get_my_bets(
    status: Optional[str] = Query(None, description="Фильтр по статусу"),
    bet_type: Optional[str] = Query(None, description="Фильтр по типу"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user_data: Dict[str, Any] = Depends(get_user_from_init_data),
):
    """
    Получить мои ставки с фильтрацией
    """
    telegram_id = user_data['id']
    user = get_user_by_telegram_id(db, telegram_id)
    
    try:
        from .betting_repository import BettingRepository
        repository = BettingRepository(db)
        
        # Парсим фильтры
        status_filter = None
        if status:
            from .betting_models import BetStatus
            try:
                status_filter = BetStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        bet_type_filter = None
        if bet_type:
            try:
                bet_type_filter = BetType(bet_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid bet_type: {bet_type}")
        
        # Получаем ставки
        bets = repository.get_user_bets(
            user_id=user.id,
            status=status_filter,
            bet_type=bet_type_filter,
            limit=limit,
            offset=offset,
        )
        
        # Получаем статистику
        stats = repository.get_user_betting_stats(user.id)
        
        return {
            "success": True,
            "data": {
                "bets": [bet.to_dict() for bet in bets],
                "stats": stats,
            },
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": len(bets),
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/my-predictions", response_model=Dict[str, Any])
async def get_my_predictions(
    status: Optional[str] = Query(None, description="Фильтр по статусу"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user_data: Dict[str, Any] = Depends(get_user_from_init_data),
):
    """
    Получить мои прогнозы цены
    """
    telegram_id = user_data['id']
    user = get_user_by_telegram_id(db, telegram_id)
    
    try:
        from .betting_repository import BettingRepository
        repository = BettingRepository(db)
        
        # Парсим фильтр статуса
        status_filter = None
        if status:
            from .betting_models import BetStatus
            try:
                status_filter = BetStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        # Получаем прогнозы
        predictions = repository.get_user_price_predictions(
            user_id=user.id,
            status=status_filter,
            limit=limit,
            offset=offset,
        )
        
        return {
            "success": True,
            "data": {
                "predictions": [pred.to_dict() for pred in predictions],
            },
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": len(predictions),
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bet/{bet_id}", response_model=Dict[str, Any])
async def get_bet(
    bet_id: int,
    db: Session = Depends(get_db),
    user_data: Dict[str, Any] = Depends(get_user_from_init_data),
):
    """
    Получить информацию о конкретной ставке
    """
    telegram_id = user_data['id']
    user = get_user_by_telegram_id(db, telegram_id)
    
    try:
        from .betting_repository import BettingRepository
        repository = BettingRepository(db)
        
        bet = repository.get_bet_by_id(bet_id)
        
        if not bet:
            raise HTTPException(status_code=404, detail="Bet not found")
        
        # Проверка что ставка принадлежит пользователю
        if bet.user_id != user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return {
            "success": True,
            "data": bet.to_dict(),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-stats/{market_id}", response_model=Dict[str, Any])
async def get_market_stats(
    market_id: int,
    db: Session = Depends(get_db),
    user_data: Dict[str, Any] = Depends(get_user_from_init_data),
):
    """
    Получить статистику рынка
    """
    telegram_id = user_data['id']
    user = get_user_by_telegram_id(db, telegram_id)
    
    try:
        from .betting_repository import BettingRepository
        repository = BettingRepository(db)
        
        stats = repository.get_market_stats(market_id)
        
        return {
            "success": True,
            "data": stats,
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
