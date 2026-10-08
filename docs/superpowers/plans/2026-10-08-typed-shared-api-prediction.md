# Typed Shared API Prediction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make prediction input/output and v2 imputation explicitly typed, and route both API versions through the same `predict_price` helper without changing their HTTP contracts.

**Architecture:** Add internal dataclass types for complete prediction input, prediction result, and imputation result. Extract v2 Pydantic schemas to a neutral schema module, make the shared prediction and imputation helpers consume/return these defined types, and adapt v1's existing request and artifact loading to the shared prediction helper.

**Tech Stack:** Python 3.14, FastAPI, Pydantic, pandas, scikit-learn, pytest, Pyright, Ruff.

**Spec:** `docs/superpowers/specs/2026-10-08-typed-shared-api-prediction-design.md`

## Global Constraints

- Keep the v1 endpoint intentionally minimally typed.
- Preserve both versions' existing HTTP and OpenAPI contracts.
- Do not add dependencies or broaden this work into a general API rewrite.
- Preserve the current integer conversion behavior for imputed `bedrooms`; changing its rounding/truncation semantics is out of scope.
- Keep artifact loading responsibilities and runtime behavior unchanged, except that v1 supplies its loaded prediction artifacts to the shared prediction function.

## Review Focus

- Fractional KNN output for `bedrooms`: preserve and explicitly test current integer conversion behavior in the imputation helper (Task 2).
- Omitted versus explicit-null v2 fields: both must be imputed and reported as missing (Task 3).
- Valid zero values: they must pass through rather than be treated as missing (Task 3).
- Unknown zipcode: shared inference must continue to return the same 404 detail in both API versions (Tasks 2 and 4).
- v1/v2 HTTP and OpenAPI compatibility: schemas, required/nullable fields, response properties, and documented errors must remain unchanged (Tasks 1, 3, and 4).

---

### Task 1: Extract v2 HTTP schemas and define internal API types

**Files:**

- Create: `src/api/constants.py`
- Create: `src/api/types.py`
- Create: `src/api/schemas_v2.py`
- Modify: `src/api/shared.py: REQUEST_COLUMNS and UNKNOWN_ZIP declarations`
- Modify: `src/api/endpoints_v2.py: schema declarations and imports`
- Test: `test/unit/test_openapi_contract_unit.py`

**Interfaces:**

- Produces `PredictionInput`, a frozen, slotted dataclass with fields `bedrooms: int`, `bathrooms: float`, `sqft_living: float`, `sqft_lot: float`, `floors: float`, `sqft_above: float`, `sqft_basement: float`, and `zipcode: str`.
- Produces `PredictionResult`, a frozen, slotted dataclass with `predicted_price: float`.
- Produces `ImputationResult`, a frozen, slotted dataclass with `features: PredictionInput` and `missing_fields: list[str]`.
- Produces `HomeFeaturesV2`, `PredictionResponse`, `ImputeResponse`, `HealthResponse`, `ErrorDetail`, and `ERROR_RESPONSES` in `api.schemas_v2`.
- `api.constants` owns `REQUEST_COLUMNS` and `UNKNOWN_ZIP`, avoiding schema/shared import cycles.

- [ ] **Step 1: Add OpenAPI compatibility assertions before moving models**

In `test/unit/test_openapi_contract_unit.py`, add assertions that:

```python
    schemas: dict[str, Any] = spec["components"]["schemas"]
    v2_request = schemas["HomeFeaturesV2"]
    assert v2_request["properties"]["zipcode"]["pattern"] == r"^\d{5}$"
    assert set(v2_request["required"]) == {"zipcode"}
    bedroom_types = {
        option["type"]
        for option in v2_request["properties"]["bedrooms"]["anyOf"]
    }
    assert bedroom_types == {"integer", "null"}
    impute = paths["/impute"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert impute["$ref"].endswith("ImputeResponse")
    assert {"404", "500"} <= set(paths["/impute"]["post"]["responses"])
    assert set(schemas["ImputeResponse"]["properties"]) == {
        "bedrooms", "bathrooms", "sqft_living", "sqft_lot", "floors",
        "sqft_above", "sqft_basement", "zipcode", "imputed",
    }
```

- [ ] **Step 2: Run the focused contract tests to verify the assertions match today's schema**

Run: `uv run --group test pytest test/unit/test_openapi_contract_unit.py -q -p no:cacheprovider --no-cov`
Expected: PASS before the extraction. If the present Pydantic schema uses an equivalent but different union representation, assert its actual stable shape instead of weakening the required/nullable check.

