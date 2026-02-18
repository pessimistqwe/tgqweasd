"""
EventPredict - Profile API Tests
"""
import requests
import os

BASE_URL = os.getenv("EVENTPREDICT_URL", "http://localhost:8000")
TEST_TELEGRAM_ID = 987654321


def test_profile_get():
    """Test: get profile"""
    print("\n[Test] Profile GET")
    
    response = requests.get(
        f"{BASE_URL}/user/{TEST_TELEGRAM_ID}/profile",
        timeout=10
    )
    
    if response.status_code != 200:
        print(f"[FAIL] Status: {response.status_code}")
        return False
    
    data = response.json()
    required_fields = ["telegram_id", "username", "custom_username", "avatar_url", "balance_usdt"]
    missing = [f for f in required_fields if f not in data]
    
    if missing:
        print(f"[FAIL] Missing fields: {missing}")
        return False
    
    print(f"[PASS] Profile retrieved, balance: {data.get('balance_usdt')} USDT")
    return True


def test_profile_update_username():
    """Test: update username"""
    print("\n[Test] Update username")
    
    test_username = f"test_user_{TEST_TELEGRAM_ID}"
    update_data = {"custom_username": test_username}
    
    response = requests.post(
        f"{BASE_URL}/user/profile/update",
        params={"telegram_id": TEST_TELEGRAM_ID},
        json=update_data,
        timeout=10
    )
    
    if response.status_code != 200:
        print(f"[FAIL] Status: {response.status_code}")
        return False
    
    data = response.json()
    if not data.get("success"):
        print("[FAIL] success=False")
        return False
    
    print(f"[PASS] Username updated: {test_username}")
    return True


def test_profile_username_length_limit():
    """Test: username length limit"""
    print("\n[Test] Username length limit")
    
    update_data = {"custom_username": "A" * 51}
    
    response = requests.post(
        f"{BASE_URL}/user/profile/update",
        params={"telegram_id": TEST_TELEGRAM_ID},
        json=update_data,
        timeout=10
    )
    
    passed = response.status_code == 400
    print(f"[{'PASS' if passed else 'FAIL'}] Long username {'rejected' if passed else 'accepted'}")
    return passed


def test_profile_upload_avatar():
    """Test: upload avatar"""
    print("\n[Test] Upload avatar")
    
    # 1x1 PNG
    test_image = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
        0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
        0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,
        0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
        0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,
        0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,
        0x42, 0x60, 0x82
    ])
    
    files = {"file": ("test_avatar.png", test_image, "image/png")}
    
    response = requests.post(
        f"{BASE_URL}/user/profile/upload-avatar",
        params={"telegram_id": TEST_TELEGRAM_ID},
        files=files,
        timeout=10
    )
    
    if response.status_code != 200:
        print(f"[FAIL] Status: {response.status_code}")
        return False
    
    data = response.json()
    if not data.get("success"):
        print("[FAIL] success=False")
        return False
    
    avatar_url = data.get("avatar_url")
    if not avatar_url or "/uploads/avatars/" not in avatar_url:
        print(f"[FAIL] Invalid URL: {avatar_url}")
        return False
    
    print(f"[PASS] Avatar uploaded: {avatar_url}")
    return True


def test_profile_avatar_validation():
    """Test: avatar file type validation"""
    print("\n[Test] Avatar validation")
    
    files = {"file": ("test.txt", b"Not an image", "text/plain")}
    
    response = requests.post(
        f"{BASE_URL}/user/profile/upload-avatar",
        params={"telegram_id": TEST_TELEGRAM_ID},
        files=files,
        timeout=10
    )
    
    passed = response.status_code == 400
    print(f"[{'PASS' if passed else 'FAIL'}] Invalid file type {'rejected' if passed else 'accepted'}")
    return passed


def test_profile_endpoints_exist():
    """Test: endpoints exist in code"""
    print("\n[Test] Endpoints exist")
    
    try:
        with open('api/index.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        has_get = '@app.get("/user/{telegram_id}/profile")' in content
        has_update = '@app.post("/user/profile/update")' in content
        has_upload = '@app.post("/user/profile/upload-avatar")' in content
        
        passed = has_get and has_update and has_upload
        print(f"[{'PASS' if passed else 'FAIL'}] Endpoints exist")
        return passed
    except Exception as e:
        print(f"[FAIL] {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("EventPredict - Profile API Tests")
    print("=" * 60)
    
    try:
        results = []
        results.append(test_profile_endpoints_exist())
        results.append(test_profile_get())
        results.append(test_profile_update_username())
        results.append(test_profile_username_length_limit())
        results.append(test_profile_upload_avatar())
        results.append(test_profile_avatar_validation())
        
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
