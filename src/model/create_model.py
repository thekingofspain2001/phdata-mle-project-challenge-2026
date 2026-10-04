"""Train a home price model and export artifacts."""

import json
import pickle
from typing import cast

import numpy as np
import pandas as pd
from sklearn import model_selection, neighbors, pipeline, preprocessing
from sklearn.pipeline import Pipeline

from paths import DEMOGRAPHICS_PATH, FEATURES_PATH, MODEL_PATH, SALES_PATH

# List of columns (subset) that will be taken from home sale data
SALES_COLUMN_SELECTION = [
    "price",
    "bedrooms",
    "bathrooms",
    "sqft_living",
    "sqft_lot",
    "floors",
    "sqft_above",
    "sqft_basement",
    "zipcode",
]

# Updated to use modern X | Y union and native lowercase collections
type DataFrameOrArray = pd.DataFrame | np.ndarray | pd.Series
type SplitFrames = tuple[
    DataFrameOrArray,
    DataFrameOrArray,
    DataFrameOrArray,
    DataFrameOrArray,
]
type RegressorPipeline = Pipeline


def load_data(
    sales_path: str,
    demographics_path: str,
    sales_column_selection: list[str],
) -> tuple[pd.DataFrame, pd.Series]:
    """Load the target and feature data by merging sales and demographics.

    Args:
        sales_path: path to CSV file with home sale data
        demographics_path: path to CSV file with home sale data
        sales_column_selection: list of columns from sales data to be used as
            features

    Returns:
        Tuple containing two elements: a DataFrame and a Series of the same
        length.  The DataFrame contains features for machine learning, the
        series contains the target variable (home sale price).

    """
    data = pd.read_csv(
        sales_path,
        usecols=sales_column_selection,
        dtype={"zipcode": str},
    )
    demographics = pd.read_csv(
        demographics_path,
        dtype={"zipcode": str},
    )

    merged_data = data.merge(demographics, how="left", on="zipcode").drop(
        columns="zipcode",
    )
    # Remove the target variable from the dataframe, features will remain
    y = merged_data.pop("price")
    x = merged_data

    return x, y


def main() -> None:
    """Load data, train model, and export artifacts."""
    x, y = load_data(str(SALES_PATH), str(DEMOGRAPHICS_PATH), SALES_COLUMN_SELECTION)

    # Silenced Pyright's partial unknown on internal library return signatures
    split: SplitFrames = cast(
        "SplitFrames",
        tuple(model_selection.train_test_split(x, y, random_state=42)),  # type: ignore[reportUnknownFunctionType]
    )
    x_train, _x_test, y_train, _y_test = split

    # Direct functional calls keep compilation trace legible
    model: RegressorPipeline = pipeline.make_pipeline(  # type: ignore[reportUnknownFunctionType]
        preprocessing.RobustScaler(),
        neighbors.KNeighborsRegressor(),
    ).fit(x_train, y_train)  # type: ignore[reportUnknownMemberType]

    MODEL_PATH.parent.mkdir(exist_ok=True)

    # Output model artifacts: pickled model and JSON list of features
    with MODEL_PATH.open("wb") as model_file:
        pickle.dump(model, model_file)
    with FEATURES_PATH.open("w") as features_file:
        # Cast to pd.DataFrame cleanly handles column checking
        json.dump(list(cast("pd.DataFrame", x_train).columns), features_file)


if __name__ == "__main__":
    main()
