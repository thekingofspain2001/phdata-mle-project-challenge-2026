"""API endpoints for home price prediction."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.shared import load_artifacts, predict_price

router = APIRouter(tags=["default"])


class HomeFeatures(BaseModel):
    """Input features for home price prediction."""

    bedrooms: int = Field(examples=[3])
    bathrooms: float = Field(examples=[1.0])
    sqft_living: float = Field(examples=[1600.0])
    sqft_lot: float = Field(examples=[5001.0])
    floors: float = Field(examples=[1.5])
    sqft_above: float = Field(examples=[1080.0])
    sqft_basement: float = Field(examples=[520.0])
    zipcode: str = Field(examples=["98125"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """Check API readiness.

    Return 200 with a healthy status when ready to accept requests.
    """
    return {"status": "healthy"}


@router.post("/predict")
def predict(home_features: HomeFeatures) -> dict[str, float]:
    """Predict a home sale price from listing and demographic features."""
    artifacts = load_artifacts()
    try:
        return predict_price(home_features.model_dump(), artifacts)
    finally:
        del artifacts
