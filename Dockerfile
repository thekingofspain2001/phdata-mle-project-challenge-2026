ARG PYTHON_VERSION=3.14
FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-trixie-slim AS builder

WORKDIR /app

ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock .python-version ./
COPY src ./src

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

ARG PYTHON_VERSION=3.14
FROM python:${PYTHON_VERSION}-slim
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/.venv /app/.venv
COPY src ./src

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# python -m main (not the uvicorn CLI) so the supervisor process also loads
# logger_config; workers default to CPU count, override with WEB_CONCURRENCY.
CMD ["python", "-m", "main"]
