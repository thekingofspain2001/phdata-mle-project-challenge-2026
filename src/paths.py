"""Single source of truth for artifact and data file locations.

Both the API and the training script resolve their files from here, anchored
to this file's directory rather than the process CWD, so neither depends on
where it was launched from.

The layout is the same in a checkout (``<repo>/src/``) and in the model image
(``/app/``): ``paths.py`` sits beside ``data/`` and ``model/``.
"""

import pathlib

# ponytail: anchored to package file, CWD-independent; no symlinks needed
ROOT = pathlib.Path(__file__).resolve().parent

MODEL_PATH = ROOT / "model" / "model.pkl"
FEATURES_PATH = ROOT / "model" / "model_features.json"
DEMOGRAPHICS_PATH = ROOT / "data" / "zipcode_demographics.csv"
SALES_PATH = ROOT / "data" / "kc_house_data.csv"
UNSEEN_PATH = ROOT / "data" / "future_unseen_examples.csv"
