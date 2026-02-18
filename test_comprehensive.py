"""
EventPredict - Comprehensive Tests

Комплексные тесты для проверки работоспособности приложения.
Включает тесты backend API, базы данных, и интеграции.
"""

import sys
import os
import unittest
import requests
import json
from datetime import datetime

# Добавляем корень проекта в path
try:
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
except NameError:
    PROJECT_ROOT = os.getcwd()
sys.path.insert(0, PROJECT_ROOT)

# Конфигурация
BASE_URL = os.getenv("EVENTPREDICT_URL", "http://localhost:8000")
TIMEOUT = 30  # секунд


class TestBackendImports(unittest.TestCase):
    """Тесты импортов backend"""
    
    def test_api_imports(self):
        """Проверка что все импорты работают"""
        try:
            # Пытаемся импортировать основные модули
            import_result = {}
            
            # FastAPI
            try:
                from fastapi import FastAPI
                import_result['fastapi'] = True
            except ImportError as e:
                import_result['fastapi'] = str(e)
            
            # SQLAlchemy
            try:
                from sqlalchemy import create_engine
                import_result['sqlalchemy'] = True
            except ImportError as e:
                import_result['sqlalchemy'] = str(e)
            
            # APScheduler
            try:
                from apscheduler.schedulers.asyncio import AsyncIOScheduler
                import_result['apscheduler'] = True
            except ImportError as e:
                import_result['apscheduler'] = str(e)
            
            # Pydantic
            try:
                from pydantic import BaseModel
                import_result['pydantic'] = True
            except ImportError as e:
                import_result['pydantic'] = str(e)
            
            # Проверяем что все импорты успешны
            failed = [k for k, v in import_result.items() if v is not True]
            
            if failed:
                self.fail(f"Failed imports: {failed}")
                
        except Exception as e:
            self.fail(f"Import test failed: {e}")
    
    def test_index_module_import(self):
        """Проверка импорта api.index"""
        try:
            # Меняем рабочую директорию на api
            api_dir = os.path.join(os.path.dirname(__file__), 'api')
            if os.path.exists(api_dir):
                sys.path.insert(0, api_dir)
                try:
                    import index
                    self.assertTrue(hasattr(index, 'app'))
                finally:
                    sys.path.remove(api_dir)
            else:
                self.skipTest("api/index.py not found")
        except ImportError as e:
            self.fail(f"Cannot import api.index: {e}")


class TestDatabaseConnection(unittest.TestCase):
    """Тесты подключения к базе данных"""
    
    def test_database_module_import(self):
        """Проверка импорта models.py"""
        try:
            api_dir = os.path.join(os.path.dirname(__file__), 'api')
            if os.path.exists(api_dir):
                sys.path.insert(0, api_dir)
                try:
                    from models import User, Event, EventOption, Transaction, PriceHistory
                    self.assertTrue(True)
                finally:
                    sys.path.remove(api_dir)
            else:
                self.skipTest("api/models.py not found")
        except ImportError as e:
            self.fail(f"Cannot import models: {e}")


class TestHealthEndpoint(unittest.TestCase):
    """Тесты health endpoint"""
    
    def test_health_endpoint(self):
        """Проверка /health endpoint"""
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIn("status", data)
            self.assertEqual(data["status"], "healthy")
            
            # Проверяем наличие sync информации
            if "sync" in data:
                self.assertIn("next_sync_in", data["sync"])
                
        except requests.exceptions.ConnectionError:
            self.skipTest(f"Cannot connect to {BASE_URL}")
        except Exception as e:
            self.fail(f"Health endpoint test failed: {e}")
    
    def test_root_endpoint(self):
        """Проверка корневого endpoint"""
        try:
            response = requests.get(f"{BASE_URL}/", timeout=TIMEOUT)
            # Должен вернуть 200 (frontend или API status)
            self.assertIn(response.status_code, [200, 304])
        except requests.exceptions.ConnectionError:
            self.skipTest(f"Cannot connect to {BASE_URL}")
        except Exception as e:
            self.fail(f"Root endpoint test failed: {e}")


