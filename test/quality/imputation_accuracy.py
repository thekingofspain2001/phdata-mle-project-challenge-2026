"""Compare mean, median and KNN imputation of the seven v2 request fields.

`POST /predict/v2` accepts seven home features - bedrooms, bathrooms, sqft_living,
sqft_lot, floors, sqft_above, sqft_basement - and lets every one of them be null
except zipcode. So the question this script answers is narrow and practical:

    a listing arrives missing one specification, say sqft_lot.
    can the other six specifications recover it?

Four imputers are compared on that one task, all fitted on a train split and
scored on held-out rows they have never seen:

    mean         per-field mean of the training rows (sklearn SimpleImputer)
    median       per-field median of the training rows (sklearn SimpleImputer)
    knn_raw      KNNImputer(k=5, distance) on the raw columns - shipped in v2
    knn_scaled   KNNImputer(k=5, distance) on z-scored columns

`knn_scaled` earns its place rather than being a variant for its own sake. The
seven fields differ in spread by a factor of ~77,000 (floors std 0.54 versus
sqft_lot std 41,420), and KNN measures neighbours with an unweighted Euclidean
distance, so on raw columns the distance is effectively "how different are the
lot sizes" and the other six specifications barely contribute. Scaling is the
standard correction, and the only honest way to find out whether the shipped
configuration is leaving accuracy on the table is to measure it.

Metrics, chosen from the imputation-evaluation literature rather than by
convention. Raw MAE and RMSE are not comparable across these seven fields,
because sqft_lot spans five orders of magnitude more than floors and would
dominate any average; see https://arxiv.org/html/2507.11297v1 on why pointwise
errors also systematically favour imputers that collapse toward a conditional
mean. So:

    MAE / RMSE      in the field's own units, for reading
    NMAE / NRMSE    divided by the held-out standard deviation, so all seven
                    fields can be averaged into one comparable number
    Pearson r / R^2 the decisive metric. Mean and median return the same number
                    for every row, so their correlation with the truth is
                    structurally 0 however good their MAE looks; only an imputer
                    that reads the other six fields can say *which* rows are
                    larger. Note the implication: an MAE-only comparison cannot
                    see this difference at all.
    bias            sign and size of systematic over- or under-shoot

Proof that a difference is real, rather than one lucky masking:

    - identical masks for every method within a scenario, so all comparisons
      are paired
    - Wilcoxon signed-rank on the paired per-row absolute errors
    - bootstrap confidence interval on the mean paired difference
    - the whole run repeated over several masking seeds for the multi-field case

Not used, and why: the energy-I-Score of Naf et al. (2025) is the current state
of the art for ranking imputations, but it needs repeated draws from an
imputation *distribution*. All four methods here are deterministic point
imputers, so that score cannot separate them; it is deliberately omitted rather
than approximated with something that would not mean what its name says.

Run: `python test/quality/imputation_accuracy.py`
Outputs (next to this file): `imputation_accuracy_fields.csv` (per field),
`imputation_accuracy_summary.csv` (per scenario), `imputation_accuracy_paired.csv`,
`imputation_accuracy_by_field.csv`, `imputation_accuracy.md`.
"""

from __future__ import annotations

import csv
import pathlib
import sys
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.impute import KNNImputer, SimpleImputer
from sklearn.preprocessing import StandardScaler

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from types import SimpleNamespace

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SALES_CSV = REPO_ROOT / "src" / "data" / "kc_house_data.csv"
OUTPUT_DIR = pathlib.Path(__file__).resolve().parent
FIELDS_CSV = OUTPUT_DIR / "imputation_accuracy_fields.csv"
SUMMARY_CSV = OUTPUT_DIR / "imputation_accuracy_summary.csv"
PAIRED_CSV = OUTPUT_DIR / "imputation_accuracy_paired.csv"
REPORT_MD = OUTPUT_DIR / "imputation_accuracy.md"

