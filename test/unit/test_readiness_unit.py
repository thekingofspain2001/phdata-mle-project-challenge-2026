"""Readiness tests for lifespan artifact failures across health and predict."""

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from api.shared import ArtifactLoadError
from src.main import app

if TYPE_CHECKING:
    from collections.abc import Iterator

HTTP_STATUS_OK = 200
HTTP_STATUS_INTERNAL_ERROR = 500
HTTP_STATUS_UNAVAILABLE = 503

# Contract: lifespan must populate app.state under these exact keys.
LIFESPAN_ARTIFACTS = ["model", "model_features", "demographics", "imputer"]
HEALTH_V2_ENDPOINT = "/health/v2"


@pytest.fixture
def unloaded_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Serve the app with lifespan artifact loading forced to fail."""

    def fail_load() -> object:
        message = "lifespan load failed in test"
        raise ArtifactLoadError(message)

    monkeypatch.setattr("api.lifespan.load_artifacts", fail_load)
    with TestClient(app) as client:
        yield client


@pytest.fixture
def loaded_client() -> Iterator[TestClient]:
    """Serve the app with lifespan artifact loading succeeding."""
    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize("artifact", LIFESPAN_ARTIFACTS)
def test_health_v2_unavailable_when_artifact_missing(
    unloaded_client: TestClient,
    artifact: str,
) -> None:
    """V2 health reports unavailable when any lifespan artifact failed to load."""
    _ = artifact
    response = unloaded_client.get(HEALTH_V2_ENDPOINT)
    assert response.status_code == HTTP_STATUS_UNAVAILABLE


def test_predict_v1_ok_when_lifespan_unloaded(
    unloaded_client: TestClient,
    sample_home_features: dict[str, int | float | str],
) -> None:
    """/predict v1 self-loads per request and ignores lifespan state."""
    response = unloaded_client.post("/predict", json=sample_home_features)
    assert response.status_code == HTTP_STATUS_OK


def test_predict_v2_500_when_lifespan_unloaded(
    unloaded_client: TestClient,
    sample_home_features: dict[str, int | float | str],
) -> None:
    """/predict v2 fails when lifespan artifacts never loaded."""
    response = unloaded_client.post("/predict/v2", json=sample_home_features)
    assert response.status_code == HTTP_STATUS_INTERNAL_ERROR


def test_predict_v2_ok_when_imputer_not_needed(
    loaded_client: TestClient,
    sample_home_features: dict[str, int | float | str],
) -> None:
    """/predict v2 with a complete payload does not need the KNN imputer artifact."""
    response = loaded_client.post("/predict/v2", json=sample_home_features)
    assert response.status_code == HTTP_STATUS_OK
