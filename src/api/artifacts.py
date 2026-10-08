"""Prediction artifact loading for startup and per-request use."""

from __future__ import annotations

import hashlib
import json
import pickle
from typing import TYPE_CHECKING, Protocol, cast, runtime_checkable

import pandas as pd
import structlog
from fastapi import HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sklearn.impute import KNNImputer

from api.constants import REQUEST_COLUMNS
from paths import DEMOGRAPHICS_PATH, FEATURES_PATH, MODEL_PATH, SALES_PATH

if TYPE_CHECKING:
    import pathlib

    import numpy as np
    import numpy.typing as npt

logger = structlog.get_logger(__name__)


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


ARTIFACT_MODEL = "model"
ARTIFACT_MODEL_FEATURES = "model_features"
ARTIFACT_DEMOGRAPHICS = "demographics"
ARTIFACT_IMPUTER = "imputer"


class PredictArtifacts(BaseModel):
    """What /predict loads per request: model, ordered features, demographics."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    model: Predictor
    model_features: list[str]
    demographics: pd.DataFrame


class Artifacts(PredictArtifacts):
    """Adds the fitted KNN imputer that /predict/v2 needs at startup."""

    imputer: ImputerProtocol


class ArtifactLoadError(RuntimeError):
    """Raised when a startup artifact fails to load; message carries the artifact name."""


def _digest(path: pathlib.Path) -> str:
    """Short content digest of an artifact, for identifying it in the logs."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def load_model() -> Predictor:
    """Load the trained regressor from its trusted build artifact."""
    try:
        with MODEL_PATH.open("rb") as model_file:
            model = cast("Predictor", pickle.load(model_file))  # noqa: S301 - trusted build artifact from create_model.py
    except Exception as exc:
        logger.exception("artifact_load_failed", artifact=ARTIFACT_MODEL)
        raise ArtifactLoadError(ARTIFACT_MODEL) from exc

    # Identify which model.pkl this process is serving. The artifact gets
    # retrained and re-committed, so a stale image layer and a fresh one are
    # otherwise indistinguishable in the logs.
    logger.info("artifact_loaded", artifact=ARTIFACT_MODEL, sha256=_digest(MODEL_PATH))

    return model


def _require_feature_list(raw: object) -> list[str]:
    """Return raw as a feature list, or raise if it is not one.

    json.load hands back Any, so without this the list[str] return type is an
    unchecked assertion and a corrupt file only fails inside predict_price,
    as an opaque 500 on the first request.
    """
    got = type(raw).__name__

    if not isinstance(raw, list):
        msg = f"{FEATURES_PATH.name} must be a non-empty list of strings, got {got}"
        raise TypeError(msg)
    features = cast("list[object]", raw)

    if not features:
        msg = f"{FEATURES_PATH.name} must be a non-empty list of strings, got empty list"
        raise TypeError(msg)

    if not all(isinstance(feature, str) for feature in features):
        msg = f"{FEATURES_PATH.name} must be a non-empty list of strings, got list of {type(features[0]).__name__}"
        raise TypeError(msg)

    return cast("list[str]", features)


def load_model_features() -> list[str]:
    """Load the ordered model feature list."""
    try:
        with FEATURES_PATH.open() as features_file:
            return _require_feature_list(json.load(features_file))

    except Exception as exc:
        logger.exception("artifact_load_failed", artifact=ARTIFACT_MODEL_FEATURES)
        raise ArtifactLoadError(ARTIFACT_MODEL_FEATURES) from exc


def load_demographics() -> pd.DataFrame:
    """Load the zipcode demographics table."""
    try:
        demographics = pd.read_csv(DEMOGRAPHICS_PATH, dtype={"zipcode": str})

    except Exception as exc:
        logger.exception("artifact_load_failed", artifact=ARTIFACT_DEMOGRAPHICS)
        raise ArtifactLoadError(ARTIFACT_DEMOGRAPHICS) from exc

    # The lookup is what decides both the 404 boundary and 26 of the 33 model
    # features, so a retrained model paired with a stale table is the case worth
    # being able to spot.
    logger.info("artifact_loaded", artifact=ARTIFACT_DEMOGRAPHICS, sha256=_digest(DEMOGRAPHICS_PATH), rows=len(demographics))

    return demographics


def load_imputer() -> ImputerProtocol:
    """Fit the KNN imputer (k=5, distance) on training request columns."""
    try:
        sales = pd.read_csv(SALES_PATH, usecols=REQUEST_COLUMNS)
        return cast(
            "ImputerProtocol",
            KNNImputer(n_neighbors=5, weights="distance").fit(sales[REQUEST_COLUMNS]),  # type: ignore[reportUnknownMemberType]
        )

    except Exception as exc:
        logger.exception("artifact_load_failed", artifact=ARTIFACT_IMPUTER)
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
    """Return lifespan artifacts or raise 500 when startup loading failed."""
    artifacts = getattr(request.app.state, "artifacts", None)

    if artifacts is None:
        detail = "Prediction service unavailable"
        raise HTTPException(status_code=500, detail=detail)

    return artifacts
