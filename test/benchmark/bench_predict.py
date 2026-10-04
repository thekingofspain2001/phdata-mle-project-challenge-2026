"""Time the async and sync v1 handlers under closed-loop concurrency.

Each test is isolated: one endpoint, one concurrency level, a fresh server, so
no earlier test's warm state or artifacts leak into the next one.

Load model is closed-loop. C callers start together; as each call completes that
caller immediately sends the next, so concurrency stays at C for the whole run
and total time reflects a steady arrival pattern rather than a burst.

The load generator is async on purpose. At C=50, fifty client threads would
fight over the GIL and contaminate the very server latency being measured. One
event loop driving C tasks removes that, and costs less than a thread per
caller.

Measurement hygiene: the hot loop only times a call and writes one float into a
preallocated slot. No locks, no statistics, no formatting. Every derived figure
and every CSV write happens after the run completes, so reporting never sits on
the critical path.

    python test/benchmark/bench_predict.py                       # both routes, all levels
    python test/benchmark/bench_predict.py --endpoint /predict   # one route, all levels
    python test/benchmark/bench_predict.py --endpoint /predict-sync --concurrency 20

Reported per test:

    total   wall clock for all calls to drain
    mean    total / calls
    min/max fastest and slowest single call
    rps     calls / total

Individual call times are appended to results.csv.

Endpoints under test come from endpoints_v1_variants.py, both derived from the
e9ef514 baseline and differing only in `async def` vs `def`.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import csv
import importlib.util
import itertools
import os
import sys
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

import httpx2 as httpx
import uvicorn
from fastapi import FastAPI

if TYPE_CHECKING:
    from collections.abc import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_CSV = REPO_ROOT / "src" / "data" / "future_unseen_examples.csv"
RESULTS_CSV = Path(__file__).resolve().parent / "results.csv"
sys.path.insert(0, str(Path(__file__).resolve().parent))
HOST = "127.0.0.1"
PORT = 8936
BASE_URL = f"http://{HOST}:{PORT}"

# The three real routes: v1 restored, v2 modernised async, v2 modernised sync.
REAL_ENDPOINTS = ("/predict", "/predict/v2", "/predict_sync/v2")
# e9ef514 variants used only to attribute cost; see endpoints_v1_variants.py.
VARIANT_ENDPOINTS = ("/predict-original", "/predict-sync")
ENDPOINTS = REAL_ENDPOINTS
CONCURRENCY_LEVELS = (1, 5, 10, 20, 50)

type Scalar = str | int | float | None
type Payload = dict[str, Scalar]


def load_app() -> FastAPI:
    """Import the FastAPI app from src/ without needing it on the path."""
    spec = importlib.util.spec_from_file_location("bench_app", REPO_ROOT / "src" / "main.py")
    if spec is None or spec.loader is None:
        message = f"cannot load the app from {REPO_ROOT / 'src' / 'main.py'}"
        raise RuntimeError(message)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(REPO_ROOT / "src"))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(REPO_ROOT / "src"))
    app = getattr(module, "app", None)
    if not isinstance(app, FastAPI):
        message = "src/main.py does not expose a FastAPI app"
        raise TypeError(message)
    # Bench-only variants live beside this file so src/ stays untouched. Imported
    # here because api.shared needs src/ on sys.path, which load_app sets first.
    from endpoints_v1_variants import router_variants  # noqa: PLC0415

    app.include_router(router_variants)
    return app


def coerce(raw: str, key: str) -> Scalar:
    """Turn a CSV string into the JSON scalar the models expect."""
    if key == "zipcode":
        return raw
    try:
        return int(raw) if key == "bedrooms" else float(raw)
    except ValueError:
        return raw


def load_rows(path: Path) -> list[Payload]:
    """Read the examples CSV into request-ready payloads."""
    with path.open() as handle:
        rows = csv.DictReader(handle)
        return [{key: coerce(value, key) for key, value in row.items()} for row in rows]


def load_swagger_examples(app: FastAPI) -> list[Payload]:
    """Pull the request examples straight off /docs and keep them as they are.

    No filtering. example_0_unknown_zip and every *_no_* example are included
    even though they are expected to fail, because those failures are part of
    what the real routes do when handed the published examples.
    """
    schema = app.openapi()
    content = schema["paths"]["/predict"]["post"]["requestBody"]["content"]["application/json"]
    return [example["value"] for example in content["examples"].values()]


def serve() -> uvicorn.Server:
    """Start the app in a background thread and block until it is up."""
    config = uvicorn.Config(load_app(), host=HOST, port=PORT, log_level="error")
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    return server


async def closed_loop(path: str, payloads: Sequence[Payload], concurrency: int) -> tuple[list[float], float]:
    """Drive `concurrency` closed-loop callers; return per-call times and the total.

    The hot path does two things: time one await, and write one float into this
    caller's own slot of a preallocated list. No lock, no lock-free claim on a
    shared counter beyond itertools (atomic in CPython), no arithmetic on the
    timings, no output. Everything derived is computed by the caller afterwards.
    """
    slots = [0.0] * len(payloads)
    claims = itertools.count()

    async with httpx.AsyncClient(timeout=120.0) as client:
        await client.get(f"{BASE_URL}/health")

        async def caller() -> None:
            for index in claims:
                if index >= len(payloads):
                    return
                started = time.perf_counter()
                # The published examples include payloads the routes reject, and a
                # rejected handler can drop the connection. The call still
                # happened and still cost time, so record it and move on.
                with contextlib.suppress(httpx.HTTPError):
                    await client.post(f"{BASE_URL}{path}", json=payloads[index])
                slots[index] = time.perf_counter() - started

        tasks = [asyncio.create_task(caller()) for _ in range(concurrency)]
        started = time.perf_counter()
        await asyncio.gather(*tasks)
        wall = time.perf_counter() - started

    return slots, wall


def summarise(path: str, concurrency: int, slots: Sequence[float], wall: float) -> str:
    """Compute and format every figure, after the run has finished."""
    done = sorted(value for value in slots if value > 0.0)
    calls = len(done)
    if calls == 0:
        return f"{path:<20} callers {concurrency:>3}  no calls completed\n"
    return (
        f"{path:<20} callers {concurrency:>3}  wall {wall:7.2f}s  calls {calls:>4}  "
        f"rps {calls / wall:6.1f}  mean/call {sum(done) / calls * 1e3:7.1f}ms  "
        f"min {done[0] * 1e3:7.1f}ms  max {done[-1] * 1e3:8.1f}ms\n"
    )


def run_test(path: str, concurrency: int, rows: Sequence[Payload]) -> list[tuple[float, float]]:
    """One isolated test: fresh server, one endpoint, one concurrency level.

    Returns each call time paired with that test's wall clock, so the CSV can
    carry the measured wall alongside the individual times rather than leaving
    throughput to be back-derived from latency.
    """
    server = serve()
    original = sys.stdout
    try:
        # The v1 handlers print a DataFrame per call. Send stdout to devnull for
        # the whole run so the report stays readable; the repr is still built,
        # which is the cost under test, only the terminal write is dropped.
        with Path(os.devnull).open("w") as sink:
            sys.stdout = sink
            slots, wall = asyncio.run(closed_loop(path, rows, concurrency))
    finally:
        sys.stdout = original
        server.should_exit = True
        time.sleep(0.3)
    sys.stderr.write(summarise(path, concurrency, slots, wall))
    sys.stderr.flush()
    return [(value, wall) for value in slots if value > 0.0]


def main() -> None:
    """Run the requested tests, writing every individual call time to results.csv."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default=None, help="single endpoint to test")
    parser.add_argument("--concurrency", type=int, default=None, help="single concurrency level")
    parser.add_argument("--levels", default=None, help="comma-separated concurrency levels, e.g. 1,5,20")
    parser.add_argument("--repeat", type=int, default=1, help="passes over the example set")
    parser.add_argument("--calls", type=int, default=None, help="exact number of calls, cycling the examples")
    parser.add_argument("--source", choices=("swagger", "csv"), default="swagger", help="payload source")
    parser.add_argument(
        "--routes",
        choices=("real", "variants"),
        default="real",
        help="real API routes or bench variants",
    )
    args = parser.parse_args()

    if args.source == "swagger":
        payloads = load_swagger_examples(load_app())
        sys.stdout.write(f"{len(payloads)} payloads from the /docs request examples\n\n")
    else:
        payloads = load_rows(EXAMPLES_CSV)
        sys.stdout.write(f"{len(payloads)} payloads from {EXAMPLES_CSV.name}\n\n")

    routes = (args.endpoint,) if args.endpoint else (REAL_ENDPOINTS if args.routes == "real" else VARIANT_ENDPOINTS)
    if args.levels:
        levels = tuple(int(level) for level in args.levels.split(","))
    elif args.concurrency is not None:
        levels = (args.concurrency,)
    else:
        levels = CONCURRENCY_LEVELS
    if args.calls:
        sized = list(payloads) * (args.calls // len(payloads) + 1)
        payloads = sized[: args.calls]
    elif args.repeat > 1:
        payloads = payloads * args.repeat
    plan = [(path, level) for path in routes for level in levels]

    recorded: list[tuple[str, int, float, float]] = []
    for path, level in plan:
        recorded.extend((path, level, value, wall) for value, wall in run_test(path, level, payloads))

    with RESULTS_CSV.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["endpoint", "concurrency", "call_seconds", "test_wall_seconds"])
        writer.writerows(recorded)
    sys.stdout.write(f"\n{len(recorded)} individual call times written to {RESULTS_CSV.name}\n")


if __name__ == "__main__":
    main()
