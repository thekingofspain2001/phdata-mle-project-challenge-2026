"""V2 prediction endpoints with nullable fields and KNN imputation."""

from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Body, HTTPException, Request
from pydantic import BaseModel, Field

from api.shared import REQUEST_COLUMNS, UNKNOWN_ZIP, Artifacts, listing_examples, predict_price, require_artifacts

router_v2 = APIRouter(tags=["v2"])


class PredictionResponse(BaseModel):
    """Predicted home sale price."""

    predicted_price: float = Field(examples=[394708.0])


class HealthResponse(BaseModel):
    """Service health status."""

    status: str = Field(examples=["healthy"])


class ErrorDetail(BaseModel):
    """String-detail error body returned by v2 routes."""

    detail: str = Field(examples=[f"Unknown zipcode: {UNKNOWN_ZIP}"])


class HomeFeaturesV2(BaseModel):
    """Input features for home price prediction v2; non-zipcode fields nullable."""

    # Field-level examples were dropped: Swagger prints schema examples
    # verbatim (swagger-ui json-schema-2020-12 Examples.jsx) and they had
    # drifted from the request examples. Those now come from
    # openapi_examples, one per CSV row, via listing_examples(). Add
    # Field(examples=[...]) back per field if a schema-level sample is ever
    # wanted again.
    bedrooms: int | None = Field(default=None, ge=0)
    bathrooms: float | None = Field(default=None, ge=0)
    sqft_living: float | None = Field(default=None, ge=0)
    sqft_lot: float | None = Field(default=None, ge=0)
    floors: float | None = Field(default=None, ge=0)
    sqft_above: float | None = Field(default=None, ge=0)
    sqft_basement: float | None = Field(default=None, ge=0)
    zipcode: str = Field(pattern=r"^\d{5}$")


ERROR_RESPONSES = {
    404: {
        "model": ErrorDetail,
        "content": {
            "application/json": {
                "examples": {
                    "unknown_zipcode": {
                        "summary": "Zipcode has no demographics",
                        "description": ("The zipcode is five digits but has no rows in zipcode_demographics.csv, so there is nothing to join."),
                        "value": {"detail": f"Unknown zipcode: {UNKNOWN_ZIP}"},
                    },
                },
            },
        },
    },
    500: {
        "model": ErrorDetail,
        "content": {
            "application/json": {
                "examples": {
                    "artifacts_unavailable": {
                        "summary": "Startup artifacts never loaded",
                        "description": (
                            "Lifespan could not load the model, features, demographics "
                            "or imputer, so nothing can be predicted until the process "
                            "restarts and /health/v2 reports healthy."
                        ),
                        "value": {
                            "detail": "Prediction service unavailable - the office lights are still off.",
                        },
                    },
                },
            },
        },
    },
}


@router_v2.get("/health/v2", response_model=HealthResponse, responses={503: {"model": ErrorDetail}})
def health_check_v2(request: Request) -> HealthResponse:
    """Check v2 API readiness (lifespan artifacts incl. imputer)."""
    require_artifacts(request)
    return HealthResponse(status="healthy")


@router_v2.post(
    "/predict/v2",
    response_model=PredictionResponse,
    responses=ERROR_RESPONSES,
)
def predict_v2(
    home_features: Annotated[HomeFeaturesV2, Body(openapi_examples=listing_examples())],
    request: Request,
) -> PredictionResponse:
    """Predict a home sale price, imputing null fields via KNN (k=5)."""
    try:
        artifacts: Artifacts = require_artifacts(request)
    except HTTPException as exc:
        detail = str(exc.detail) if exc.detail else "Prediction service unavailable"
        raise HTTPException(status_code=500, detail=detail) from exc
    payload = home_features.model_dump()
    row = pd.DataFrame([{c: payload.get(c) for c in REQUEST_COLUMNS}])
    if row.isna().any().any():
        filled = pd.DataFrame(
            artifacts.imputer.transform(row[REQUEST_COLUMNS]),
            columns=REQUEST_COLUMNS,
        )
        row[REQUEST_COLUMNS] = filled
        payload |= {c: float(row.iloc[0][c]) for c in REQUEST_COLUMNS}
    return PredictionResponse(**predict_price(payload, artifacts))
