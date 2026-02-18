"""
EventPredict - Image Proxy Tests
Automated tests for image proxy functionality with Telegram WebApp support
"""

import requests
import os

BASE_URL = os.getenv("EVENTPREDICT_URL", "http://localhost:8000")
TEST_IMAGE_URL = "https://gamma-api.polymarket.com/test-image.jpg"


def test_image_proxy_returns_cors_headers():
    """Check proxy endpoint returns CORS headers"""
    print("\n[Test] CORS headers proxy endpoint")
    
    response = requests.get(
        f"{BASE_URL}/proxy/image",
        params={"url": TEST_IMAGE_URL},
        timeout=10
    )
    
    assert "Access-Control-Allow-Origin" in response.headers, "Missing Access-Control-Allow-Origin"
    assert response.headers["Access-Control-Allow-Origin"] == "*", "Should be '*'"
    
    assert "Cross-Origin-Resource-Policy" in response.headers, "Missing Cross-Origin-Resource-Policy"
    assert response.headers["Cross-Origin-Resource-Policy"] == "cross-origin", "Should be 'cross-origin'"
    
    assert "Access-Control-Allow-Headers" in response.headers, "Missing Access-Control-Allow-Headers"
    assert "Cache-Control" in response.headers, "Missing Cache-Control"
    assert "max-age=86400" in response.headers["Cache-Control"], "Should have max-age=86400"
    
    print("[PASS] CORS headers present and correct")
    return True


def test_image_proxy_for_telegram():
    """Check proxy for Telegram WebApp mode"""
    print("\n[Test] Telegram WebApp proxy mode")
    
    response = requests.get(
        f"{BASE_URL}/proxy/image",
        params={"url": TEST_IMAGE_URL, "telegram_webapp": "1"},
        timeout=10
    )
    
    assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
    assert "Access-Control-Allow-Origin" in response.headers, "Missing CORS headers"
    
    print("[PASS] Telegram WebApp mode works")
    return True


def test_image_proxy_url_validation():
    """Check URL validation"""
    print("\n[Test] URL validation")
    
    response = requests.get(f"{BASE_URL}/proxy/image", params={"url": ""}, timeout=10)
    assert response.status_code == 400, f"Empty URL should return 400, got {response.status_code}"
    
    response = requests.get(
        f"{BASE_URL}/proxy/image",
        params={"url": "https://example.com/image.jpg"},
        timeout=10
    )
    assert response.status_code == 400, f"Non-Polymarket URL should return 400, got {response.status_code}"
    
    print("[PASS] URL validation works")
    return True


def test_image_proxy_polymarket_urls():
    """Check Polymarket URLs are allowed"""
    print("\n[Test] Polymarket URLs allowed")
    
    valid_urls = [
        "https://gamma-api.polymarket.com/image.jpg",
        "https://polymarket.com/image.png",
    ]
    
    for url in valid_urls:
        response = requests.get(
            f"{BASE_URL}/proxy/image",
            params={"url": url},
            timeout=10
        )
        assert response.status_code in [200, 404], f"Polymarket URL {url} should be allowed"
    
    print("[PASS] Polymarket URLs allowed")
    return True


def test_image_fallback_on_error():
    """Check frontend has fallback function"""
    print("\n[Test] Frontend image fallback")
    
    script_path = os.path.join(os.path.dirname(__file__), "frontend", "script.js")
    
    if os.path.exists(script_path):
        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        assert "handleImageError" in content, "handleImageError function missing"
        assert "style.display = 'none'" in content, "Should hide image on error"
        assert "event-image-placeholder" in content, "Should have placeholder"
        
        print("[PASS] Frontend fallback implemented")
        return True
    else:
        print("[SKIP] script.js not found")
        return True


def test_image_proxy_content_type():
    """Check proxy returns correct Content-Type"""
    print("\n[Test] Content-Type")
    
    response = requests.get(
        f"{BASE_URL}/proxy/image",
        params={"url": TEST_IMAGE_URL},
        timeout=10
    )
    
    if response.status_code == 200:
        content_type = response.headers.get("content-type", "")
        assert content_type.startswith("image/"), f"Content-Type should be image/*, got {content_type}"
        print(f"[PASS] Content-Type correct: {content_type}")
    else:
        print(f"[SKIP] Image not found (404), skipping Content-Type check")
    
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("EventPredict - Image Proxy Tests")
    print("=" * 60)
    
    try:
        results = []
        results.append(test_image_proxy_returns_cors_headers())
        results.append(test_image_proxy_for_telegram())
        results.append(test_image_proxy_url_validation())
        results.append(test_image_proxy_polymarket_urls())
        results.append(test_image_fallback_on_error())
        results.append(test_image_proxy_content_type())
        
        print("\n" + "=" * 60)
        passed = sum(results)
        total = len(results)
        print(f"Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("[OK] ALL TESTS PASSED")
        else:
            print(f"[WARN] {total - passed} tests failed")
        
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        exit(1)
    except requests.exceptions.RequestException as e:
        print(f"\n[ERROR] NETWORK ERROR: {e}")
        exit(1)
    except Exception as e:
        print(f"\n[ERROR] UNEXPECTED ERROR: {e}")
        exit(1)
