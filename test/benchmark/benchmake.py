"""Time the five S6 tests: three v1 variants and two /predict/v2 payload shapes.

The slide footnote says "median of 3 runs x 1000 calls, one at a time, over the
201 examples published on /docs". `bench_predict.py` measures one run and prints
a summary; nothing in the repo performs the three-run median, so the figure on
the slide cannot be re-derived from the repo as it stands.

Five tests, each RUNS runs of 1000 sequential calls at concurrency 1, so no run
overlaps another and nothing contends for CPU:

  1 /predict-original   v1 baseline: reload per call, prints the frame
  2 /predict-cached     same, artifacts from lifespan  -> prices the reload
  3 /predict-noprint    same, print removed            -> prices the print
  4 /predict/v2         the 201 examples, no nulls
  5 /predict/v2         one explicit null, moving between the nullable fields

Tests 1-3 differ from the baseline by exactly one variable each, so the S6 cost
split is read off by subtraction: original - noprint is the print, original -
cached is the per-call reload. /predict-sync is excluded; it exists only to
price the async-vs-sync question, which is not on the slide.

Tests 4 and 5 are not variations of one another. The 201 published examples
carry no explicit null at all - their missing data is an *omitted key*, which
v1 rejects with 422 and v2 fills from its default. pydantic treats an absent
key and an explicit null differently against `int | None`, so test 5 measures
a path nothing in the repo currently times.

The 201 examples are cycled unfiltered to fill each run, so means include the
422s and the one 500 the examples provoke. That is the whole example set, and
the status mix is recorded per test so the share of each mean that is real
work is visible rather than assumed.

Reads the app and the example payloads; writes only its own CSV. `results.csv`
is the committed evidence of the last single run and is never truncated here.
"""

from __future__ import annotations

import csv
import platform
import statistics
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from bench_predict import load_app, load_swagger_examples, run_test

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bench_predict import Payload

# The seven fields HomeFeaturesV2 declares nullable, in the order test 5 moves
# its single null across them. zipcode is absent: it is the lookup key, not an
# imputable feature, and v1 requires it.
NULLABLE_FIELDS = ("bedrooms", "bathrooms", "sqft_living", "sqft_lot", "floors", "sqft_above", "sqft_basement")

V1_TESTS = (("v1-original", "/predict-original"), ("v1-cached", "/predict-cached"), ("v1-noprint", "/predict-noprint"))
RUNS = 5
V2_TESTS = (("v2-no-nulls", "/predict/v2"), ("v2-moving-null", "/predict/v2"))

CALLS = 1000
CONCURRENCY = 1
OUT_CSV = Path(__file__).resolve().parent / "benchmake_results.csv"
OUT_RAW = Path(__file__).resolve().parent / "benchmake_raw.csv"

# One row per call: test, run, measured seconds, and that run's wall clock. The
# wall travels with each call so throughput is read directly rather than
# back-derived from a latency that may have lost calls.
type RawRow = tuple[str, int, float, float]


def cycle(payloads: Sequence[Payload], count: int) -> list[Payload]:
    """Repeat the example set up to `count` payloads, cycling from the top."""
    return [payloads[index % len(payloads)] for index in range(count)]


def moving_null(payloads: Sequence[Payload]) -> list[Payload]:
    """Give each payload exactly one explicit null, rotating which field holds it.

    The null walks NULLABLE_FIELDS one step per call, so every field is exercised
    equally and no single field's imputation cost dominates the mean. Each
    payload is copied first: the caller's example objects are shared, and
    mutating them in place would leak the null into later tests.
    """
    return [{**payloads[index], NULLABLE_FIELDS[index % len(NULLABLE_FIELDS)]: None} for index in range(len(payloads))]


