ARG PYTHON_VERSION=3.14
FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-trixie-slim AS builder

WORKDIR /app

ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock .python-version ./
COPY src/data ./data

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

ARG PYTHON_VERSION=3.14
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY src/model/create_model.py ./
COPY src/paths.py ./
COPY src/data ./data

ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "create_model.py"]
