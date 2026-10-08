"""API endpoints for home price prediction.

Restored to the first-commit shape (e9ef514) on purpose: untyped, original
imports, artifacts loaded from disk on every request. The one thing kept from
the later work is the OpenAPI request examples, so /docs still shows sample
bodies. File is excluded from lint in ruff.toml for the same reason.
"""

from typing import Annotated

from fastapi import APIRouter, Body
from pydantic import BaseModel

from api.shared import (
    PredictArtifacts,
    listi' no
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
async def health_check():
    """
    Health check endpoint for container orchestration.
    Returns 200 if API is ready to accept requests.
    """
    return {"status": "healthy"}


@router.post("/predict")
async def predict(home_features: Annotated[HomeFeatures, Body(openapi_examples=listing_examples())]):
    # Load the model and features
    with MODEL_PATH.open("rb") as model_file:
        model = pickle.load(model_file)

    with FEATURES_PATH.open() as features_file:
        model_features: list[str] = json.load(features_file)

    # Load demographic data
    demographics = load_demographics()
    artifacts = PredictArtifacts(
        model=model,
        model_features=model_features,
        demographics=demographics,
    )
    features = PredictionInput(
        bedrooms=home_features.bedrooms,
        bathrooms=home_features.bathrooms,
        sqft_living=home_features.sqft_living,
        sqft_lot=home_features.sqft_lot,
        floors=home_features.floors,
        sqft_above=home_features.sqft_above,
        sqft_basement=home_features.sqft_basement,
        zipcode=home_features.zipcode,
    )
    result = predict_price(features, artifacts)

    return {"predicted_price": result.predicted_price}
