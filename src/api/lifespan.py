"""Application lifespan: load prediction artifacts once before serving."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from api.shared import ArtifactLoadError, load_artifacts

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Load prediction artifacts once before serving requests."""
    try:
        app.state.artifacts = load_artifacts()
    except ArtifactLoadError:
        app.state.artifacts = None
    yield
    app.state.artifacts = None
