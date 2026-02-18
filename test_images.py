"""
EventPredict — Image Proxy Tests

Автоматические тесты для проверки proxy изображений для Telegram WebApp
"""

import requests
import os

BASE_URL = os.getenv("EVENTPREDICT_URL", "http://localhost:8000")

# Тестовый URL изображения Polymarket
TEST_IMAGE_URL = "https://gamma-api.polymarket.com/test-image.jpg"


def test_image_proxy_returns_cors_headers():
    """Проверка что proxy endpoint возвращает CORS заголовки"""
    print("\n📸 Тест: CORS заголовки proxy endpoint")
    
    response = requests.get(
        f"{BASE_URL}/proxy/image",
        params={"url": TEST_IMAGE_URL},
        timeout=10
    )
    
    # Проверяем что endpoint доступен (может вернуть 404 для несуществующего изображения)
    # Главное что CORS заголовки присутствуют
    assert "Access-Control-Allow-Origin" in response.headers, \
        "Отсутствует заголовок Access-Control-Allow-Origin"
    assert response.headers["Access-Control-Allow-Origin"] == "*", \
        "Access-Control-Allow-Origin должен быть '*'"
    
    assert "Cross-Origin-Resource-Policy" in response.headers, \
        "Отсутствует заголовок Cross-Origin-Resource-Policy"
    assert response.headers["Cross-Origin-Resource-Policy"] == "cross-origin", \
        "Cross-Origin-Resource-Policy должен быть 'cross-origin'"
    
    assert "Access-Control-Allow-Headers" in response.headers, \
        "Отсутствует заголовок Access-Control-Allow-Headers"
    
    assert "Cache-Control" in response.headers, \
        "Отсутствует заголовок Cache-Control"
    assert "max-age=86400" in response.headers["Cache-Control"], \
        "Cache-Control должен содержать max-age=86400 (24 часа)"
    
    print("✅ CORS заголовки присутствуют и корректны")


def test_image_proxy_for_telegram():
    """Проверка режима proxy для Telegram WebApp"""
    print("\n📸 Тест: Telegram WebApp режим proxy")
    
    response = requests.get(
        f"{BASE_URL}/proxy/image",
        params={"url": TEST_IMAGE_URL, "telegram_webapp": "1"},
        timeout=10
    )
    
    # Проверяем что endpoint принимает параметр telegram_webapp
    assert response.status_code in [200, 404], \
        f"Неожиданный статус ответа: {response.status_code}"
    
    # CORS заголовки должны быть независимо от режима
    assert "Access-Control-Allow-Origin" in response.headers, \
        "Отсутствует заголовок Access-Control-Allow-Origin"
    
    print("✅ Telegram WebApp режим работает корректно")


def test_image_proxy_url_validation():
    """Проверка валидации URL изображений"""
    print("\n📸 Тест: Валидация URL изображений")
    
    # Тест с пустым URL
    response = requests.get(
        f"{BASE_URL}/proxy/image",
        params={"url": ""},
        timeout=10
    )
    assert response.status_code == 400, \
        f"Пустой URL должен вернуть 400, получил: {response.status_code}"
    
    # Тест с невалидным доменом (не Polymarket)
    response = requests.get(
        f"{BASE_URL}/proxy/image",
        params={"url": "https://example.com/image.jpg"},
        timeout=10
    )
    assert response.status_code == 400, \
        f"Не-Polymarket URL должен вернуть 400, получил: {response.status_code}"
    
    print("✅ Валидация URL работает корректно")


def test_image_proxy_polymarket_urls():
    """Проверка что Polymarket URL разрешены"""
    print("\n📸 Тест: Разрешённые Polymarket URL")
    
    # Разные варианты Polymarket URL
    valid_urls = [
        "https://gamma-api.polymarket.com/image.jpg",
        "https://polymarket.com/image.png",
        "https://polygon.com/image.webp"
    ]
    
    for url in valid_urls:
        response = requests.get(
            f"{BASE_URL}/proxy/image",
            params={"url": url},
            timeout=10
        )
        # Должен принять URL (404 OK для несуществующего файла)
        assert response.status_code in [200, 404], \
            f"Polymarket URL {url} должен быть разрешён, статус: {response.status_code}"
    
    print("✅ Polymarket URL корректно разрешены")


def test_image_fallback_on_error():
    """
    Проверка что frontend имеет fallback на placeholder
    
    Этот тест проверяет наличие функции handleImageError в script.js
    """
    print("\n📸 Тест: Fallback на placeholder при ошибке")
    
    # Читаем frontend/script.js и проверяем наличие функции
    script_path = os.path.join(os.path.dirname(__file__), "frontend", "script.js")
    
    if not os.path.exists(script_path):
        # Пробуем альтернативный путь
        script_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "script.js")
    
    if os.path.exists(script_path):
        with open(script_path, "r", encoding="utf-8") as f:
            script_content = f.read()
        
        # Проверяем наличие функции handleImageError
        assert "handleImageError" in script_content, \
            "Функция handleImageError отсутствует в script.js"
        
        # Проверяем что функция скрывает изображение и показывает placeholder
        assert "style.display = 'none'" in script_content, \
            "Функция должна скрывать изображение при ошибке"
        assert "event-image-placeholder" in script_content, \
            "Должен существовать placeholder для изображений"
        
        print("✅ Fallback на placeholder реализован в frontend")
    else:
        print("⚠️  script.js не найден, пропускаем тест frontend")


def test_image_proxy_content_type():
    """Проверка что proxy возвращает правильный Content-Type"""
    print("\n📸 Тест: Content-Type изображений")
    
    # Тестовый URL (может вернуть 404, но это OK)
    response = requests.get(
        f"{BASE_URL}/proxy/image",
        params={"url": TEST_IMAGE_URL},
        timeout=10
    )
    
    # Если изображение загрузилось (200), проверяем Content-Type
    if response.status_code == 200:
        content_type = response.headers.get("content-type", "")
        assert content_type.startswith("image/"), \
            f"Content-Type должен быть image/*, получен: {content_type}"
        print(f"✅ Content-Type корректен: {content_type}")
    else:
        print("⚠️  Изображение не найдено (404), пропускаем проверку Content-Type")


if __name__ == "__main__":
    print("=" * 60)
    print("EventPredict — Тесты Image Proxy")
    print("=" * 60)
    
    try:
        test_image_proxy_returns_cors_headers()
        test_image_proxy_for_telegram()
        test_image_proxy_url_validation()
        test_image_proxy_polymarket_urls()
        test_image_fallback_on_error()
        test_image_proxy_content_type()
        
        print("\n" + "=" * 60)
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ ТЕСТ ПРОВАЛЕН: {e}")
        exit(1)
    except requests.exceptions.RequestException as e:
        print(f"\n❌ ОШИБКА СЕТИ: {e}")
        print("Убедитесь что сервер запущен и EVENTPREDICT_URL настроен корректно")
        exit(1)
    except Exception as e:
        print(f"\n❌ НЕОЖИДАННАЯ ОШИБКА: {e}")
        exit(1)
