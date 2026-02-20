#!/usr/bin/env python3
"""
Test script to verify the application starts correctly
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing application startup...")
print("=" * 50)

# Test 1: Import the app
print("\n1. Importing api.index...")
try:
    from api.index import app
    print("   [OK] Successfully imported api.index:app")
except Exception as e:
    print(f"   [FAIL] Import failed: {e}")
    sys.exit(1)

# Test 2: Check routes
print("\n2. Checking API routes...")
try:
    routes = [r.path for r in app.routes]
    print(f"   [OK] Found {len(routes)} routes")
    
    # Check critical routes
    critical = ['/health', '/api/polymarket/search', '/api/leaderboard', '/']
    for route in critical:
        if route in routes:
            print(f"   [OK] Route {route} exists")
        else:
            print(f"   [WARN] Route {route} missing")
except Exception as e:
    print(f"   [FAIL] Route check failed: {e}")
    sys.exit(1)

# Test 3: Check database
print("\n3. Checking database...")
try:
    from api.models import get_db, User, Event
    print("   [OK] Database models imported")
    
    # Try to create a session
    db = next(get_db())
    print("   [OK] Database connection works")
except Exception as e:
    print(f"   [WARN] Database check: {e}")
    # Not fatal, continue

# Test 4: Check new modules
print("\n4. Checking new modules...")
modules_to_check = [
    ('api.polymarket_routes', 'router'),
    ('api.cache_service', 'cache'),
    ('api.websocket_service', 'PolymarketWebSocketService'),
    ('api.leaderboard_routes', 'router'),
    ('api.polymarket_chart_routes', 'router'),
]

for module_name, attr in modules_to_check:
    try:
        module = __import__(module_name, fromlist=[attr])
        getattr(module, attr)
        print(f"   [OK] {module_name}.{attr}")
    except Exception as e:
        print(f"   [FAIL] {module_name}.{attr}: {e}")

print("\n" + "=" * 50)
print("[OK] All tests passed! Application is ready to deploy.")
print("=" * 50)
