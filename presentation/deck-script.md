# Deck script (DRAFT for review) — Sound Realty valuation API

10-minute Part 1, non-technical audience per `CANDIDATE_PROJECT.md:11`. Slide 1 is the whole story;
slides 2+ expand each beat. Part 2 is live demo, no slides — runbook in Appendix D.
Numbers render from `DECK_METRICS` in `deck.js` via `data-metric`; never hardcode in HTML.

Status: DRAFT. Approve/edit narration + slide count; then build `phdata.css` + `deck.html` + `deck.js` from this script.

## S1 — Cover: everything in one line

- Pattern: `.ph-cover`, `h1.r-fit-text`.
- Say: "Every listing gets a price — even when the paperwork is incomplete. We made Sound Realty's valuation API handle messy data, answer 6× faster, and fail clearly."
- Source: contract `CANDIDATE_PROJECT.md:21-29`.

## S2 — Executive summary (metric band)

- Pattern: `.ph-metrics` + `.ph-metric-band` (3 metrics, phData hero pattern).
- Metrics: `nnr.recovered` = 10–20% requests recovered · `perf.v2p50` vs `perf.v1p50` latency ·
  unknown zip → clear 404, no crash.
- Say: "Three outcomes: listings that used to be rejected now price. Typical answers in under 10 ms.
  Bad zipcodes get a plain-English error instead of a crash."
- Sources: notebook MCAR `missing_rate=0.15` (10–20% band); harness 2026-09-29 (v1 p50 55.8 ms / p95 78.9 ms;
  v2 p50 9.4 ms / p95 13.4 ms, n=30 TestClient); `shared.py:151-153`.

## S3 — At a glance

- Pattern: `.ph-glance` table (phData case-study row labels).
- Rows: Client / Challenge / Delivery / Result.
- Say: "Seattle valuations. Challenge: incomplete listings rejected, slow answers, cryptic failures.
  Delivery: smart fill-in on `/predict/v2`, load-once caching, typed contracts."

## S4 — Problem: three pains

- Pattern: `.ph-cols` ×3 (Core / Feature / Bug+Utility).
- Core: 10–20% of production data not pristine → rejected requests, lost coverage.
- Feature: model + data reloaded per request → slow under load.
- Bug/Utility: unknown zip crashes; Python 3.10 → 3.14, untyped code, Swagger/response mismatch.
- Say: "Agents can't wait on partial paperwork; every reload adds latency; every crash costs a conversation."
- Sources: `endpoints.py:36` per-request `load_artifacts()`; initial `Dockerfile: python:3.10-slim` → current `3.14`.

## S5 — Use case: the incomplete listing

- Pattern: prose + `.ph-risk` callout (cost of doing nothing).
- Say: "A listing missing bathrooms or lot size used to be a dead end — agent calls back, seller waits,
  deal stalls. Cost is coverage: up to one in five requests."
- Issue/Cost beat from user notes; 10–20% from notebook §2 (`missing_rate=0.15`).

## S6 — Solution A: Mean fill-in (baseline)

- Pattern: `figure.ph-diagram` — flat line at column average; `figcaption`: ignores relationships.
- Say: "Plan A: fill every blank with the average. Simple, but every house gets the same guess —
  a small condo and a large family home look identical on the missing field."

## S7 — Solution B: Median fill-in (baseline)

- Pattern: `figure.ph-diagram` — flat line at median, outlier-resistant note.
- Say: "Plan B: fill with the middle value. Sturdier against mansions skewing the average,
  but still blind to the house in front of us."

## S8 — Solution C: KNN fill-in (k=5, distance-weighted)

- Pattern: `figure.ph-diagram` — five nearest-neighbor houses vote, closer ones count more.
- Say: "Plan C: look at five similar homes — similar size, grade, age — and let the closest ones
  weigh more. The guess adapts to the house, not the whole city."
- Source: `KNNImputer(n_neighbors=5, weights="distance")`, `shared.py:117`; notebook §3.

## S9 — Use case summary: KNN selected

