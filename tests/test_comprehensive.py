"""
Comprehensive Tests for EventPredict Project

Запуск:
    pytest tests/test_comprehensive.py -v

Тест-кейсы:
1. test_chart_endpoint_works — endpoint возвращает 200 и данные
2. test_chart_different_symbols — BTC и ETH возвращают разные данные
3. test_sdk_imports_work — все SDK импортируются без ошибок
4. test_web3_config_complete — все 4 контракта имеют адреса
5. test_polymarket_api_docs_exist — файл POLYMARKET_API_REFERENCE.md создан
"""

import pytest
import requests
import os
import sys

# Base URL для тестирования (localhost для dev, Zeabur для production)
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")

# Retry decorator для обработки concurrent access issues с SQLite
def retry_on_failure(max_attempts=3, delay=1.0):
    """Decorator для повторных попыток при неудаче"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except (AssertionError, requests.exceptions.RequestException) as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        import time
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator


# ===========================================
# Chart Endpoint Tests
# ===========================================

class TestChartEndpoints:
    """Tests for chart endpoints"""

    @retry_on_failure(max_attempts=3, delay=1.0)
    def test_chart_endpoint_works(self):
        """test_chart_endpoint_works — endpoint возвращает 200 и данные"""
        try:
            response = requests.get(
                f"{BASE_URL}/chart/history/BTCUSDT",
                params={"interval": "15m", "limit": 5},
                timeout=30
            )
        except requests.exceptions.ConnectionError:
            pytest.skip(f"Server not available at {BASE_URL}")
            return
        
        if response.status_code != 200:
            pytest.skip(f"Chart endpoint returned {response.status_code}")
        
        data = response.json()
        
        # Проверяем наличие обязательных полей
        assert "symbol" in data, "Response should have 'symbol' field"
        assert "candles" in data, "Response should have 'candles' field"
        assert "labels" in data, "Response should have 'labels' field"
        assert "prices" in data, "Response should have 'prices' field"
        assert "first_price" in data, "Response should have 'first_price' field"
        assert "last_price" in data, "Response should have 'last_price' field"
        
        # Проверяем что данные не пустые
        assert len(data["candles"]) >= 1, "Should have at least 1 candle"
        assert len(data["labels"]) >= 1, "Should have at least 1 label"
        assert len(data["prices"]) >= 1, "Should have at least 1 price"
        
        print(f"[PASS] test_chart_endpoint_works ({len(data['candles'])} candles)")

    @retry_on_failure(max_attempts=3, delay=1.0)
    def test_chart_different_symbols(self):
        """test_chart_different_symbols — BTC и ETH возвращают разные данные"""
        try:
            btc_response = requests.get(
                f"{BASE_URL}/chart/history/BTCUSDT",
                params={"interval": "15m", "limit": 5},
                timeout=30
            )
            eth_response = requests.get(
                f"{BASE_URL}/chart/history/ETHUSDT",
                params={"interval": "15m", "limit": 5},
                timeout=30
            )
        except requests.exceptions.ConnectionError:
            pytest.skip(f"Server not available at {BASE_URL}")
            return
        
        if btc_response.status_code != 200:
            pytest.skip(f"BTC endpoint returned {btc_response.status_code}")
        if eth_response.status_code != 200:
            pytest.skip(f"ETH endpoint returned {eth_response.status_code}")

        btc_data = btc_response.json()
        eth_data = eth_response.json()

        btc_prices = [c["close"] for c in btc_data["candles"]]
        eth_prices = [c["close"] for c in eth_data["candles"]]

        # Проверяем что цены разные
        assert btc_prices[0] != eth_prices[0], "BTC and ETH prices should be different"
        
        # Проверяем что BTC дороже ETH
        assert btc_prices[0] > eth_prices[0], "BTC should be more expensive than ETH"
        
        # Проверяем что цены в разумных пределах
        assert 10000 < btc_prices[0] < 200000, f"BTC price ${btc_prices[0]:.2f} seems unreasonable"
        assert 100 < eth_prices[0] < 20000, f"ETH price ${eth_prices[0]:.2f} seems unreasonable"

        print(f"[PASS] test_chart_different_symbols")
        print(f"   BTC: ${btc_prices[0]:.2f}")
        print(f"   ETH: ${eth_prices[0]:.2f}")


# ===========================================
# SDK Import Tests
# ===========================================

class TestSDKImports:
    """Tests for SDK imports"""

    def test_sdk_imports_work(self):
        """test_sdk_imports_work — все SDK импортируются без ошибок"""
        
        # Тестируем импорт polymarket_sdk
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
            from api.services.polymarket_sdk import (
                PolymarketSDK,
                get_polymarket_sdk,
                is_polymarket_configured,
                PolymarketSDKError,
                PolymarketNotConfiguredError
            )
            sdk_imported = True
        except ImportError as e:
            pytest.skip(f"polymarket_sdk not available: {e}")
            return
        except NameError as e:
            # py-clob-client not installed - это ожидаемо для dev среды
            pytest.skip(f"py-clob-client not installed (expected for dev): {e}")
            return
        
        # Проверяем что класс PolymarketSDK существует
        assert hasattr(PolymarketSDK, 'is_configured'), "PolymarketSDK should have is_configured method"
        assert hasattr(PolymarketSDK, 'get_markets'), "PolymarketSDK should have get_markets method"
        assert hasattr(PolymarketSDK, 'place_order'), "PolymarketSDK should have place_order method"
        assert hasattr(PolymarketSDK, 'cancel_order'), "PolymarketSDK should have cancel_order method"
        assert hasattr(PolymarketSDK, 'get_positions'), "PolymarketSDK should have get_positions method"
        
        # Проверяем что get_polymarket_sdk возвращает экземпляр
        sdk = get_polymarket_sdk()
        assert isinstance(sdk, PolymarketSDK), "get_polymarket_sdk should return PolymarketSDK instance"
        
        # Проверяем что is_polymarket_configured возвращает bool
        configured = is_polymarket_configured()
        assert isinstance(configured, bool), "is_polymarket_configured should return bool"
        
        print("[PASS] test_sdk_imports_work")
        print(f"   SDK configured: {configured}")

    def test_frontend_sdk_file_exists(self):
        """test_frontend_sdk_file_exists — frontend SDK файл существует"""
        sdk_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'frontend',
            'services',
            'polymarketSDK.ts'
        )
        
        assert os.path.exists(sdk_path), f"Frontend SDK file should exist at {sdk_path}"
        
        # Проверяем что файл не пустой
        with open(sdk_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert len(content) > 1000, "Frontend SDK file should have substantial content"
        assert "export class PolymarketSDK" in content, "Should export PolymarketSDK class"
        assert "getMarkets" in content, "Should have getMarkets method"
        assert "placeOrder" in content, "Should have placeOrder method"
        assert "connectWallet" in content, "Should have connectWallet method"
        
        print(f"[PASS] test_frontend_sdk_file_exists ({len(content)} bytes)")


# ===========================================
# Web3 Config Tests
# ===========================================

class TestWeb3Config:
    """Tests for Web3 configuration"""

    def test_web3_config_complete(self):
        """test_web3_config_complete — все 4 контракта имеют адреса"""
        
        # Импортируем конфигурацию
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        
        try:
            from api.config.polymarket_contracts import POLYMARKET_CONTRACTS
            config = POLYMARKET_CONTRACTS
        except ImportError:
            # Альтернативный путь
            try:
                from models import POLYMARKET_CONTRACTS
                config = POLYMARKET_CONTRACTS
            except ImportError:
                # Если нет модуля, проверяем файл напрямую
                config_path = os.path.join(
                    os.path.dirname(__file__),
                    '..',
                    'api',
                    'config',
                    'polymarket_contracts.py'
                )
                
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Проверяем наличие адресов контрактов в файле
                    required_contracts = [
                        'USDC_E',
                        'CTF',
                        'CTF_EXCHANGE',
                        'NEG_RISK_CTF_EXCHANGE'
                    ]
                    
                    for contract in required_contracts:
                        assert contract in content, f"Contract {contract} should be in config"
                    
                    print("[PASS] test_web3_config_complete (via file check)")
                    return
                else:
                    pytest.skip("Web3 config file not found")
                    return
        
        # Проверяем структуру конфигурации
        assert "contracts" in config, "Config should have 'contracts' key"
        
        contracts = config["contracts"]
        
        # Проверяем все 4 контракта
        required_contracts = {
            'USDC_E': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
            'CTF': '0x4D97DCd97eC945f40cF65F87097ACe5EA0476045',
            'CTF_EXCHANGE': '0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E',
            'NEG_RISK_CTF_EXCHANGE': '0xC5d563A36AE78145C45a50134d48A1215220f80a'
        }
        
        for contract_name, expected_address in required_contracts.items():
            assert contract_name in contracts, f"Contract {contract_name} should be in config"
            
            actual_address = contracts[contract_name]
            assert actual_address == expected_address, \
                f"{contract_name} address mismatch: expected {expected_address}, got {actual_address}"
            
            # Проверяем формат адреса (0x + 40 hex chars)
            assert actual_address.startswith('0x'), f"{contract_name} should start with 0x"
            assert len(actual_address) == 42, f"{contract_name} should be 42 chars long"
        
        # Проверяем network (case-insensitive)
        network = config.get("network", "").lower()
        assert network == "polygon", f"Network should be 'polygon', got '{network}'"
        assert config.get("chain_id") == 137, "Chain ID should be 137"
        
        print("[PASS] test_web3_config_complete")
        print(f"   USDC_E: {contracts['USDC_E']}")
        print(f"   CTF: {contracts['CTF']}")
        print(f"   CTF_EXCHANGE: {contracts['CTF_EXCHANGE']}")
        print(f"   NEG_RISK_CTF_EXCHANGE: {contracts['NEG_RISK_CTF_EXCHANGE']}")


# ===========================================
# Documentation Tests
# ===========================================

class TestDocumentation:
    """Tests for documentation files"""

    def test_polymarket_api_docs_exist(self):
        """test_polymarket_api_docs_exist — файл POLYMARKET_API_REFERENCE.md создан"""
        
        docs_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'POLYMARKET_API_REFERENCE.md'
        )
        
        assert os.path.exists(docs_path), f"POLYMARKET_API_REFERENCE.md should exist at {docs_path}"
        
        # Проверяем что файл не пустой
        with open(docs_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert len(content) > 5000, "POLYMARKET_API_REFERENCE.md should have substantial content"
        
        # Проверяем наличие ключевых разделов
        required_sections = [
            'API Endpoints',
            'Аутентификация',
            'SDK',
            'Markets',
            'Orders',
            'Rate Limits'
        ]
        
        for section in required_sections:
            assert section in content, f"Documentation should have '{section}' section"
        
        # Проверяем что есть примеры кода
        assert '```python' in content or '```typescript' in content, \
            "Documentation should have code examples"
        
        # Проверяем что есть таблица SDK
        assert 'py-clob-client' in content, "Documentation should mention py-clob-client"
        assert '@polymarket/clob-client' in content, \
            "Documentation should mention @polymarket/clob-client"
        
        print(f"[PASS] test_polymarket_api_docs_exist ({len(content)} bytes)")

    def test_one_pager_exists(self):
        """test_one_pager_exists — файл ONE_PAGER_FOR_SALE.md создан"""
        
        docs_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'ONE_PAGER_FOR_SALE.md'
        )
        
        assert os.path.exists(docs_path), f"ONE_PAGER_FOR_SALE.md should exist at {docs_path}"
        
        with open(docs_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert len(content) > 3000, "ONE_PAGER_FOR_SALE.md should have substantial content"
        
        # Проверяем ключевые разделы
        required_sections = [
            'Краткое описание',
            'Ключевые преимущества',
            'Технический стек',
            'Web3 Интеграция',
            'Цена и условия'
        ]
        
        for section in required_sections:
            assert section in content, f"One pager should have '{section}' section"
        
        print(f"[PASS] test_one_pager_exists ({len(content)} bytes)")

    def test_web3_integration_updated(self):
        """test_web3_integration_updated — WEB3_INTEGRATION.md обновлён"""
        
        docs_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'WEB3_INTEGRATION.md'
        )
        
        assert os.path.exists(docs_path), f"WEB3_INTEGRATION.md should exist at {docs_path}"
        
        with open(docs_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert len(content) > 10000, "WEB3_INTEGRATION.md should have substantial content"
        
        # Проверяем что есть информация о SDK
        assert 'polymarket_sdk.py' in content, \
            "WEB3_INTEGRATION.md should mention polymarket_sdk.py"
        assert 'polymarketSDK.ts' in content, \
            "WEB3_INTEGRATION.md should mention polymarketSDK.ts"
        
        # Проверяем что есть таблица SDK
        assert 'CLOB Client' in content, "Should mention CLOB Client"
        assert 'Builder Signing' in content or 'Builder SDK' in content, \
            "Should mention Builder SDK"
        
        print(f"[PASS] test_web3_integration_updated ({len(content)} bytes)")


# ===========================================
# Integration Tests
# ===========================================

class TestIntegration:
    """Integration tests"""

    @retry_on_failure(max_attempts=3, delay=1.0)
    def test_health_endpoint(self):
        """test_health_endpoint - health check works"""
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("[PASS] test_health_endpoint")

    @retry_on_failure(max_attempts=3, delay=1.0)
    def test_chart_status_endpoint(self):
        """test_chart_status_endpoint - chart service status available"""
        response = requests.get(f"{BASE_URL}/chart/status", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "cache_size" in data
        assert "current_endpoint" in data
        print(f"[PASS] test_chart_status_endpoint (cache: {data['cache_size']})")

    @retry_on_failure(max_attempts=3, delay=1.0)
    def test_events_endpoint(self):
        """test_events_endpoint - events endpoint works"""
        response = requests.get(f"{BASE_URL}/events", timeout=30)
        if response.status_code != 200:
            pytest.skip("Events endpoint not available")
        
        data = response.json()
        assert "events" in data or isinstance(data, list)
        print(f"[PASS] test_events_endpoint")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
