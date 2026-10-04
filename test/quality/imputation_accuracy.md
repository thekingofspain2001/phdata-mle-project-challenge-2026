# Recovering a missing home specification: mean vs median vs KNN

The v2 endpoint accepts 7 optional specifications: bedrooms, bathrooms, sqft_living, sqft_lot, floors, sqft_above, sqft_basement. This compares what each imputer does when one of them is absent and the rest are present, using nothing but those seven fields.

Imputers fitted on 18,270 sales rows, scored on 3,000 held-out rows, so no method ever sees the row it is being asked to fill.

## Verdict

Across the 7 leave-one-out cases (one specification absent, the other six observed), counting the best method in each case:

| method | best_nmae_in_n_cases | best_pearson_r_in_n_cases | pearson_r_always_zero |
| ------ | -------------------- | ------------------------- | --------------------- |
| knn_raw | 0 | 1 | False |
| knn_scaled | 6 | 6 | False |
| median | 1 | 0 | True |
| mean | 0 | 0 | False |

On scale-free error the shipped `knn_raw` imputer is best in 0 of 7 cases; the z-scored variant in 6; median in 1; mean in 0. No error metric can separate the two constant imputers from each other, because both ignore the six observed specifications entirely; correlation can, and it puts them last.

## Which metrics, and why these

