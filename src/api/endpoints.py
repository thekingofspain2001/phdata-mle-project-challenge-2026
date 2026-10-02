"""API endpoints for home price prediction."""

from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Body
from pydantic import BaseModel

from api.shared import listing_examples, load_predict_artifacts

router = APIRouter(tags=["default"])


class HomeFeatures(BaseModel):
    """Input features for home price prediction."""

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
    """Check API readiness.

    Return 200 with a healthy status when ready to accept requests.
    """
    return {"status": "healthy"}


@router.post("/predict")
async def predict(
    home_features: Annotated[HomeFeatures, Body(openapi_examples=listing_examples())],
) -> dict[str, float]:
    """Predict a home sale price from listing and demographic features."""
    artifacts = load_predict_artifacts()
    try:
        demographics = artifacts.demographics
        input_data: pd.DataFrame = pd.DataFrame([home_features.model_dump()])

        # Combine input data with demographic data
        demographic_info = (
            demographics[demographics["zipcode"] == home_features.zipcode]
            .drop(
                columns="zipcode",
            )
            .reset_index(drop=True)
        )
        input_data = pd.concat([input_data, demographic_info], axis=1)
        print(input_data)

        # Ensure the input data has the correct features
        input_data = input_data[artifacts.model_features]
        # Make prediction
        prediction = artifacts.model.predict(input_data)
        return {"predicted_price": prediction[0]}
    finally:
        del artifacts
