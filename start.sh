#!/bin/bash
# Startup script for Zeabur

echo "Starting EventPredict API..."
echo "PORT=${PORT:-8000}"

# Set Python path
export PYTHONPATH=/app:/app/api

# Change to app directory
cd /app

# Run the application - use PORT from environment
exec python -m uvicorn api.index:app --host 0.0.0.0 --port ${PORT:-8000}
