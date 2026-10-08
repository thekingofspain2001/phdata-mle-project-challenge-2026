"""v1 variants for cost attribution, all derived from the first commit e9ef514.

The baseline body below is src/api/endpoints.py as of e9ef514: async def, model
and features reloaded from disk per call, demographics re-read per call, one
print of the joined frame. Each endpoint changes exactly one thing so every
cost is a subtraction rather than an argument:

  /predict-original   the baseline, async def
  /predict-sync       plain def instead of async  -> the async cost
  /predict-cached     async + startup-cached artifacts -> the per-call reload cost
  /predict-noprint    async + print removed       -> the print cost

Only /predict-sync is not async. Every other endpoint keeps the baseline's
async def, so each subtraction against /predict-original isolates one change.

Two forced deviations from e9ef514, both because the original cannot run here:
  * paths come from api.shared (the original used bare "model/model.pkl"
    relative to CWD, so it only ran from src/); the loading mechanism is
    unchanged - pickle per call, csv per call
  * .model_dump() instead of .dict(); pydantic 2 deprecation warnings would
    otherwise be emitted on every timed request
"""

import json
import pickle
from typing import cast

import pandas as pd
from fastapi import APIRouter, Request
from pydantic import BaseModel

from api.artifacts import Predictor, require_artifacts
from paths import DEMOGRAPHICS_PATH, FEATURES_PATH, MODEL_PATH

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


def _reload_from_disk() -> tuple[Predictor, list[str], pd.DataFrame]:
    """Reproduce the e9ef514 per-call load: unpickle the model, read both data files."""
    with MODEL_PATH.open("rb") as model_file:
        model = cast("Predictor", pickle.load(model_file))  # noqa: S301 - trusted artifact, mirrors e9ef514
    with FEATURES_PATH.open() as features_file:
        model_features = json.load(features_file)
    demographics = pd.read_csv(DEMOGRAPHICS_PATH, dtype={"zipcode": str})
    return model, model_features, demographics


def _join(model_features: list[str], demographics: pd.DataFrame, features: HomeFeatures) -> pd.DataFrame:
    """Concatenate the listing with its zipcode demographics row."""
    input_data = pd.DataFrame([features.model_dump()])
    demographic_info = demographics[demographics["zipcode"] == features.zipcode].drop(columns="zipcode").reset_index(drop=True)
    return pd.concat([input_data, demographic_info], axis=1)[model_features]


@router_variants.post("/predict-original")
async def predict_original(home_features: HomeFeatures) -> dict[str, float]:
    """Baseline: async handler, reloads everything per call, prints the frame."""
    model, model_features, demographics = _reload_from_disk()
    input_data = _join(model_features, demographics, home_features)
    print(input_data)  # noqa: T201 - mirrors e9ef514 src/api/endpoints.py:44
    prediction = model.predict(input_data)
    return {"predicted_price": prediction[0]}


@router_variants.post("/predict-sync")
def predict_sync(home_features: HomeFeatures) -> dict[str, float]:
    """Baseline with one change: plain def, so FastAPI runs it in the threadpool."""
    model, model_features, demographics = _reload_from_disk()
    input_data = _join(model_features, demographics, home_features)
    print(input_data)  # noqa: T201 - unchanged from the baseline
    prediction = model.predict(input_data)
    return {"predicted_price": prediction[0]}


@router_variants.post("/predict-cached")
async def predict_cached(request: Request, home_features: HomeFeatures) -> dict[str, float]:
    """Baseline with one change: artifacts come from lifespan, not from disk."""
    artifacts = require_artifacts(request)
    input_data = _join(artifacts.model_features, artifacts.demographics, home_features)
    print(input_data)  # noqa: T201 - unchanged from the baseline
    prediction = artifacts.model.predict(input_data)
    return {"predicted_price": prediction[0]}


@router_variants.post("/predict-noprint")
async def predict_noprint(home_features: HomeFeatures) -> dict[str, float]:
    """Baseline with one change: the debug print is commented out."""
    model, model_features, demographics = _reload_from_disk()
    input_data = _join(model_features, demographics, home_features)
    # print(input_data)  # noqa: ERA001 - the single difference from the baseline
    prediction = model.predict(input_data)
    return {"predicted_price": prediction[0]}
