"""Time /predict vs /predict/v2 over the unseen examples, serial and parallel.

Runs the real app under uvicorn and drives it over HTTP so the sync-vs-async
route difference and the startup-cached artifacts are both exercised. Sends the
whole CSV row; Pydantic ignores the columns neither model declares.

    python test/bench_predict.py [--workers 8] [--repeat 1]
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING

import httpx2 as httpx
import uvicorn
from fastapi import FastAPI

if TYPE_CHECKING:
    from collections.abc import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_CSV = REPO_ROOT / "src" / "data" / "future_unseen_examples.csv"
HOST = "127.0.0.1"
PORT = 8936
ENDPOINTS = ("/predict", "/predict/v2")

type Scalar = str | int | float
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
    return app


def coerce(raw: str, key: str) -> Scalar:
    """Turn a CSV string into the JSON scalar the models expect."""
    if key == "zipcode":
        return raw
    try:
        return int(raw)
    except ValueError:
        return float(raw)


def load_rows(path: Path) -> list[Payload]:
    """Read the examples CSV into request-ready payloads."""
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [{key: coerce(value, key) for key, value in row.items()} for row in rows]


def serve() -> uvicorn.Server:
    """Start the app in a background thread and block until it is up."""
    config = uvicorn.Config(load_app(), host=HOST, port=PORT, log_level="error")
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    return server


def time_call(client: httpx.Client, path: str, payload: Payload) -> float:
    """POST one payload, assert it succeeded, return elapsed seconds."""
    started = time.perf_counter()
    response = client.post(f"http://{HOST}:{PORT}{path}", json=payload)
    elapsed = time.perf_counter() - started
    response.raise_for_status()
    return elapsed


def run_serial(client: httpx.Client, path: str, rows: Sequence[Payload], repeat: int) -> list[float]:
    """Time every row one after another."""
    return [time_call(client, path, row) for row in rows for _ in range(repeat)]


def run_parallel(
    client: httpx.Client,
    path: str,
    rows: Sequence[Payload],
    workers: int,
    repeat: int,
) -> list[float]:
    """Fire every row at once across a thread pool and time each response."""
    jobs = [row for row in rows for _ in range(repeat)]
    latencies: list[float] = []
    lock = threading.Lock()

    def worker(payload: Payload) -> None:
        elapsed = time_call(client, path, payload)
        with lock:
            latencies.append(elapsed)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(worker, jobs))
    return latencies


def report(label: str, latencies: Sequence[float], wall: float, count: int) -> None:
    """Print one timing row: wall clock, per-call latency, throughput."""
    ordered = sorted(latencies)
    line = (
        f"{label:<34} wall {wall:6.2f}s  "
        f"p50 {statistics.median(ordered) * 1e3:7.1f}ms  "
        f"p95 {ordered[int(len(ordered) * 0.95) - 1] * 1e3:7.1f}ms  "
        f"mean {statistics.fmean(ordered) * 1e3:7.1f}ms  "
        f"rps {count / wall:6.1f}"
    )
    sys.stdout.write(f"{line}\n")


def main() -> None:
    """Time both endpoints serially and in parallel, then stop the server."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--repeat", type=int, default=1)
    args = parser.parse_args()

    rows = load_rows(EXAMPLES_CSV)
    sys.stdout.write(f"{len(rows)} examples from {EXAMPLES_CSV.name}, {args.workers} parallel workers\n\n")

    server = serve()
    try:
        with httpx.Client(timeout=120.0) as client:
            client.get(f"http://{HOST}:{PORT}/health").raise_for_status()

            for path in ENDPOINTS:
                started = time.perf_counter()
                latencies = run_serial(client, path, rows, args.repeat)
                report(f"{path} serial", latencies, time.perf_counter() - started, len(latencies))

            for path in ENDPOINTS:
                started = time.perf_counter()
                latencies = run_parallel(client, path, rows, args.workers, args.repeat)
                report(f"{path} parallel x{args.workers}", latencies, time.perf_counter() - started, len(latencies))
    finally:
        server.should_exit = True


if __name__ == "__main__":
    main()
