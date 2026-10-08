# Typed Shared API Prediction Design

## Goal

Make the v2 API's internal data flow consistently typed and make prediction
inference a shared path for v1 and v2. Keep the v1 endpoint's intentionally
minimal type annotations and preserve both versions' existing HTTP and OpenAPI
contracts.

## Current state

- `endpoints.py` defines the v1 `HomeFeatures` request model and performs
  prediction work directly in the route.
- `endpoints_v2.py` defines v2 request and response models and calls helpers in
  `shared.py`.
- `fill_missing` accepts a broad dictionary and returns a dictionary whose
  values are all typed as `float`, losing the field-level type distinction
  (notably, `bedrooms` is an integer in the API models).
- `predict_price` accepts and returns broad dictionaries. Its logic is not
  currently shared by the v1 route.
- Strict Pyright checking is configured and currently passes.

## Design

### Shared prediction types

Add explicit internal types in a neutral API module:

- `PredictionInput`: all required, non-null prediction features, with
  `bedrooms` represented as `int`, continuous numeric features as `float`, and
  `zipcode` as `str`.
- `PredictionResult`: the predicted price as `float`.

These internal types define the interface of the shared prediction function;
they do not replace or leak into the HTTP/OpenAPI schemas unless already
represented there.

### Shared prediction path

Refactor `predict_price` to have the interface
`predict_price(features: PredictionInput, artifacts: PredictArtifacts) ->
PredictionResult`. It remains responsible for constructing the pandas row,
joining zipcode demographics, selecting model features, invoking the model,
and reporting an unknown zipcode as the existing 404.

Both API versions call this helper:

- V1 retains its current request model and its intentionally minimal route
  annotations. The route adapts validated request values into
  `PredictionInput`, loads the prediction artifacts as it does today, and
  calls `predict_price`.
- V2 keeps its nullable HTTP request model. It passes that model to the
  imputation helper; after imputation, it builds a complete `PredictionInput`
  and calls the same `predict_price` function.

The helper returns `PredictionResult`. Each route maps that result to its
existing HTTP response shape, avoiding a change to response validation or
OpenAPI schemas.

### V2 request and imputation types

Move v2 request and response models out of `endpoints_v2.py` into a schema
module that has no dependency on endpoint or service code. Keep field names,
constraints, nullability, examples, and response models unchanged.

Replace the generic dictionary interface of `fill_missing` with a typed v2
request input and a named imputation result. The result contains:

- a complete `PredictionInput`, with imputed fields represented using their
  declared feature types;
- the names of fields that were missing in the original request.

The v2 route maps this result into the existing `/impute` response model. The
current integer conversion behavior for `bedrooms` is preserved in this
structural refactor; any change to rounding/truncation semantics is out of
scope and should be considered separately.

### Boundaries and compatibility

- Keep `endpoints.py` v1 request validation, HTTP paths, statuses, JSON
  response shape, and intentionally minimal route typing.
- Keep v2 paths, validation rules, statuses, request/response JSON, and
  OpenAPI contract unchanged.
- Keep artifact loading responsibilities and runtime behavior unchanged,
  except that v1 supplies its loaded prediction artifacts to the shared
  prediction function.
- Do not add dependencies or broaden this work into a general API rewrite.

## Testing and acceptance criteria

1. Unit-test the shared prediction function's typed input/output behavior,
   including successful predictions and unknown zipcodes.
2. Verify both v1 and v2 routes call the shared prediction path and preserve
   their current response JSON and status codes.
3. Test v2 imputation with complete and nullable requests, including the
   reported list of originally missing fields and the preserved integer
   conversion behavior for bedrooms.
4. Retain and pass request validation and OpenAPI contract tests.
5. Run focused API unit tests, strict Pyright, and Ruff.
6. Confirm v1 remains excluded from a broader annotation cleanup and all
   observed v1/v2 HTTP and OpenAPI contracts remain unchanged.
