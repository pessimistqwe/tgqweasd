"""
EventPredict — Profile API Tests

Автоматические тесты для проверки функциональности профиля
"""

import requests
import os
import io

BASE_URL = os.getenv("EVENTPREDICT_URL", "http://localhost:8000")

# Тестовые данные
TEST_TELEGRAM_ID = 987654321
TEST_USERNAME = "profile_test_user"


def print_status(name, passed, message=""):
    """Print test status"""
    status = "[PASS]" if passed else "[FAIL]"
    print(f"{status}: {name}")
    if message and not passed:
        print(f"   + {message}")
    return passed


def test_profile_get():
    """Тест: получение профиля"""
    print("\n👤 Тест: Получение профиля")
    
    try:
        response = requests.get(
            f"{BASE_URL}/user/{TEST_TELEGRAM_ID}/profile",
            timeout=10
        )
        
        if response.status_code != 200:
            return print_status("Profile GET", False,
                              f"Status code: {response.status_code}")
        
        data = response.json()
        
        # Проверяем обязательные поля
        required_fields = ["telegram_id", "username", "custom_username",
                          "avatar_url", "balance_usdt", "balance_ton"]
        
        missing_fields = [f for f in required_fields if f not in data]
        if missing_fields:
            return print_status("Profile GET", False,
                              f"Missing fields: {missing_fields}")
        
        # Проверяем что telegram_id совпадает
        if data.get("telegram_id") != TEST_TELEGRAM_ID:
            return print_status("Profile GET", False,
                              f"telegram_id mismatch: {data.get('telegram_id')}")
        
        return print_status("Profile GET", True,
                          f"Balance: {data.get('balance_usdt')} USDT")
    except Exception as e:
        return print_status("Profile GET", False, str(e))


def test_profile_update_username():
    """Тест: обновление имени пользователя"""
    print("\n👤 Тест: Обновление имени пользователя")
    
    test_username = f"test_user_{TEST_TELEGRAM_ID}"
    
    try:
        # Обновляем профиль
        update_data = {
            "custom_username": test_username
        }
        
        response = requests.post(
            f"{BASE_URL}/user/profile/update",
            params={"telegram_id": TEST_TELEGRAM_ID},
            json=update_data,
            timeout=10
        )
        
        if response.status_code != 200:
            return print_status("Update Username", False,
                              f"Status code: {response.status_code}, {response.text}")
        
        data = response.json()
        
        # Проверяем ответ
        if not data.get("success"):
            return print_status("Update Username", False, "success=False in response")
        
        profile = data.get("profile", {})
        if profile.get("custom_username") != test_username:
            return print_status("Update Username", False,
                              f"Username not updated: {profile.get('custom_username')}")
        
        # Проверяем что обновление сохранилось
        get_response = requests.get(
            f"{BASE_URL}/user/{TEST_TELEGRAM_ID}/profile",
            timeout=10
        )
        get_data = get_response.json()
        
        if get_data.get("custom_username") != test_username:
            return print_status("Update Username", False,
                              "Username not persisted in database")
        
        return print_status("Update Username", True,
                          f"Username: {test_username}")
    except Exception as e:
        return print_status("Update Username", False, str(e))


def test_profile_username_length_limit():
    """Тест: лимит длины имени"""
    print("\n👤 Тест: Лимит длины имени")
    
    # Имя длиннее 50 символов
    long_username = "A" * 51
    
    try:
        update_data = {
            "custom_username": long_username
        }
        
        response = requests.post(
            f"{BASE_URL}/user/profile/update",
            params={"telegram_id": TEST_TELEGRAM_ID},
            json=update_data,
            timeout=10
        )
        
        # Должен вернуть 400 (Bad Request)
        passed = response.status_code == 400
        return print_status("Username Length Limit", passed,
                          f"Status: {response.status_code}")
    except Exception as e:
        return print_status("Username Length Limit", False, str(e))


def test_profile_upload_avatar():
    """Тест: загрузка аватара"""
    print("\n👤 Тест: Загрузка аватара")
    
    try:
        # Создаём тестовое изображение (1x1 pixel PNG)
        # PNG 1x1 pixel
        test_image = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1
            0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
            0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,  # IDAT chunk
            0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
            0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,
            0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,  # IEND chunk
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
            return print_status("Upload Avatar", False,
                              f"Status code: {response.status_code}, {response.text}")
        
        data = response.json()
        
        # Проверяем ответ
        if not data.get("success"):
            return print_status("Upload Avatar", False, "success=False in response")
        
        avatar_url = data.get("avatar_url")
        if not avatar_url:
            return print_status("Upload Avatar", False, "No avatar_url in response")
        
        # Проверяем что URL содержит путь к аватару
        if "/uploads/avatars/" not in avatar_url:
            return print_status("Upload Avatar", False,
                              f"Invalid avatar URL: {avatar_url}")
        
        return print_status("Upload Avatar", True, f"URL: {avatar_url}")
    except Exception as e:
        return print_status("Upload Avatar", False, str(e))


