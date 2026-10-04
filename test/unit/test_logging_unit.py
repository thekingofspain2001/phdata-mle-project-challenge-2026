"""Contract tests for request-id echoing and unhandled-exception handling."""

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from api import endpoints_v2
from src.main import app

if TYPE_CHECKING:
    from collections.abc import Iterator

REQUEST_ID = "8f14e45f-ea0f-4b76-9c2a-1f3d5b7c9e01"
INTERNAL_SERVER_ERROR = 500
UUID_LENGTH = 36
UUID4_VERSION_INDEX = 14
BOOM_MESSAGE = "model exploded"


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Serve the app without re-raising server errors, the way uvicorn does."""
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def explode(_payload: dict[str, object], _artifacts: object) -> dict[str, float]:
    """Stand in for the prediction pipeline: always fails."""
    raise RuntimeError(BOOM_MESSAGE)


def test_inbound_request_id_is_echoed(client: TestClient) -> None:
    """A supplied X-Request-ID comes back on the response."""
    response = client.get("/health", headers={"X-Request-ID": REQUEST_ID})
    assert response.headers["x-request-id"] == REQUEST_ID


def test_missing_request_id_is_generated(client: TestClient) -> None:
    """Without the header, the server mints a UUIDv4 and returns it."""
    response = client.get("/health")
    generated = response.headers["x-request-id"]
    assert len(generated) == UUID_LENGTH
    assert generated[UUID4_VERSION_INDEX] == "4"


def test_unhandled_exception_returns_500_json_with_request_id(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An escaping exception logs the traceback and still answers JSON 500 plus the id."""
    monkeypatch.setattr(endpoints_v2, "predict_price", explode)
    response = client.post(
        "/predict/v2",
        json={"zipcode": "98042"},
        headers={"X-Request-ID": REQUEST_ID},
    )

    assert response.status_code == INTERNAL_SERVER_ERROR
    assert response.json() == {"detail": "Internal server error"}
    assert response.headers["x-request-id"] == REQUEST_ID
