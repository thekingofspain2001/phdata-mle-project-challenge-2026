"""API endpoints for home price prediction."""

import json
import logging
import pathlib
import pickle

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# ponytail: anchored to package file, CWD-independent; no symlinks needed
_SRC = pathlib.Path(__file__).resolve().parents[1]
MODEL_PATH = _SRC / "model" / "model.pkl"
FEATURES_PATH = _SRC / "model" / "model_features.json"
DEMOGRAPHICS_PATH = _SRC / "data" / "zipcode_demographics.csv"


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
def predict(home_features: HomeFeatures) -> dict[str, float]:
    """Predict a home sale price from listing and demographic features."""
    # Load the model and features
    with MODEL_PATH.open("rb") as model_file:
        model = pickle.load(model_file)

    with FEATURES_PATH.open() as features_file:
        model_features: list[str] = json.load(features_file)

    input_data: pd.DataFrame = pd.DataFrame([home_features.model_dump()])

    # Load demographic data
    demographics = pd.read_csv(DEMOGRAPHICS_PATH, dtype={"zipcode": str})
    demographic_info = (
        demographics[demographics["zipcode"] == home_features.zipcode]
        .drop(columns="zipcode")
        .reset_index(drop=True)
    )
    if demographic_info.empty:
        raise HTTPException(status_code=404, detail=f"Unknown zipcode: {home_features.zipcode}")

    # Combine input data with demographic data
    input_data = pd.concat([input_data, demographic_info], axis=1)
    logger.info("input_data: %s", input_data)

    # Ensure the input data has the correct features
    input_data = input_data[model_features]

    # Make prediction
    prediction = model.predict(input_data)

    return {"predicted_price": prediction[0]}
