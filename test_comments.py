"""
EventPredict — Comments API Tests

Автоматические тесты для проверки функциональности комментариев
"""

import requests
import os
import time

BASE_URL = os.getenv("EVENTPREDICT_URL", "http://localhost:8000")

# Тестовые данные
TEST_TELEGRAM_ID = 123456789
TEST_USERNAME = "test_user"


def print_status(name, passed, message=""):
    """Print test status"""
    status = "[PASS]" if passed else "[FAIL]"
    print(f"{status}: {name}")
    if message and not passed:
        print(f"   + {message}")
    return passed


def get_test_event_id():
    """Получить ID первого доступного события для тестов"""
    try:
        response = requests.get(f"{BASE_URL}/events", timeout=10)
        events = response.json().get("events", [])
        if events:
            return events[0]["id"]
    except Exception as e:
        print(f"Error getting event ID: {e}")
    return None


def test_comments_api_get():
    """Тест: получение комментариев"""
    print("\n💬 Тест: Получение комментариев")
    
    event_id = get_test_event_id()
    if not event_id:
        return print_status("Comments API GET", False, "No events available")
    
    try:
        response = requests.get(
            f"{BASE_URL}/events/{event_id}/comments",
            timeout=10
        )
        
        if response.status_code != 200:
            return print_status("Comments API GET", False,
                              f"Status code: {response.status_code}")
        
        data = response.json()
        
        # Проверяем что это список
        if not isinstance(data, list):
            return print_status("Comments API GET", False,
                              f"Expected list, got {type(data)}")
        
        # Если есть комментарии, проверяем структуру
        if data:
            first_comment = data[0]
            required_fields = ["id", "event_id", "telegram_id", "username",
                             "comment_text", "created_at"]
            
            missing_fields = [f for f in required_fields if f not in first_comment]
            if missing_fields:
                return print_status("Comments API GET", False,
                                  f"Missing fields: {missing_fields}")
        
        return print_status("Comments API GET", True,
                          f"Returned {len(data)} comments")
    except Exception as e:
        return print_status("Comments API GET", False, str(e))


def test_comments_api_post():
    """Тест: добавление комментария"""
    print("\n💬 Тест: Добавление комментария")
    
    event_id = get_test_event_id()
    if not event_id:
        return print_status("Comments API POST", False, "No events available")
    
    try:
        # Создаём тестовый комментарий
        comment_data = {
            "comment_text": "Тестовый комментарий для проверки API",
            "telegram_id": TEST_TELEGRAM_ID,
            "username": TEST_USERNAME
        }
        
        response = requests.post(
            f"{BASE_URL}/events/{event_id}/comments",
            json=comment_data,
            timeout=10
        )
        
        if response.status_code != 200:
            return print_status("Comments API POST", False,
                              f"Status code: {response.status_code}, {response.text}")
        
        data = response.json()
        
        # Проверяем ответ
        if not data.get("success"):
            return print_status("Comments API POST", False, "success=False in response")
        
        comment = data.get("comment", {})
        if not comment.get("id"):
            return print_status("Comments API POST", False, "No comment ID in response")
        
        # Проверяем что комментарий сохранился
        if comment.get("comment_text") != comment_data["comment_text"]:
            return print_status("Comments API POST", False,
                              "Comment text mismatch")
        
        return print_status("Comments API POST", True,
                          f"Created comment ID: {comment.get('id')}")
    except Exception as e:
        return print_status("Comments API POST", False, str(e))


def test_comments_block_links():
    """Тест: блокировка ссылок"""
    print("\n💬 Тест: Блокировка ссылок")
    
    event_id = get_test_event_id()
    if not event_id:
        return print_status("Block Links", False, "No events available")
    
    # Тестовые комментарии со ссылками
    link_comments = [
        "Проверьте https://example.com",
        "Вот ссылка: www.test.com",
        "HTTP://EXAMPLE.COM/link",
        "Visit http://spam.com"
    ]
    
    blocked_count = 0
    for comment_text in link_comments:
        try:
            comment_data = {
                "comment_text": comment_text,
                "telegram_id": TEST_TELEGRAM_ID + 1,  # Разный telegram_id для rate limit
                "username": TEST_USERNAME
            }
            
            response = requests.post(
                f"{BASE_URL}/events/{event_id}/comments",
                json=comment_data,
                timeout=10
            )
            
            # Должен вернуть 400 (Bad Request)
            if response.status_code == 400:
                blocked_count += 1
        except Exception:
            pass
    
    passed = blocked_count == len(link_comments)
    return print_status("Block Links", passed,
                      f"Blocked {blocked_count}/{len(link_comments)} links")


def test_comments_block_profanity():
    """Тест: блокировка оскорблений"""
    print("\n💬 Тест: Блокировка оскорблений")
    
    event_id = get_test_event_id()
    if not event_id:
        return print_status("Block Profanity", False, "No events available")
    
    # Тестовые комментарии с оскорблениями
    profanity_comments = [
        "Ты дурак",
        "Это полный пиздец",
        "Какой же ты идиот",
        "Fuck you",
        "This is bullshit"
    ]
    
    blocked_count = 0
    for i, comment_text in enumerate(profanity_comments):
        try:
            comment_data = {
                "comment_text": comment_text,
                "telegram_id": TEST_TELEGRAM_ID + 100 + i,  # Разный telegram_id
                "username": TEST_USERNAME
            }
            
            response = requests.post(
                f"{BASE_URL}/events/{event_id}/comments",
                json=comment_data,
                timeout=10
            )
            
            # Должен вернуть 400 (Bad Request)
            if response.status_code == 400:
                blocked_count += 1
        except Exception:
            pass
    
    passed = blocked_count > 0  # Хотя бы некоторые должны заблокироваться
    return print_status("Block Profanity", passed,
                      f"Blocked {blocked_count}/{len(profanity_comments)} profanity comments")


