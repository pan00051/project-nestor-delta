FROM python:3.10.14-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

COPY requirements-web.txt ./
RUN pip install --no-cache-dir -r requirements-web.txt

COPY . ./
RUN chmod +x scripts/start-railway-service.sh

CMD ["./scripts/start-railway-service.sh"]
