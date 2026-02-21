# Dockerfile for Zeabur deployment
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    TEST_DB_PATH=/tmp/events.db \
    PYTHONPATH=/app:/app/api

# Create /tmp directory for SQLite database
RUN mkdir -p /tmp && chmod 777 /tmp

# Copy and install requirements
COPY api/requirements-minimal.txt .
RUN pip install --no-cache-dir -r requirements-minimal.txt

# Copy application code
COPY api ./api
COPY frontend ./frontend
COPY start.sh ./start.sh

# Make start script executable
RUN chmod +x /app/start.sh

EXPOSE 8000

# Start the application
CMD ["/app/start.sh"]