def test_comments_rate_limit():
    """Тест: rate limiting"""
    print("\n💬 Тест: Rate limiting")
    
    event_id = get_test_event_id()
    if not event_id:
        return print_status("Rate Limiting", False, "No events available")
    
    # Отправляем больше 3 комментариев за минуту с одного telegram_id
    rate_limit_triggered = False
    test_telegram_id = TEST_TELEGRAM_ID + 999  # Уникальный ID для теста
    
    try:
        for i in range(5):
            comment_data = {
                "comment_text": f"Тестовый комментарий #{i}",
                "telegram_id": test_telegram_id,
                "username": TEST_USERNAME
            }
            
            response = requests.post(
                f"{BASE_URL}/events/{event_id}/comments",
                json=comment_data,
                timeout=10
            )
            
            # 4-й и 5-й комментарии должны вернуть 429 (Too Many Requests)
            if i >= 3 and response.status_code == 429:
                rate_limit_triggered = True
                break
            
            time.sleep(0.1)  # Небольшая задержка
    except Exception as e:
        return print_status("Rate Limiting", False, str(e))
    
    return print_status("Rate Limiting", rate_limit_triggered,
                      "Rate limit triggered" if rate_limit_triggered else "Rate limit not triggered")


def test_comments_length_limit():
    """Тест: лимит длины комментария"""
    print("\n💬 Тест: Лимит длины комментария")
    
    event_id = get_test_event_id()
    if not event_id:
        return print_status("Length Limit", False, "No events available")
    
    try:
        # Комментарий длиннее 1000 символов
        long_comment = "A" * 1001
        
        comment_data = {
            "comment_text": long_comment,
            "telegram_id": TEST_TELEGRAM_ID + 888,
            "username": TEST_USERNAME
        }
        
        response = requests.post(
            f"{BASE_URL}/events/{event_id}/comments",
            json=comment_data,
            timeout=10
        )
        
        # Должен вернуть 400 (Bad Request)
        passed = response.status_code == 400
        return print_status("Length Limit", passed,
                          f"Status: {response.status_code}")
    except Exception as e:
        return print_status("Length Limit", False, str(e))


def test_comments_admin_delete():
    """Тест: удаление комментария админом"""
    print("\n💬 Тест: Удаление комментария админом")
    
    event_id = get_test_event_id()
    if not event_id:
        return print_status("Admin Delete", False, "No events available")
    
    # Получаем ADMIN_TELEGRAM_ID из environment или используем дефолтный
    admin_telegram_id = os.getenv("ADMIN_TELEGRAM_ID", "1972885597")
    
    try:
        # Сначала создаём комментарий
        comment_data = {
            "comment_text": "Комментарий для удаления",
            "telegram_id": TEST_TELEGRAM_ID + 777,
            "username": TEST_USERNAME
        }
        
        create_response = requests.post(
            f"{BASE_URL}/events/{event_id}/comments",
            json=comment_data,
            timeout=10
        )
        
        if create_response.status_code != 200:
            return print_status("Admin Delete", False,
                              f"Failed to create comment: {create_response.status_code}")
        
        comment_id = create_response.json().get("comment", {}).get("id")
        if not comment_id:
            return print_status("Admin Delete", False, "No comment ID in response")
        
        # Теперь удаляем комментарий (как админ)
        delete_response = requests.delete(
            f"{BASE_URL}/admin/comments/{comment_id}",
            params={"telegram_id": admin_telegram_id},
            timeout=10
        )
        
        if delete_response.status_code != 200:
            return print_status("Admin Delete", False,
                              f"Delete status: {delete_response.status_code}")
        
        # Проверяем что комментарий удалён (is_deleted=True)
        get_response = requests.get(
            f"{BASE_URL}/events/{event_id}/comments",
            timeout=10
        )
        comments = get_response.json()
        
        deleted_comment = next((c for c in comments if c["id"] == comment_id), None)
        
        # Удалённый комментарий не должен отображаться в списке
        passed = deleted_comment is None
        return print_status("Admin Delete", passed,
                          "Comment deleted successfully" if passed else "Comment still visible")
    except Exception as e:
        return print_status("Admin Delete", False, str(e))


def test_comments_non_admin_delete():
    """Тест: попытка удаления комментария не админом"""
    print("\n💬 Тест: Попытка удаления не админом")
    
    event_id = get_test_event_id()
    if not event_id:
        return print_status("Non-Admin Delete", False, "No events available")
    
    try:
        # Пытаемся удалить комментарий с не-админ telegram_id
        fake_admin_id = 999999999
        
        delete_response = requests.delete(
            f"{BASE_URL}/admin/comments/999",  # Несуществующий ID
            params={"telegram_id": fake_admin_id},
            timeout=10
        )
        
        # Должен вернуть 403 (Forbidden)
        passed = delete_response.status_code == 403
        return print_status("Non-Admin Delete", passed,
                          f"Status: {delete_response.status_code}")
    except Exception as e:
        return print_status("Non-Admin Delete", False, str(e))


if __name__ == "__main__":
    print("=" * 60)
    print("EventPredict — Тесты Comments API")
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
        time.sleep(0.5)
        
        results.append(test_comments_rate_limit())
        time.sleep(0.5)
        
        results.append(test_comments_admin_delete())
        time.sleep(0.5)
        
        results.append(test_comments_non_admin_delete())
        
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
