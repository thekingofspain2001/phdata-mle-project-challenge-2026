"""Unit tests for the shared prediction and imputation helpers."""

import numpy as np
import numpy.typing as npt
import pandas as pd
import pytest
from fastapi import HTTPException

from api.artifacts import Artifacts, PredictArtifacts
from api.schemas_v2 import HomeFeaturesV2
from api.shared import impute_home_features, predict_price
from api.types import ImputationResult, PredictionInput, PredictionResult


class RecordingPredictor:
    def __init__(self) -> None:
        self.received: pd.DataFrame | None = None

    def predict(self, features: pd.DataFrame) -> npt.NDArray[np.float64]:
        self.received = features.copy()
        return np.array([123.0])


class FixedImputer:
    """Test double imputer that returns a fixed feature row."""

    def fit(self, _features: pd.DataFrame) -> FixedImputer:
        return self

    def transform(self, _features: pd.DataFrame) -> npt.NDArray[np.float64]:
        return np.array([[3.8, 2.5, 1500.0, 5000.0, 1.0, 1200.0, 300.0]])


def prediction_input(zipcode: str = "98042") -> PredictionInput:
    return PredictionInput(
        bedrooms=3,
        bathrooms=1.0,
        sqft_living=1.0,
        sqft_lot=1.0,
        floors=1.0,
        sqft_above=1.0,
        sqft_basement=1.0,
        zipcode=zipcode,
    )


def predict_artifacts(model: RecordingPredictor) -> PredictArtifacts:
    return PredictArtifacts(
        model=model,
        model_features=["bedrooms"],
        demographics=pd.DataFrame({"zipcode": ["98042"], "median_income": [1.0]}),
    )


def test_predict_price_returns_typed_result_and_sends_selected_features() -> None:
    model = RecordingPredictor()

    result = predict_price(prediction_input(), predict_artifacts(model))

    assert result == PredictionResult(predicted_price=123.0)
    assert model.received is not None
    assert model.received.iloc[0]["bedrooms"] == 3


def test_predict_price_returns_not_found_for_unknown_zipcode() -> None:
    with pytest.raises(HTTPException) as exc_info:
        predict_price(prediction_input("00000"), predict_artifacts(RecordingPredictor()))

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Unknown zipcode: 00000"


def test_impute_home_features_returns_typed_result_and_preserves_bedrooms() -> None:
    artifacts = Artifacts(
        model=RecordingPredictor(),
        model_features=["bedrooms"],
        demographics=pd.DataFrame({"zipcode": ["98042"], "median_income": [1.0]}),
        imputer=FixedImputer(),
    )

    result = impute_home_features(
        HomeFeaturesV2(
            zipcode="98042",
            bedrooms=3,
            bathrooms=1.0,
            sqft_living=None,
            sqft_lot=1.0,
            floors=1.0,
            sqft_above=1.0,
            sqft_basement=1.0,
        ),
        artifacts,
    )

    assert isinstance(result, ImputationResult)
    assert isinstance(result.features, PredictionInput)
    assert result.missing_fields == ["sqft_living"]
    assert result.features.bedrooms == 3.8