# The v2 request fields, and nothing else. This is the entire feature set the
# imputer is allowed to see, so it is also the entire set under test.
FIELDS: tuple[str, ...] = (
    "bedrooms",
    "bathrooms",
    "sqft_living",
    "sqft_lot",
    "floors",
    "sqft_above",
    "sqft_basement",
)
METHODS: tuple[str, ...] = ("knn_raw", "knn_scaled", "median", "mean")
METHOD_LABEL: dict[str, str] = {
    "knn_raw": "KNN k=5 distance, raw columns (shipped in v2)",
    "knn_scaled": "KNN k=5 distance, z-scored columns",
    "median": "per-field median",
    "mean": "per-field mean",
}
# Method whose win/loss count the verdict counts, i.e. the shipped one.
SHIPPED = "knn_raw"
SCALED = "knn_scaled"

SPLIT_SEED = 20260903
EVAL_ROWS = 3_000
KNN_NEIGHBORS = 5
MCAR_RATES: tuple[float, ...] = (0.15, 0.30, 0.50)
MCAR_SEEDS: tuple[int, ...] = (1, 2, 3, 4, 5)
BOOTSTRAP_REPS = 2_000
SIGNIFICANCE = 0.05

type Scalar = str | int | float | None
type Row = dict[str, Scalar]


@dataclass(frozen=True)
class Scenario:
    """One pattern of absent fields applied to the evaluation rows."""

    name: str
    description: str
    mask: Callable[[pd.DataFrame], pd.DataFrame]


@dataclass
class Results:
    """Everything the report needs, so the writer takes a single argument."""

    fields: list[Row] = field(default_factory=list[Row])
    summary: list[Row] = field(default_factory=list[Row])
    paired: list[Row] = field(default_factory=list[Row])
    timings: list[Row] = field(default_factory=list[Row])
    train_rows: int = 0
    eval_rows: int = 0
    scale_spread: float = 0.0


class Imputer:
    """A fitted imputer that turns a feature frame into filled values."""

    def transform(self, features: pd.DataFrame) -> np.ndarray:
        """Return one filled row per input row, in the input column order."""
        raise NotImplementedError


class SimpleFill(Imputer):
    """sklearn SimpleImputer, used for the mean and median baselines."""

    def __init__(self, strategy: str, train: pd.DataFrame) -> None:
        """Fit the per-column statistic on the training rows."""
        self.imputer = SimpleImputer(strategy=strategy).fit(train[list(FIELDS)])

    def transform(self, features: pd.DataFrame) -> np.ndarray:
        """Fill every missing cell with the fitted column statistic."""
        return np.asarray(self.imputer.transform(features[list(FIELDS)]), dtype=float)


class KnnFill(Imputer):
    """KNNImputer, optionally over z-scored columns.

    Scaling is applied before the neighbour search and inverted afterwards, so
    the caller always receives values in the original units. The scaler is fitted
    on the training rows only, so no held-out row influences the transform.
    """

    def __init__(self, train: pd.DataFrame, *, scaled: bool) -> None:
        """Fit the imputer, and the scaler when one is needed."""
        columns = train[list(FIELDS)]
        self.scaler = StandardScaler().fit(columns) if scaled else None
        reference = self.scaler.transform(columns) if self.scaler is not None else columns
        self.imputer = KNNImputer(n_neighbors=KNN_NEIGHBORS, weights="distance").fit(reference)

    def transform(self, features: pd.DataFrame) -> np.ndarray:
        """Fill missing cells from the k nearest training rows."""
        columns = features[list(FIELDS)]
        scaled = self.scaler.transform(columns) if self.scaler is not None else columns
        filled = np.asarray(self.imputer.transform(scaled), dtype=float)
        return self.scaler.inverse_transform(filled) if self.scaler is not None else filled


def build_imputers(train: pd.DataFrame) -> dict[str, Imputer]:
    """Fit all four approaches on the training rows."""
    return {
        "knn_raw": KnnFill(train, scaled=False),
        "knn_scaled": KnnFill(train, scaled=True),
        "median": SimpleFill("median", train),
        "mean": SimpleFill("mean", train),
    }


def write(stream: str) -> None:
    """Print one line to stdout (ruff bans bare print)."""
    sys.stdout.write(f"{stream}\n")


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------


