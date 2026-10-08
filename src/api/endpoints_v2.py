"""V2 prediction endpoints with nullable fields and KNN imputation."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Body, HTTPException, Request

from api.schemas_v2 import (
    ERROR_RESPONSES,
    ErrorDetail,
    HealthResponse,
    HomeFeaturesV2,
    ImputeResponse,
    PredictionResponse,
)
from api.shared import Artifacts, fill_missing, listing_examples, predict_price, require_artifacts

router_v2 = APIRouter(tags=["v2"])

log = structlog.get_logger(__name__)


@router_v2.get("/health/v2", response_model=HealthResponse, responses={500: {"model": ErrorDetail}})
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
        # require_artifacts already answers 500 for this state; log before it propagates.
        log.warning("artifacts_unavailable", detail=str(exc.detail), status_code=exc.status_code)
        raise
    payload = home_features.model_dump()
    filled, _ = fill_missing(payload, artifacts)
    payload |= filled
    return PredictionResponse(**predict_price(payload, artifacts))


@router_v2.post(
    "/impute",
    response_model=ImputeResponse,
    responses=ERROR_RESPONSES,
)
def impute(
    home_features: Annotated[HomeFeaturesV2, Body(openapi_examples=listing_examples())],
    request: Request,
) -> ImputeResponse:
    """Fill null fields via KNN (k=5); output feeds v1 /predict as-is."""
    try:
        artifacts: Artifacts = require_artifacts(request)
    except HTTPException as exc:
        log.warning("artifacts_unavailable", detail=str(exc.detail), status_code=exc.status_code)
        raise

    request_payload = home_features.model_dump()
    filled, missing = fill_missing(request_payload, artifacts)

    return ImputeResponse(
        bedrooms=int(filled["bedrooms"]),
        bathrooms=filled["bathrooms"],
        sqft_living=filled["sqft_living"],
        sqft_lot=filled["sqft_lot"],
        floors=filled["floors"],
        sqft_above=filled["sqft_above"],
        sqft_basement=filled["sqft_basement"],
        zipcode=home_features.zipcode,
        imputed=missing,
    )
