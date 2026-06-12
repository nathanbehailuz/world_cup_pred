# Predicting World Cup 2026 Match Outcomes: Methodology Report

## 1. Problem formulation

Given two national teams A and B and the match venue (home advantage or neutral ground), predict the probability distribution over the three possible outcomes:

- **Home win** (class 0)
- **Draw** (class 1)
- **Away win** (class 2)

The target is the **match winner regardless of how the match was decided** — in 90 minutes, in extra time, or on penalties. A knockout match that finishes level and is settled in a shootout is labeled with the shootout winner. The draw class is reserved for matches with no winner at all (group-stage and friendly draws).

The output is a probability vector p = (p_{HW}, p_D, p_{AW}), not a hard label. Draws occur in roughly a quarter of international matches but are rarely the single most likely outcome, so an argmax label would under-report them; this is a statistical tendency, not a structural restriction — for closely matched opponents the draw probability can and does top the list. Probabilities carry strictly more information than a label, and Section 6.3 verifies they are well calibrated.

The primary match context is the venue. Whether friendlies belong in the training data at all is treated as an experiment — configurations training on all matches vs competitive-only are compared on the same test set in Section 6.1. A `competitive` flag (1 for major competitions, 0 for friendlies) was also tested as a training-time feature; the ablation in Section 6.1 shows it contributes nothing measurable and is omitted from the production model.

A single global model is trained on all international matches rather than one model per team pairing. Head-to-head histories are far too sparse (many pairs of national teams have met fewer than ten times ever), so team identity is never used directly; instead, each team's strength is encoded in features computed from its full match history.

## 2. Data

