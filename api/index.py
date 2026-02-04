# api/index.py - Entry point for Vercel
import os
import sys

# Добавляем папку api в путь
api_dir = os.path.dirname(os.path.abspath(__file__))
if api_dir not in sys.path:
    sys.path.insert(0, api_dir)

# Импортируем FastAPI app
from main import app

# Vercel ожидает переменную 'app' для Python Runtime
# Не используем 'handler' - это устаревший формат

# Для совместимости экспортируем и то и другое
handler = app
