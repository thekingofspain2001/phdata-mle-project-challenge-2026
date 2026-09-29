"""Shared prediction artifacts, paths, and pipeline helpers."""

from __future__ import annotations

import json
import logging
import pathlib
import pickle
from typing import TYPE_CHECKING, Protocol, cast, runtime_checkable

import pandas as pd
from fastapi import HTTPException, Request
from pydantic import BaseModel
from sklearn.impute import KNNImputer

if TYPE_CHECKING:
    import numpy as np
    import numpy.typing as npt

logger = logging.getLogger(__name__)


@runtime_checkable
class Predictor(Protocol):
    """Any regressor exposing sklearn-style predict over a DataFrame."""

    def predict(self, features: pd.DataFrame) -> npt.NDArray[np.float64]:
        """Predict targets for the given feature frame."""
        ...


@runtime_checkable
class ImputerProtocol(Protocol):
    """KNN-style imputer with fit/transform over DataFrames."""

    def fit(self, features: pd.DataFrame) -> ImputerProtocol:
        """Fit the imputer on the given feature frame."""
        ...

    def transform(self, features: pd.DataFrame) -> npt.NDArray[np.float64]:
        """Fill missing values in the given feature frame."""
        ...


# ponytail: anchored to package file, CWD-independent; no symlinks needed
_SRC = pathlib.Path(__file__).resolve().parents[1]
MODEL_PATH = _SRC / "model" / "model.pkl"
FEATURES_PATH = _SRC / "model" / "model_features.json"
DEMOGRAPHICS_PATH = _SRC / "data" / "zipcode_demographics.csv"
SALES_PATH = _SRC / "data" / "kc_house_data.csv"
REQUEST_COLUMNS = [
    "bedrooms",
    "bathrooms",
    "sqft_living",
    "sqft_lot",
    "floors",
    "sqft_above",
    "sqft_basement",
]
ARTIFACT_MODEL = "model"
ARTIFACT_MODEL_FEATURES = "model_features"
ARTIFACT_DEMOGRAPHICS = "demographics"
ARTIFACT_IMPUTER = "imputer"


class Artifacts(BaseModel):
    """Prediction artifacts loaded once at startup; trusted build outputs."""

    model_config = {"arbitrary_types_allowed": True}

    model: Predictor
    model_features: list[str]
    demographics: pd.DataFrame
    imputer: ImputerProtocol


class ArtifactLoadError(RuntimeError):
    """Raised when a startup artifact fails to load; message carries the artifact name."""


def load_model() -> Predictor:
    """Load the trained regressor from its trusted build artifact."""
    try:
        with MODEL_PATH.open("rb") as model_file:
            return cast("Predictor", pickle.load(model_file))  # trusted build artifact from create_model.py
    except Exception as exc:
        logger.exception("Failed to load model artifact.")
        raise ArtifactLoadError(ARTIFACT_MODEL) from exc


def load_model_features() -> list[str]:
    """Load the ordered model feature list."""
    try:
        with FEATURES_PATH.open() as features_file:
            model_features: list[str] = json.load(features_file)
            return model_features
    except Exception as exc:
        logger.exception("Failed to load model features artifact.")
        raise ArtifactLoadError(ARTIFACT_MODEL_FEATURES) from exc


def load_demographics() -> pd.DataFrame:
    """Load the zipcode demographics table."""
    try:
        return pd.read_csv(DEMOGRAPHICS_PATH, dtype={"zipcode": str})
    except Exception as exc:
        logger.exception("Failed to load demographics artifact.")
        raise ArtifactLoadError(ARTIFACT_DEMOGRAPHICS) from exc


def load_imputer() -> ImputerProtocol:
    """Fit the KNN imputer (k=5, distance) on training request columns."""
    try:
        sales = pd.read_csv(SALES_PATH, usecols=REQUEST_COLUMNS)
        return cast(
            "ImputerProtocol",
            KNNImputer(n_neighbors=5, weights="distance").fit(sales[REQUEST_COLUMNS]),  # type: ignore[reportUnknownMemberType]
        )
    except Exception as exc:
        logger.exception("Failed to load imputer artifact.")
        raise ArtifactLoadError(ARTIFACT_IMPUTER) from exc


def load_artifacts() -> Artifacts:
    """Load model, features, demographics, and fitted KNN imputer."""
    return Artifacts(
        model=load_model(),
        model_features=load_model_features(),
        demographics=load_demographics(),
        imputer=load_imputer(),
    )


def require_artifacts(request: Request) -> Artifacts:
    """Return lifespan artifacts or raise 503 when startup loading failed."""
    artifacts = getattr(request.app.state, "artifacts", None)
    if artifacts is None:
        detail = "Prediction service unavailable"
        raise HTTPException(status_code=503, detail=detail)
    return artifacts


def predict_price(payload: dict[str, int | float | str | None], artifacts: Artifacts) -> dict[str, float]:
    """Run the shared load/join/predict pipeline over a raw feature payload."""
    model = artifacts.model
    model_features = artifacts.model_features
    demographics = artifacts.demographics

    input_data: pd.DataFrame = pd.DataFrame([payload])

    demographic_info = demographics[demographics["zipcode"] == payload["zipcode"]].drop(columns="zipcode").reset_index(drop=True)
    if demographic_info.empty:
        raise HTTPException(status_code=404, detail=f"Unknown zipcode: {payload['zipcode']}")

    # Combine input data with demographic data
    input_data = pd.concat([input_data, demographic_info], axis=1)
    logger.info("input_data: %s", input_data)

    # Ensure the input data has the correct features
    input_data = input_data[model_features]
    # Make prediction
    prediction = model.predict(input_data)

    return {"predicted_price": float(prediction[0])}