**Sources:** [martj42/international_results](https://github.com/martj42/international_results), a public dataset of every full international match since 1872, comprising `results.csv` (match results; scores include extra time but not penalty shootouts) and `shootouts.csv` (penalty shootout winners, joined to relabel shootout matches with their winner).

**Coverage after cleaning:** 49,405 matches from 1872-11-30 through 2026-06-11, covering 336 national teams; 677 matches carry a shootout winner.

**Cleaning steps** (`download_data.py`):

1. Drop scheduled/unplayed matches (null scores).
2. Normalize team names to canonical forms (e.g. "Czechia" → "Czech Republic", "Korea Republic" → "South Korea") via an explicit alias map.
3. Deduplicate fixtures that collide on (date, home team, away team) after normalization (2 rows in the current snapshot).
4. Join shootout winners onto their matches by (date, home team, away team).

Matches are stored in SQLite (`data/worldcup.db`, table `matches`) with columns: date, home/away team, home/away score, tournament, a neutral-venue flag, shootout winner (nullable), and source.

Only matches from **1990-01-01 onward** are used for model fitting, to keep the era roughly comparable to modern international football. All matches (including pre-1990) feed the Elo computation, since ratings need the full history to converge.

## 3. Feature engineering

All features are **point-in-time**: for each match row, they are computed using only matches strictly before that match's date. This eliminates temporal leakage — no feature can encode information from the future.

### 3.1 Elo ratings

Each team carries an Elo rating, initialized at 1500 and updated after every match in chronological order. For a match between home team H and away team A:

E_H = \frac{1}{1 + 10^{(R_A - R'_H)/400}}, \qquad R'_H = R_H + \begin{cases} 100 & \text{home venue}  0 & \text{neutral venue} \end{cases}

R_H \leftarrow R_H + K(S_H - E_H), \qquad R_A \leftarrow R_A - K(S_H - E_H) where S_H \in 1, 0.5, 0 is the actual on-field result for the home side and the K-factor follows the tiered scheme used by the World Football Elo Ratings ([eloratings.net](https://www.eloratings.net/about)), weighting matches by how much a result reveals about team strength:

| Match type | K |
| --- | --- |
| World Cup finals tournament | 60 |
| Continental championship finals, Confederations Cup | 50 |
| World Cup / continental qualifiers, Nations League | 40 |
| Other tournaments | 30 |
| Friendlies | 20 |

Friendlies are deliberately **kept** in the rating computation at reduced weight — they are real observations of team strength, particularly between tournaments when squads change.

Two details about shootouts: Elo updates use the on-field result (a shootout match counts as a draw for ratings), because a penalty shootout is a near-coin-flip tiebreaker and carries little information about team strength. The outcome *label*, in contrast, uses the shootout winner — ratings measure strength, labels record who advanced.

### 3.2 Rolling form

For each team, over its last 5 and last 10 matches as of the match date:

- **Points**: 3 per win, 1 per draw, 0 per loss
- **Goal difference**: goals scored minus conceded
- **Goals for / goals against**: kept separate so the model can distinguish attacking strength from defensive solidity (goal difference alone conflates a side winning 1-0 repeatedly with one trading 4-3 results)

### 3.3 Squad market value

**Source:** [transfermarkt-datasets](https://github.com/transfermarkt-datasets) publishes `players.csv.gz` (citizenship) and `player_valuations.csv.gz` (dated market values, 2000–2026). `download_squad_values.py` builds quarterly point-in-time snapshots from 2004 onward.

**Proxy:** each national squad is approximated as the sum of market values of that citizenship's top-25 most valuable players at each snapshot date. A player's value is their latest valuation within the prior 18 months. Citizenship is mapped to martj42 canonical team names via `normalize_team_name` plus explicit aliases (e.g. "Korea, South" → South Korea).

**Known limitations:** dual nationals' actual national-team choice is ignored; fringe call-ups are missed. The proxy is point-in-time correct and fully automatable.

**Missing data:** matches before 2004 have NaN squad features. XGBoost handles missing values natively; no imputation is applied. The logistic baseline (Elo only) is unaffected.

### 3.4 Full feature vector

The production model receives **17 features** per match (squad features included; `competitive` flag omitted after ablation — see Section 6.1):

| Feature                                        | Description                                                                    |
| ---------------------------------------------- | ------------------------------------------------------------------------------ |
| `elo_diff`                                     | Home Elo minus away Elo                                                        |
| `home_elo`, `away_elo`                         | Absolute ratings (lets the model condition on match quality, not just the gap) |
| `form_pts_5_diff`, `form_pts_10_diff`          | Points difference over last 5 / 10 matches                                     |
| `form_gd_5_diff`, `form_gd_10_diff`            | Goal-difference difference over last 5 / 10                                    |
| `form_gf_5_diff`, `form_gf_10_diff`            | Goals-scored difference over last 5 / 10                                       |
| `form_ga_5_diff`, `form_ga_10_diff`            | Goals-conceded difference over last 5 / 10                                     |
| `home_days_since_last`, `away_days_since_last` | Rest / inactivity in days                                                      |
| `neutral`                                      | 1 if neutral venue (most World Cup matches; hosts USA/Mexico/Canada excepted)  |
| `home_squad_value_log`, `away_squad_value_log` | log1p of top-25 squad market value (EUR) per team                                |
| `squad_value_log_diff`                         | Home minus away squad log-value (mirrors as negation on neutral venues)        |

At prediction time, Elo, form, and squad value are read from the `team_ratings` table, computed chronologically through the cutoff date.

On measuring which features matter: PCA is not the right tool — it is unsupervised dimensionality reduction that finds directions of maximum feature *variance* while knowing nothing about the outcome, and its components are uninterpretable mixtures of the originals. The appropriate tools are permutation importance (shuffle one feature in the test set, measure the log-loss degradation), XGBoost's built-in gain importance, and SHAP values for per-prediction attribution. This analysis is planned (see `TODO.md`); the expectation is that `elo_diff` dominates and the form features are largely redundant with it.

## 4. Models

### 4.1 Baseline: logistic regression on Elo difference

A multinomial logistic regression using **only** standardized `elo_diff` (scikit-learn `LogisticRegression`, `max_iter=1000`). This is the sanity-check model: international football outcomes are largely explained by rating difference, and any richer model must beat this to justify its complexity.

### 4.2 Gradient-boosted trees: XGBoost

`XGBClassifier` with objective `multi:softprob` (3 classes) and hyperparameters:

| Hyperparameter     | Value      | Rationale                                                                               |
| ------------------ | ---------- | --------------------------------------------------------------------------------------- |
| `max_depth`        | 4          | Shallow trees; the signal is mostly smooth and monotone in Elo/form, deep trees overfit |
| `learning_rate`    | 0.1        | Standard step size                                                                      |
| `n_estimators`     | 300        | Enough rounds at this learning rate to plateau                                          |
| `subsample`        | 0.8        | Row subsampling for regularization                                                      |
| `colsample_bytree` | 0.8        | Feature subsampling for regularization                                                  |
| `eval_metric`      | `mlogloss` | Matches the evaluation objective                                                        |
| `random_state`     | 42         | Reproducibility                                                                         |

These values are sensible defaults rather than the result of a tuning search; hyperparameter optimization (e.g. with time-series cross-validation) is future work.

### 4.3 Output symmetrization for neutral venues

Neutral venues are handled at two levels. In the *data*, every match carries a neutral flag: the Elo update skips the 100-point home-advantage offset when it is set, and the flag is a model feature (Section 3.3), so the model learns separate mappings for the two venue regimes.

The flag alone is not sufficient, however. Nothing forces a tree ensemble to be *structurally symmetric*: trees split on `home_elo` and `away_elo` independently, so even with the neutral flag set, feeding (A, B) and (B, A) lands in different leaves and returns slightly different distributions for the same physical match. The diff features mirror cleanly (they just negate), but the slot-specific features (`home_elo`/`away_elo`, rest days) do not. The flag and the averaging therefore solve different problems — "no home advantage here" vs "slot order must not matter" — and both are used.

To make the symmetry exact, predictions for neutral matches are computed twice, once per slot ordering, and averaged after mirroring:

p_sym(A, B) = ( p(A, B) + reverse(p(B, A)) ) / 2

where reverse swaps the home-win and away-win probabilities. Mirroring a feature vector negates all `*_diff` features and swaps the home/away slot features.

This is applied both at prediction time (`predict.py`) and during evaluation (`train.py`), so reported metrics describe exactly what the deployed predictor outputs. Non-neutral matches are never symmetrized — home advantage there is real and the slot assignment is meaningful.

### 4.4 Schedule-driven point-in-time prediction (`main.py`)

For World Cup 2026 fixtures, `main.py` orchestrates the full pipeline:

1. **Schedule lookup** — reloads the fixturedownload.com JSON feed into the `schedule` table and finds the earliest match between the two teams.
2. **Cutoff date** — `min(today, match_date)`. Feature engineering uses only matches with `date < cutoff`, so ratings reflect information available *before* kickoff. Predicting the June 11 Mexico–South Africa opener on June 12 uses data through June 10, never the 2–0 result.
3. **Neutral inference** — if a fixture exists, home advantage is applied only when one team is the venue's host nation (USA, Mexico, or Canada); otherwise the match is treated as neutral. Override with `--neutral` or `--home`.
4. **Efficiency** — martj42 and squad-value downloads are skipped when already current; model retraining is skipped when the same cutoff was used in the last run.

Run `python download_schedule.py` after each matchday to reload fixtures and see knockout placeholders resolve to real teams.

### 4.5 Inference walkthrough

What happens when `python main.py FRA BRA` runs, end to end:

1. FIFA codes are resolved to canonical team names (`fifa_codes.py`).
2. The schedule is refreshed and searched for a fixture between the two teams; the cutoff date and venue neutrality are derived as in Section 4.4.
3. Each team's current Elo and rolling form are read from `team_ratings` — these were computed chronologically through the cutoff, so they are exactly the pre-kickoff state of knowledge.
4. The 17-feature vector is assembled: rating and form differences, squad log-values, rest days, and `neutral` from the venue inference.
5. The production XGBoost model returns `predict_proba` — three probabilities summing to 1.
6. If the venue is neutral, the mirrored feature vector is also scored and the two distributions are averaged (Section 4.3).
7. The result is printed as win/draw/win percentages for the two teams.

## 5. Evaluation protocol

### 5.1 Temporal split

Train on matches from 1990-01-01 to 2022-12-31; test on matches from 2023-01-01 onward. A random split would leak future information (a team's 2024-informed Elo trajectory appearing in training while 2023 matches sit in test), inflating scores.

### 5.2 Test set

The shared test set is the **2,245 competitive matches** from 2023 onward, because competitive matches are the target domain (World Cup 2026). All model configurations are evaluated on this identical set — comparisons across different test sets are not meaningful.

### 5.3 Metrics

For true outcome y_i and predicted probabilities p_i:

- **Multiclass log loss** (primary): -\frac{1}{N}\sum_i \log p_{i,y_i} — proper scoring rule, punishes confident wrong predictions.
- **Brier score**: \frac{1}{N}\sum_i \lVert p_i - \mathbf{1}_{y_i} \rVert^2— proper scoring rule, more forgiving of tail probabilities.
- **Accuracy** (secondary): argmax hit rate. Reported for interpretability but misleading alone for a 3-class problem with ~25% draws.

The right response to the draw-frequency problem is not to force more draw predictions — class weights or oversampling would inflate draw probabilities and destroy calibration, which is the property that actually matters. The response is to (a) report probabilities rather than labels, (b) verify calibration empirically (Section 6.3), and (c) longer-term, model the score distribution directly (e.g. a Poisson goals model, where draws emerge naturally from the diagonal) — planned in `TODO.md`.

## 6. Results

### 6.1 Experiment grid: training data, squad features, competitive flag

All XGBoost configurations evaluated on the same 2,245-match competitive test set (2023+), with neutral-venue symmetrization (Section 4.3). Targets include shootout winners; Elo uses the tiered K scheme. Baseline (logistic on `elo_diff` only) is unchanged across ablations: log loss 0.8355, Brier 0.4888, accuracy 62.8%.

| Configuration | Features | Train size | Log loss | Brier | Accuracy |
| --- | --- | --- | --- | --- | --- |
| All matches, full (squad + competitive flag) | 18 | 28,689 | 0.8343 | 0.4880 | 63.2% |
| Competitive-only, full | 18 | 14,212 | 0.8444 | 0.4911 | 63.6% |
| All matches, no competitive flag | 17 | 28,689 | **0.8327** | **0.4872** | 63.3% |
| All matches, no squad features | 15 | 28,689 | 0.8387 | 0.4911 | 63.3% |

**Findings:**

1. **Friendlies in training** still win: competitive-only training (0.8444) is worse than all-matches configurations on every metric.
2. **Squad features help:** removing them (0.8387) is worse than the full 18-feature set (0.8343) by Δ log loss ≈ 0.004. The citizenship proxy carries signal beyond Elo and form.
3. **Competitive flag is inert:** dropping it (0.8327) changes log loss by only 0.0016 vs the full set — within the ±0.005 noise band. It is omitted from the production model; friendlies-vs-competitive behaviour is already encoded in the training rows themselves.
4. **Production selection:** `train-all-matches-no-competitive-flag` wins by log loss and **beats the Elo baseline** (0.8327 vs 0.8355) for the first time — squad value is the feature that tips the balance.
5. Methodological notes: (a) comparisons are only valid on identical evaluation data; (b) symmetrization is applied throughout so metrics describe deployed behaviour.

### 6.2 Production model

After evaluation, the winning configuration (all matches, 17 features: squad included, competitive flag dropped) is refit on **all 32,288 matches** (1990 through 2026-06-11) with no holdout, and saved to `models/xgb_model.json`. The temporal split exists only to estimate honest generalization; withholding the most recent three years from the deployed model would discard the most relevant data.

### 6.3 Calibration

Reliability check on the test set (production configuration): predicted probabilities are binned per class and compared with empirical frequencies. Full tables are stored in `models/model_meta.json`; summary:

- **Home win and away win are well calibrated** across the full range (e.g. home-win bin 0.9–1.0: mean predicted 0.945 vs empirical 0.958). There is mild overconfidence in the 0.5–0.9 home-win range (predicted ≈ 0.05 above empirical).
- **Draw predictions never exceed ~0.40**, reflecting the true ceiling on draw likelihood between any two teams. Calibration is good in the bulk (0.2–0.3 bin: 0.247 predicted vs 0.248 empirical), with slight under-prediction at the low end (0.1–0.2: 0.152 vs 0.195) and over-prediction at the top (0.3–0.4: 0.324 vs 0.269).

Conclusion: the probabilities can be taken at face value; no recalibration layer is currently warranted. The residual draw miscalibration is the strongest argument for the planned Poisson goals model.

## 7. Limitations and future work

Near-term work items are tracked with concrete plans in [TODO.md](TODO.md); the main known limitations:

- **Squad proxy is coarse.** Market value by citizenship captures aggregate talent but misses dual-national choices, actual call-ups, injuries, and manager effects. Lineups and player availability remain unmodeled.
- **No hyperparameter tuning** has been performed; gains of similar size to the current XGBoost-vs-baseline margin may be available. The tiered K values are taken from convention, not tuned for log loss.
- **Feature importance not yet measured** (permutation importance + gain, planned in `TODO.md`).
- **Draw modeling**: the residual draw miscalibration motivates a Poisson goals model as a structural alternative (planned in `TODO.md`).
- **Quasi-home effects** (e.g. Mexico playing in Los Angeles) are not modeled; venue is binary home/neutral. Slot asymmetry on neutral ground is handled by mirror-averaging (Section 4.3), but genuine crowd or travel advantages within "neutral" matches remain invisible.
- **FIFA rankings were deliberately excluded**: the post-2018 formula is itself an Elo variant (redundant with ours), and the pre-2018 formula was of notoriously poor quality.
- **During-tournament updating**: the pipeline should be re-run after each matchday so group-stage results flow into Elo before knockout predictions.

## 8. Reproducibility

```bash
python main.py MEX RSA         # schedule-aware full pipeline (preferred)
python download_schedule.py    # reload fixtures after each matchday
```

All randomness is seeded (`random_state=42`). Experiment metrics and calibration tables are persisted in `models/model_meta.json`; a running narrative log is kept in `DEVLOG.md`.
