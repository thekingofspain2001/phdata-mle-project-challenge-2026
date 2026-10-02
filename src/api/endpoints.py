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

from api.shared import listing_examples

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
    with open("model/model.pkl", "rb") as model_file:
        model = pickle.load(model_file)

    with open("model/model_features.json") as features_file:
        model_features = json.load(features_file)

    input_data = pd.DataFrame([home_features.dict()])

    # Load demographic data
    demographics = pd.read_csv("data/zipcode_demographics.csv", dtype={"zipcode": str})
    demographic_info = demographics[
        demographics["zipcode"] == home_features.zipcode
    ].drop(columns="zipcode").reset_index(drop=True)

    # Combine input data with demographic data
    input_data = pd.concat([input_data, demographic_info], axis=1)
    print(input_data)

    # Ensure the input data has the correct features
    input_data = input_data[model_features]

    # Make prediction
    prediction = model.predict(input_data)

    return {"predicted_price": prediction[0]}