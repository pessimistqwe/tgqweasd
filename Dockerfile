# Multi-stage build для минимального размера образа
FROM python:3.12-alpine AS builder

WORKDIR /build

# Устанавливаем только build-зависимости
RUN apk add --no-cache gcc musl-dev libffi-dev

# Копируем и устанавливаем зависимости
COPY api/requirements-minimal.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --user -r /tmp/requirements.txt

# Финальный образ - только runtime
FROM python:3.12-alpine

WORKDIR /app

# Копируем установленные пакеты из builder
COPY --from=builder /root/.local /root/.local

# Убеждаемся что локальные пакеты в PATH
ENV PATH=/root/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Копируем только нужные файлы
COPY api /app/api
COPY frontend /app/frontend

EXPOSE 8000

CMD ["uvicorn", "index:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "api"]
