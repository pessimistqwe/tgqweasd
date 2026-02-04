"""
Vercel serverless function handler
Этот файл обрабатывает все API запросы на Vercel
"""

from fastapi import Request
from main import app
import json

# Vercel serverless handler
async def handler(request: Request):
    """
    Обработчик для Vercel Serverless Functions
    """
    try:
        # Получаем путь из запроса
        path = request.url.path
        
        # Убираем /api/ префикс если есть
        if path.startswith('/api'):
            path = path[4:]
        
        # Создаём новый запрос для FastAPI
        scope = request.scope.copy()
        scope['path'] = path
        
        # Вызываем FastAPI app
        from fastapi.responses import JSONResponse
        
        return await app(scope, request.receive, request.send)
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": str(e)}
        )

# Экспортируем для Vercel
app = app  # FastAPI app будет использоваться напрямую
