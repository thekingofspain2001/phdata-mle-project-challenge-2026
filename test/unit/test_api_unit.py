"""Unit tests for the API endpoints."""

from fastapi.testclient import TestClient

HTTP_STATUS_OK = 200


def test_health_endpoint(test_client: TestClient) -> None:
    """Test the /health endpoint returns correct status."""
    response = test_client.get("/health")
    assert response.status_code == HTTP_STATUS_OK
    response_data = response.json()
    assert "status" in response_data
    assert response_data["status"] == "healthy"


def test_predict_endpoint_valid_input(
    test_client: TestClient,
    sample_home_features: dict[str, int | float | str],
) -> None:
    """Test the /predict endpoint with valid input."""
    response = test_client.post("/predict", json=sample_home_features)
    assert response.status_code == HTTP_STATUS_OK
    response_data = response.json()
    assert "predicted_price" in response_data
    assert isinstance(response_data["predicted_price"], float)