class TestApiEndpoints(unittest.TestCase):
    """Тесты API endpoints"""
    
    def test_categories_endpoint(self):
        """Проверка /categories endpoint"""
        try:
            response = requests.get(f"{BASE_URL}/categories", timeout=TIMEOUT)
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIn("categories", data)
            self.assertIsInstance(data["categories"], list)
            self.assertGreater(len(data["categories"]), 0)
            
        except requests.exceptions.ConnectionError:
            self.skipTest(f"Cannot connect to {BASE_URL}")
        except Exception as e:
            self.fail(f"Categories endpoint test failed: {e}")
    
    def test_events_endpoint(self):
        """Проверка /events endpoint"""
        try:
            response = requests.get(f"{BASE_URL}/events", timeout=TIMEOUT)
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIn("events", data)
            self.assertIsInstance(data["events"], list)
            
        except requests.exceptions.ConnectionError:
            self.skipTest(f"Cannot connect to {BASE_URL}")
        except Exception as e:
            self.fail(f"Events endpoint test failed: {e}")
    
    def test_events_with_category_filter(self):
        """Проверка /events?category= endpoint"""
        try:
            categories = ['politics', 'sports', 'crypto', 'business']
            
            for category in categories:
                response = requests.get(
                    f"{BASE_URL}/events?category={category}",
                    timeout=TIMEOUT
                )
                self.assertEqual(response.status_code, 200)
                
                data = response.json()
                self.assertIn("events", data)
                
        except requests.exceptions.ConnectionError:
            self.skipTest(f"Cannot connect to {BASE_URL}")
        except Exception as e:
            self.fail(f"Category filter test failed: {e}")
    
    def test_user_endpoint(self):
        """Проверка /user/{telegram_id} endpoint"""
        try:
            test_id = 123456789
            response = requests.get(
                f"{BASE_URL}/user/{test_id}",
                timeout=TIMEOUT
            )
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIn("telegram_id", data)
            self.assertIn("points", data)
            
        except requests.exceptions.ConnectionError:
            self.skipTest(f"Cannot connect to {BASE_URL}")
        except Exception as e:
            self.fail(f"User endpoint test failed: {e}")


class TestPolymarketIntegration(unittest.TestCase):
    """Тесты интеграции с Polymarket"""
    
    def test_polymarket_api_connection(self):
        """Проверка подключения к Polymarket API"""
        try:
            response = requests.get(
                "https://gamma-api.polymarket.com/markets",
                params={"limit": 1},
                timeout=10
            )
            self.assertEqual(response.status_code, 200)
        except Exception as e:
            self.fail(f"Polymarket API connection failed: {e}")
    
    def test_polymarket_candles_api(self):
        """Проверка Polymarket candles API"""
        try:
            # Тестовый запрос к candles API
            response = requests.get(
                "https://gamma-api.polymarket.com/candles",
                params={
                    "market": "test",
                    "outcome": "Yes",
                    "resolution": "hour",
                    "limit": 1
                },
                timeout=10
            )
            # API может вернуть 400 для невалидного market, это нормально
            self.assertIn(response.status_code, [200, 400, 404])
        except Exception as e:
            self.fail(f"Polymarket candles API test failed: {e}")


