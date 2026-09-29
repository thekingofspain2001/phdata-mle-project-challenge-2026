"""Integration tests for the API endpoints."""

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    import httpx2

HTTP_STATUS_OK = 200


@pytest.mark.integration
def test_predict_endpoint_integration(
    http_client: httpx2.Client,
    sample_home_features: dict[str, int | float | str],
) -> None:
    """Test the /predict endpoint via HTTP using httpx2 client."""
    response = http_client.post("/predict", json=sample_home_features)
    assert response.status_code == HTTP_STATUS_OK
    response_data = response.json()
    assert "predicted_price" in response_data
    assert isinstance(response_data["predicted_price"], float)
    assert response_data["predicted_price"] > 0


@pytest.mark.integration
def test_health_endpoint_integration(http_client: httpx2.Client) -> None:
    """Test the /health endpoint via HTTP using httpx2 client."""
    response = http_client.get("/health")
    assert response.status_code == HTTP_STATUS_OK
    response_data = response.json()
    assert "status" in response_data
    assert response_data["status"] == "healthy"
