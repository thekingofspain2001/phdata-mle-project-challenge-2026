"""V2 prediction endpoints with nullable fields and KNN imputation."""

import pandas as pd
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from api.shared import REQUEST_COLUMNS, Artifacts, predict_price, require_artifacts

router_v2 = APIRouter(tags=["v2"])


class HomeFeaturesV2(BaseModel):
    """Input features for home price prediction v2; non-zipcode fields nullable."""

    bedrooms: int | None = Field(default=None, ge=0, examples=[3])
    bathrooms: float | None = Field(default=None, ge=0, examples=[1.0])
    sqft_living: float | None = Field(default=None, ge=0, examples=[1600.0])
    sqft_lot: float | None = Field(default=None, ge=0, examples=[5001.0])
    floors: float | None = Field(default=None, ge=0, examples=[1.5])
    sqft_above: float | None = Field(default=None, ge=0, examples=[1080.0])
    sqft_basement: float | None = Field(default=None, ge=0, examples=[520.0])
    zipcode: str = Field(pattern=r"^\d{5}$", examples=["98125"])


@router_v2.get("/health/v2")
def health_check_v2(request: Request) -> dict[str, str]:
    """Check v2 API readiness (lifespan artifacts incl. imputer)."""
    require_artifacts(request)
    return {"status": "healthy"}


@router_v2.post("/predict/v2")
def predict_v2(home_features: HomeFeaturesV2, request: Request) -> dict[str, float]:
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
    return predict_price(payload, artifacts)
