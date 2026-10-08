"""Neutral internal contracts for shared API prediction helpers."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PredictionInput:
    bedrooms: int
    bathrooms: float
    sqft_living: float
    sqft_lot: float
    floors: float
    sqft_above: float
    sqft_basement: float
    zipcode: str


@dataclass(frozen=True, slots=True)
class PredictionResult:
    predicted_price: float


@dataclass(frozen=True, slots=True)
class ImputationResult:
    features: PredictionInput
    missing_fields: list[str]