- [ ] **Step 3: Move shared constants and extract the v2 Pydantic models**

Create `src/api/constants.py` with `REQUEST_COLUMNS` and `UNKNOWN_ZIP` unchanged. Move all v2 request/response model declarations and `ERROR_RESPONSES` from `endpoints_v2.py` to `schemas_v2.py`; retain field declarations, constraints, examples, and error example content exactly. Update imports in `shared.py` and `endpoints_v2.py`. Do not move or alter the v1 `HomeFeatures` model.

- [ ] **Step 4: Add the internal dataclasses**

Create `src/api/types.py` with these declarations and imports:

```python
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
```

- [ ] **Step 5: Run schema contract tests and strict type checking**

Run: `uv run --group test pytest test/unit/test_openapi_contract_unit.py -q -p no:cacheprovider --no-cov`
Expected: PASS with the same schema component names and request/response field contract.

Run: `uv run --group test pyright`
Expected: PASS; schema relocation introduces no import cycle or new diagnostics.

- [ ] **Step 6: Commit the schema and type boundary**

```bash
git add src/api/constants.py src/api/types.py src/api/schemas_v2.py src/api/shared.py src/api/endpoints_v2.py test/unit/test_openapi_contract_unit.py
git commit -m "refactor(api): define typed shared prediction contracts"
```

### Task 2: Type the shared prediction and imputation helpers

**Files:**

- Modify: `src/api/shared.py: fill_missing and predict_price`
- Create: `test/unit/test_prediction_service_unit.py`

**Interfaces:**

- Consumes: `PredictionInput`, `PredictionResult`, `ImputationResult` from `api.types`; `HomeFeaturesV2` from `api.schemas_v2`.
- Produces: `fill_missing(home_features: HomeFeaturesV2, artifacts: Artifacts) -> ImputationResult`.
- Produces: `predict_price(features: PredictionInput, artifacts: PredictArtifacts) -> PredictionResult`.
- `predict_price` remains responsible for the DataFrame conversion, demographic join, feature selection, model invocation, and existing 404 behavior.

- [ ] **Step 1: Write shared-helper tests using small deterministic artifacts**

In `test/unit/test_prediction_service_unit.py`, import `numpy as np`, `numpy.typing as npt`, `pandas as pd`, `pytest`, `HTTPException`, `PredictArtifacts`, `Artifacts`, `HomeFeaturesV2`, both helpers, and the three dataclasses. Define deterministic doubles:

```python
class RecordingPredictor:
    def __init__(self) -> None:
        self.received: pd.DataFrame | None = None

    def predict(self, features: pd.DataFrame) -> npt.NDArray[np.float64]:
        self.received = features.copy()
        return np.array([123.0])


class FixedImputer:
    def fit(self, _features: pd.DataFrame) -> FixedImputer:
        return self

    def transform(self, _features: pd.DataFrame) -> npt.NDArray[np.float64]:
        return np.array([[3.8, 2.5, 1500.0, 5000.0, 1.0, 1200.0, 300.0]])
```

Add two prediction tests. In each, build `PredictArtifacts` with a fresh recorder, `model_features=["bedrooms"]`, and `pd.DataFrame({"zipcode": ["98042"], "median_income": [1.0]})`. Pass a `PredictionInput` with bedrooms `3`, every other numeric field `1.0`, and zipcode `"98042"` to the success case; assert the result equals `PredictionResult(predicted_price=123.0)` and the recorder received a row with bedrooms `3`. For the unknown-zipcode case, change only the zipcode to `"00000"` and assert `HTTPException` status 404 and detail `"Unknown zipcode: 00000"`.

For imputation, construct `Artifacts` with a `RecordingPredictor`, `model_features=["bedrooms"]`, the same demographics frame, and `FixedImputer()`. Pass `HomeFeaturesV2(zipcode="98042", bedrooms=3, bathrooms=2.0, sqft_living=None, sqft_lot=5000.0, floors=1.0, sqft_above=1200.0, sqft_basement=300.0)` to `fill_missing`, explicitly setting every non-target feature so only `sqft_living` is missing. Assert the result is an `ImputationResult`, `result.features` is a `PredictionInput`, `result.missing_fields == ["sqft_living"]`, and `result.features.bedrooms == 3` (the existing truncation behavior).

- [ ] **Step 2: Run the new tests to verify they expose current broad-dictionary signatures**

