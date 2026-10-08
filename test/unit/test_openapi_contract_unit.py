"""OpenAPI contract tests: v2 response schemas must match actual bodies."""

from typing import Any, cast

from fastapi.testclient import TestClient

HTTP_STATUS_OK = 200


def _v2_spec(test_client: TestClient) -> dict[str, Any]:
    response = test_client.get("/openapi.json")
    assert response.status_code == HTTP_STATUS_OK
    spec = cast("dict[str, Any]", response.json())
    assert isinstance(spec, dict)
    return spec


def test_predict_v2_openapi_documents_prediction_response(test_client: TestClient) -> None:
    """The /predict/v2 200 schema names a predicted_price number field."""
    spec = _v2_spec(test_client)
    paths: dict[str, Any] = spec["paths"]
    post: dict[str, Any] = paths["/predict/v2"]["post"]
    ok_schema: dict[str, Any] = post["responses"]["200"]["content"]["application/json"]["schema"]
    ref: str = ok_schema.get("$ref", "")
    assert ref.endswith("PredictionResponse")
    schemas: dict[str, Any] = spec["components"]["schemas"]
    price_prop: dict[str, Any] = schemas["PredictionResponse"]["properties"]["predicted_price"]
    assert price_prop["type"] == "number"


def test_predict_v2_openapi_documents_error_responses(test_client: TestClient) -> None:
    """The /predict/v2 spec documents the 404 and 500 string-detail errors."""
    spec = _v2_spec(test_client)
    paths: dict[str, Any] = spec["paths"]
    responses: dict[str, Any] = paths["/predict/v2"]["post"]["responses"]
    assert "404" in responses
    assert "500" in responses
    schemas: dict[str, Any] = spec["components"]["schemas"]
    assert "ErrorDetail" in schemas


def test_health_v2_openapi_documents_unavailable(test_client: TestClient) -> None:
    """The /health/v2 spec documents the 500 string-detail error."""
    spec = _v2_spec(test_client)
    paths: dict[str, Any] = spec["paths"]
    responses: dict[str, Any] = paths["/health/v2"]["get"]["responses"]
    assert "500" in responses


def test_v2_openapi_documents_request_and_imputation_contract(test_client: TestClient) -> None:
    """V2 schemas retain nullable inputs and the complete imputation response."""
    spec = _v2_spec(test_client)
    paths: dict[str, Any] = spec["paths"]
    schemas: dict[str, Any] = spec["components"]["schemas"]
    v2_request: dict[str, Any] = schemas["HomeFeaturesV2"]

    assert v2_request["properties"]["zipcode"]["pattern"] == r"^\d{5}$"
    assert set(v2_request["required"]) == {"zipcode"}
    bedroom_types = {
        option["type"]
        for option in v2_request["properties"]["bedrooms"]["anyOf"]
    }
    assert bedroom_types == {"integer", "null"}
    impute: dict[str, Any] = paths["/impute"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert impute["$ref"].endswith("ImputeResponse")
    assert {"404", "500"} <= set(paths["/impute"]["post"]["responses"])
    assert set(schemas["ImputeResponse"]["properties"]) == {
        "bedrooms", "bathrooms", "sqft_living", "sqft_lot", "floors",
        "sqft_above", "sqft_basement", "zipcode", "imputed",
    }
