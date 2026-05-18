FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache --no-dev

COPY bot.py ./
COPY cogs ./cogs

CMD ["uv", "run", "python", "bot.py"]
