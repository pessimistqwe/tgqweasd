# Dockerfile for Zeabur deployment
FROM python:3.12-alpine

WORKDIR /app

# Install system dependencies
RUN apk add --no-cache gcc musl-dev libffi-dev

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    TEST_DB_PATH=/tmp/events.db \
    DATABASE_URL="" \
    PYTHONPATH=/app:/app/api

# Create /tmp directory for SQLite database
RUN mkdir -p /tmp && chmod 777 /tmp

# Copy requirements and install dependencies
COPY api/requirements-minimal.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy application code
COPY api/ /app/api/
COPY frontend/ /app/frontend/

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8000/health || exit 1

# Start the application using api.index
CMD ["uvicorn", "api.index:app", "--host", "0.0.0.0", "--port", "8000"]
