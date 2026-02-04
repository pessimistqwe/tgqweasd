# api/app.py - ASGI entry point for Vercel
from main import app

# Vercel Python Runtime ищет 'app' переменную
# Не используем 'handler' - это для WSGI
