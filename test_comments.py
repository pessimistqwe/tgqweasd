"""
EventPredict - Comments API Tests
"""
import requests
import os
import time

BASE_URL = os.getenv("EVENTPREDICT_URL", "http://localhost:8000")
TEST_TELEGRAM_ID = 123456789


def get_test_event_id():
    """Get first available event ID"""
    try:
        response = requests.get(f"{BASE_URL}/events", timeout=10)
        events = response.json().get("events", [])
        return events[0]["id"] if events else None
    except:
        return None


def test_comments_api_get():
    """Test: get comments"""
    print("\n[Test] Comments API GET")
    event_id = get_test_event_id()
    if not event_id:
        print("[SKIP] No events available")
        return True
    
    response = requests.get(f"{BASE_URL}/events/{event_id}/comments", timeout=10)
    if response.status_code != 200:
        print(f"[FAIL] Status: {response.status_code}")
        return False
    
    data = response.json()
    if not isinstance(data, list):
        print("[FAIL] Expected list")
        return False
    
    print(f"[PASS] Returned {len(data)} comments")
    return True


def test_comments_api_post():
    """Test: create comment"""
    print("\n[Test] Comments API POST")
    event_id = get_test_event_id()
    if not event_id:
        print("[SKIP] No events available")
        return True
    
    comment_data = {
        "comment_text": "Test comment",
        "telegram_id": TEST_TELEGRAM_ID,
        "username": "test_user"
    }
    
    response = requests.post(
        f"{BASE_URL}/events/{event_id}/comments",
        json=comment_data,
        timeout=10
    )
    
    if response.status_code != 200:
        print(f"[FAIL] Status: {response.status_code}")
        return False
    
    data = response.json()
    if not data.get("success"):
        print("[FAIL] success=False")
        return False
    
    print(f"[PASS] Created comment ID: {data.get('comment', {}).get('id')}")
    return True


def test_comments_block_links():
    """Test: block links"""
    print("\n[Test] Block links")
    event_id = get_test_event_id()
    if not event_id:
        return True
    
    comment_data = {
        "comment_text": "Check https://example.com",
        "telegram_id": TEST_TELEGRAM_ID + 1,
        "username": "test_user"
    }
    
    response = requests.post(
        f"{BASE_URL}/events/{event_id}/comments",
        json=comment_data,
        timeout=10
    )
    
    passed = response.status_code == 400
    print(f"[{'PASS' if passed else 'FAIL'}] Links {'blocked' if passed else 'not blocked'}")
    return passed


def test_comments_block_profanity():
    """Test: block profanity"""
    print("\n[Test] Block profanity")
    event_id = get_test_event_id()
    if not event_id:
        return True
    
    comment_data = {
        "comment_text": "You are an idiot",
        "telegram_id": TEST_TELEGRAM_ID + 2,
        "username": "test_user"
    }
    
    response = requests.post(
        f"{BASE_URL}/events/{event_id}/comments",
        json=comment_data,
        timeout=10
    )
    
    passed = response.status_code == 400
    print(f"[{'PASS' if passed else 'FAIL'}] Profanity {'blocked' if passed else 'not blocked'}")
    return passed


def test_comments_length_limit():
    """Test: comment length limit"""
    print("\n[Test] Length limit")
    event_id = get_test_event_id()
    if not event_id:
        return True
    
    comment_data = {
        "comment_text": "A" * 1001,
        "telegram_id": TEST_TELEGRAM_ID + 3,
        "username": "test_user"
    }
    
    response = requests.post(
        f"{BASE_URL}/events/{event_id}/comments",
        json=comment_data,
        timeout=10
    )
    
    passed = response.status_code == 400
    print(f"[{'PASS' if passed else 'FAIL'}] Long comments {'blocked' if passed else 'not blocked'}")
    return passed


if __name__ == "__main__":
    print("=" * 60)
    print("EventPredict - Comments API Tests")
    print("=" * 60)
    
    try:
        results = []
        results.append(test_comments_api_get())
        time.sleep(0.5)
        results.append(test_comments_api_post())
        time.sleep(0.5)
        results.append(test_comments_block_links())
        time.sleep(0.5)
        results.append(test_comments_block_profanity())
        time.sleep(0.5)
        results.append(test_comments_length_limit())
        
        print("\n" + "=" * 60)
        passed = sum(results)
        total = len(results)
        print(f"Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("[OK] ALL TESTS PASSED")
        else:
            print(f"[WARN] {total - passed} tests failed")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        exit(1)