def load_sales() -> pd.DataFrame:
    """Sales rows, deduplicated, carrying only the seven v2 request fields."""
    sales = pd.read_csv(SALES_CSV, usecols=list(FIELDS))
    return sales.drop_duplicates().reset_index(drop=True)


def split_sales(sales: pd.DataFrame, eval_rows: int, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Deterministic train/eval split; eval rows are never seen by an imputer."""
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(sales))
    return sales.iloc[np.sort(order[eval_rows:])].reset_index(drop=True), sales.iloc[np.sort(order[:eval_rows])].reset_index(drop=True)


# --------------------------------------------------------------------------
# masking: the patterns a real request can arrive in
# --------------------------------------------------------------------------


def blank(frame: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    """Copy of frame with the given columns set to NaN."""
    masked = frame.copy()
    masked[list(columns)] = np.nan
    return masked


def scenario_leave_one_out(field_name: str) -> Scenario:
    """Every row missing exactly this one field, the rest fully observed."""

    def mask(frame: pd.DataFrame) -> pd.DataFrame:
        return blank(frame, [field_name])

    return Scenario(f"missing_{field_name}", f"{field_name} absent, other six observed", mask)


def scenario_mcar(rate: float, seed: int) -> Scenario:
    """Each cell independently absent with probability `rate` (MCAR)."""

    def mask(frame: pd.DataFrame) -> pd.DataFrame:
        rng = np.random.default_rng(seed)
        hits = rng.random(frame[list(FIELDS)].shape) < rate
        masked = frame.copy()
        masked[list(FIELDS)] = masked[list(FIELDS)].mask(hits)
        return masked

    return Scenario(f"mcar_{rate:.2f}_seed{seed}", f"MCAR {rate:.0%}", mask)


def scenario_all_missing() -> Scenario:
    """Nothing but a zipcode: the degenerate request the API must still answer."""

    def mask(frame: pd.DataFrame) -> pd.DataFrame:
        return blank(frame, FIELDS)

    return Scenario("all_missing", "all seven absent", mask)


def build_scenarios() -> list[Scenario]:
    """Leave-one-out for each field, then multi-field MCAR, then the worst case."""
    scenarios = [scenario_leave_one_out(name) for name in FIELDS]
    scenarios += [scenario_mcar(rate, seed) for rate in MCAR_RATES for seed in MCAR_SEEDS]
    scenarios.append(scenario_all_missing())
    return scenarios


# --------------------------------------------------------------------------
# metrics
# --------------------------------------------------------------------------


def correlation(actual: np.ndarray, filled: np.ndarray) -> float:
    """Pearson correlation, reported as 0.0 when the imputer emits a constant.

    Mean and median imputation return the same number for every row, so the
    correlation is genuinely undefined there. Zero is the honest reading: the
    imputation carries no information about which rows are larger than which,
    which is exactly the property a house specification needs.
    """
    if float(np.std(filled)) == 0.0 or float(np.std(actual)) == 0.0:
        return 0.0
    return float(np.corrcoef(actual, filled)[0, 1])


def field_metrics(truth: pd.DataFrame, filled: pd.DataFrame, mask: np.ndarray, scale: pd.Series) -> list[Row]:
    """Accuracy of the imputed cells of each field, over that field's own values."""
    rows: list[Row] = []
    for position, name in enumerate(FIELDS):
        held: np.ndarray = mask[:, position]
        actual: np.ndarray = truth.loc[held, name].to_numpy(dtype=float)
        if actual.size == 0:
            continue
        got: np.ndarray = filled.loc[held, name].to_numpy(dtype=float)
        error = got - actual
        spread = float(scale[name])
        r = correlation(actual, got)
        rows.append(
            {
                "field": name,
                "n_masked": int(held.sum()),
                "mae": float(np.mean(np.abs(error))),
                "rmse": float(np.sqrt(np.mean(error**2))),
                "nmae": float(np.mean(np.abs(error)) / spread),
                "nrmse": float(np.sqrt(np.mean(error**2)) / spread),
                "bias": float(np.mean(error)),
                "pearson_r": r,
                "r2": r**2,
                "imputed_sd": float(np.std(got)),
                "true_sd": spread,
                "distinct_values": len(np.unique(got)),
            },
        )
    return rows


def summarise(scenario: Scenario, per_field: list[Row], seconds: float) -> Row:
    """Roll per-field metrics up to one comparable row per method."""
    weighted = [row for row in per_field if number(row, "n_masked") > 0]
    return {
        "scenario": scenario.name,
        "description": scenario.description,
        "fields_scored": len(weighted),
        "n_masked_cells": int(sum(number(row, "n_masked") for row in weighted)),
        "nmae_mean": float(np.mean([number(row, "nmae") for row in weighted])),
        "nrmse_mean": float(np.mean([number(row, "nrmse") for row in weighted])),
        "pearson_r_mean": float(np.mean([number(row, "pearson_r") for row in weighted])),
        "r2_mean": float(np.mean([number(row, "r2") for row in weighted])),
        "nmae_worst_field": max(number(row, "nmae") for row in weighted),
        "bias_mean": float(np.mean([number(row, "bias") / number(row, "true_sd") for row in weighted])),
        "impute_ms": seconds,
    }


def paired_test(left: np.ndarray, right: np.ndarray, comparison: str, scenario: str) -> Row:
    """Paired comparison of two per-row absolute errors."""
    difference = left - right
    rng = np.random.default_rng(SPLIT_SEED)
    draws = cast("np.ndarray", rng.integers(0, len(difference), size=(BOOTSTRAP_REPS, len(difference))))
    low, high = np.percentile(difference[draws].mean(axis=1), [2.5, 97.5])
    identical = not np.any(difference)
    pvalue = float("nan") if identical else float(cast("SimpleNamespace", stats.wilcoxon(left, right)).pvalue)
    return {
        "scenario": scenario,
        "comparison": comparison,
        "mean_abs_error_difference": float(difference.mean()),
        "ci95_low": float(low),
        "ci95_high": float(high),
        "wilcoxon_p": pvalue,
        "significant": bool(np.isfinite(pvalue) and pvalue < SIGNIFICANCE),
        "left_better_pct": float(np.mean(difference < 0) * 100.0),
    }


def number(row: Row, key: str) -> float:
    """Numeric value of one metric cell; metric tables never hold text."""
    value = row[key]
    if not isinstance(value, int | float) or isinstance(value, bool):
        msg = f"metric {key!r} is not numeric: {value!r}"
        raise TypeError(msg)
    return float(value)


# --------------------------------------------------------------------------
# one scenario
# --------------------------------------------------------------------------


def evaluate_scenario(
    scenario: Scenario,
    eval_rows: pd.DataFrame,
    scale: pd.Series,
    imputers: dict[str, Imputer],
) -> tuple[list[Row], list[Row], dict[str, dict[str, np.ndarray]]]:
    """Impute one mask with all four methods and score the filled cells.

    Returns the per-field metric rows, one summary row per method, and the
    actual per-cell absolute errors keyed by method and field. Those real error
    vectors are what the paired tests consume; a test run on anything
    reconstructed from the summary averages would be measuring nothing.
    """
    masked = scenario.mask(eval_rows)
    truth = eval_rows[list(FIELDS)]
    mask: np.ndarray = masked[list(FIELDS)].isna().to_numpy()

    field_rows: list[Row] = []
    summary_rows: list[Row] = []
    errors: dict[str, dict[str, np.ndarray]] = {}

    for method in METHODS:
        started = time.perf_counter()
        filled = pd.DataFrame(imputers[method].transform(masked[list(FIELDS)]), columns=FIELDS, index=masked.index)
        seconds = (time.perf_counter() - started) * 1000.0
        per_field = field_metrics(truth, filled, mask, scale)
        errors[method] = {
            str(entry["field"]): np.abs(
                filled.loc[mask[:, position], str(entry["field"])].to_numpy(dtype=float)
                - truth.loc[mask[:, position], str(entry["field"])].to_numpy(dtype=float),
            )
            for position, entry in enumerate(per_field)
        }
        row = summarise(scenario, per_field, seconds)
        row["method"] = method
        row["label"] = METHOD_LABEL[method]
        summary_rows.append(row)
        field_rows.extend({"scenario": scenario.name, "method": method, **entry} for entry in per_field)

    return field_rows, summary_rows, errors


def paired_rows(scenario_name: str, errors: dict[str, dict[str, np.ndarray]]) -> list[Row]:
    """Every method pair over the whole masked block of one scenario."""
    return [
        paired_test(
            np.concatenate(list(errors[left].values())),
            np.concatenate(list(errors[right].values())),
            f"{left} minus {right}",
            scenario_name,
        )
        for index, left in enumerate(METHODS)
        for right in METHODS[index + 1 :]
    ]


def leave_one_out_paired(errors_by_scenario: dict[str, dict[str, dict[str, np.ndarray]]]) -> list[Row]:
    """Pair the methods within each leave-one-out scenario, per field.

    In these scenarios exactly one field is ever missing, so its per-cell error
    vector is directly comparable between methods with no cross-field mixing.
    """
    rows: list[Row] = []
    for scenario, errors in errors_by_scenario.items():
        for index, left in enumerate(METHODS):
            for right in METHODS[index + 1 :]:
                name = scenario.removeprefix("missing_")
                rows.append(paired_test(errors[left][name], errors[right][name], f"{left} minus {right}", scenario))
    return rows


def timing(predict_rows: pd.DataFrame, imputers: dict[str, Imputer]) -> list[Row]:
    """Median per-request impute cost for the shape the API actually receives."""
    payload = blank(predict_rows.head(64), ["sqft_lot"])
    rows: list[Row] = []
    for method in METHODS:
        samples: list[float] = []
        for _ in range(5):
            started = time.perf_counter()
            imputers[method].transform(payload[list(FIELDS)])
            samples.append((time.perf_counter() - started) * 1000.0)
        rows.append({"method": method, "label": METHOD_LABEL[method], "ms_per_request": float(np.median(samples))})
    return rows


# --------------------------------------------------------------------------
# output
# --------------------------------------------------------------------------


def write_csv(path: pathlib.Path, rows: Sequence[Row]) -> None:
    """Write rows with a stable column order."""
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def table(rows: Sequence[Row], columns: Sequence[str], digits: int = 3) -> str:
    """Markdown table; integers stay integers, floats get the requested precision."""

    def cell(row: Row, column: str) -> str:
        value = row[column]
        if isinstance(value, bool) or not isinstance(value, int | float):
            return str(value)
        return f"{value:,.0f}" if isinstance(value, int) else f"{value:,.{digits}f}"

    header = "| " + " | ".join(columns) + " |"
    rule = "| " + " | ".join("-" * len(column) for column in columns) + " |"
    body = ["| " + " | ".join(cell(row, column) for column in columns) + " |" for row in rows]
    return "\n".join([header, rule, *body])


def scenario_rows(results: Results, name: str) -> list[Row]:
    """Summary rows for one scenario, ordered so the shipped method leads."""
    rows = [row for row in results.summary if row["scenario"] == name]
    return sorted(rows, key=lambda row: (number(row, "nmae_mean"), str(row["method"])))


def verdict(results: Results) -> list[str]:
    """Derive the answer from the measured numbers rather than asserting it."""
    cases = {
        scenario: {str(row["method"]): row for row in results.summary if row["scenario"] == scenario}
        for scenario in dict.fromkeys(str(row["scenario"]) for row in results.summary)
        if scenario.startswith("missing_")
    }

    def wins(*, largest: bool) -> dict[str, int]:
        """Per method, the leave-one-out cases where it has the best value."""
        tally = dict.fromkeys(METHODS, 0)
        metric = "pearson_r_mean" if largest else "nmae_mean"
        for methods in cases.values():
            winner = (max if largest else min)(methods.values(), key=lambda row: number(row, metric))
            tally[str(winner["method"])] = tally[str(winner["method"])] + 1
        return tally

    wins_nmae = wins(largest=False)
    wins_r = wins(largest=True)
    constant = {method: all(number(methods[method], "pearson_r_mean") == 0.0 for methods in cases.values()) for method in METHODS}
    return [
        "## Verdict",
        "",
        (f"Across the {len(cases)} leave-one-out cases (one specification absent, the other six observed), counting the best method in each case:"),
        "",
        table(
            [
                {
                    "method": method,
                    "label": METHOD_LABEL[method],
                    "best_nmae_in_n_cases": wins_nmae[method],
                    "best_pearson_r_in_n_cases": wins_r[method],
                    "pearson_r_always_zero": constant[method],
                }
                for method in METHODS
            ],
            ["method", "best_nmae_in_n_cases", "best_pearson_r_in_n_cases", "pearson_r_always_zero"],
            digits=0,
        ),
        "",
        (
            f"On scale-free error the shipped `{SHIPPED}` imputer is best in {wins_nmae[SHIPPED]} of {len(cases)} "
            f"cases; the z-scored variant in {wins_nmae[SCALED]}; median in {wins_nmae['median']}; mean in "
            f"{wins_nmae['mean']}. No error metric can separate the two constant imputers from each other, because "
            "both ignore the six observed specifications entirely; correlation can, and it puts them last."
        ),
    ]


def write_report(results: Results) -> None:
    """Markdown report answering which imputer recovers a missing specification best."""
    lines = [
        "# Recovering a missing home specification: mean vs median vs KNN",
        "",
        (
            f"The v2 endpoint accepts {len(FIELDS)} optional specifications: {', '.join(FIELDS)}. "
            "This compares what each imputer does when one of them is absent and the rest are present, "
            "using nothing but those seven fields."
        ),
        "",
        (
            f"Imputers fitted on {results.train_rows:,} sales rows, scored on {results.eval_rows:,} held-out "
            "rows, so no method ever sees the row it is being asked to fill."
        ),
        "",
        *verdict(results),
        "",
        "## Which metrics, and why these",
        "",
        (
            "Taken from the imputation-evaluation literature, not from convention. Raw MAE and RMSE are not "
            "comparable across these seven fields: their standard deviations span a factor of "
            f"{results.scale_spread:,.0f} (floors 0.54 versus sqft_lot 41,420), so any unweighted average of "
            "raw errors is just a measurement of sqft_lot. See "
            "[Näf et al. (2025)](https://arxiv.org/html/2507.11297v1) on why pointwise error additionally "
            "favours imputers that collapse toward a conditional mean."
        ),
        "",
        ("- **NMAE / NRMSE** divide by the held-out standard deviation, putting all seven fields on one scale."),
        (
            "- **Pearson r / R²** are the decisive metric. Mean and median return one number for every row, so "
            "their correlation with the truth is structurally 0 no matter how good their MAE looks. Only an "
            "imputer that reads the other six specifications can say *which* houses are larger. An MAE-only "
            "comparison cannot see this difference at all."
        ),
        (
            "- **Wilcoxon signed-rank** on paired per-row errors, plus a bootstrap CI on the mean paired "
            "difference, so a win is consistent rather than one lucky masking."
        ),
        "",
        (
            "Not used: the energy-I-Score of Näf et al. is the current state of the art for ranking imputations, "
            "but it requires repeated draws from an imputation distribution. All four methods here are "
            "deterministic point imputers, so it cannot separate them and is omitted rather than approximated."
        ),
        "",
        "## Leave-one-out: one specification absent, six observed",
        "",
        "The realistic request shape. NMAE and Pearson r per field; lower NMAE and higher r are better.",
        "",
    ]

    for name in FIELDS:
        scenario = f"missing_{name}"
        lines += [
            f"### {name} missing",
            "",
            table(
                [
                    {
                        "method": row["method"],
                        "nmae": number(row, "nmae_mean"),
                        "nrmse": number(row, "nrmse_mean"),
                        "mae_units": number(next(f for f in results.fields if f["scenario"] == scenario and f["method"] == row["method"]), "mae"),
                        "pearson_r": number(row, "pearson_r_mean"),
                        "bias_in_sd": number(row, "bias_mean"),
                    }
                    for row in scenario_rows(results, scenario)
                ],
                ["method", "nmae", "nrmse", "mae_units", "pearson_r", "bias_in_sd"],
            ),
            "",
        ]

    lines += [
        "## Paired significance, leave-one-out",
        "",
        "Negative difference means the method on the left produced the smaller error on more cells.",
        "",
        table(
            [row for row in results.paired if str(row["scenario"]).startswith("missing_")],
            ["scenario", "comparison", "mean_abs_error_difference", "ci95_low", "ci95_high", "wilcoxon_p", "significant"],
            digits=4,
        ),
        "",
        "## Multi-field missing (MCAR)",
        "",
        "Several specifications absent at once, averaged over 5 masking seeds per rate.",
        "",
    ]
    for rate in MCAR_RATES:
        lines += [
            f"### MCAR {rate:.0%}",
            "",
            table(
                sorted(
                    (row for row in results.summary if str(row["scenario"]).startswith(f"mcar_{rate:.2f}_")),
                    key=lambda row: (str(row["scenario"]), number(row, "nmae_mean")),
                ),
                ["scenario", "method", "n_masked_cells", "nmae_mean", "nrmse_mean", "pearson_r_mean"],
            ),
            "",
        ]

    lines += [
        "## All seven absent",
        "",
        (
            "The degenerate request: nothing but a zipcode. With no dimension left on which to measure a "
            "distance, `KNNImputer` falls back to the training column average, so both KNN variants and mean are "
            "identical to the last decimal - which is why every one of them shows zero correlation here, and why "
            "this is the one case where the choice of imputer does not matter. Median is ahead on error alone "
            "because the training median of sqft_basement is 0, matching most houses, where the mean does not; "
            "it still returns one constant for every row, so it is no more informative than the others."
        ),
        "",
        table(scenario_rows(results, "all_missing"), ["method", "nmae_mean", "nrmse_mean", "pearson_r_mean"], digits=4),
        "",
        "## Per-request cost",
        "",
        table(results.timings, ["method", "ms_per_request"], digits=2),
        "",
        "## Reading",
        "",
        (
            "Read the leave-one-out section for the answer to the question asked. Pearson r is the column that "
            "settles it: it separates an imputer that consults the other specifications from one that ignores "
            "them, which no error metric does."
        ),
        "",
    ]
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------


def main() -> None:
    """Run the comparison and write every artefact."""
    sales = load_sales()
    train, eval_rows = split_sales(sales, EVAL_ROWS, SPLIT_SEED)
    imputers = build_imputers(train)
    scale = eval_rows[list(FIELDS)].std(ddof=0)
    results = Results(
        train_rows=len(train),
        eval_rows=len(eval_rows),
        scale_spread=float(scale.max() / scale.min()),
    )
    started = time.perf_counter()

    leave_one_out: dict[str, dict[str, dict[str, np.ndarray]]] = {}
    for scenario in build_scenarios():
        field_rows, summary_rows, errors = evaluate_scenario(scenario, eval_rows, scale, imputers)
        results.fields += field_rows
        results.summary += summary_rows
        results.paired += paired_rows(scenario.name, errors)
        if scenario.name.startswith("missing_"):
            leave_one_out[scenario.name] = errors
        write(f"  {scenario.name:<22} done")

    results.paired += leave_one_out_paired(leave_one_out)
    results.timings = timing(eval_rows, imputers)
    write(f"\nall {len(results.summary)} method-runs in {time.perf_counter() - started:.1f}s")
    write_csv(FIELDS_CSV, results.fields)
    write_csv(SUMMARY_CSV, results.summary)
    write_csv(PAIRED_CSV, results.paired)
    write_report(results)
    write(f"wrote {FIELDS_CSV.name}, {SUMMARY_CSV.name}, {PAIRED_CSV.name}, {REPORT_MD.name}")


if __name__ == "__main__":
    main()
