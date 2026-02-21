#!/usr/bin/env python3
"""
Tests for EventPredict API - Search and Charts

Run with: python test_api.py
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("\n=== Testing /health ===")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_categories():
    """Test categories endpoint"""
    print("\n=== Testing /categories ===")
    try:
        response = requests.get(f"{BASE_URL}/categories")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Categories: {len(data.get('categories', []))}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_events():
    """Test events endpoint"""
    print("\n=== Testing /events ===")
    try:
        response = requests.get(f"{BASE_URL}/events")
        print(f"Status: {response.status_code}")
        data = response.json()
        if isinstance(data, list):
            print(f"Events count: {len(data)}")
            if data:
                print(f"First event: {data[0].get('title', 'N/A')[:50]}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_search():
    """Test search endpoint"""
    print("\n=== Testing /events/search?q=bitcoin ===")
    try:
        response = requests.get(f"{BASE_URL}/events/search", params={"q": "bitcoin", "limit": 10})
        print(f"Status: {response.status_code}")
        data = response.json()
        if "events" in data:
            print(f"Search results: {len(data['events'])}")
            for event in data['events'][:3]:
                print(f"  - {event.get('title', 'N/A')[:50]} (relevance: {event.get('relevance_score', 0)})")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_search_category():
    """Test search with category filter"""
    print("\n=== Testing /events/search?q=crypto&category=crypto ===")
    try:
        response = requests.get(f"{BASE_URL}/events/search", params={"q": "crypto", "category": "crypto", "limit": 10})
        print(f"Status: {response.status_code}")
        data = response.json()
        if "events" in data:
            print(f"Search results: {len(data['events'])}")
            for event in data['events'][:3]:
                print(f"  - {event.get('title', 'N/A')[:50]} (category: {event.get('category', 'N/A')})")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_chart_history():
    """Test chart history endpoint"""
    print("\n=== Testing /chart/history/BTCUSDT ===")
    try:
        response = requests.get(f"{BASE_URL}/chart/history/BTCUSDT", params={"interval": "1h", "limit": 10})
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Symbol: {data.get('symbol', 'N/A')}")
            print(f"Candles count: {len(data.get('candles', []))}")
            if data.get('candles'):
                print(f"First candle: {data['candles'][0]}")
                print(f"Last candle: {data['candles'][-1]}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_polymarket_chart():
    """Test Polymarket chart endpoint"""
    print("\n=== Testing /api/polymarket/chart/test (should fallback) ===")
    try:
        response = requests.get(f"{BASE_URL}/api/polymarket/chart/test", params={"outcome": "Yes", "resolution": "hour", "limit": 10})
        print(f"Status: {response.status_code}")
        if response.status_code in [200, 404]:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)[:500]}")
        return response.status_code in [200, 404]
    except Exception as e:
        print(f"Error: {e}")
        return False

def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("EventPredict API Tests")
    print("=" * 60)
    
    tests = [
        ("Health Check", test_health),
        ("Categories", test_categories),
        ("Events List", test_events),
        ("Search (basic)", test_search),
        ("Search (with category)", test_search_category),
        ("Chart History", test_chart_history),
        ("Polymarket Chart", test_polymarket_chart),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    return passed == total

if __name__ == "__main__":
    print(f"Testing API at: {BASE_URL}")
    print("Make sure the server is running: uvicorn api.index:app --reload")
    
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted")
        sys.exit(1)
