# Predicting World Cup 2026 Match Outcomes: Methodology Report

## 1. Problem formulation

Given two national teams A and B and match context (venue neutrality,
competitive vs friendly), predict the probability distribution over the three
possible 90-minute outcomes:

- **Home win** (class 0)
- **Draw** (class 1)
- **Away win** (class 2)

The output is a probability vector \(p = (p_{HW}, p_D, p_{AW})\), not a hard
label. Draws occur in roughly a quarter of international matches but are
rarely the most likely single outcome, so an argmax label would almost never
predict them; probabilities carry strictly more information. Knockout matches
are modeled by their 90-minute result; penalty shootouts are out of scope.

A single global model is trained on all international matches rather than one
model per team pairing. Head-to-head histories are far too sparse (many pairs
of national teams have met fewer than ten times ever), so team identity is
never used directly; instead, each team's strength is encoded in features
computed from its full match history.

## 2. Data

**Source:** [martj42/international_results](https://github.com/martj42/international_results),
a public dataset of every full international match since 1872.

**Coverage after cleaning:** 49,405 matches from 1872-11-30 through
2026-06-11, covering 336 national teams.

**Cleaning steps** (`download_data.py`):

1. Drop scheduled/unplayed matches (null scores).
2. Normalize team names to canonical forms (e.g. "Czechia" → "Czech
   Republic", "Korea Republic" → "South Korea") via an explicit alias map.
3. Deduplicate fixtures that collide on (date, home team, away team) after
   normalization (2 rows in the current snapshot).

Matches are stored in SQLite (`data/worldcup.db`, table `matches`) with
columns: date, home/away team, home/away score, tournament, a neutral-venue
flag, and source.

Only matches from **1990-01-01 onward** are used for model fitting, to keep
the era roughly comparable to modern international football. All matches
(including pre-1990) feed the Elo computation, since ratings need the full
history to converge.

## 3. Feature engineering

All features are **point-in-time**: for each match row, they are computed
using only matches strictly before that match's date. This eliminates
temporal leakage — no feature can encode information from the future.

### 3.1 Elo ratings

Each team carries an Elo rating, initialized at 1500 and updated after every
match in chronological order. For a match between home team \(H\) and away
team \(A\):

\[
E_H = \frac{1}{1 + 10^{(R_A - R'_H)/400}}, \qquad
R'_H = R_H + \begin{cases} 100 & \text{home venue} \\ 0 & \text{neutral venue} \end{cases}
\]

\[
R_H \leftarrow R_H + K\,(S_H - E_H), \qquad R_A \leftarrow R_A - K\,(S_H - E_H)
\]

where \(S_H \in \{1, 0.5, 0\}\) is the actual result for the home side and
the K-factor reflects match importance:

| Match type | K |
|---|---|
| Competitive (World Cup, continental championships, qualifiers, Nations League, ...) | 40 |
| Friendly | 20 |

Friendlies are deliberately **kept** in the rating computation at reduced
weight — they are real observations of team strength, particularly between
tournaments when squads change.

### 3.2 Rolling form

For each team, over its last 5 and last 10 matches as of the match date:

- **Points**: 3 per win, 1 per draw, 0 per loss
- **Goal difference**: goals scored minus conceded
- **Goals for / goals against**: kept separate so the model can distinguish
  attacking strength from defensive solidity (goal difference alone conflates
  a side winning 1-0 repeatedly with one trading 4-3 results)

### 3.3 Full feature vector

The model receives 15 features per match:

| Feature | Description |
|---|---|
| `elo_diff` | Home Elo minus away Elo |
| `home_elo`, `away_elo` | Absolute ratings (lets the model condition on match quality, not just the gap) |
| `form_pts_5_diff`, `form_pts_10_diff` | Points difference over last 5 / 10 matches |
| `form_gd_5_diff`, `form_gd_10_diff` | Goal-difference difference over last 5 / 10 |
| `form_gf_5_diff`, `form_gf_10_diff` | Goals-scored difference over last 5 / 10 |
| `form_ga_5_diff`, `form_ga_10_diff` | Goals-conceded difference over last 5 / 10 |
| `home_days_since_last`, `away_days_since_last` | Rest / inactivity in days |
| `neutral` | 1 if neutral venue (most World Cup matches; hosts USA/Mexico/Canada excepted) |
| `competitive` | 1 if competitive fixture, 0 if friendly |

At prediction time, the same quantities are read from the `team_ratings`
table, which holds every team's current Elo and form computed through the
latest data in the database.

## 4. Models

### 4.1 Baseline: logistic regression on Elo difference

A multinomial logistic regression using **only** standardized `elo_diff`
(scikit-learn `LogisticRegression`, `max_iter=1000`). This is the
sanity-check model: international football outcomes are largely explained by
rating difference, and any richer model must beat this to justify its
complexity.

### 4.2 Gradient-boosted trees: XGBoost

`XGBClassifier` with objective `multi:softprob` (3 classes) and
hyperparameters:

| Hyperparameter | Value | Rationale |
|---|---|---|
| `max_depth` | 4 | Shallow trees; the signal is mostly smooth and monotone in Elo/form, deep trees overfit |
| `learning_rate` | 0.1 | Standard step size |
| `n_estimators` | 300 | Enough rounds at this learning rate to plateau |
| `subsample` | 0.8 | Row subsampling for regularization |
| `colsample_bytree` | 0.8 | Feature subsampling for regularization |
| `eval_metric` | `mlogloss` | Matches the evaluation objective |
| `random_state` | 42 | Reproducibility |

These values are sensible defaults rather than the result of a tuning search;
hyperparameter optimization (e.g. with time-series cross-validation) is
future work.

## 5. Evaluation protocol

### 5.1 Temporal split

Train on matches from 1990-01-01 to 2022-12-31; test on matches from
2023-01-01 onward. A random split would leak future information (a team's
2024-informed Elo trajectory appearing in training while 2023 matches sit in
test), inflating scores.

### 5.2 Test set

The shared test set is the **2,138 competitive matches** from 2023 onward,
because competitive matches are the target domain (World Cup 2026). All model
configurations are evaluated on this identical set — comparisons across
different test sets are not meaningful.

### 5.3 Metrics

For true outcome \(y_i\) and predicted probabilities \(p_i\):

- **Multiclass log loss** (primary): \(-\frac{1}{N}\sum_i \log p_{i,y_i}\) —
  proper scoring rule, punishes confident wrong predictions.
- **Brier score**: \(\frac{1}{N}\sum_i \lVert p_i - \mathbf{1}_{y_i} \rVert^2\)
  — proper scoring rule, more forgiving of tail probabilities.
- **Accuracy** (secondary): argmax hit rate. Reported for interpretability
  but misleading alone for a 3-class problem with ~25% draws.

## 6. Results

### 6.1 Training-data experiment: should friendlies be included?

Both configurations evaluated on the same 2,138-match competitive test set:

| Configuration | Train size | Log loss | Brier | Accuracy |
|---|---|---|---|---|
| Baseline (logistic on `elo_diff`) | 28,689 | 0.8428 | 0.4953 | 61.4% |
| **XGBoost, all matches** | **28,689** | **0.8396** | **0.4932** | **62.2%** |
| XGBoost, competitive-only | 13,517 | 0.8574 | 0.5009 | 61.3% |

**Findings:**

1. Training on all matches (friendlies included) wins on every metric.
   Excluding friendlies halves the training data, and the competitive-only
   XGBoost falls behind even the Elo baseline.
2. The XGBoost improvement over the baseline is real but modest (Δ log loss
   ≈ 0.003) — consistent with the literature: international match outcomes
   are noisy, and rating difference carries most of the signal.
3. Methodological note: an earlier version of this experiment evaluated each
   configuration on its own test set and reached the *opposite* conclusion.
   The shared-test-set comparison corrected this.

### 6.2 Production model

After evaluation, the winning configuration is refit on **all 32,288
matches** (1990 through 2026-06-11) with no holdout, and saved to
`models/xgb_model.json`. The temporal split exists only to estimate honest
generalization; withholding the most recent three years from the deployed
model would discard the most relevant data.

## 7. Limitations and future work

- **Squad-level shocks are invisible.** Elo and form lag reality when a key
  player is injured, a generation retires, or a new manager arrives.
  Incorporating player-level data (squad market value, lineups) is the
  largest potential improvement and the largest effort.
- **No hyperparameter tuning** has been performed; gains of similar size to
  the current XGBoost-over-baseline margin may be available.
- **Calibration** has not been formally checked (e.g. reliability diagrams),
  though proper scoring rules partially guard against miscalibration.
- **Quasi-home effects** (e.g. Mexico playing in Los Angeles) are not
  modeled; venue is binary home/neutral.
- **FIFA rankings were deliberately excluded**: the post-2018 formula is
  itself an Elo variant (redundant with ours), and the pre-2018 formula was
  of notoriously poor quality.
- **During-tournament updating**: the pipeline should be re-run after each
  matchday so group-stage results flow into Elo before knockout predictions.

## 8. Reproducibility

```bash
python download_data.py        # data acquisition + cleaning
python feature_engineering.py  # Elo + form features (point-in-time)
python train.py                # experiments + production refit
python predict.py "France" "Brazil" --neutral
```

All randomness is seeded (`random_state=42`). Experiment metrics are
persisted in `models/model_meta.json`; a running narrative log is kept in
`DEVLOG.md`.
