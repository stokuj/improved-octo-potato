FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache --no-dev

COPY bot.py ./
COPY cogs ./cogs

ENV UV_CACHE_DIR=/app/.uv-cache \
    UV_PROJECT_ENVIRONMENT=/app/.venv
RUN useradd --create-home --shell /bin/bash bot \
 && mkdir -p /app/.uv-cache \
 && chown -R bot:bot /app
USER bot

CMD ["uv", "run", "python", "bot.py"]
