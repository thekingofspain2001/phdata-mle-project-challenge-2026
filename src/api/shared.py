"""Shared home-price prediction pipeline helpers."""

from __future__ import annotations

import csv
from typing import TYPE_CHECKING

import pandas as pd
import structlog
from fastapi import HTTPException
from fastapi.openapi.models import Example

from api.constants import REQUEST_COLUMNS, UNKNOWN_ZIP
from api.types import ImputationResult, PredictionInput, PredictionResult
from paths import UNSEEN_PATH

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from api.artifacts import Artifacts, PredictArtifacts
    from api.schemas_v2 import HomeFeaturesV2

logger = structlog.get_logger(__name__)


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


def impute_home_features(home_features: HomeFeaturesV2, artifacts: Artifacts) -> ImputationResult:
    """Fill null request fields via the fitted KNN imputer; return values + filled names."""
    request_values = {
        "bedrooms": home_features.bedrooms,
        "bathrooms": home_features.bathrooms,
        "sqft_living": home_features.sqft_living,
        "sqft_lot": home_features.sqft_lot,
        "floors": home_features.floors,
        "sqft_above": home_features.sqft_above,
        "sqft_basement": home_features.sqft_basement,
    }
    missing = [c for c in REQUEST_COLUMNS if request_values[c] is None]
    request_row = pd.DataFrame([request_values], columns=REQUEST_COLUMNS)

    if request_row.isna().any().any():
        logger.info("imputing_null_features")
        imputed_values = pd.DataFrame(
            artifacts.imputer.transform(request_row[REQUEST_COLUMNS]),
            columns=REQUEST_COLUMNS,
        )
        request_row[REQUEST_COLUMNS] = imputed_values

    numeric_values = {c: float(request_row.iloc[0][c]) for c in REQUEST_COLUMNS}

    return ImputationResult(
        features=PredictionInput(
            bedrooms=numeric_values["bedrooms"],
            bathrooms=numeric_values["bathrooms"],
            sqft_living=numeric_values["sqft_living"],
            sqft_lot=numeric_values["sqft_lot"],
            floors=numeric_values["floors"],
            sqft_above=numeric_values["sqft_above"],
            sqft_basement=numeric_values["sqft_basement"],
            zipcode=home_features.zipcode,
        ),
        missing_fields=missing,
    )


def predict_price(features: PredictionInput, artifacts: PredictArtifacts) -> PredictionResult:
    """Run the shared load/join/predict pipeline over typed prediction features."""
    model = artifacts.model
    model_features = artifacts.model_features
    demographics = artifacts.demographics

    request_frame: pd.DataFrame = pd.DataFrame(
        [
            {
                "bedrooms": features.bedrooms,
                "bathrooms": features.bathrooms,
                "sqft_living": features.sqft_living,
                "sqft_lot": features.sqft_lot,
                "floors": features.floors,
                "sqft_above": features.sqft_above,
                "sqft_basement": features.sqft_basement,
                "zipcode": features.zipcode,
            },
        ],
    )

    matching_demographics = demographics[demographics["zipcode"] == features.zipcode].drop(columns="zipcode").reset_index(drop=True)

    if matching_demographics.empty:
        logger.warning("unknown_zipcode", zipcode=features.zipcode)
        raise HTTPException(status_code=404, detail=f"Unknown zipcode: {features.zipcode}")

    # Combine input data with demographic data
    request_frame = pd.concat([request_frame, matching_demographics], axis=1)
    logger.debug("joined_features", columns=len(request_frame.columns))

    # Ensure the input data has the correct features
    request_frame = request_frame[model_features]
    # Make prediction
    prediction = model.predict(request_frame)
    logger.info("prediction_complete", predicted_price=float(prediction[0]))

    return PredictionResult(predicted_price=float(prediction[0]))