Run: `uv run --group test pytest test/unit/test_prediction_service_unit.py -q -p no:cacheprovider --no-cov`
Expected: FAIL because the helpers do not yet accept/return the defined model and result types.

- [ ] **Step 3: Implement the typed helper signatures and mappings**

Change `predict_price` to accept `PredictionInput`; construct the pandas row from its named fields, then keep the existing demographic lookup, feature selection, prediction logging, and 404 behavior. Return `PredictionResult(predicted_price=float(prediction[0]))`.

Change `fill_missing` to accept `HomeFeaturesV2` directly. Use its named nullable feature fields to build the ordered DataFrame, retain `REQUEST_COLUMNS` order and missing-field detection, run the fitted imputer only when null values exist, and return `ImputationResult(features=PredictionInput(...), missing_fields=missing)`. Convert the `bedrooms` imputed float using the current `int()` behavior; do not change rounding semantics in this task.

- [ ] **Step 4: Run helper tests and strict Pyright**

Run: `uv run --group test pytest test/unit/test_prediction_service_unit.py -q -p no:cacheprovider --no-cov`
Expected: PASS for a typed prediction result, existing unknown-zipcode behavior, and typed imputation result.

Run: `uv run --group test pyright`
Expected: The new service code is typed; remaining errors, if any, are expected call sites to be updated in Tasks 3 and 4. Update those call sites only when their task begins; do not suppress diagnostics.

- [ ] **Step 5: Commit the typed shared helpers**

```bash
git add src/api/shared.py test/unit/test_prediction_service_unit.py
git commit -m "refactor(api): type prediction and imputation helpers"
```

### Task 3: Route v2 through typed request, imputation, and prediction

**Files:**

- Modify: `src/api/endpoints_v2.py: predict_v2 and impute`
- Modify: `test/unit/test_api_unit.py`
- Modify: `test/unit/test_openapi_contract_unit.py`

**Interfaces:**

- Consumes: `HomeFeaturesV2`, response schemas from `api.schemas_v2`; `ImputationResult`; typed `fill_missing` and `predict_price`.
- Produces: v2 handlers pass `HomeFeaturesV2` directly to `fill_missing`, then pass `ImputationResult.features` to `predict_price`.
- HTTP response models, field names, validation, and documented errors remain unchanged.

- [ ] **Step 1: Add `/impute` route tests before changing route code**

Add tests to `test/unit/test_api_unit.py`, using the existing `test_client` and `sample_home_features` fixtures:

```python
def test_impute_complete_input_returns_same_features_and_no_missing_fields(
    test_client: TestClient,
    sample_home_features: dict[str, int | float | str],
) -> None:
    response = test_client.post("/impute", json=sample_home_features)
    assert response.status_code == 200
    assert response.json()["zipcode"] == sample_home_features["zipcode"]
    assert response.json()["bedrooms"] == sample_home_features["bedrooms"]
    assert response.json()["imputed"] == []


def test_impute_null_field_returns_value_and_names_it(
    test_client: TestClient,
    sample_home_features: dict[str, int | float | str],
) -> None:
    payload = sample_home_features | {"sqft_living": None}
    response = test_client.post("/impute", json=payload)
    assert response.status_code == 200
    assert isinstance(response.json()["sqft_living"], float)
    assert response.json()["imputed"] == ["sqft_living"]


def test_impute_omitted_field_names_it(
    test_client: TestClient,
    sample_home_features: dict[str, int | float | str],
) -> None:
    payload = sample_home_features.copy()
    del payload["sqft_living"]
    response = test_client.post("/impute", json=payload)
    assert response.status_code == 200
    assert response.json()["imputed"] == ["sqft_living"]
```

The direct fractional-imputation test in Task 2 pins existing `bedrooms` truncation. Add a `/predict/v2` test that confirms a missing feature is accepted and the response contains only the existing `predicted_price` property.

- [ ] **Step 2: Run the focused route tests to check their baseline**

Run: `uv run --group test pytest test/unit/test_api_unit.py -q -p no:cacheprovider --no-cov`
Expected: The existing v2 tests fail because the routes still pass dictionaries to the newly typed helper; this is the expected RED state before the route changes. Existing v1 tests remain passing.

- [ ] **Step 3: Replace dictionary conversion in the v2 routes**

In `predict_v2`, call `fill_missing(home_features, artifacts)` directly, pass `imputation.features` to `predict_price`, and construct `PredictionResponse(predicted_price=result.predicted_price)`.

