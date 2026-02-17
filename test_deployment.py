#!/usr/bin/env python3
"""
EventPredict Deployment Test Script
Automated tests for checking deployment status
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

def test_health():
    """Test health endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        data = response.json()
        passed = data.get("status") == "healthy" and data.get("sync", {}).get("total_synced", 0) > 0
        return print_status("Health Check", passed, 
                           f"Status: {data.get('status')}, Synced: {data.get('sync', {}).get('total_synced')}")
    except Exception as e:
        return print_status("Health Check", False, str(e))

def test_categories():
    """Test categories endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/categories", timeout=10)
        data = response.json()
        passed = "categories" in data and len(data["categories"]) >= 7
        return print_status("Categories Endpoint", passed,
                           f"Categories count: {len(data.get('categories', []))}")
    except Exception as e:
        return print_status("Categories Endpoint", False, str(e))

def test_events():
    """Test events endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/events", timeout=10)
        data = response.json()
        passed = "events" in data and len(data["events"]) > 0
        return print_status("Events Endpoint", passed,
                           f"Events count: {len(data.get('events', []))}")
    except Exception as e:
        return print_status("Events Endpoint", False, str(e))

def test_events_crypto():
    """Test crypto category events"""
    try:
        response = requests.get(f"{BASE_URL}/events?category=crypto", timeout=10)
        data = response.json()
        events = data.get("events", [])
        all_crypto = all(e.get("category") == "crypto" for e in events)
        passed = len(events) > 0 and all_crypto
        return print_status("Crypto Category", passed,
                           f"Crypto events: {len(events)}")
    except Exception as e:
        return print_status("Crypto Category", False, str(e))

def test_events_sports():
    """Test sports category events"""
    try:
        response = requests.get(f"{BASE_URL}/events?category=sports", timeout=10)
        data = response.json()
        events = data.get("events", [])
        all_sports = all(e.get("category") == "sports" for e in events)
        passed = len(events) > 0 and all_sports
        return print_status("Sports Category", passed,
                           f"Sports events: {len(events)}")
    except Exception as e:
        return print_status("Sports Category", False, str(e))

def test_admin_check():
    """Test admin check endpoint"""
    try:
        ADMIN_ID = 1972885597
        response = requests.get(f"{BASE_URL}/admin/check/{ADMIN_ID}", timeout=10)
        data = response.json()
        passed = data.get("is_admin") == True
        return print_status("Admin Check (Your ID)", passed,
                           f"is_admin: {data.get('is_admin')}")
    except Exception as e:
        return print_status("Admin Check", False, str(e))

def test_admin_stats():
    """Test admin stats endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/admin/stats", timeout=10)
        data = response.json()
        passed = "total_events" in data or "total_users" in data
        return print_status("Admin Stats", passed,
                           f"Stats: {data}")
    except Exception as e:
        return print_status("Admin Stats", False, str(e))

def test_price_history():
    """Test price history endpoint"""
    try:
        # Get first event
        events_response = requests.get(f"{BASE_URL}/events", timeout=10)
        events = events_response.json().get("events", [])
        if not events:
            return print_status("Price History", False, "No events available")
        
        event_id = events[0]["id"]
        response = requests.get(f"{BASE_URL}/events/{event_id}/price-history", timeout=10)
        data = response.json()
        passed = isinstance(data, list)
        return print_status("Price History Endpoint", passed,
                           f"History points: {len(data)}")
    except Exception as e:
        return print_status("Price History Endpoint", False, str(e))

def test_single_event():
    """Test single event endpoint"""
    try:
        events_response = requests.get(f"{BASE_URL}/events", timeout=10)
        events = events_response.json().get("events", [])
        if not events:
            return print_status("Single Event", False, "No events available")
        
        event_id = events[0]["id"]
        response = requests.get(f"{BASE_URL}/events/{event_id}", timeout=10)
        data = response.json()
        passed = "title" in data and "options" in data
        return print_status("Single Event Endpoint", passed,
                           f"Title: {data.get('title', 'N/A')[:50]}")
    except Exception as e:
        return print_status("Single Event Endpoint", False, str(e))

def main():
    """Run all tests"""
    print("=" * 60)
    print("EventPredict Deployment Tests")
    print(f"Base URL: {BASE_URL}")
    print("=" * 60)
    print()
    
    tests = [
        test_health,
        test_categories,
        test_events,
        test_events_crypto,
        test_events_sports,
        test_admin_check,
        test_admin_stats,
        test_price_history,
        test_single_event,
    ]
    
    results = []
    for test in tests:
        results.append(test())
        time.sleep(0.5)  # Small delay between tests
    
    print()
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("[OK] All tests passed! Deployment is working correctly.")
    else:
        print(f"[ERR] {total - passed} tests failed. Check the errors above.")

    print("=" * 60)

    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
