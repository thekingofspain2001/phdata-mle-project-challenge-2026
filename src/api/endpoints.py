"""Legacy v1 API endpoints for home price prediction."""

from typing import Annotated

from fastapi import APIRouter, Body
from pydantic import BaseModel

from api.artifacts import (
    PredictArtifacts,
    load_demographics,
    load_model,
    load_model_features,
)
from api.shared import listing_examples, predict_price
from api.types import PredictionInput

router = APIRouter()


class HomeFeatures(BaseModel):
    bedrooms: int
    bathrooms: float
    sqft_living: float
    sqft_lot: float
    floors: float
    sqft_above: float
    sqft_basement: float
    zipcode: str


@router.get("/health")
def health_check() -> dict[str, str]:
    """
    Health check endpoint for container orchestration.
    Returns 200 if API is ready to accept requests.
    """
    return {"status": "healthy"}


@router.post("/predict")
def predict(home_features: Annotated[HomeFeatures, Body(openapi_examples=listing_examples())]) -> dict[str, float]:
    loaded_model = load_model()
    loaded_model_features = load_model_features()
    demographics = load_demographics()

    artifacts = PredictArtifacts(
        model=loaded_model,
        model_features=loaded_model_features,
        demographics=demographics,
    )

    prediction_input = PredictionInput(
        bedrooms=home_features.bedrooms,
        bathrooms=home_features.bathrooms,
        sqft_living=home_features.sqft_living,
        sqft_lot=home_features.sqft_lot,
        floors=home_features.floors,
        sqft_above=home_features.sqft_above,
        sqft_basement=home_features.sqft_basement,
        zipcode=home_features.zipcode,
    )

    prediction_result = predict_price(prediction_input, artifacts)

    return {"predicted_price": prediction_result.predicted_price}
