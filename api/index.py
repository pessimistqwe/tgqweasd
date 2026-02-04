# api/index.py - ASGI entry point for Vercel
import os
import sys

# Добавляем папку api в путь
api_dir = os.path.dirname(os.path.abspath(__file__))
if api_dir not in sys.path:
    sys.path.insert(0, api_dir)

# Импортируем FastAPI app
from main import app

# Экспортируем ASGI приложение
# Vercel Python Runtime использует 'app' для ASGI
