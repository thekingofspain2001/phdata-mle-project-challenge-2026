"""Neutral internal contracts for shared API prediction helpers."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PredictionInput:
    """Input features for a house price prediction request.

    Attributes
    ----------
    bedrooms : float
        Number of bedrooms.
    bathrooms : float
        Number of bathrooms.
    sqft_living : float
        Living area in square feet.
    sqft_lot : float
        Lot area in square feet.
    floors : float
        Number of floors.
    sqft_above : float
        Above-ground area in square feet.
    sqft_basement : float
        Basement area in square feet.
    zipcode : str
        Property zipcode.
    """

    bedrooms: float
    bathrooms: float
    sqft_living: float
    sqft_lot: float
    floors: float
    sqft_above: float
    sqft_basement: float
    zipcode: str


@dataclass(frozen=True, slots=True)
class PredictionResult:
    """Result of a house price prediction request.

    Attributes
    ----------
    predicted_price : float
        Predicted house price.
    """

    predicted_price: float


@dataclass(frozen=True, slots=True)
class ImputationResult:
    """Result of imputing missing fields in a prediction request.

    Attributes
    ----------
    features : PredictionInput
        Input features with missing values imputed.
    missing_fields : list[str]
        Names of fields that were missing and imputed.
    """

    features: PredictionInput
    missing_fields: list[str]
