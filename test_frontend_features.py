#!/usr/bin/env python3
"""
EventPredict Frontend Tests
Tests for Russian translation and image handling
"""
import re
import sys

def print_status(name, passed, message=""):
    """Print test status"""
    status = "[PASS]" if passed else "[FAIL]"
    print(f"{status}: {name}")
    if message and not passed:
        print(f"   + {message}")
    return passed

def test_translation_preserve_terms():
    """Test that preserve terms (names, crypto) are not translated"""
    try:
        with open('frontend/script.js', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check PRESERVE_TERMS exists
        has_preserve = 'PRESERVE_TERMS' in content
        
        # Check key terms are in preserve list
        key_terms = ['Bitcoin', 'Ethereum', 'Trump', 'Biden', 'Tesla', 'NBA', 'NFL']
        terms_found = sum(1 for term in key_terms if f"'{term}'" in content)
        
        passed = has_preserve and terms_found >= 5
        return print_status("Translation Preserve Terms", passed,
                           f"Found {terms_found}/{len(key_terms)} key terms in preserve list")
    except Exception as e:
        return print_status("Translation Preserve Terms", False, str(e))

def test_translation_dict():
    """Test that translation dictionary exists and is comprehensive"""
    try:
        with open('frontend/script.js', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check TRANSLATION_DICT exists
        has_dict = 'TRANSLATION_DICT' in content
        
        # Check key translations
        key_translations = [
            "'market': 'рынок'",
            "'price': 'цена'",
            "'election': 'выборы'",
            "'team': 'команда'"
        ]
        translations_found = sum(1 for t in key_translations if t in content)
        
        passed = has_dict and translations_found >= 3
        return print_status("Translation Dictionary", passed,
                           f"Found {translations_found}/{len(key_translations)} key translations")
    except Exception as e:
        return print_status("Translation Dictionary", False, str(e))

def test_translate_function():
    """Test that translateEventText function exists"""
    try:
        with open('frontend/script.js', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check function exists
        has_function = 'function translateEventText(text)' in content
        
        # Check it uses preserve mechanism
        uses_preserve = 'PRESERVE_TERMS' in content and 'preservedMap' in content
        
        # Check it's called for event titles
        called_for_titles = 'translateEventText(event.title)' in content
        
        passed = has_function and uses_preserve and called_for_titles
        return print_status("Translate Function", passed,
                           f"Function exists: {has_function}, Uses preserve: {uses_preserve}")
    except Exception as e:
        return print_status("Translate Function", False, str(e))

def test_image_proxy_usage():
    """Test that image proxy is used in frontend"""
    try:
        with open('frontend/script.js', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check proxy URL is used
        uses_proxy = 'proxy/image' in content or 'proxiedUrl' in content
        
        # Check onerror handler exists
        has_fallback = 'onerror' in content and 'style.display' in content
        
        # Check placeholder exists
        has_placeholder = 'event-image-placeholder' in content
        
        passed = uses_proxy and has_fallback and has_placeholder
        return print_status("Image Proxy Usage", passed,
                           f"Uses proxy: {uses_proxy}, Has fallback: {has_fallback}")
    except Exception as e:
        return print_status("Image Proxy Usage", False, str(e))

def test_backend_proxy_endpoint():
    """Test that backend proxy endpoint exists"""
    try:
        with open('api/index.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check endpoint exists
        has_endpoint = '@app.get("/proxy/image")' in content
        
        # Check it validates URLs
        has_validation = 'polymarket.com' in content
        
        # Check it returns images
        returns_image = 'media_type' in content and 'image/' in content
        
        passed = has_endpoint and has_validation and returns_image
        return print_status("Backend Proxy Endpoint", passed,
                           f"Endpoint exists: {has_endpoint}, Validates: {has_validation}")
    except Exception as e:
        return print_status("Backend Proxy Endpoint", False, str(e))

def test_chart_data_from_polymarket():
    """Test that chart uses real data from Polymarket"""
    try:
        with open('frontend/script.js', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check price history fetch
        fetches_history = 'price-history' in content
        
        # Check PriceHistory model in backend
        with open('api/models.py', 'r', encoding='utf-8') as models_f:
            models_content = models_f.read()
        
        has_model = 'class PriceHistory' in models_content
        
        # Check chart rendering
        has_chart = 'renderEventChart' in content and 'Chart.js' in content
        
        passed = fetches_history and has_model and has_chart
        return print_status("Chart Data from Polymarket", passed,
                           f"Fetches history: {fetches_history}, Has model: {has_model}")
    except Exception as e:
        return print_status("Chart Data from Polymarket", False, str(e))

def test_russian_language_detection():
    """Test that Russian language is auto-detected"""
    try:
        with open('frontend/script.js', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check language detection
        detects_lang = 'getUserLanguage' in content or 'language_code' in content
        
        # Check isRussian flag
        has_flag = 'isRussian' in content
        
        # Check Telegram integration
        uses_telegram = 'tg.initDataUnsafe' in content or 'Telegram.WebApp' in content
        
        passed = detects_lang and has_flag and uses_telegram
        return print_status("Russian Language Detection", passed,
                           f"Detects language: {detects_lang}, Uses Telegram: {uses_telegram}")
    except Exception as e:
        return print_status("Russian Language Detection", False, str(e))

def test_security_no_xss():
    """Test basic XSS protection"""
    try:
        with open('frontend/script.js', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check escapeHtml function exists
        has_escape = 'escapeHtml' in content or 'escapeRegExp' in content
        
        # Check it's used for event titles
        escapes_titles = 'escapeHtml(translateEventText' in content
        
        passed = has_escape and escapes_titles
        return print_status("XSS Protection", passed,
                           f"Has escape: {has_escape}, Escapes titles: {escapes_titles}")
    except Exception as e:
        return print_status("XSS Protection", False, str(e))

def test_backend_security():
    """Test backend security measures"""
    try:
        with open('api/index.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check admin validation
        admin_check = 'ADMIN_TELEGRAM_ID' in content
        
        # Check input validation
        input_validation = 'HTTPException' in content and 'status_code=400' in content
        
        # Check CORS
        cors = 'CORSMiddleware' in content
        
        passed = admin_check and input_validation and cors
        return print_status("Backend Security", passed,
                           f"Admin check: {admin_check}, Input validation: {input_validation}")
    except Exception as e:
        return print_status("Backend Security", False, str(e))

def main():
    """Run all frontend tests"""
    print("=" * 60)
    print("EventPredict Frontend Tests")
    print("Testing: Translation, Images, Charts, Security")
    print("=" * 60)
    print()

    tests = [
        test_translation_preserve_terms,
        test_translation_dict,
        test_translate_function,
        test_image_proxy_usage,
        test_backend_proxy_endpoint,
        test_chart_data_from_polymarket,
        test_russian_language_detection,
        test_security_no_xss,
        test_backend_security,
    ]

    results = []
    for test in tests:
        results.append(test())

    print()
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("[OK] All frontend tests passed!")
    else:
        print(f"[ERR] {total - passed} tests failed. Check the errors above.")

    print("=" * 60)

    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
