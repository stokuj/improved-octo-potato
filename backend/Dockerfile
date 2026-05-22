FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache --no-dev

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

# Pin uv cache/venv into /app so non-root user can write to them.
ENV UV_CACHE_DIR=/app/.uv-cache \
    UV_PROJECT_ENVIRONMENT=/app/.venv
RUN useradd --create-home --shell /bin/bash app \
 && mkdir -p /app/.uv-cache \
 && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"]
