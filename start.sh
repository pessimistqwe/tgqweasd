#!/bin/bash
# Startup script for Zeabur

echo "========================================"
echo "Starting EventPredict API..."
echo "PORT: ${PORT:-8000}"
echo "PYTHONPATH: ${PYTHONPATH:-/app:/app/api}"
echo "TEST_DB_PATH: ${TEST_DB_PATH:-/tmp/events.db}"
echo "========================================"

# Set Python path
export PYTHONPATH=/app:/app/api

# Change to app directory
cd /app

# Run the application
echo "Running: python -m uvicorn api.index:app --host 0.0.0.0 --port ${PORT:-8000}"
exec python -m uvicorn api.index:app --host 0.0.0.0 --port ${PORT:-8000}
