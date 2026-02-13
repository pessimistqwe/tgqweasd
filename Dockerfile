FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Only copy requirements first for better layer cache
COPY api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm -rf /root/.cache/pip

# Copy only what the app needs (smaller image, less ephemeral-storage)
COPY api /app/api
COPY frontend /app/frontend

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn index:app --host 0.0.0.0 --port ${PORT} --app-dir api"]
