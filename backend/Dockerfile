# One image runs both the API and the MCP server; docker-compose.yml picks the command.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first so code changes do not invalidate the cached install layer.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Run as an unprivileged user. Uploads and course documents live in volumes owned by it.
RUN useradd --create-home --uid 10001 app \
    && mkdir -p /app/uploads /app/data/kb \
    && chown -R app:app /app/uploads /app/data
USER app

EXPOSE 8000

# Apply migrations, then serve. The API is only reachable through the frontend's nginx proxy, which is why
# forwarded headers are trusted: they carry the real client address that rate limiting is keyed on.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