- Pattern: `.ph-callout` + compact table (notebook §7, price-predictive features).
- Rows: sqft_above `knn.sqftAbove` −17% · bathrooms `knn.bathrooms` −16% · floors `knn.floors` −15% ·
  grade `knn.grade` −14% vs mean RMSE. Caveat line: aggregate average misleads (lot-size outliers dominate).
- Say: "On the features that move price, neighbor-based guesses beat averages by 14–17%.
  The headline average hides this because two lot-size fields with wild outliers swamp it —
  so we judged per feature that matters, and picked KNN."
- Source: `notebooks/imputation_experiment.ipynb` §7.

## S10 — Feature: model caching — problem and impact

- Pattern: `.ph-cols` (before/after pipeline).
- Before: model `.pkl` + demographics CSV + imputer refit read from disk on every request
  (`endpoints.py:36-40`). After: loaded once at startup, reused (`lifespan.py:20`, `require_artifacts`,
  503 when unavailable, 404 on unknown zip).
- Say: "Before, every knock on the door reloaded the whole office — model, maps, comparables.
  Under load that queues up. After, we load once when the service wakes and serve from memory."

## S11 — Feature: caching results

- Pattern: `.ph-metric-band` (2 metrics) + `.ph-foot` method line.
- Metrics: p50 `perf.v1p50` → `perf.v2p50`; p95 `perf.v1p95` → `perf.v2p95` (keys, not literals).
- Say: "Same question, same machine: typical answer falls from ~56 ms to ~9 ms; the slow tail
  from ~79 ms to ~13 ms. Headroom for traffic spikes without touching accuracy."
- Foot: "Local harness, TestClient n=30, payload 98042 — not a production SLA."

## S12 — Bug: unknown zipcodes

- Pattern: `.ph-cols` (before crash / after 404 `Unknown zipcode: 00000`).
- Say: "A typo'd zip used to blow up. Now it returns a clear not-found naming the zip —
  agent fixes the digit, moves on."
- Source: `shared.py:151-153`; tests `test_api_unit.py:57-83`.

## S13 — Utility: modernized base

- Pattern: `.ph-glance` rows — Runtime / Typing / Contracts.
- Runtime: Python 3.10 → 3.14, pip → uv lockfile, Docker `ARG PYTHON_VERSION`.
- Typing: builtin generics, typed boundaries (`Predictor`/`ImputerProtocol`), pyright clean.
- Contracts: `/predict/v2` + `/health/v2` typed response models (`PredictionResponse`,
  `HealthResponse`, `ErrorDetail`) so Swagger matches reality.
- Say (one line each, non-technical): "Current supported runtime, reproducible installs.
  Typed code catches mistakes before customers do. Docs now promise what the API actually returns."
- Sources: `pyproject.toml: requires-python >=3.14`; commits `f12ab59 b4067af 3e11170 6ff6964 05a6a87`.

## S14 — Close + handoff to demo

- Pattern: `.ph-cover`-lite, single `r-fit-text` line + next-step list.
- Say: "Shipped: no listing left behind, answers in milliseconds, errors you can act on,
  on a base we can maintain. Next I'll show it live — missing fields, bad zip, and speed —
  then we can go as technical as you like."
- Demo cue → Appendix D.

---

## Appendix D — Part 2 demo runbook (NOT slides, per assignment)

1. Missing data: POST `/predict/v2` with `bathrooms: null`, `sqft_lot: null` → 200 + `predicted_price`;
   same payload to v1 fails (required fields). Imputation trace: `endpoints_v2.py:63-71`.
2. Unknown zip: `"zipcode": "00000"` → 404 `Unknown zipcode: 00000` (`shared.py:151-153`).
3. Speed: note lifespan load-once (`lifespan.py:20`) vs v1 per-request (`endpoints.py:36`);
   cite harness p50/p95 from `DECK_METRICS`, offer live re-run.
4. Readiness: `/health/v2` 200 vs 503 when artifacts missing (`lifespan.py`, `test_readiness_unit.py`).
5. Contracts: `/docs` shows `PredictionResponse`/`HealthResponse`/`ErrorDetail` with examples.
6. AI usage (expected question, `CANDIDATE_PROJECT.md:163-170`): tool used, context technique,
   validation via unit/integration suites + live probes.
