"""Shared pytest fixtures for API tests."""

import os
from typing import TYPE_CHECKING

import httpx2
import pytest
from fastapi.testclient import TestClient

from src.main import app

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def test_client() -> Iterator[TestClient]:
    """Fixture for unit tests using FastAPI TestClient."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def api_base_url() -> str:
    """Fixture providing API base URL for integration tests."""
    return os.getenv("API_BASE_URL", "http://localhost:8000")


@pytest.fixture
def http_client(api_base_url: str) -> httpx2.Client:
    """Fixture for integration tests using httpx2."""
    return httpx2.Client(base_url=api_base_url, timeout=10.0)


@pytest.fixture
def sample_home_features() -> dict[str, int | float | str]:
    """Fixture providing sample input data for tests."""
    return {
        "bedrooms": 3,
        "bathrooms": 2.0,
        "sqft_living": 1500.0,
        "sqft_lot": 5000.0,
        "floors": 1.0,
        "sqft_above": 1200.0,
        "sqft_basement": 300.0,
        "zipcode": "98042",
    }
