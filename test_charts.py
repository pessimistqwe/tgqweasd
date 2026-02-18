#!/usr/bin/env python3
"""
EventPredict Chart Tests
Tests for price history and chart data from Polymarket
"""
import requests
import sys
import time

BASE_URL = "https://eventpredict-production.up.railway.app"


def print_status(name, passed, message=""):
    """Print test status"""
    status = "[PASS]" if passed else "[FAIL]"
    print(f"{status}: {name}")
    if message and not passed:
        print(f"   + {message}")
    return passed


def test_price_history_endpoint():
    """Test that price history endpoint exists and returns data"""
    try:
        events_response = requests.get(f"{BASE_URL}/events", timeout=10)
        events = events_response.json().get("events", [])

        if not events:
            return print_status("Price History Endpoint", False, "No events available")

        event_id = events[0]["id"]
        response = requests.get(f"{BASE_URL}/events/{event_id}/price-history", timeout=10)

        if response.status_code != 200:
            return print_status("Price History Endpoint", False, f"Status code: {response.status_code}")

        data = response.json()
        if not isinstance(data, list):
            return print_status("Price History Endpoint", False, f"Expected list, got {type(data)}")

        passed = len(data) >= 0
        return print_status("Price History Endpoint", passed, f"Returned {len(data)} data points")
    except Exception as e:
        return print_status("Price History Endpoint", False, str(e))


def test_price_history_structure():
    """Test that price history has correct structure"""
    try:
        events_response = requests.get(f"{BASE_URL}/events", timeout=10)
        events = events_response.json().get("events", [])

        if not events:
            return print_status("Price History Structure", False, "No events available")

        event_id = events[0]["id"]
        response = requests.get(f"{BASE_URL}/events/{event_id}/price-history", timeout=10)
        data = response.json()

        if not data:
            return print_status("Price History Structure", False, "No history data")

        first_item = data[0]
        required_fields = ["event_id", "option_index", "price", "timestamp"]
        missing_fields = [f for f in required_fields if f not in first_item]

        if missing_fields:
            return print_status("Price History Structure", False, f"Missing fields: {missing_fields}")

        price = first_item.get("price", 0)
        if not (0 <= price <= 1):
            return print_status("Price History Structure", False, f"Price {price} out of range [0, 1]")

        return print_status("Price History Structure", True, f"Fields: {list(first_item.keys())}")
    except Exception as e:
        return print_status("Price History Structure", False, str(e))


def test_events_have_options():
    """Test that events have options with probabilities"""
    try:
        response = requests.get(f"{BASE_URL}/events", timeout=10)
        data = response.json()
        events = data.get("events", [])

        if not events:
            return print_status("Events Have Options", False, "No events available")

        event = events[0]
        has_options = "options" in event and len(event["options"]) > 0

        if not has_options:
            return print_status("Events Have Options", False, "No options in event")

        options = event["options"]
        has_probabilities = all("probability" in opt for opt in options)

        passed = has_options and has_probabilities
        return print_status("Events Have Options", passed, f"Options: {len(options)}")
    except Exception as e:
        return print_status("Events Have Options", False, str(e))


def test_chart_data_range():
    """Test that chart data has reasonable range"""
    try:
        events_response = requests.get(f"{BASE_URL}/events", timeout=10)
        events = events_response.json().get("events", [])

        if not events:
            return print_status("Chart Data Range", False, "No events available")

        event_id = events[0]["id"]
        response = requests.get(f"{BASE_URL}/events/{event_id}/price-history", timeout=10)
        data = response.json()

        if not data:
            return print_status("Chart Data Range", False, "No history data")

        prices = [item["price"] for item in data]
        min_price = min(prices)
        max_price = max(prices)

        if min_price < 0 or max_price > 1:
            return print_status("Chart Data Range", False, f"Prices out of range: [{min_price}, {max_price}]")

        return print_status("Chart Data Range", True, f"Price range: [{min_price:.2%}, {max_price:.2%}]")
    except Exception as e:
        return print_status("Chart Data Range", False, str(e))


def test_polymarket_sync():
    """Test that Polymarket sync is working"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        data = response.json()

        sync_info = data.get("sync", {})
        total_synced = sync_info.get("total_synced", 0)

        passed = total_synced > 0
        return print_status("Polymarket Sync", passed, f"Total synced: {total_synced}")
    except Exception as e:
        return print_status("Polymarket Sync", False, str(e))


def test_chart_single_line():
    """Test that chart uses single line for primary option"""
    try:
        with open('frontend/script.js', 'r', encoding='utf-8') as f:
            content = f.read()

        uses_first_option = 'options[0]' in content
        legend_hidden = "'display: false'" in content or '"display: false"' in content
        single_line_pattern = 'SINGLE LINE' in content

        passed = uses_first_option and (legend_hidden or single_line_pattern)
        return print_status("Chart Single Line", passed, f"Uses options[0]: {uses_first_option}")
    except Exception as e:
        return print_status("Chart Single Line", False, str(e))


def test_chart_gradient_exists():
    """Test that chart has gradient fill"""
    try:
        with open('frontend/script.js', 'r', encoding='utf-8') as f:
            content = f.read()

        has_gradient = 'createLinearGradient' in content
        has_green_gradient = 'rgba(34, 197, 94' in content
        has_red_gradient = 'rgba(239, 68, 68' in content
        applies_gradient = 'backgroundColor = gradient' in content

        passed = has_gradient and has_green_gradient and has_red_gradient and applies_gradient
        return print_status("Chart Gradient", passed, f"Has gradient: {has_gradient}")
    except Exception as e:
        return print_status("Chart Gradient", False, str(e))


def test_chart_styling():
    """Test that chart has Polymarket-like styling"""
    try:
        with open('frontend/script.js', 'r', encoding='utf-8') as f:
            content = f.read()

        has_green = '#22c55e' in content
        has_tension = 'tension: 0.4' in content or 'tension:0.4' in content
        no_points = 'pointRadius: 0' in content or 'pointRadius:0' in content
        has_hover = 'pointHoverRadius: 5' in content or 'pointHoverRadius:5' in content

        passed = has_green and has_tension and no_points and has_hover
        return print_status("Chart Styling", passed, f"Green: {has_green}, Tension: {has_tension}")
    except Exception as e:
        return print_status("Chart Styling", False, str(e))


def main():
    """Run all chart tests"""
    print("=" * 70)
    print("EventPredict Chart Tests")
    print(f"Base URL: {BASE_URL}")
    print("=" * 70)
    print()

    tests = [
        test_polymarket_sync,
        test_events_have_options,
        test_price_history_endpoint,
        test_price_history_structure,
        test_chart_data_range,
        test_chart_single_line,
        test_chart_gradient_exists,
        test_chart_styling,
    ]

    results = []
    for test in tests:
        results.append(test())
        time.sleep(0.5)

    print()
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("[OK] All chart tests passed!")
    else:
        print(f"[WARN] {total - passed} tests failed.")

    print("=" * 70)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
