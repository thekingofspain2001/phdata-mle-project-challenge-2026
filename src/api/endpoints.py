"""API endpoints for home price prediction.

Restored to the first-commit shape (e9ef514) on purpose: untyped, original
imports, artifacts loaded from disk on every request. The one thing kept from
the later work is the OpenAPI request examples, so /docs still shows sample
bodies. File is excluded from lint in ruff.toml for the same reason.
"""

from typing import Annotated

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

import json
import pickle

import pandas as pd

from api.shared import DEMOGRAPHICS_PATH, FEATURES_PATH, MODEL_PATH, listing_examples

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

    input_data: pd.DataFrame = pd.DataFrame([home_features.model_dump()])

    # Load demographic data
    demographics = pd.read_csv(DEMOGRAPHICS_PATH, dtype={"zipcode": str})
    demographic_info = demographics[
        demographics["zipcode"] == home_features.zipcode
    ].drop(columns="zipcode").reset_index(drop=True)

    # A zipcode with no demographics row joins to nothing; without this guard the
    # model is handed NaN features and fails with an opaque 500.
    if demographic_info.empty:
        raise HTTPException(status_code=404, detail=f"Unknown zipcode: {home_features.zipcode}")

    # Combine input data with demographic data
    input_data = pd.concat([input_data, demographic_info], axis=1)

    # Ensure the input data has the correct features
    selected: pd.DataFrame = input_data[model_features]

    # Make prediction
    prediction = model.predict(selected)

    return {"predicted_price": prediction[0]}