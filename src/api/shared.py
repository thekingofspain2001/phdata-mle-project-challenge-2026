"""Shared prediction artifacts, paths, and pipeline helpers."""

from __future__ import annotations

import csv
import hashlib
import json
import pickle
from typing import TYPE_CHECKING, Protocol, cast, runtime_checkable

import pandas as pd
import structlog
from fastapi import HTTPException, Request
from fastapi.openapi.models import Example
from pydantic import BaseModel
from sklearn.impute import KNNImputer

from api.constants import REQUEST_COLUMNS, UNKNOWN_ZIP
from paths import DEMOGRAPHICS_PATH, FEATURES_PATH, MODEL_PATH, SALES_PATH, UNSEEN_PATH

if TYPE_CHECKING:
    import pathlib
    from collections.abc import Iterator, Mapping

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


def _unseen_rows() -> Iterator[Mapping[str, str]]:
    """Yield one mapping per row of the unseen-listings dataset."""
    if not UNSEEN_PATH.is_file():
        msg = f"Unseen listings file not found: {UNSEEN_PATH}"
        raise FileNotFoundError(msg)
    with UNSEEN_PATH.open(newline="", encoding="utf-8") as handle:
        yield from csv.DictReader(handle)


def _listing_line(row: Mapping[str, str]) -> str:
    """Terse listing line: bed, bath, living sq ft, floors, zipcode, waterfront."""
    line = (
        f"{int(row['bedrooms'])} bed, {float(row['bathrooms']):g} bath, {float(row['sqft_living']):,.0f} sq ft, {float(row['floors']):g} fl, {row['zipcode']}"
    )
    if float(row["waterfront"]) != 0:
        line += ", waterfront"
    return line


def _listing_value(row: Mapping[str, str]) -> dict[str, float | int | str]:
    """Complete request payload for one row."""
    return {
        "bedrooms": int(row["bedrooms"]),
        "bathrooms": float(row["bathrooms"]),
        "sqft_living": float(row["sqft_living"]),
        "sqft_lot": float(row["sqft_lot"]),
        "floors": float(row["floors"]),
        "sqft_above": float(row["sqft_above"]),
        "sqft_basement": float(row["sqft_basement"]),
        "zipcode": row["zipcode"],
    }


def listing_examples() -> dict[str, Example]:
    """Two named examples per row of the unseen-listings dataset.

    The complete listing, plus one with a single input field left out. The
    omitted field rotates through all eight request parameters, so the set
    covers every one of them — including zipcode, whose examples fail
    validation rather than being imputed.
    """
    droppable = [*REQUEST_COLUMNS, "zipcode"]
    rows = list(_unseen_rows())
    first = rows[0]
    unknown_line = _listing_line(first).replace(first["zipcode"], UNKNOWN_ZIP)
    examples: dict[str, Example] = {
        "example_0_unknown_zip": Example(
            summary=f"Example 0 - Unknown Zip - {unknown_line}, not in the demographics table",
            value=_listing_value(first) | {"zipcode": UNKNOWN_ZIP},
        ),
    }
    for index, row in enumerate(rows, start=1):
        line = _listing_line(row)
        value = _listing_value(row)
        examples[f"example_{index}_all"] = Example(
            summary=f"Example {index} - All - {line}",
            value=value,
        )
        missing = droppable[(index - 1) % len(droppable)]
        examples[f"example_{index}_no_{missing}"] = Example(
            summary=f"Example {index} - No {missing} - {line}",
            value={key: item for key, item in value.items() if key != missing},
        )
    return examples


class PredictArtifacts(BaseModel):
    """What /predict loads per request: model, ordered features, demographics."""

    model_config = {"arbitrary_types_allowed": True}

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


def fill_missing(payload: dict[str, int | float | str | None], artifacts: Artifacts) -> tuple[dict[str, float], list[str]]:
    """Fill null request fields via the fitted KNN imputer; return values + filled names."""
    missing = [c for c in REQUEST_COLUMNS if payload.get(c) is None]
    row = pd.DataFrame([{c: payload.get(c) for c in REQUEST_COLUMNS}])
    if row.isna().any().any():
        logger.info("imputing_null_features")
        filled = pd.DataFrame(
            artifacts.imputer.transform(row[REQUEST_COLUMNS]),
            columns=REQUEST_COLUMNS,
        )
        row[REQUEST_COLUMNS] = filled
    return {c: float(row.iloc[0][c]) for c in REQUEST_COLUMNS}, missing


def predict_price(payload: dict[str, int | float | str | None], artifacts: Artifacts) -> dict[str, float]:
    """Run the shared load/join/predict pipeline over a raw feature payload."""
    model = artifacts.model
    model_features = artifacts.model_features
    demographics = artifacts.demographics
    input_data: pd.DataFrame = pd.DataFrame([payload])

    demographic_info = demographics[demographics["zipcode"] == payload["zipcode"]].drop(columns="zipcode").reset_index(drop=True)
    if demographic_info.empty:
        logger.warning("unknown_zipcode", zipcode=payload["zipcode"])
        raise HTTPException(status_code=404, detail=f"Unknown zipcode: {payload['zipcode']}")

    # Combine input data with demographic data
    input_data = pd.concat([input_data, demographic_info], axis=1)
    logger.debug("joined_features", columns=len(input_data.columns))

    # Ensure the input data has the correct features
    input_data = input_data[model_features]
    # Make prediction
    prediction = model.predict(input_data)
    logger.info("prediction_complete", predicted_price=float(prediction[0]))

    return {"predicted_price": float(prediction[0])}
