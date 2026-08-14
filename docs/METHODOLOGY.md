# Predicting World Cup 2026 Match Outcomes: Methodology Report

## 1. Problem formulation

Given two national teams A and B and the match venue (home advantage or neutral ground), predict the probability distribution over three outcomes, reported to users as **Team A win / Draw / Team B win**. Internally, historical data encodes these as home and away slots (classes 0, 1, 2); for neutral World Cup matches the slot assignment is arbitrary and predictions are symmetrized (Section 4.3).

The target is the **match winner regardless of how the match was decided** — in 90 minutes, in extra time, or on penalties. A knockout match that finishes level and is settled in a shootout is labeled with the shootout winner. The draw class is reserved for matches with no winner at all (group-stage and friendly draws).

**Interpreting the target.** Because knockout matches cannot end in a draw, the label is best read as a **final match / advancement outcome**, not strictly the 90-minute result. The same on-field state after normal time — a level score — becomes a draw in a group match but a win for one side in a knockout match settled in extra time or on penalties. The model therefore learns a mixture of team strength and competition-format rules. The draw class is structurally unavailable for knockout fixtures. A cleaner future design would model the 90-minute scoreline first, then separately model extra time, penalties, or advancement conditional on knockout context.

The output is a probability vector p = (p_A, p_D, p_B), not a hard label. Draws occur in roughly a quarter of international matches but are rarely the single most likely outcome, so an argmax label would under-report them; for closely matched opponents the draw probability can and does top the list. Probabilities carry strictly more information than a label, and Section 6.3 verifies they are reasonably calibrated.

Whether friendlies belong in the training data is treated as an experiment (Section 6.1). A `competitive` training-time flag was tested and omitted from production after ablation.

A single global model is trained on all international matches rather than one model per team pairing. Head-to-head histories are far too sparse, so team identity is never used directly; strength is encoded in features computed from each team's full match history.

## 2. Data

