# FastAPI Machine Learning Model Deployment

This project implements a RESTful API using FastAPI to deploy a machine learning model for predicting home prices based on various features. The model is trained on real estate data and can provide predictions based on user input.

## Project Structure

``` text
phdata-mle-project-challenge-2026
├── src
│   ├── main.py                    # App factory, middleware, exception handlers
│   ├── logger_config.py           # JSON logging for app + uvicorn on stdout
│   ├── paths.py                   # Single source of truth for artifact and data file paths
│   ├── api
│   │   ├── endpoints.py           # Legacy v1 router: /predict, /health
│   │   ├── endpoints_v2.py        # Current router: /predict/v2, /health/v2
│   │   ├── lifespan.py            # Loads model, features, demographics and imputer once at startup
│   │   └── shared.py              # Artifact loaders, KNN imputer, predict pipeline
│   ├── model
│   │   ├── create_model.py        # Trains the model and writes the artifacts
│   │   ├── Dockerfile             # Builds and runs create_model.py
│   │   ├── model.pkl              # Serialized machine learning model
│   │   └── model_features.json    # Ordered features required for predictions
│   └── data
│       ├── kc_house_data.csv      # Training data for the model
│       ├── zipcode_demographics.csv # Demographic data for predictions
│       └── future_unseen_examples.csv # Listings used as OpenAPI examples
├── test
│   ├── conftest.py                # TestClient, http_client, sample payload
│   ├── unit/                      # In-process tests via TestClient
│   ├── integration/               # HTTP tests against the running container
│   ├── quality/                   # Analysis scripts, write results in place
│   └── benchmark/                 # Latency measurement, writes results.csv
├── notebooks/                     # Imputation experiments
├── presentation/                  # Deck source
├── .github/workflows/ci.yml       # pytest, ruff, pyright, image builds
├── Dockerfile                     # API image; CMD python -m main
├── Dockerfile.test                # Test image
├── docker-compose.test.yml        # api + test services for integration runs
├── Makefile                       # test-build / test-unit / test-integration / test-all / clean / help
├── pyproject.toml                 # Dependencies and pytest config
├── uv.lock                        # Locked dependency versions
├── ruff.toml                      # Lint config (selects ALL)
├── pyrightconfig.json             # Type-checker config
├── .python-version                # Single source of truth for image builds
├── CANDIDATE_PROJECT.md           # Challenge write-up
└── README.md
```

## Setup Instructions

### Prerequisites

- Docker installed on your system
- Git (for cloning the repository)

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd phdata-mle-project-challenge-2026
```

### Step 2: Generate Model Artifacts (First Time Only)

Before running the API, you need to generate the model files. This only needs to be done once, or when you want to retrain the model.

**Build the model creation Docker image:**

```bash
docker build -f src/model/Dockerfile -t create-model .
```

**Run the container to generate model artifacts:**

```bash
docker run --rm -v "$(pwd)/src/model:/app/model" create-model
```

This will create `model.pkl` and `model_features.json` in the `src/model/` directory. Both the training script and the API
resolve their file paths from `src/paths.py`, anchored to that file rather than the process working directory, so neither
depends on where it was launched from. The `-v` mount is what puts the trained artifacts back in your checkout.

### Step 3: Build and Run the API

**Build the API Docker image:**

```bash
docker build -t mle-project-challenge-2026 .
```

**Run the API container:**

```bash
docker run -d -p 8000:8000 --name housing-api mle-project-challenge-2026
```

### Step 4: Access the API

Open your browser and go to `http://127.0.0.1:8000/docs` to view the interactive API documentation.

### Managing the Container

**Stop the container:**

```bash
docker stop housing-api
```

**Start the container again:**

```bash
docker start housing-api
```

**Remove the container:**

```bash
docker rm housing-api
```

**View container logs:**

```bash
docker logs housing-api
```

### Logging

