"""HTTP request and response schemas for the v2 API."""

from pydantic import BaseModel, ConfigDict, Field

from api.constants import UNKNOWN_ZIP


class PredictionResponse(BaseModel):
    """Predicted home sale price."""

    predicted_price: float = Field(examples=[394708.0])


class ImputeResponse(BaseModel):
    """KNN-imputed request fields; valid input for v1 /predict."""

    bedrooms: float = Field(examples=[3])
    bathrooms: float = Field(examples=[2.25])
    sqft_living: float = Field(examples=[1840.0])
    sqft_lot: float = Field(examples=[11403.0])
    floors: float = Field(examples=[2.0])
    sqft_above: float = Field(examples=[1840.0])
    sqft_basement: float = Field(examples=[0.0])
    zipcode: str = Field(examples=["98045"])
    imputed: list[str] = Field(examples=[["sqft_living"]])


class HealthResponse(BaseModel):
    """Service health status."""

    status: str = Field(examples=["healthy"])


class ErrorDetail(BaseModel):
    """String-detail error body returned by v2 routes."""

    detail: str = Field(examples=[f"Unknown zipcode: {UNKNOWN_ZIP}"])


class HomeFeaturesV2(BaseModel):
    """Input features for home price prediction v2; non-zipcode fields nullable."""

    # Infinity and NaN pass plain float validation, then blow up inside
    # model.predict as an opaque 500. Rejecting them here turns that into a
    # 422 at the boundary. None is still allowed - that is what the imputer
    # is for.
    model_config = ConfigDict(allow_inf_nan=False)

    # Field-level examples were dropped: Swagger prints schema examples
    # verbatim (swagger-ui json-schema-2020-12 Examples.jsx) and they had
    # drifted from the request examples. Those now come from
    # openapi_examples, one per CSV row, via listing_examples(). Add
    # Field(examples=[...]) back per field if a schema-level sample is ever
    # wanted again.
    bedrooms: int | None = Field(default=None, ge=0)
    bathrooms: float | None = Field(default=None, ge=0)
    sqft_living: float | None = Field(default=None, ge=0)
    sqft_lot: float | None = Field(default=None, ge=0)
    floors: float | None = Field(default=None, ge=0)
    sqft_above: float | None = Field(default=None, ge=0)
    sqft_basement: float | None = Field(default=None, ge=0)
    zipcode: str = Field(pattern=r"^\d{5}$")


ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    404: {
        "model": ErrorDetail,
        "content": {
            "application/json": {
                "examples": {
                    "unknown_zipcode": {
                        "summary": "Zipcode has no demographics",
                        "description": ("The zipcode is five digits but has no rows in zipcode_demographics.csv, so there is nothing to join."),
                        "value": {"detail": f"Unknown zipcode: {UNKNOWN_ZIP}"},
                    },
                },
            },
        },
    },
    500: {
        "model": ErrorDetail,
        "content": {
            "application/json": {
                "examples": {
                    "artifacts_unavailable": {
                        "summary": "Startup artifacts never loaded",
                        "description": (
                            "Lifespan could not load the model, features, demographics "
                            "or imputer, so nothing can be predicted until the process "
                            "restarts and /health/v2 reports healthy."
                        ),
                        "value": {
                            "detail": "Prediction service unavailable - the office lights are still off.",
                        },
                    },
                },
            },
        },
    },
}