Taken from the imputation-evaluation literature, not from convention. Raw MAE and RMSE are not comparable across these seven fields: their standard deviations span a factor of 80,012 (floors 0.54 versus sqft_lot 41,420), so any unweighted average of raw errors is just a measurement of sqft_lot. See [Näf et al. (2025)](https://arxiv.org/html/2507.11297v1) on why pointwise error additionally favours imputers that collapse toward a conditional mean.

- **NMAE / NRMSE** divide by the held-out standard deviation, putting all seven fields on one scale.
- **Pearson r / R²** are the decisive metric. Mean and median return one number for every row, so their correlation with the truth is structurally 0 no matter how good their MAE looks. Only an imputer that reads the other six specifications can say *which* houses are larger. An MAE-only comparison cannot see this difference at all.
- **Wilcoxon signed-rank** on paired per-row errors, plus a bootstrap CI on the mean paired difference, so a win is consistent rather than one lucky masking.

Not used: the energy-I-Score of Näf et al. is the current state of the art for ranking imputations, but it requires repeated draws from an imputation distribution. All four methods here are deterministic point imputers, so it cannot separate them and is omitted rather than approximated.

## Leave-one-out: one specification absent, six observed

The realistic request shape. NMAE and Pearson r per field; lower NMAE and higher r are better.

### bedrooms missing

| method | nmae | nrmse | mae_units | pearson_r | bias_in_sd |
| ------ | ---- | ----- | --------- | --------- | ---------- |
| knn_scaled | 0.571 | 0.797 | 0.514 | 0.623 | 0.004 |
| knn_raw | 0.611 | 0.838 | 0.549 | 0.579 | 0.007 |
| median | 0.731 | 1.082 | 0.658 | 0.000 | -0.413 |
| mean | 0.806 | 1.000 | 0.726 | 0.000 | 0.006 |

### bathrooms missing

| method | nmae | nrmse | mae_units | pearson_r | bias_in_sd |
| ------ | ---- | ----- | --------- | --------- | ---------- |
| knn_scaled | 0.435 | 0.617 | 0.328 | 0.792 | 0.017 |
| knn_raw | 0.488 | 0.671 | 0.367 | 0.747 | -0.007 |
| median | 0.791 | 1.015 | 0.595 | 0.000 | 0.175 |
| mean | 0.799 | 1.000 | 0.602 | -0.000 | 0.003 |

### sqft_living missing

| method | nmae | nrmse | mae_units | pearson_r | bias_in_sd |
| ------ | ---- | ----- | --------- | --------- | ---------- |
| knn_scaled | 0.048 | 0.128 | 43.048 | 0.992 | -0.014 |
| knn_raw | 0.073 | 0.241 | 65.441 | 0.972 | -0.021 |
| median | 0.755 | 1.015 | 677.067 | 0.000 | -0.172 |
| mean | 0.768 | 1.000 | 689.124 | 0.000 | 0.018 |

### sqft_lot missing

| method | nmae | nrmse | mae_units | pearson_r | bias_in_sd |
| ------ | ---- | ----- | --------- | --------- | ---------- |
| median | 0.243 | 1.016 | 10,603.236 | 0.000 | -0.179 |
| knn_raw | 0.314 | 1.015 | 13,711.603 | 0.196 | -0.029 |
| mean | 0.327 | 1.000 | 14,280.863 | -0.000 | -0.007 |
| knn_scaled | 0.337 | 1.111 | 14,730.149 | 0.120 | 0.001 |

### floors missing

| method | nmae | nrmse | mae_units | pearson_r | bias_in_sd |
| ------ | ---- | ----- | --------- | --------- | ---------- |
| knn_scaled | 0.318 | 0.579 | 0.174 | 0.819 | -0.014 |
| knn_raw | 0.345 | 0.586 | 0.188 | 0.813 | -0.008 |
| median | 0.905 | 1.000 | 0.494 | 0.000 | -0.001 |
| mean | 0.905 | 1.000 | 0.494 | 0.000 | -0.010 |

### sqft_above missing

| method | nmae | nrmse | mae_units | pearson_r | bias_in_sd |
| ------ | ---- | ----- | --------- | --------- | ---------- |
| knn_scaled | 0.056 | 0.146 | 45.274 | 0.990 | -0.009 |
| knn_raw | 0.072 | 0.224 | 58.544 | 0.976 | -0.008 |
| median | 0.741 | 1.035 | 603.349 | 0.000 | -0.268 |
| mean | 0.779 | 1.000 | 634.694 | 0.000 | 0.009 |

### sqft_basement missing

| method | nmae | nrmse | mae_units | pearson_r | bias_in_sd |
| ------ | ---- | ----- | --------- | --------- | ---------- |
| knn_scaled | 0.078 | 0.209 | 34.002 | 0.978 | -0.018 |
| knn_raw | 0.099 | 0.302 | 42.889 | 0.953 | -0.014 |
| median | 0.659 | 1.198 | 286.184 | 0.000 | -0.659 |
| mean | 0.834 | 1.000 | 361.929 | 0.000 | 0.020 |

## Paired significance, leave-one-out

Negative difference means the method on the left produced the smaller error on more cells.

| scenario | comparison | mean_abs_error_difference | ci95_low | ci95_high | wilcoxon_p | significant |
| -------- | ---------- | ------------------------- | -------- | --------- | ---------- | ----------- |
| missing_bedrooms | knn_raw minus knn_scaled | 0.0353 | 0.0194 | 0.0511 | 0.0000 | True |
| missing_bedrooms | knn_raw minus median | -0.1086 | -0.1338 | -0.0836 | 0.0000 | True |
| missing_bedrooms | knn_raw minus mean | -0.1762 | -0.1948 | -0.1572 | 0.0000 | True |
| missing_bedrooms | knn_scaled minus median | -0.1439 | -0.1685 | -0.1206 | 0.0000 | True |
| missing_bedrooms | knn_scaled minus mean | -0.2114 | -0.2302 | -0.1936 | 0.0000 | True |
| missing_bedrooms | median minus mean | -0.0675 | -0.0801 | -0.0542 | 0.0000 | True |
| missing_bathrooms | knn_raw minus knn_scaled | nan | nan | nan | nan | False |
| missing_bathrooms | knn_raw minus median | nan | nan | nan | nan | False |
| missing_bathrooms | knn_raw minus mean | nan | nan | nan | nan | False |
| missing_bathrooms | knn_scaled minus median | nan | nan | nan | nan | False |
| missing_bathrooms | knn_scaled minus mean | nan | nan | nan | nan | False |
| missing_bathrooms | median minus mean | nan | nan | nan | nan | False |
| missing_sqft_living | knn_raw minus knn_scaled | nan | nan | nan | nan | False |
| missing_sqft_living | knn_raw minus median | nan | nan | nan | nan | False |
| missing_sqft_living | knn_raw minus mean | nan | nan | nan | nan | False |
| missing_sqft_living | knn_scaled minus median | nan | nan | nan | nan | False |
| missing_sqft_living | knn_scaled minus mean | nan | nan | nan | nan | False |
| missing_sqft_living | median minus mean | nan | nan | nan | nan | False |
| missing_sqft_lot | knn_raw minus knn_scaled | nan | nan | nan | nan | False |
| missing_sqft_lot | knn_raw minus median | nan | nan | nan | nan | False |
| missing_sqft_lot | knn_raw minus mean | nan | nan | nan | nan | False |
| missing_sqft_lot | knn_scaled minus median | nan | nan | nan | nan | False |
| missing_sqft_lot | knn_scaled minus mean | nan | nan | nan | nan | False |
| missing_sqft_lot | median minus mean | nan | nan | nan | nan | False |
| missing_floors | knn_raw minus knn_scaled | nan | nan | nan | nan | False |
| missing_floors | knn_raw minus median | nan | nan | nan | nan | False |
| missing_floors | knn_raw minus mean | nan | nan | nan | nan | False |
| missing_floors | knn_scaled minus median | nan | nan | nan | nan | False |
| missing_floors | knn_scaled minus mean | nan | nan | nan | nan | False |
| missing_floors | median minus mean | nan | nan | nan | nan | False |
| missing_sqft_above | knn_raw minus knn_scaled | nan | nan | nan | nan | False |
| missing_sqft_above | knn_raw minus median | nan | nan | nan | nan | False |
| missing_sqft_above | knn_raw minus mean | nan | nan | nan | nan | False |
| missing_sqft_above | knn_scaled minus median | nan | nan | nan | nan | False |
| missing_sqft_above | knn_scaled minus mean | nan | nan | nan | nan | False |
| missing_sqft_above | median minus mean | nan | nan | nan | nan | False |
| missing_sqft_basement | knn_raw minus knn_scaled | nan | nan | nan | nan | False |
| missing_sqft_basement | knn_raw minus median | nan | nan | nan | nan | False |
| missing_sqft_basement | knn_raw minus mean | nan | nan | nan | nan | False |
| missing_sqft_basement | knn_scaled minus median | nan | nan | nan | nan | False |
| missing_sqft_basement | knn_scaled minus mean | nan | nan | nan | nan | False |
| missing_sqft_basement | median minus mean | nan | nan | nan | nan | False |
| missing_bedrooms | knn_raw minus knn_scaled | 0.0353 | 0.0194 | 0.0511 | 0.0000 | True |
| missing_bedrooms | knn_raw minus median | -0.1086 | -0.1338 | -0.0836 | 0.0000 | True |
| missing_bedrooms | knn_raw minus mean | -0.1762 | -0.1948 | -0.1572 | 0.0000 | True |
| missing_bedrooms | knn_scaled minus median | -0.1439 | -0.1685 | -0.1206 | 0.0000 | True |
| missing_bedrooms | knn_scaled minus mean | -0.2114 | -0.2302 | -0.1936 | 0.0000 | True |
| missing_bedrooms | median minus mean | -0.0675 | -0.0801 | -0.0542 | 0.0000 | True |
| missing_bathrooms | knn_raw minus knn_scaled | nan | nan | nan | nan | False |
| missing_bathrooms | knn_raw minus median | nan | nan | nan | nan | False |
| missing_bathrooms | knn_raw minus mean | nan | nan | nan | nan | False |
| missing_bathrooms | knn_scaled minus median | nan | nan | nan | nan | False |
| missing_bathrooms | knn_scaled minus mean | nan | nan | nan | nan | False |
| missing_bathrooms | median minus mean | nan | nan | nan | nan | False |
| missing_sqft_living | knn_raw minus knn_scaled | nan | nan | nan | nan | False |
| missing_sqft_living | knn_raw minus median | nan | nan | nan | nan | False |
| missing_sqft_living | knn_raw minus mean | nan | nan | nan | nan | False |
| missing_sqft_living | knn_scaled minus median | nan | nan | nan | nan | False |
| missing_sqft_living | knn_scaled minus mean | nan | nan | nan | nan | False |
| missing_sqft_living | median minus mean | nan | nan | nan | nan | False |
| missing_sqft_lot | knn_raw minus knn_scaled | nan | nan | nan | nan | False |
| missing_sqft_lot | knn_raw minus median | nan | nan | nan | nan | False |
| missing_sqft_lot | knn_raw minus mean | nan | nan | nan | nan | False |
| missing_sqft_lot | knn_scaled minus median | nan | nan | nan | nan | False |
| missing_sqft_lot | knn_scaled minus mean | nan | nan | nan | nan | False |
| missing_sqft_lot | median minus mean | nan | nan | nan | nan | False |
| missing_floors | knn_raw minus knn_scaled | nan | nan | nan | nan | False |
| missing_floors | knn_raw minus median | nan | nan | nan | nan | False |
| missing_floors | knn_raw minus mean | nan | nan | nan | nan | False |
| missing_floors | knn_scaled minus median | nan | nan | nan | nan | False |
| missing_floors | knn_scaled minus mean | nan | nan | nan | nan | False |
| missing_floors | median minus mean | nan | nan | nan | nan | False |
| missing_sqft_above | knn_raw minus knn_scaled | nan | nan | nan | nan | False |
| missing_sqft_above | knn_raw minus median | nan | nan | nan | nan | False |
| missing_sqft_above | knn_raw minus mean | nan | nan | nan | nan | False |
| missing_sqft_above | knn_scaled minus median | nan | nan | nan | nan | False |
| missing_sqft_above | knn_scaled minus mean | nan | nan | nan | nan | False |
| missing_sqft_above | median minus mean | nan | nan | nan | nan | False |
| missing_sqft_basement | knn_raw minus knn_scaled | nan | nan | nan | nan | False |
| missing_sqft_basement | knn_raw minus median | nan | nan | nan | nan | False |
| missing_sqft_basement | knn_raw minus mean | nan | nan | nan | nan | False |
| missing_sqft_basement | knn_scaled minus median | nan | nan | nan | nan | False |
| missing_sqft_basement | knn_scaled minus mean | nan | nan | nan | nan | False |
| missing_sqft_basement | median minus mean | nan | nan | nan | nan | False |

## Multi-field missing (MCAR)

Several specifications absent at once, averaged over 5 masking seeds per rate.

### MCAR 15%

| scenario | method | n_masked_cells | nmae_mean | nrmse_mean | pearson_r_mean |
| -------- | ------ | -------------- | --------- | ---------- | -------------- |
| mcar_0.15_seed1 | knn_scaled | 3,214 | 0.330 | 0.787 | 0.709 |
| mcar_0.15_seed1 | knn_raw | 3,214 | 0.359 | 0.738 | 0.699 |
| mcar_0.15_seed1 | median | 3,214 | 0.702 | 1.137 | 0.000 |
| mcar_0.15_seed1 | mean | 3,214 | 0.755 | 1.084 | 0.000 |
| mcar_0.15_seed2 | knn_scaled | 3,194 | 0.317 | 0.614 | 0.722 |
| mcar_0.15_seed2 | knn_raw | 3,194 | 0.350 | 0.648 | 0.703 |
| mcar_0.15_seed2 | median | 3,194 | 0.685 | 1.033 | 0.000 |
| mcar_0.15_seed2 | mean | 3,194 | 0.750 | 0.984 | 0.000 |
| mcar_0.15_seed3 | knn_scaled | 3,192 | 0.305 | 0.573 | 0.744 |
| mcar_0.15_seed3 | knn_raw | 3,192 | 0.342 | 0.613 | 0.713 |
| mcar_0.15_seed3 | median | 3,192 | 0.688 | 1.005 | 0.000 |
| mcar_0.15_seed3 | mean | 3,192 | 0.746 | 0.951 | 0.000 |
| mcar_0.15_seed4 | knn_scaled | 3,210 | 0.306 | 0.601 | 0.736 |
| mcar_0.15_seed4 | knn_raw | 3,210 | 0.340 | 0.611 | 0.713 |
| mcar_0.15_seed4 | median | 3,210 | 0.692 | 1.008 | 0.000 |
| mcar_0.15_seed4 | mean | 3,210 | 0.744 | 0.952 | -0.000 |
| mcar_0.15_seed5 | knn_scaled | 3,180 | 0.315 | 0.607 | 0.716 |
| mcar_0.15_seed5 | knn_raw | 3,180 | 0.345 | 0.634 | 0.689 |
| mcar_0.15_seed5 | median | 3,180 | 0.693 | 1.009 | 0.000 |
| mcar_0.15_seed5 | mean | 3,180 | 0.750 | 0.959 | -0.000 |

### MCAR 30%

| scenario | method | n_masked_cells | nmae_mean | nrmse_mean | pearson_r_mean |
| -------- | ------ | -------------- | --------- | ---------- | -------------- |
| mcar_0.30_seed1 | knn_scaled | 6,366 | 0.382 | 0.769 | 0.681 |
| mcar_0.30_seed1 | knn_raw | 6,366 | 0.413 | 0.773 | 0.670 |
| mcar_0.30_seed1 | median | 6,366 | 0.703 | 1.117 | 0.000 |
| mcar_0.30_seed1 | mean | 6,366 | 0.760 | 1.068 | 0.000 |
| mcar_0.30_seed2 | knn_scaled | 6,335 | 0.373 | 0.683 | 0.678 |
| mcar_0.30_seed2 | knn_raw | 6,335 | 0.403 | 0.693 | 0.651 |
| mcar_0.30_seed2 | median | 6,335 | 0.691 | 1.017 | 0.000 |
| mcar_0.30_seed2 | mean | 6,335 | 0.747 | 0.963 | 0.000 |
| mcar_0.30_seed3 | knn_scaled | 6,255 | 0.371 | 0.727 | 0.680 |
| mcar_0.30_seed3 | knn_raw | 6,255 | 0.406 | 0.761 | 0.642 |
| mcar_0.30_seed3 | median | 6,255 | 0.693 | 1.080 | 0.000 |
| mcar_0.30_seed3 | mean | 6,255 | 0.750 | 1.030 | 0.000 |
| mcar_0.30_seed4 | knn_scaled | 6,363 | 0.364 | 0.669 | 0.692 |
| mcar_0.30_seed4 | knn_raw | 6,363 | 0.407 | 0.711 | 0.645 |
| mcar_0.30_seed4 | median | 6,363 | 0.690 | 1.016 | 0.000 |
| mcar_0.30_seed4 | mean | 6,363 | 0.743 | 0.962 | 0.000 |
| mcar_0.30_seed5 | knn_scaled | 6,392 | 0.388 | 0.751 | 0.661 |
| mcar_0.30_seed5 | knn_raw | 6,392 | 0.414 | 0.738 | 0.628 |
| mcar_0.30_seed5 | median | 6,392 | 0.700 | 1.050 | 0.000 |
| mcar_0.30_seed5 | mean | 6,392 | 0.753 | 0.996 | 0.000 |

### MCAR 50%

| scenario | method | n_masked_cells | nmae_mean | nrmse_mean | pearson_r_mean |
| -------- | ------ | -------------- | --------- | ---------- | -------------- |
| mcar_0.50_seed1 | knn_scaled | 10,530 | 0.471 | 0.846 | 0.588 |
| mcar_0.50_seed1 | knn_raw | 10,530 | 0.484 | 0.831 | 0.569 |
| mcar_0.50_seed1 | median | 10,530 | 0.687 | 1.072 | 0.000 |
| mcar_0.50_seed1 | mean | 10,530 | 0.747 | 1.023 | -0.000 |
| mcar_0.50_seed2 | knn_scaled | 10,523 | 0.462 | 0.794 | 0.602 |
| mcar_0.50_seed2 | knn_raw | 10,523 | 0.481 | 0.812 | 0.577 |
| mcar_0.50_seed2 | median | 10,523 | 0.691 | 1.065 | 0.000 |
| mcar_0.50_seed2 | mean | 10,523 | 0.749 | 1.013 | -0.000 |
| mcar_0.50_seed3 | knn_scaled | 10,516 | 0.459 | 0.789 | 0.589 |
| mcar_0.50_seed3 | knn_raw | 10,516 | 0.481 | 0.812 | 0.560 |
| mcar_0.50_seed3 | median | 10,516 | 0.688 | 1.049 | 0.000 |
| mcar_0.50_seed3 | mean | 10,516 | 0.744 | 0.997 | -0.000 |
| mcar_0.50_seed4 | knn_scaled | 10,510 | 0.470 | 0.802 | 0.591 |
| mcar_0.50_seed4 | knn_raw | 10,510 | 0.496 | 0.802 | 0.540 |
| mcar_0.50_seed4 | median | 10,510 | 0.696 | 1.022 | 0.000 |
| mcar_0.50_seed4 | mean | 10,510 | 0.747 | 0.965 | 0.000 |
| mcar_0.50_seed5 | knn_scaled | 10,553 | 0.470 | 0.818 | 0.586 |
| mcar_0.50_seed5 | knn_raw | 10,553 | 0.496 | 0.819 | 0.554 |
| mcar_0.50_seed5 | median | 10,553 | 0.691 | 1.052 | 0.000 |
| mcar_0.50_seed5 | mean | 10,553 | 0.745 | 1.001 | -0.000 |

## All seven absent

The degenerate request: nothing but a zipcode. With no dimension left on which to measure a distance, `KNNImputer` falls back to the training column average, so both KNN variants and mean are identical to the last decimal - which is why every one of them shows zero correlation here, and why this is the one case where the choice of imputer does not matter. Median is ahead on error alone because the training median of sqft_basement is 0, matching most houses, where the mean does not; it still returns one constant for every row, so it is no more informative than the others.

| method | nmae_mean | nrmse_mean | pearson_r_mean |
| ------ | --------- | ---------- | -------------- |
| median | 0.6892 | 1.0515 | 0.0000 |
| knn_raw | 0.7456 | 1.0001 | 0.0000 |
| knn_scaled | 0.7456 | 1.0001 | 0.0000 |
| mean | 0.7456 | 1.0001 | 0.0000 |

## Per-request cost

| method | ms_per_request |
| ------ | -------------- |
| knn_raw | 87.48 |
| knn_scaled | 72.50 |
| median | 6.53 |
| mean | 2.36 |

## Reading

Read the leave-one-out section for the answer to the question asked. Pearson r is the column that settles it: it separates an imputer that consults the other specifications from one that ignores them, which no error metric does.