In `impute`, call `fill_missing(home_features, artifacts)` directly and construct the existing `ImputeResponse` from `result.features` and `result.missing_fields`. Do not call `model_dump()` or unpack a generic dict in either v2 route.

- [ ] **Step 4: Run route, validation, and OpenAPI tests**

Run: `uv run --group test pytest test/unit/test_api_unit.py test/unit/test_openapi_contract_unit.py -q -p no:cacheprovider --no-cov`
Expected: PASS, including zero-valued feature tests, null/omitted-field prediction tests, `/impute` output shape, and unchanged OpenAPI contract.

- [ ] **Step 5: Run strict Pyright on the v2 path**

Run: `uv run --group test pyright`
Expected: V2 route and helper calls have no broad-payload type errors. Any remaining diagnostic should be confined to the not-yet-migrated v1 route and addressed in Task 4.

- [ ] **Step 6: Commit the typed v2 flow**

```bash
git add src/api/endpoints_v2.py test/unit/test_api_unit.py test/unit/test_openapi_contract_unit.py
git commit -m "refactor(api): use typed v2 prediction flow"
```

### Task 4: Adapt v1 to the shared typed prediction path

**Files:**

- Modify: `src/api/endpoints.py: predict`
- Modify: `test/unit/test_api_unit.py`
- Modify: `test/unit/test_logging_unit.py`

**Interfaces:**

- Consumes: existing untyped v1 route and `HomeFeatures`; `PredictionInput`, `PredictionResult`, and `PredictArtifacts`; existing artifact paths and loading behavior.
- Produces: v1 creates a `PredictionInput`, constructs `PredictArtifacts` from the artifacts it already loads, calls `predict_price`, and returns the existing `{"predicted_price": ...}` JSON shape.
- Keep v1's intentionally minimal endpoint typing; do not add a response model or otherwise redesign the v1 HTTP surface.

- [ ] **Step 1: Add a v1 shared-call assertion**

Add a route test that monkeypatches `api.endpoints.predict_price` with a spy accepting `(features, artifacts)` and returning `PredictionResult(predicted_price=123.0)`. Post a valid v1 request and assert a 200 response with exactly `{"predicted_price": 123.0}`; assert the spy received the submitted feature values, the correct zipcode, and loaded prediction artifacts.

- [ ] **Step 2: Run the focused v1 route test against the current endpoint**

Run: `uv run --group test pytest test/unit/test_api_unit.py -q -p no:cacheprovider --no-cov`
Expected: The new spy test FAILS because v1 currently performs prediction work directly instead of calling `predict_price`.

- [ ] **Step 3: Replace v1's inline join/predict with the shared call**

Keep v1's existing loading of model, model feature JSON, and demographics. Create `PredictArtifacts(model=model, model_features=model_features, demographics=demographics)`. Build `PredictionInput` from the validated `HomeFeatures` attributes, call `predict_price`, and return `{"predicted_price": result.predicted_price}`. Remove now-unused pandas and HTTPException imports, but do not add annotations to the route or alter its request model.

- [ ] **Step 4: Run both endpoint contract tests**

Run: `uv run --group test pytest test/unit/test_api_unit.py test/unit/test_openapi_contract_unit.py -q -p no:cacheprovider --no-cov`
Expected: PASS for valid v1/v2 prediction, unknown zipcode 404 in both versions, nullable/omitted v2 inputs, and unchanged OpenAPI request/response schemas.

- [ ] **Step 5: Run logging tests and the complete strict checks**

Run: `uv run --group test pytest test/unit/test_logging_unit.py -q -p no:cacheprovider --no-cov`
Expected: PASS; update the exception stub in this test to the new `PredictionInput` / `PredictArtifacts` / `PredictionResult` signature while preserving its 500 response assertions.

Run: `uv run --group test pyright`
Expected: PASS with strict typing enabled, including the shared call sites.

Run: `uvx ruff@0.16.10 check .`
Expected: PASS; v1 remains excluded under the existing Ruff configuration.

- [ ] **Step 6: Run all API unit tests**

Run: `uv run --group test pytest test/unit -q -p no:cacheprovider`
Expected: PASS with the repository's configured coverage threshold and all v1/v2 compatibility assertions.

- [ ] **Step 7: Commit the shared v1/v2 prediction path**

```bash
git add src/api/endpoints.py test/unit/test_api_unit.py test/unit/test_logging_unit.py
git commit -m "refactor(api): share typed prediction path with v1"
```
