"""Application lifespan: load prediction artifacts once before serving."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from api.artifacts import ArtifactLoadError, load_artifacts
from logger_config import setup_logging

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Configure JSON logging, then load prediction artifacts once."""
    setup_logging()
    try:
        app.state.artifacts = load_artifacts()
    except ArtifactLoadError:
        app.state.artifacts = None
    yield
    app.state.artifacts = None
