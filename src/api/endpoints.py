"""API endpoints for home price prediction."""

import json
import logging
import pathlib
import pickle

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sklearn.impute import KNNImputer

logger = logging.getLogger(__name__)

router = APIRouter()

# ponytail: anchored to package file, CWD-independent; no symlinks needed
_SRC = pathlib.Path(__file__).resolve().parents[1]
MODEL_PATH = _SRC / "model" / "model.pkl"
FEATURES_PATH = _SRC / "model" / "model_features.json"
DEMOGRAPHICS_PATH = _SRC / "data" / "zipcode_demographics.csv"
SALES_PATH = _SRC / "data" / "kc_house_data.csv"
REQUEST_COLUMNS = [
    "bedrooms",
    "bathrooms",
    "sqft_living",
    "sqft_lot",
    "floors",
    "sqft_above",
    "sqft_basement",
]


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


@router.get("/health")
def health_check() -> dict[str, str]:
    """Check API readiness.

    Return 200 with a healthy status when ready to accept requests.
    """
    return {"status": "healthy"}


def _load_knn_imputer() -> tuple[KNNImputer, list[str]]:
    """Fit KNNImputer (k=5, distance) on training request columns."""
    sales = pd.read_csv(SALES_PATH, usecols=REQUEST_COLUMNS)
    imputer = KNNImputer(n_neighbors=5, weights="distance")
    imputer.fit(sales[REQUEST_COLUMNS])
    return imputer, REQUEST_COLUMNS


def _predict_price(payload: dict[str, int | float | str | None]) -> dict[str, float]:
    # Load the model and features
    with MODEL_PATH.open("rb") as model_file:
        model = pickle.load(model_file)

    with FEATURES_PATH.open() as features_file:
        model_features: list[str] = json.load(features_file)

    input_data: pd.DataFrame = pd.DataFrame([payload])

    # Load demographic data
    demographics = pd.read_csv(DEMOGRAPHICS_PATH, dtype={"zipcode": str})
    demographic_info = demographics[demographics["zipcode"] == payload["zipcode"]].drop(columns="zipcode").reset_index(drop=True)
    if demographic_info.empty:
        raise HTTPException(status_code=404, detail=f"Unknown zipcode: {payload['zipcode']}")

    # Combine input data with demographic data
    input_data = pd.concat([input_data, demographic_info], axis=1)
    logger.info("input_data: %s", input_data)

    # Ensure the input data has the correct features
    input_data = input_data[model_features]

    # Make prediction
    prediction = model.predict(input_data)

    return {"predicted_price": prediction[0]}


@router.post("/predict")
def predict(home_features: HomeFeatures) -> dict[str, float]:
    """Predict a home sale price from listing and demographic features."""
    return _predict_price(home_features.model_dump())


@router.post("/predict/v2")
def predict_v2(home_features: HomeFeaturesV2) -> dict[str, float]:
    """Predict a home sale price, imputing null fields via KNN (k=5)."""
    payload = home_features.model_dump()
    row = pd.DataFrame([{c: payload.get(c) for c in REQUEST_COLUMNS}])
    if row.isna().any().any():
        imputer, _ = _load_knn_imputer()
        row[REQUEST_COLUMNS] = imputer.transform(row[REQUEST_COLUMNS])
        payload |= {c: float(row.iloc[0][c]) for c in REQUEST_COLUMNS}
    return _predict_price(payload)
