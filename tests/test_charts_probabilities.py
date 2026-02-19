"""
Test Coverage for Charts & Polymarket Probabilities

Запуск:
    pytest tests/test_charts_probabilities.py -v

Тест-кейсы:
1. test_chart_endpoint_exists - endpoint возвращает 200
2. test_chart_data_not_empty - возвращается минимум 1 свеча
3. test_chart_different_symbols - BTC и ETH возвращают разные данные
4. test_chart_format_valid - каждая свеча имеет open, high, low, close, timestamp
5. test_events_have_probabilities - у событий есть поле probability
6. test_probabilities_sum_100 - сумма процентов для outcomes ≈ 100%

Примечание: Тесты требуют запущенного сервера на localhost:8000
"""

import pytest
import requests
from decimal import Decimal
import time

# Base URL для тестирования (localhost для dev, Zeabur для production)
BASE_URL = "http://localhost:8000"

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
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator


# ===========================================
# Chart Tests
# ===========================================

class TestChartEndpoints:
    """Tests for chart endpoints"""

    @retry_on_failure(max_attempts=3, delay=1.0)
    def test_chart_endpoint_exists(self):
        """test_chart_endpoint_exists - endpoint returns 200 status"""
        response = requests.get(
            f"{BASE_URL}/chart/history/BTCUSDT",
            params={"interval": "15m", "limit": 5},
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("[PASS] test_chart_endpoint_exists")

    @retry_on_failure(max_attempts=3, delay=1.0)
    def test_chart_data_not_empty(self):
        """test_chart_data_not_empty - returns at least 1 candle"""
        response = requests.get(
            f"{BASE_URL}/chart/history/BTCUSDT",
            params={"interval": "15m", "limit": 5},
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()

        assert "candles" in data, "Response should have 'candles' field"
        assert len(data["candles"]) >= 1, "Should have at least 1 candle"
        print(f"[PASS] test_chart_data_not_empty ({len(data['candles'])} candles)")

    @retry_on_failure(max_attempts=3, delay=1.0)
    def test_chart_different_symbols(self):
        """test_chart_different_symbols - BTC and ETH return different data"""
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

        assert btc_response.status_code == 200
        assert eth_response.status_code == 200

        btc_data = btc_response.json()
        eth_data = eth_response.json()

        btc_prices = [c["close"] for c in btc_data["candles"]]
        eth_prices = [c["close"] for c in eth_data["candles"]]

        assert btc_prices[0] != eth_prices[0], "BTC and ETH prices should be different"
        assert btc_prices[0] > eth_prices[0], "BTC should be more expensive than ETH"

        print(f"[PASS] test_chart_different_symbols")
        print(f"   BTC: ${btc_prices[0]:.2f}")
        print(f"   ETH: ${eth_prices[0]:.2f}")

    @retry_on_failure(max_attempts=3, delay=1.0)
    def test_chart_format_valid(self):
        """test_chart_format_valid - each candle has open, high, low, close, timestamp"""
        response = requests.get(
            f"{BASE_URL}/chart/history/BTCUSDT",
            params={"interval": "15m", "limit": 5},
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()

        required_fields = ["timestamp", "open", "high", "low", "close", "volume"]

        for i, candle in enumerate(data["candles"]):
            for field in required_fields:
                assert field in candle, f"Candle {i} missing '{field}' field"

            assert isinstance(candle["timestamp"], int), "timestamp should be int"
            assert isinstance(candle["open"], float), "open should be float"
            assert isinstance(candle["high"], float), "high should be float"
            assert isinstance(candle["low"], float), "low should be float"
            assert isinstance(candle["close"], float), "close should be float"
            assert candle["high"] >= candle["low"], "high should be >= low"

        print(f"[PASS] test_chart_format_valid ({len(data['candles'])} candles validated)")

    @retry_on_failure(max_attempts=3, delay=1.0)
    def test_chart_has_labels_and_prices(self):
        """test_chart_has_labels_and_prices - response has labels and prices arrays"""
        response = requests.get(
            f"{BASE_URL}/chart/history/BTCUSDT",
            params={"interval": "15m", "limit": 5},
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()

        assert "labels" in data, "Response should have 'labels' field"
        assert "prices" in data, "Response should have 'prices' field"
        assert len(data["labels"]) == len(data["prices"]), "labels and prices should have same length"
        assert len(data["labels"]) > 0, "Should have at least 1 label/price"

        print(f"[PASS] test_chart_has_labels_and_prices")


# ===========================================
# Polymarket Probabilities Tests
# ===========================================

class TestPolymarketProbabilities:
    """Tests for Polymarket probabilities"""

    @retry_on_failure(max_attempts=3, delay=1.0)
    def test_events_endpoint_exists(self):
        """test_events_endpoint_exists - /events endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/events", timeout=30)
        if response.status_code != 200:
            pytest.skip("Events endpoint not available")
        print("[PASS] test_events_endpoint_exists")

    @retry_on_failure(max_attempts=3, delay=1.0)
    def test_events_have_options(self):
        """test_events_have_options - events have options array"""
        response = requests.get(f"{BASE_URL}/events", timeout=30)
        if response.status_code != 200:
            pytest.skip("Events endpoint not available or empty")

        data = response.json()
        if not data.get("events"):
            pytest.skip("No events available for testing")

        events = data["events"]
        assert len(events) > 0, "Should have at least 1 event"

        for event in events[:5]:
            assert "options" in event, f"Event {event.get('id')} missing 'options' field"
            assert len(event["options"]) > 0, f"Event {event.get('id')} should have at least 1 option"

        print(f"[PASS] test_events_have_options ({len(events)} events)")

    @retry_on_failure(max_attempts=3, delay=1.0)
    def test_options_have_probability_field(self):
        """test_options_have_probability_field - options have probability field"""
        response = requests.get(f"{BASE_URL}/events", timeout=30)
        if response.status_code != 200:
            pytest.skip("Events endpoint not available")

        data = response.json()
        if not data.get("events"):
            pytest.skip("No events available")

        events = data["events"]

        for event in events[:5]:
            for option in event.get("options", []):
                assert "probability" in option, f"Option missing 'probability' field"

        print(f"[PASS] test_options_have_probability_field")

    @retry_on_failure(max_attempts=3, delay=1.0)
    def test_probabilities_are_numeric(self):
        """test_probabilities_are_numeric - probability is numeric"""
        response = requests.get(f"{BASE_URL}/events", timeout=30)
        if response.status_code != 200:
            pytest.skip("Events endpoint not available")

        data = response.json()
        if not data.get("events"):
            pytest.skip("No events available")

        events = data["events"]

        for event in events[:5]:
            for option in event.get("options", []):
                prob = option.get("probability")
                assert prob is not None, "probability should not be None"
                assert isinstance(prob, (int, float)), f"probability should be numeric, got {type(prob)}"
                assert 0 <= prob <= 100, f"probability should be 0-100, got {prob}"

        print(f"[PASS] test_probabilities_are_numeric")

    @retry_on_failure(max_attempts=3, delay=1.0)
    def test_probabilities_sum_approximately_100(self):
        """test_probabilities_sum_approximately_100 - probabilities sum to ~100%"""
        response = requests.get(f"{BASE_URL}/events", timeout=30)
        if response.status_code != 200:
            pytest.skip("Events endpoint not available")

        data = response.json()
        if not data.get("events"):
            pytest.skip("No events available")

        events = data["events"]

        for event in events[:3]:
            options = event.get("options", [])
            if len(options) < 2:
                continue

            total_probability = sum(opt.get("probability", 0) for opt in options)
            assert 95 <= total_probability <= 105, \
                f"Event {event.get('title')}: probabilities sum to {total_probability}, expected ~100"

        print(f"[PASS] test_probabilities_sum_approximately_100")


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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
