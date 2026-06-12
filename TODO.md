# Planned Work

Deferred items with concrete plans. Completed work is logged in `DEVLOG.md`.

## 1. Feature importance analysis (not immediate)

**Goal:** identify which of the 17 production features the model actually relies on, and which are redundant.

**Approach** (PCA is not suitable — it is unsupervised and ignores the outcome):

1. **Permutation importance** (primary): on the held-out competitive test set, shuffle one feature column at a time and measure the increase in log loss. Use `sklearn.inspection.permutation_importance` with the symmetrized scorer, ~10 repeats.
2. **XGBoost gain importance** (free sanity check): `model.feature_importances_` with `importance_type="gain"`.
3. Optional deep dive: **SHAP values** (`shap.TreeExplainer`) for per-prediction attribution if the first two disagree or surprise.

**Implementation sketch:** add a `--importance` flag to `train.py` that runs steps 1–2 after evaluation and prints a ranked table; store in `model_meta.json`.

**Expected outcome:** `elo_diff` dominates; form features largely redundant with Elo. Squad features may rank mid-tier given the ablation result.

## 2. Poisson goals model for draw probabilities (later)

**Goal:** address the residual draw miscalibration (see METHODOLOGY Section 6.3) structurally instead of post-hoc.

**Idea:** model each team's expected goals with two rates (attack/defense adjusted by opponent and venue), treat the score as a bivariate Poisson, and derive P(home win), P(draw), P(away win) by summing the score matrix. Draws emerge from the diagonal naturally, with no 3-class machinery.

**Plan:**

1. Baseline: independent Poisson with rates from a log-linear model on `elo_diff` and venue (classic Maher/Dixon-Coles setup).
2. Compare on the same 2,245-match competitive test set, same metrics (log loss, Brier, calibration tables).
3. If draws calibrate better, consider an ensemble: average Poisson-derived and XGBoost probabilities.
4. Extension: Dixon-Coles low-score correction; shootout-winner labels need a separate handling decision (Poisson predicts the on-field score, so shootout matches should be evaluated on the 120-minute result).

## 3. Hyperparameter tuning (later)

- XGBoost: small grid or Optuna over `max_depth`, `learning_rate`, `n_estimators`, with a time-series validation split (e.g. validate on 2020–2022, test on 2023+ untouched).
- Elo K-factors: the tiered values (60/50/40/30/20) are taken from eloratings.net convention; tune the tier multipliers by minimizing baseline log loss.
- Home advantage offset (currently fixed at 100 Elo points) can be tuned the same way.
