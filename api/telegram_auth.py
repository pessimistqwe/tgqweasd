"""
Telegram initData Validator

Утилита для валидации данных от Telegram WebApp.
Использует HMAC-SHA256 для проверки подлинности данных.

Документация: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""

import hmac
import hashlib
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta


class TelegramAuthError(Exception):
    """Ошибка аутентификации Telegram"""
    pass


class TelegramAuthValidator:
    """
    Валидатор initData от Telegram
    
    Пример использования:
        validator = TelegramAuthValidator(bot_token)
        user_data = validator.validate(init_data)
    """
    
    def __init__(self, bot_token: str):
        """
        Инициализация валидатора
        
        Args:
            bot_token: Токен бота от @BotFather
        """
        self.bot_token = bot_token
    
    def validate(self, init_data: str, max_age_seconds: int = 300) -> Dict[str, Any]:
        """
        Валидировать initData от Telegram
        
        Args:
            init_data: Строка initData из Telegram WebApp
            max_age_seconds: Максимальный возраст данных (по умолчанию 5 минут)
            
        Returns:
            Dict с данными пользователя:
            {
                "user": {...},
                "chat": {...},
                "auth_date": datetime,
                ...
            }
            
        Raises:
            TelegramAuthError: Если данные невалидны
        """
        if not init_data:
            raise TelegramAuthError("initData is empty")
        
        # Парсим строку initData
        parsed_data = self._parse_init_data(init_data)
        
        # Извлекаем hash для проверки
        received_hash = parsed_data.pop('hash', None)
        if not received_hash:
            raise TelegramAuthError("hash is missing")
        
        # Проверяем возраст данных
        auth_date = parsed_data.get('auth_date')
        if auth_date:
            auth_timestamp = int(auth_date)
            if time.time() - auth_timestamp > max_age_seconds:
                raise TelegramAuthError("initData is too old")
        
        # Вычисляем ожидаемый hash
        expected_hash = self._compute_hash(parsed_data)
        
        # Сравниваем hash
        if not hmac.compare_digest(received_hash, expected_hash):
            raise TelegramAuthError("hash mismatch")
        
        # Возвращаем распарсенные данные
        return self._parse_user_data(parsed_data)
    
    def _parse_init_data(self, init_data: str) -> Dict[str, str]:
        """
        Распарсить строку initData в словарь
        
        Формат: key1=value1&key2=value2...
        """
        result = {}
        
        for pair in init_data.split('&'):
            if '=' in pair:
                key, value = pair.split('=', 1)
                result[key] = value
        
        return result
    
    def _compute_hash(self, data: Dict[str, str]) -> str:
        """
        Вычислить HMAC-SHA256 hash для данных
        
        Алгоритм:
        1. Сортируем ключи
        2. Формируем строку data_check_string
        3. Вычисляем HMAC-SHA256 с ключом derived from bot_token
        """
        # Сортируем ключи
        sorted_keys = sorted(data.keys())
        
        # Формируем строку для хеширования
        data_check_string = '\n'.join(
            f"{key}={data[key]}" for key in sorted_keys
        )
        
        # Создаём ключ для HMAC
        # Key = HMAC-SHA256("WebAppData", bot_token)
        secret_key = hmac.new(
            b"WebAppData",
            self.bot_token.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        # Вычисляем hash
        computed_hash = hmac.new(
            secret_key,
            data_check_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return computed_hash
    
    def _parse_user_data(self, data: Dict[str, str]) -> Dict[str, Any]:
        """
        Распарсить данные пользователя из строковых значений
        
        Преобразует JSON-строки в словари (user, chat и т.д.)
        """
        import json
        
        result = {}
        
        for key, value in data.items():
            # Пытаемся распарсить JSON для сложных полей
            if key in ('user', 'chat', 'receiver', 'chat_type'):
                try:
                    result[key] = json.loads(value)
                except json.JSONDecodeError:
                    result[key] = value
            elif key == 'auth_date':
                try:
                    result[key] = datetime.fromtimestamp(int(value))
                except (ValueError, TypeError):
                    result[key] = value
            else:
                result[key] = value
        
        return result


# Глобальный валидатор (инициализируется при старте)
_validator: Optional[TelegramAuthValidator] = None


def init_telegram_validator(bot_token: str) -> None:
    """
    Инициализировать глобальный валидатор
    
    Args:
        bot_token: Токен бота
    """
    global _validator
    _validator = TelegramAuthValidator(bot_token)


def validate_telegram_init_data(init_data: str) -> Dict[str, Any]:
    """
    Валидировать initData используя глобальный валидатор
    
    Args:
        init_data: Строка initData от Telegram
        
    Returns:
        Dict с данными пользователя
        
    Raises:
        TelegramAuthError: Если данные невалидны
    """
    if not _validator:
        raise TelegramAuthError("Validator not initialized")
    
    return _validator.validate(init_data)


def get_telegram_user_from_init_data(init_data: str) -> Optional[Dict[str, Any]]:
    """
    Безопасно получить данные пользователя из initData
    
    Args:
        init_data: Строка initData от Telegram
        
    Returns:
        Dict с данными пользователя или None если ошибка
    """
    try:
        data = validate_telegram_init_data(init_data)
        return data.get('user')
    except TelegramAuthError:
        return None