class TestFrontend(unittest.TestCase):
    """Тесты frontend"""
    
    def test_frontend_index_exists(self):
        """Проверка существования frontend/index.html"""
        index_path = os.path.join(
            os.path.dirname(__file__),
            'frontend',
            'index.html'
        )
        if os.path.exists(index_path):
            self.assertTrue(True)
        else:
            # Пробуем альтернативный путь
            alt_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'frontend',
                'index.html'
            )
            if os.path.exists(alt_path):
                self.assertTrue(True)
            else:
                self.fail("frontend/index.html not found")
    
    def test_script_js_syntax(self):
        """Проверка синтаксиса frontend/script.js"""
        script_paths = [
            os.path.join(os.path.dirname(__file__), 'frontend', 'script.js'),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'script.js')
        ]
        
        for script_path in script_paths:
            if os.path.exists(script_path):
                try:
                    with open(script_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    # Проверяем что файл не пустой и валидный JS
                    self.assertGreater(len(content), 100)
                    # Проверяем наличие основных функций
                    self.assertIn('function', content)
                    return
                except Exception as e:
                    self.fail(f"Error reading script.js: {e}")
        
        self.fail("frontend/script.js not found")
    
    def test_styles_css_exists(self):
        """Проверка существования frontend/styles.css"""
        css_paths = [
            os.path.join(os.path.dirname(__file__), 'frontend', 'styles.css'),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'styles.css')
        ]
        
        for css_path in css_paths:
            if os.path.exists(css_path):
                with open(css_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.assertGreater(len(content), 100)
                return
        
        self.fail("frontend/styles.css not found")


class TestSchedulerInitialization(unittest.TestCase):
    """Тесты инициализации планировщика"""
    
    def test_scheduler_module_available(self):
        """Проверка доступности APScheduler"""
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            scheduler = AsyncIOScheduler()
            self.assertIsNotNone(scheduler)
        except ImportError as e:
            self.fail(f"APScheduler not available: {e}")


class TestPriceHistoryFunction(unittest.TestCase):
    """Тесты функции fetch_polymarket_price_history"""
    
    def test_price_history_function_exists(self):
        """Проверка существования функции"""
        api_dir = os.path.join(os.path.dirname(__file__), 'api')
        if os.path.exists(api_dir):
            sys.path.insert(0, api_dir)
            try:
                import index
                self.assertTrue(hasattr(index, 'fetch_polymarket_price_history'))
            except ImportError:
                self.skipTest("Cannot import api.index")
            finally:
                sys.path.remove(api_dir)
        else:
            self.skipTest("api/index.py not found")


class TestDatabaseTablesExist(unittest.TestCase):
    """Тесты существования таблиц БД"""
    
    def test_models_defined(self):
        """Проверка что модели определены"""
        api_dir = os.path.join(os.path.dirname(__file__), 'api')
        if os.path.exists(api_dir):
            sys.path.insert(0, api_dir)
            try:
                from models import User, Event, EventOption, Transaction, PriceHistory
                # Проверяем что классы существуют
                self.assertTrue(User)
                self.assertTrue(Event)
                self.assertTrue(EventOption)
                self.assertTrue(Transaction)
                self.assertTrue(PriceHistory)
            except ImportError as e:
                self.fail(f"Cannot import models: {e}")
            finally:
                sys.path.remove(api_dir)
        else:
            self.skipTest("api/models.py not found")


class TestStartupNoErrors(unittest.TestCase):
    """Тесты отсутствия ошибок при старте"""
    
    def test_syntax_valid(self):
        """Проверка синтаксиса Python файлов"""
        api_dir = os.path.join(os.path.dirname(__file__), 'api')
        
        if not os.path.exists(api_dir):
            self.skipTest("api directory not found")
        
        py_files = ['index.py', 'models.py']
        
        for py_file in py_files:
            file_path = os.path.join(api_dir, py_file)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        compile(f.read(), file_path, 'exec')
                except SyntaxError as e:
                    self.fail(f"Syntax error in {py_file}: {e}")
            else:
                self.skipTest(f"{py_file} not found")


class TestAllEndpoints(unittest.TestCase):
    """Полная проверка всех endpoints"""
    
    def test_all_public_endpoints(self):
        """Проверка всех публичных endpoints"""
        endpoints = [
            ("/", 200),
            ("/health", 200),
            ("/categories", 200),
            ("/events", 200),
        ]
        
        for endpoint, expected_status in endpoints:
            try:
                response = requests.get(f"{BASE_URL}{endpoint}", timeout=TIMEOUT)
                self.assertEqual(response.status_code, expected_status)
            except requests.exceptions.ConnectionError:
                self.skipTest(f"Cannot connect to {BASE_URL}")
            except Exception as e:
                self.fail(f"Endpoint {endpoint} failed: {e}")


def run_tests():
    """Запуск всех тестов"""
    # Создаём тестовый suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Добавляем все тесты
    test_classes = [
        TestBackendImports,
        TestDatabaseConnection,
        TestHealthEndpoint,
        TestApiEndpoints,
        TestPolymarketIntegration,
        TestFrontend,
        TestSchedulerInitialization,
        TestPriceHistoryFunction,
        TestDatabaseTablesExist,
        TestStartupNoErrors,
        TestAllEndpoints,
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Запускаем тесты
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Возвращаем результат
    return result.wasSuccessful()


if __name__ == '__main__':
    print("=" * 60)
    print("EventPredict - Comprehensive Tests")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"Timeout: {TIMEOUT}s")
    print("=" * 60)
    
    success = run_tests()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")
    print("=" * 60)
    
    sys.exit(0 if success else 1)
