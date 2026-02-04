# api/index.py - Entry point for Vercel
import os
import sys

api_dir = os.path.dirname(os.path.abspath(__file__))
if api_dir not in sys.path:
    sys.path.insert(0, api_dir)

# Создаём таблицы ПЕРЕД импортом app
from models import Base, engine
try:
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")
except Exception as e:
    print(f"Error creating tables: {e}")

from main import app

# Vercel handler
handler = app