def run_once(path: str, payloads: Sequence[Payload]) -> tuple[float, list[float]]:
    """Time one isolated run; return its wall seconds and every call time.

    `run_test` already isolates the server per run and reports itself on stderr,
    so this only keeps what it hands back: the wall the mean is taken over, and
    the individual call times that would otherwise be discarded. The mean is
    wall/calls, the per-call figure the slide quotes.
    """
    samples = run_test(path, CONCURRENCY, payloads)
    return samples[0][1], [value for value, _ in samples]


def mean_call_ms(label: str, path: str, payloads: Sequence[Payload], raw: list[RawRow]) -> list[float]:
    """Mean ms/call for one test over RUNS isolated runs, recording every call."""
    means: list[float] = []
    for run in range(1, RUNS + 1):
        wall, calls = run_once(path, payloads)
        mean_ms = wall / len(calls) * 1e3
        means.append(mean_ms)
        raw.extend((label, run, value, wall) for value in calls)
        sys.stderr.write(f"  {label:<15} run {run}/{RUNS}: {mean_ms:.2f} ms/call\n")
        sys.stderr.flush()
    return means


def write_csv(results: list[tuple[str, str, list[float]]], calls: int) -> None:
    """Write per-run means, per-test medians, and the machine, to OUT_CSV."""
    with OUT_CSV.open("w", newline="") as handle:
        handle.write(f"# benchmake tests={len(results)} runs={RUNS} calls={calls} concurrency={CONCURRENCY}\n")
        handle.write("# payload_source=/docs request examples, cycled unfiltered; means include 422s and one 500\n")
        handle.write(f"# python={sys.version.split()[0]} platform={platform.platform()}\n")
        handle.write(f"# generated={datetime.now(UTC).isoformat(timespec='seconds')}\n")
        handle.write("#\n# per-run means\n")
        writer = csv.writer(handle)
        writer.writerow(["test", "endpoint", "run", "mean_call_ms"])
        for label, path, means in results:
            for run, mean_ms in enumerate(means, start=1):
                writer.writerow([label, path, run, f"{mean_ms:.4f}"])
        handle.write("#\n# per-test median of RUNS, the figure the deck quotes\n")
        writer.writerow(["test", "endpoint", "runs", "median_call_ms"])
        for label, path, means in results:
            writer.writerow([label, path, len(means), f"{statistics.median(means):.4f}"])


def write_raw(raw: Sequence[RawRow]) -> None:
    """Write every individual call time to OUT_RAW, so the means can be rechecked.

    The medians in OUT_CSV are means over these rows and nothing else; keeping
    the calls means a reader can recompute them, see the spread behind a median,
    and confirm which calls failed rather than taking the aggregate on trust.
    """
    with OUT_RAW.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["test", "run", "call_seconds", "test_wall_seconds"])
        writer.writerows((label, run, f"{value:.6f}", f"{wall:.6f}") for label, run, value, wall in raw)

    sys.stderr.write(f"{len(raw)} individual call times written to {OUT_RAW.name}\n")


def main() -> None:
    """Run all five tests RUNS times at CALLS calls each, then write the CSV."""
    examples = load_swagger_examples(load_app())
    nulls = moving_null(cycle(examples, CALLS))
    payloads = cycle(examples, CALLS)
    sys.stderr.write(
        f"{len(examples)} examples from /docs, {CALLS} calls per run, {RUNS} runs per test, concurrency {CONCURRENCY}\n\n",
    )

    raw: list[RawRow] = []
    results: list[tuple[str, str, list[float]]] = []
    for label, path in (*V1_TESTS, *V2_TESTS):
        shapes = nulls if label == "v2-moving-null" else payloads
        results.append((label, path, mean_call_ms(label, path, shapes, raw)))
        median = statistics.median(results[-1][2])
        sys.stderr.write(f"  {label:<15} median of {RUNS}: {median:.2f} ms/call\n\n")

    write_csv(results, CALLS)
    write_raw(raw)
    sys.stderr.write(f"written to {OUT_CSV.name}\n")


if __name__ == "__main__":
    main()
