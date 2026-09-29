"""Unit tests for the API endpoints."""

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from collections.abc import Mapping

HTTP_STATUS_OK = 200
HTTP_STATUS_NOT_FOUND = 404

NULLABLE_FIELDS = [
    "bedrooms",
    "bathrooms",
    "sqft_living",
    "sqft_lot",
    "floors",
    "sqft_above",
    "sqft_basement",
]

type FeaturePayload = dict[str, int | float | str | None]


def assert_predict_v2_ok(test_client: TestClient, payload: Mapping[str, int | float | str | None]) -> None:
    """Post payload to /predict/v2 and assert a valid prediction returns."""
    response = test_client.post("/predict/v2", json=payload)
    assert response.status_code == HTTP_STATUS_OK
    response_data = response.json()
    assert "predicted_price" in response_data
    assert isinstance(response_data["predicted_price"], float)


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


def test_predict_endpoint_unknown_zipcode_returns_not_found(
    test_client: TestClient,
    sample_home_features: dict[str, int | float | str],
) -> None:
    """Test the /predict endpoint returns 404 for a zipcode with no demographics."""
    sample_home_features["zipcode"] = "00000"
    response = test_client.post("/predict", json=sample_home_features)
    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_predict_v2_endpoint_valid_input(
    test_client: TestClient,
    sample_home_features: dict[str, int | float | str],
) -> None:
    """Test the /predict/v2 endpoint with valid input."""
    assert_predict_v2_ok(test_client, sample_home_features)


def test_predict_v2_endpoint_unknown_zipcode_returns_not_found(
    test_client: TestClient,
    sample_home_features: dict[str, int | float | str],
) -> None:
    """Test the /predict/v2 endpoint returns 404 for a zipcode with no demographics."""
    sample_home_features["zipcode"] = "00000"
    response = test_client.post("/predict/v2", json=sample_home_features)
    assert response.status_code == HTTP_STATUS_NOT_FOUND
    assert "00000" in response.json().get("detail", "")


@pytest.mark.parametrize("field", NULLABLE_FIELDS)
def test_predict_v2_endpoint_omitted_field_returns_ok(
    test_client: TestClient,
    sample_home_features: FeaturePayload,
    field: str,
) -> None:
    """Test the /predict/v2 endpoint imputes a non-zipcode field when not included."""
    del sample_home_features[field]
    assert_predict_v2_ok(test_client, sample_home_features)


@pytest.mark.parametrize("field", NULLABLE_FIELDS)
def test_predict_v2_endpoint_null_field_returns_ok(
    test_client: TestClient,
    sample_home_features: FeaturePayload,
    field: str,
) -> None:
    """Test the /predict/v2 endpoint imputes a non-zipcode field when null."""
    sample_home_features[field] = None
    assert_predict_v2_ok(test_client, sample_home_features)


@pytest.mark.parametrize("field", NULLABLE_FIELDS)
def test_predict_v2_endpoint_zero_value_returns_ok(
    test_client: TestClient,
    sample_home_features: FeaturePayload,
    field: str,
) -> None:
    """Test the /predict/v2 endpoint passes a zero value through as real data."""
    sample_home_features[field] = 0
    assert_predict_v2_ok(test_client, sample_home_features)