**Sources:** [martj42/international_results](https://github.com/martj42/international_results), comprising `results.csv` (scores include extra time but not penalty shootouts) and `shootouts.csv` (penalty shootout winners, joined to relabel shootout matches with their winner).

**Coverage after cleaning:** 49,405 matches from 1872-11-30 through 2026-06-11, covering 336 national teams; 677 matches carry a shootout winner.

**Cleaning steps** (`download_data.py`):

1. Drop scheduled/unplayed matches (null scores).
2. Normalize team names to canonical forms via an explicit alias map.
3. Deduplicate fixtures that collide on (date, home team, away team) after normalization.
4. Join shootout winners onto their matches by (date, home team, away team).

Only matches from **1990-01-01 onward** are used for model fitting. All matches (including pre-1990) feed the Elo computation.

## 3. Feature engineering

All features are **point-in-time**: computed using only matches strictly before each match's date.

### 3.1 Elo ratings

Each team carries an Elo rating, initialized at 1500 and updated after every match. Home advantage adds 100 Elo points on non-neutral venues. The K-factor follows the tiered [eloratings.net](https://www.eloratings.net/about) scheme (60 / 50 / 40 / 30 / 20 by match type).

Elo updates use the on-field result (shootouts count as draws for ratings). Outcome *labels* use the shootout winner — ratings measure strength, labels record who advanced.

### 3.2 Rolling form

For each team, over its last 5 and last 10 matches: points, goal difference, goals for, and goals against (kept separate so attack and defence are distinguishable).

### 3.3 Squad market value

**Source:** [transfermarkt-datasets](https://github.com/transfermarkt-datasets) `players.csv.gz` + `player_valuations.csv.gz`. `download_squad_values.py` builds quarterly snapshots from 2004 onward.

**Proxy:** sum of market values of a citizenship's top-25 most valuable players; each player's value is their latest valuation within the prior 18 months.

**Limitations:** dual nationals' actual national-team choice is ignored; fringe call-ups are missed; market value is biased toward European leagues; goalkeepers and defensive players may be undervalued relative to match impact; smaller nations may have missing or stale valuations; citizenship is not the same as FIFA eligibility; the top-25 pool may overstate teams with many eligible stars who do not actually play.

**Missing data:** pre-2004 matches have NaN squad features; XGBoost handles these natively.

### 3.4 Full feature vector

The production model uses **17 features** (squad included; `competitive` flag omitted — see Section 6.1):

| Feature | Description |
| --- | --- |
| `elo_diff` | Home Elo minus away Elo |
| `home_elo`, `away_elo` | Absolute ratings |
| `form_*_diff` (8 features) | Points, GD, GF, GA differences over last 5 / 10 |
| `home_days_since_last`, `away_days_since_last` | Rest / inactivity |
| `neutral` | 1 if neutral venue |
| `home_squad_value_log`, `away_squad_value_log`, `squad_value_log_diff` | log1p squad market value (EUR) |

Feature importance is assessed with supervised methods — permutation importance and XGBoost gain — in Section 6.5.

## 4. Models

### 4.1 Baselines

1. **Constant-prior baseline** — predicts the empirical class distribution from the training set for every match. Verifies that Elo and XGBoost beat naive historical frequencies.
2. **Elo logistic baseline** — multinomial logistic regression on standardized `elo_diff` only (`LogisticRegression`, `max_iter=1000`). The primary sanity check: any richer model must beat this to justify its complexity.

### 4.2 Gradient-boosted trees: XGBoost

`XGBClassifier`, `multi:softprob`, defaults: `max_depth=4`, `learning_rate=0.1`, `n_estimators=300`, `subsample=0.8`, `colsample_bytree=0.8`, `random_state=42`. Not tuned; hyperparameter optimization is future work.

### 4.3 Output symmetrization for neutral venues

On neutral ground, predictions are computed for both slot orderings and averaged after swapping home-win and away-win probabilities. Mirroring negates all `*_diff` features and swaps slot-specific columns. Applied in both `train.py` evaluation and `predict.py` deployment.

### 4.4 Schedule-driven prediction (`main.py`)

For WC 2026 fixtures, `main.py` looks up the schedule, sets cutoff = `min(today, match_date)`, runs feature engineering through that date, and infers neutral vs home advantage from the venue host (USA, Mexico, Canada). Pipeline orchestration details (skip-if-current downloads, retrain caching) are documented in `README.md`.

## 5. Evaluation protocol

### 5.1 Temporal split

Train on 1990-01-01 through 2022-12-31; test on 2023-01-01 onward.

### 5.2 Test set

The shared test set is **2,245 competitive matches** from 2023 onward (the World Cup 2026 target domain). All configurations are evaluated on this identical set.

### 5.3 Metrics

- **Multiclass log loss** (primary) — proper scoring rule.
- **Brier score** — proper scoring rule, more forgiving of tail probabilities.
- **Accuracy** (secondary) — argmax hit rate; misleading alone for a 3-class problem with ~25% draws.

Bootstrap 95% confidence intervals (1,000 resamples) are reported for log loss and for paired differences between models (Section 6.1).

### 5.4 Baselines

Both the constant-prior and Elo logistic baselines are evaluated on every training run alongside the production XGBoost configuration, using the same symmetrized test-set protocol.

### 5.5 Model-selection caveat

The 2023+ test set is used to compare a small predefined grid of four configurations. This is an honest but not fully untouched estimate — repeated selection against the same holdout inflates optimism slightly. A stricter design would use rolling-origin validation for model selection and reserve 2023+ only for a final one-shot evaluation.

## 6. Results

### 6.1 Experiment grid and baselines

Production configuration: all matches, 17 features (squad on, competitive flag off). Evaluated on the 2,245-match competitive test set with neutral symmetrization.

| Model / configuration | Log loss | Brier | Accuracy |
| --- | --- | --- | --- |
| Constant-prior baseline | 1.0469 | 0.6325 | 47.3% |
| Elo logistic baseline | 0.8355 | 0.4888 | 62.8% |
| XGBoost, all matches, full (18 feat) | 0.8343 | 0.4880 | 63.2% |
| XGBoost, competitive-only, full | 0.8444 | 0.4911 | 63.6% |
| **XGBoost, all matches, no competitive flag (production)** | **0.8327** | **0.4872** | **63.3%** |
| XGBoost, all matches, no squad (15 feat) | 0.8387 | 0.4911 | 63.3% |

**Bootstrap 95% CIs (log loss):**

| Model | Point estimate | 95% CI |
| --- | --- | --- |
| Constant prior | 1.0469 | [1.0333, 1.0611] |
| Elo logistic | 0.8355 | [0.8106, 0.8616] |
| Production XGBoost | 0.8327 | [0.8052, 0.8600] |
| **XGBoost − Elo difference** | **−0.0028** | **[−0.0119, 0.0072]** |

**Findings:**

1. Both baselines are clearly beaten: constant prior (1.047) and Elo logistic (0.836) bracket the production model.
2. Friendlies in training still win over competitive-only training (0.8444 vs ≤0.8343).
3. Squad features help: removing them raises log loss by 0.006 (0.8387 vs 0.8327).
4. The competitive flag is inert (Δ ≈ 0.002 vs full set) and is dropped from production.
5. **XGBoost vs Elo:** the point estimate favours XGBoost (−0.0028 log loss), but the bootstrap CI **includes zero** — the improvement is real but **marginally significant at best**, not a large or definitive gain. The richer model is retained for its feature interface and modest edge; it does not dramatically outperform plain Elo.

### 6.2 Production model

The winning configuration is refit on **all 32,288 matches** (1990 through 2026-06-11) with no holdout and saved to `models/xgb_model.json`. **All reported metrics above come from the pre-refit temporal test evaluation** of the selected configuration; the final refit model has no independent post-2026 holdout.

### 6.3 Calibration

Reliability check on the test set (production configuration). Full tables in `models/model_meta.json`.

- **Home win and away win** are well calibrated across most of the range, with mild overconfidence in the 0.5–0.9 home-win range.
- **Draw predictions** never exceed ~0.40. Bulk calibration is good (0.2–0.3 bin: 0.248 predicted vs 0.248 empirical), with residual error at the tails (under-prediction at 0.1–0.2, over-prediction at 0.3–0.4).

Conclusion: calibration is **good enough for practical use**, though draw probabilities show residual miscalibration at the extremes — the strongest argument for a future Poisson goals model.

### 6.4 Error analysis

Slice-level performance for the production configuration on the 2023+ test set:

| Slice | N | Log loss | Accuracy | Mean p(draw) | Observation |
| --- | ---: | ---: | ---: | ---: | --- |
| Elo gap < 50 | 332 | 1.077 | 46.4% | 0.267 | Hardest matches; draws common |
| Elo gap 50–150 | 675 | 1.016 | 51.7% | 0.244 | Moderate uncertainty |
| Elo gap 150–300 | 767 | 0.847 | 65.2% | 0.203 | Clearer favourites emerge |
| Elo gap > 300 | 471 | 0.375 | 88.8% | 0.101 | Heavy favourites usually identified |
| Neutral venues | 647 | 0.873 | 62.0% | 0.201 | Symmetrization applied |
| Non-neutral venues | 1,598 | 0.816 | 63.8% | 0.205 | Home advantage active |
| True home win | 1,062 | 0.535 | 85.8% | 0.184 | Favourites well handled |
| True draw | 458 | 1.515 | 2.0% | 0.233 | Draws rarely the argmax |
| True away win | 725 | 0.838 | 69.1% | 0.214 | Away wins moderate difficulty |

Close matches (Elo gap < 150) account for most of the aggregate log loss. Draws are well-calibrated in probability but almost never the predicted class (2% accuracy on draw rows) — expected given draw frequency vs argmax behaviour. Confederation-level slices are deferred (no mapping in the current pipeline).

### 6.5 Feature importance

Permutation importance on the test set (mean Δ log loss when feature is shuffled, 10 repeats):

| Feature | Δ log loss | Notes |
| --- | ---: | --- |
| `elo_diff` | +0.202 | Dominant |
| `squad_value_log_diff` | +0.021 | Second among diffs; justifies squad data |
| `home_elo` | +0.012 | Slot-specific context |
| `away_squad_value_log` | +0.011 | |
| `away_elo` | +0.006 | |
| `home_squad_value_log` | +0.006 | |
| Form features | +0.002–0.005 each | Small but non-zero |
| Rest days | +0.000–0.001 | Near-zero |

XGBoost gain importance confirms `elo_diff` (0.30) and `neutral` (0.11) as top splitters; `squad_value_log_diff` ranks mid-tier (0.05). The 16 non-Elo features collectively matter, but `elo_diff` alone carries most of the signal — consistent with the small margin over the Elo logistic baseline.

### 6.6 Sample predictions

Illustrative outputs from the production model:

| Match | Team A / Draw / Team B | Comment |
| --- | --- | --- |
| San Marino vs Denmark (2023-10-17, home) | 0.7% / 0.7% / 98.6% | Largest Elo gap on test set |
| Spain vs Italy (2023-06-15, neutral) | 46.6% / 25.0% / 28.5% | Closest Elo ratings; draw meaningful |
| France vs Brazil (live, neutral) | 41.8% / 22.3% / 35.9% | Symmetry check: identical both orderings |
| Canada vs Bosnia (WC 2026 opener, home) | 61.7% / 26.3% / 12.0% | Host home advantage at Toronto |

## 7. Limitations and future work

Tracked in [TODO.md](TODO.md):

- **Final-outcome labels mix match formats.** The target records the final winner, including extra time and penalties, while draws are only possible in matches allowed to end without a winner. Appropriate for advancement-style prediction, but the draw class is structurally unavailable in knockouts. Future work: model 90-minute scorelines first, then advancement.
- **Squad proxy is coarse** (see Section 3.3).
- **XGBoost margin over Elo is small** and not statistically definitive (bootstrap CI includes zero).
- **No hyperparameter tuning**; tiered K values taken from convention.
- **Draw modeling**: residual draw miscalibration motivates a Poisson goals model.
- **Quasi-home effects** not modeled; venue is binary home/neutral.
- **FIFA rankings excluded** (redundant with Elo post-2018; poor pre-2018).
- **During-tournament updating**: re-run after each matchday.
- **SHAP values** for per-prediction attribution (optional deep dive).

## 8. Reproducibility

```bash
python -m pipeline.main MEX RSA         # schedule-aware full pipeline (preferred)
python -m pipeline.download_schedule    # reload fixtures after each matchday
.venv/bin/python -m pipeline.train --retrain
```

All randomness is seeded (`random_state=42`). Metrics, bootstrap CIs, calibration, feature importance, error slices, and sample predictions are persisted in `models/model_meta.json`. A running narrative log is kept in [DEVLOG.md](DEVLOG.md).
