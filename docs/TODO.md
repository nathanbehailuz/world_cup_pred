# Planned Work

Deferred items with concrete plans. Completed work is logged in [DEVLOG.md](DEVLOG.md).

## 1. SHAP values for per-prediction attribution (optional)

Permutation importance and XGBoost gain are now computed automatically in `train.py` and stored in `model_meta.json` (see METHODOLOGY Section 6.5). If these disagree on a specific prediction or feature interaction, add `shap.TreeExplainer` as a deep-dive tool via a `--shap` flag.

## 2. Poisson goals model for draw probabilities (later)

**Goal:** address the residual draw miscalibration (see METHODOLOGY Section 6.3) structurally instead of post-hoc.

**Idea:** model each team's expected goals with two rates (attack/defense adjusted by opponent and venue), treat the score as a bivariate Poisson, and derive P(home win), P(draw), P(away win) by summing the score matrix. Draws emerge from the diagonal naturally, with no 3-class machinery.

**Plan:**

1. Baseline: independent Poisson with rates from a log-linear model on `elo_diff` and venue (classic Maher/Dixon-Coles setup).
2. Compare on the same 2,245-match competitive test set, same metrics (log loss, Brier, calibration tables).
3. If draws calibrate better, consider an ensemble: average Poisson-derived and XGBoost probabilities.
4. Extension: Dixon-Coles low-score correction; shootout-winner labels need a separate handling decision (Poisson predicts the on-field score, so shootout matches should be evaluated on the 120-minute result).

## 3. Hyperparameter tuning and stricter validation (later)

- XGBoost: small grid or Optuna over `max_depth`, `learning_rate`, `n_estimators`, with rolling-origin cross-validation (e.g. validate on 2020–2022, test on 2023+ untouched).
- Elo K-factors: tune tier multipliers by minimizing baseline log loss.
- Home advantage offset (currently 100 Elo points) can be tuned the same way.
- Reserve 2023+ as a one-shot final test after model selection on earlier folds.

## 4. Confederation / region error slices (later)

Add a static FIFA confederation map and extend the error-analysis slices in `train.py` to report log loss by region.