**Location:** stdout only. There is no log file and no rotation to configure — the container's stdout is the log, so
whatever captures container output (Docker's json-file driver, `docker logs`, Kubernetes, CloudWatch) is the
destination. The app never opens a file, which is what keeps the image free of writable volume assumptions.

**Configuration:** a single `ProcessorFormatter` in `src/logger_config.py` renders structlog events and stdlib records
(`uvicorn`, `uvicorn.error`, `uvicorn.access`) through the same `JSONRenderer`, so all four share one line format and one
`correlation_id`. `setup_logging()` replaces `root.handlers` and sets `propagate = False` on each uvicorn logger, so
access records are never emitted twice. It runs at import of `src/main.py`, which is why supervisor startup lines are JSON
too — not only request-time lines.

Every line carries `event`, `logger`, `level`, `timestamp`, and `correlation_id` (`null` outside a request). A typical
prediction emits four:

```json
{"artifact": "model", "sha256": "b06a43007cbd", "event": "artifact_loaded", "correlation_id": null, "logger": "api.shared", "level": "info", "timestamp": "..."}
{"artifact": "demographics", "sha256": "8d9be9398129", "rows": 70, "event": "artifact_loaded", "correlation_id": null, "logger": "api.shared", "level": "info", "timestamp": "..."}
{"predicted_price": 253980.0, "event": "prediction_complete", "correlation_id": "a958c139-...", "logger": "api.shared", "level": "info", "timestamp": "..."}
{"method": "POST", "path": "/predict/v2", "status_code": 200, "duration_ms": 35.69, "event": "request", "correlation_id": "a958c139-...", "logger": "api", "level": "info", "timestamp": "..."}
```

`artifact_loaded` fires once per process at startup and identifies which file that container is serving — compare the
`sha256` against the artifacts you expect. Both are re-committed during development (`model.pkl` on retraining, the
demographics table whenever zipcode coverage changes), so a stale image layer shows different digests than a fresh build.
The demographics digest matters most: that lookup decides both the 404 boundary and 26 of the 33 model features, so a new
model paired with an old table is the mismatch worth catching.

**Levels:** `logging.INFO` by default. `uvicorn.access` lines are already structured — `method`, `path`, `status_code`,
`client_ip` are exploded from uvicorn's positional args, so `jq` filters work without regex:

```bash
docker logs housing-api | jq -c 'select(.event == "request" and .status_code == 500)'
docker logs housing-api | jq -c 'select(.event == "prediction_complete") | .predicted_price'
```

**Requests:** send a UUID `X-Request-ID` to pin the ID, or read the generated one back from the response header. A
non-UUID value fails validation and is silently replaced by a fresh UUID, so short or W3C `traceparent`-style IDs do not
survive the round trip.

**One exception:** the legacy `POST /predict` path also prints a raw pandas DataFrame to stdout
(`src/api/endpoints.py:68`). That print is kept deliberately — it is the baseline the benchmark prices against — so filter
defensively when parsing:

```bash
docker logs housing-api \
  | jq -cR 'fromjson? | select(.correlation_id != null)'
```

## Usage

There are two prediction endpoints. `POST /predict/v2` is the current one; `POST /predict` is the legacy version and is kept for comparison.

| Endpoint | Status | Null inputs |
| --- | --- | --- |
| `POST /predict/v2` | Current | Accepted. The seven non-zipcode fields are optional; nulls are filled by a KNN imputer (k=5, fitted at startup). Only `zipcode` is required. |
| `POST /predict` | Legacy | Rejected with 422. All eight fields are required, so a missing specification fails validation instead of returning a prediction.[^logging] |

Both return `{"predicted_price": <float>}` and return 404 for a zipcode with no demographics row. `GET /health` (v1) and `GET /health/v2` (v2, also reports startup artifact readiness) report liveness.

Unknown error codes are not request errors. A 500 means the service never finished loading its startup artifacts — a missing or unreadable model, features file, demographics CSV, or imputer — so the failure is in the deployment, not in the payload. `/health/v2` is the readiness probe to watch: it reports 500 while artifacts are absent and 200 once they are loaded. Retry the container rather than the request; the state does not change between attempts.

```bash
# current: sqft_lot omitted, imputed from the other six specifications
curl -s -X POST http://127.0.0.1:8000/predict/v2 \
  -H 'Content-Type: application/json' \
  -d '{"bedrooms": 3, "bathrooms": 2.0, "sqft_living": 1500.0, "floors": 1.0, "sqft_above": 1200.0, "sqft_basement": 300.0, "zipcode": "98042"}'

# legacy: same payload without the optional field is a 422
curl -s -X POST http://127.0.0.1:8000/predict \
  -H 'Content-Type: application/json' \
  -d '{"bedrooms": 3, "bathrooms": 2.0, "sqft_living": 1500.0, "floors": 1.0, "sqft_above": 1200.0, "sqft_basement": 300.0, "zipcode": "98042"}'
```

[^logging]: Domain events (`prediction_complete`, `imputing_null_features`, `unknown_zipcode`, `validation_failed`) are
    emitted by `/predict/v2` and `/health/v2` only. The legacy `/predict` and `/health` paths produce just the middleware
    `request` line — no `prediction_complete`, and their 404 carries no zipcode. `artifact_loaded` is startup and is shared
    by both.

## Testing

This project uses Docker-based testing to ensure environment consistency between testing and production. All tests run inside Docker containers, eliminating "works on my machine" issues.

### Quick Start

Run unit tests (fast, recommended for development):

```bash
make test-unit
```

Run integration tests (full environment):

```bash
make test-integration
```

Run all tests:

```bash
make test-all
```

### Test Types

**Unit Tests** (`test/unit/`)

- Use FastAPI TestClient for in-process testing
- No external dependencies or containers required
- Fast execution (typically under 30 seconds)
- Ideal for rapid development iteration

**Integration Tests** (`test/integration/`)

- Test against a real running API container
- Verify end-to-end functionality via HTTP requests
- Ensure Docker networking and orchestration work correctly
- More comprehensive but slower execution

**Quality** (`test/quality/`)

Analysis scripts that measure output quality rather than assert it. They run locally against the venv and write their results next to themselves.

- `imputation_accuracy.py` - compares mean, median, raw KNN and z-scored KNN imputation of the seven non-zipcode `/predict/v2` fields, on held-out sales rows, and writes `imputation_accuracy.md` plus four CSVs. Scored on scale-free NMAE/NRMSE and on Pearson correlation, with paired Wilcoxon tests and bootstrap confidence intervals.

```bash
python test/quality/imputation_accuracy.py
```

**Benchmarks** (`test/benchmark/`)

Scripts that measure speed rather than correctness. Same contract as above: run locally, write results next to themselves.

- `bench_predict.py` - request latency under closed-loop concurrency, writing `results.csv`.

### Running Tests

#### Unit Tests Only

```bash
make test-unit
```

This command:

- Builds the test Docker image
- Runs only tests in `test/unit/` directory
- Generates coverage reports
- Completes quickly without starting the full API container

#### Integration Tests Only

```bash
make test-integration
```

This command:

- Builds both API and test containers using Docker Compose
- Starts the API container and waits for health check
- Runs tests in `test/integration/` directory
- Stops the containers when complete, but leaves them in place; run `make clean` to remove them

#### All Tests

```bash
make test-all
```

Runs both integration and unit tests for comprehensive validation.

### Viewing Coverage Reports

After running tests, coverage reports are generated in the `test-results/` directory:

**HTML Coverage Report:**

```bash
open test-results/coverage/index.html
```

#### Terminal Coverage Summary

Coverage is automatically displayed in the terminal after test execution.

### Running Specific Tests

The test image bakes `test/` and `src/` in at build time, so these commands mount both directories to run
against your working copy instead of the copy frozen in the image. Build the image once with `make test-build`.

Run a specific test file:

```bash
docker run --rm -v "$(pwd)/test:/app/test:ro" -v "$(pwd)/src:/app/src:ro" \
  ml-api-test pytest test/unit/test_api_unit.py -v
```

Run a specific test function:

```bash
docker run --rm -v "$(pwd)/test:/app/test:ro" -v "$(pwd)/src:/app/src:ro" \
  ml-api-test pytest test/unit/test_api_unit.py::test_predict_endpoint_valid_input -v
```

Run tests matching a pattern:

```bash
docker run --rm -v "$(pwd)/test:/app/test:ro" -v "$(pwd)/src:/app/src:ro" \
  ml-api-test pytest test/unit -k "predict" -v
```

### Troubleshooting

#### Issue: "Cannot connect to the Docker daemon"

Solution: Ensure Docker is running on your system.

```bash
docker ps  # Should list running containers without error
```

#### Issue: Integration tests fail with connection errors

Solution: Check if the API container is healthy.

```bash
docker compose -f docker-compose.test.yml up
# In another terminal:
docker compose -f docker-compose.test.yml ps
docker compose -f docker-compose.test.yml logs api
```

#### Issue: Tests pass locally but fail in Docker

Solution: This usually indicates environment differences. Check:

- Model artifacts exist in `src/model/` directory
- Data files exist in `src/data/` directory
- Dependencies are declared in `pyproject.toml` and pinned in `uv.lock`

#### Issue: "Port 8000 already in use"

Solution: Stop any running containers or services using port 8000.

```bash
docker compose -f docker-compose.test.yml down
docker stop housing-api  # If the main API is running
```

#### Issue: Test results not appearing in `test-results/` directory

Solution: Ensure the directory exists and has proper permissions.

```bash
mkdir -p test-results
chmod 755 test-results
```

#### Issue: Tests are very slow

Solution: Run unit tests only for faster feedback during development.

```bash
make test-unit  # Much faster than integration tests
```

#### Issue: "Image not found" errors

Solution: Build the test image explicitly.

```bash
make test-build
```

### Cleaning Up

Remove test containers and artifacts:

```bash
make clean
```

This removes:

- All Docker containers created by docker-compose.test.yml
- All test result files and coverage reports

### Development Workflow

For rapid development iteration:

1. Make code changes in `src/` or test changes in `test/`
2. Run unit tests: `make test-unit`
3. Fix any issues and repeat
4. Before committing, run full suite: `make test-all`

The `test` service mounts `./test` and `./src` as volumes, so test changes are picked up without a rebuild. The `api`
service does not mount source: `make test-integration` passes `--build`, so it rebuilds the API image on every run.
Expect a short wait before changes to `src/` take effect.

## Feedback

We welcome any feedback regarding the project or the interview process. Your insights are valuable to us as we strive to improve the experience for future candidates.
