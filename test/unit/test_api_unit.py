"""Unit tests for the API endpoints."""

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from api import endpoints
from api.types import PredictionInput, PredictionResult

if TYPE_CHECKING:
    from collections.abc import Mapping

    from api.artifacts import PredictArtifacts

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


def test_predict_endpoint_uses_shared_prediction_path(
    test_client: TestClient,
    sample_home_features: dict[str, int | float | str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pass v1's typed features and locally loaded artifacts to shared prediction."""
    received: list[tuple[PredictionInput, PredictArtifacts]] = []

    def predict_price(features: PredictionInput, artifacts: PredictArtifacts) -> PredictionResult:
        received.append((features, artifacts))
        return PredictionResult(predicted_price=123.0)

    monkeypatch.setattr(endpoints, "predict_price", predict_price)

    response = test_client.post("/predict", json=sample_home_features)

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"predicted_price": 123.0}
    assert len(received) == 1
    features, artifacts = received[0]
    assert features.bedrooms == sample_home_features["bedrooms"]
    assert features.bathrooms == sample_home_features["bathrooms"]
    assert features.sqft_living == sample_home_features["sqft_living"]
    assert features.sqft_lot == sample_home_features["sqft_lot"]
    assert features.floors == sample_home_features["floors"]
    assert features.sqft_above == sample_home_features["sqft_above"]
    assert features.sqft_basement == sample_home_features["sqft_basement"]
    assert features.zipcode == sample_home_features["zipcode"]
    assert artifacts.model is not None
    assert artifacts.model_features
    assert "98042" in artifacts.demographics["zipcode"].values


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


def test_predict_v2_endpoint_omitted_field_returns_only_prediction(
    test_client: TestClient,
    sample_home_features: FeaturePayload,
) -> None:
    """Test an omitted feature is imputed without changing the response shape."""
    del sample_home_features["sqft_living"]
    response = test_client.post("/predict/v2", json=sample_home_features)
    assert response.status_code == HTTP_STATUS_OK
    assert set(response.json()) == {"predicted_price"}


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


def test_impute_complete_input_returns_same_features_and_no_missing_fields(
    test_client: TestClient,
    sample_home_features: dict[str, int | float | str],
) -> None:
    response = test_client.post("/impute", json=sample_home_features)
    assert response.status_code == HTTP_STATUS_OK
    assert response.json()["zipcode"] == sample_home_features["zipcode"]
    assert response.json()["bedrooms"] == sample_home_features["bedrooms"]
    assert response.json()["imputed"] == []


def test_impute_null_field_returns_value_and_names_it(
    test_client: TestClient,
    sample_home_features: dict[str, int | float | str],
) -> None:
    payload = sample_home_features | {"sqft_living": None}
    response = test_client.post("/impute", json=payload)
    assert response.status_code == HTTP_STATUS_OK
    assert isinstance(response.json()["sqft_living"], float)
    assert response.json()["imputed"] == ["sqft_living"]


def test_impute_omitted_field_names_it(
    test_client: TestClient,
    sample_home_features: dict[str, int | float | str],
) -> None:
    payload = sample_home_features.copy()
    del payload["sqft_living"]
    response = test_client.post("/impute", json=payload)
    assert response.status_code == HTTP_STATUS_OK
    assert response.json()["imputed"] == ["sqft_living"]
