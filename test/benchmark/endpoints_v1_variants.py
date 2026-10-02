"""Two variants of the v1 handler, each changing exactly one thing.

The benchmark times all three v1 shapes so each cost is priced by subtraction
rather than argued:

  /predict            real v1 in src/api/endpoints.py: reload per call, print present
  /predict-noprint    same body, debug print commented out -> v1 delta is the print cost
  /predict-cached     artifacts from lifespan, print still present -> v1 delta is the reload

Do not "improve" either variant. Any edit beyond the single documented
difference makes the delta meaningless.
"""

from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Body, Request
from pydantic import BaseModel

from api.shared import listing_examples, load_predict_artifacts, require_artifacts

router_variants = APIRouter(tags=["bench"])


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


@router_variants.post("/predict-noprint")
def predict_noprint(
    home_features: Annotated[HomeFeatures, Body(openapi_examples=listing_examples())],
) -> dict[str, float]:
    """v1 with the debug print commented out; still reloads artifacts per call."""
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
        # print(input_data)  # noqa: ERA001 - the one change from v1

        # Ensure the input data has the correct features
        input_data = input_data[artifacts.model_features]
        # Make prediction
        prediction = artifacts.model.predict(input_data)
        return {"predicted_price": prediction[0]}
    finally:
        del artifacts


@router_variants.post("/predict-cached")
def predict_cached(request: Request, home_features: HomeFeatures) -> dict[str, float]:
    """v1 with startup-cached artifacts; the debug print is still present."""
    artifacts = require_artifacts(request)
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
    print(input_data)  # noqa: T201 - intentional, mirrors src/api/endpoints.py:55

    # Ensure the input data has the correct features
    input_data = input_data[artifacts.model_features]
    # Make prediction
    prediction = artifacts.model.predict(input_data)
    return {"predicted_price": prediction[0]}
