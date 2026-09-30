# Glossary — Imputation Experiment

Terms as used in `notebooks/imputation_experiment.ipynb`

## MCAR | Missing Completely At Random

 Synthetic missingness pattern: values removed uniformly at random (`missing_rate=0.15`), independent of any feature values.

## Imputers

### Mean imputation | Baseline method (`sklearn.impute.SimpleImputer`)

 fill each column with its mean.

### Median imputation | Baseline method (`sklearn.impute.SimpleImputer`)

 fill each column with its median.

### KNN | k-Nearest Neighbors

New imputation method under test: fills a missing value from the `n_neighbors=5` closest complete rows, distance-weighted (`sklearn.impute.KNNImputer`).

## Metrics

### RMSE | Root Mean Squared Error  `sqrt(mean((original − imputed)²))` over masked cells per column. Penalizes large errors; same unit as the feature. |

### MAE | Mean Absolute Error `mean(\|original − imputed\|)`

over masked cells per column. Average error magnitude, robust to outliers. |

### Avg_RMSE / Avg_MAE | — | Unweighted mean of per-column RMSE / MAE. Caveat (§7): dominated by large-scale features (`sqft_lot`, `sqft_lot15`); not scale-normalized. |