def test_profile_avatar_validation():
    """Тест: валидация типа файла аватара"""
    print("\n👤 Тест: Валидация типа файла аватара")
    
    try:
        # Пытаемся загрузить TXT файл (должен быть отклонён)
        files = {"file": ("test.txt", b"This is not an image", "text/plain")}
        
        response = requests.post(
            f"{BASE_URL}/user/profile/upload-avatar",
            params={"telegram_id": TEST_TELEGRAM_ID},
            files=files,
            timeout=10
        )
        
        # Должен вернуть 400 (Bad Request)
        passed = response.status_code == 400
        return print_status("Avatar Validation", passed,
                          f"Status: {response.status_code}")
    except Exception as e:
        return print_status("Avatar Validation", False, str(e))


def test_profile_avatar_size_limit():
    """Тест: лимит размера аватара"""
    print("\n👤 Тест: Лимит размера аватара")
    
    try:
        # Создаём файл больше 5MB
        large_file = b"A" * (6 * 1024 * 1024)  # 6MB
        files = {"file": ("large_image.png", large_file, "image/png")}
        
        response = requests.post(
            f"{BASE_URL}/user/profile/upload-avatar",
            params={"telegram_id": TEST_TELEGRAM_ID},
            files=files,
            timeout=10
        )
        
        # Должен вернуть 400 (Bad Request)
        passed = response.status_code == 400
        return print_status("Avatar Size Limit", passed,
                          f"Status: {response.status_code}")
    except Exception as e:
        return print_status("Avatar Size Limit", False, str(e))


def test_profile_update_avatar_url():
    """Тест: обновление URL аватара"""
    print("\n👤 Тест: Обновление URL аватара")
    
    test_avatar_url = "https://example.com/avatar.jpg"
    
    try:
        update_data = {
            "avatar_url": test_avatar_url
        }
        
        response = requests.post(
            f"{BASE_URL}/user/profile/update",
            params={"telegram_id": TEST_TELEGRAM_ID},
            json=update_data,
            timeout=10
        )
        
        if response.status_code != 200:
            return print_status("Update Avatar URL", False,
                              f"Status code: {response.status_code}, {response.text}")
        
        data = response.json()
        
        # Проверяем ответ
        if not data.get("success"):
            return print_status("Update Avatar URL", False, "success=False in response")
        
        profile = data.get("profile", {})
        if profile.get("avatar_url") != test_avatar_url:
            return print_status("Update Avatar URL", False,
                              f"Avatar URL not updated: {profile.get('avatar_url')}")
        
        return print_status("Update Avatar URL", True,
                          f"URL: {test_avatar_url}")
    except Exception as e:
        return print_status("Update Avatar URL", False, str(e))


def test_profile_avatar_url_length_limit():
    """Тест: лимит длины URL аватара"""
    print("\n👤 Тест: Лимит длины URL аватара")
    
    # URL длиннее 500 символов
    long_url = "https://example.com/" + "a" * 500
    
    try:
        update_data = {
            "avatar_url": long_url
        }
        
        response = requests.post(
            f"{BASE_URL}/user/profile/update",
            params={"telegram_id": TEST_TELEGRAM_ID},
            json=update_data,
            timeout=10
        )
        
        # Должен вернуть 400 (Bad Request)
        passed = response.status_code == 400
        return print_status("Avatar URL Length Limit", passed,
                          f"Status: {response.status_code}")
    except Exception as e:
        return print_status("Avatar URL Length Limit", False, str(e))


def test_profile_endpoints_exist():
    """Тест: проверка существования endpoints в коде"""
    print("\n👤 Тест: Существование endpoints в коде")
    
    try:
        with open('api/index.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверяем наличие endpoints
        has_get_profile = '@app.get("/user/{telegram_id}/profile")' in content
        has_update_profile = '@app.post("/user/profile/update")' in content
        has_upload_avatar = '@app.post("/user/profile/upload-avatar")' in content
        
        # Проверяем наличие модели ProfileUpdateRequest
        has_profile_model = 'class ProfileUpdateRequest' in content
        
        # Проверяем наличие полей в User модели
        with open('api/models.py', 'r', encoding='utf-8') as f:
            models_content = f.read()
        
        has_custom_username = 'custom_username' in models_content
        has_avatar_url = 'avatar_url' in models_content
        
        passed = (has_get_profile and has_update_profile and has_upload_avatar and
                 has_profile_model and has_custom_username and has_avatar_url)
        
        return print_status("Endpoints Exist", passed,
                          f"GET profile: {has_get_profile}, UPDATE: {has_update_profile}, UPLOAD: {has_upload_avatar}")
    except Exception as e:
        return print_status("Endpoints Exist", False, str(e))


if __name__ == "__main__":
    print("=" * 60)
    print("EventPredict — Тесты Profile API")
    print("=" * 60)
    
    try:
        results = []
        
        results.append(test_profile_endpoints_exist())
        results.append(test_profile_get())
        results.append(test_profile_update_username())
        results.append(test_profile_username_length_limit())
        results.append(test_profile_update_avatar_url())
        results.append(test_profile_avatar_url_length_limit())
        results.append(test_profile_upload_avatar())
        results.append(test_profile_avatar_validation())
        results.append(test_profile_avatar_size_limit())
        
        print("\n" + "=" * 60)
        passed = sum(results)
        total = len(results)
        print(f"Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ")
        else:
            print(f"⚠️  {total - passed} тестов провалено")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        exit(1)
