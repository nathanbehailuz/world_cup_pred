# Development Log

Running documentation for the World Cup 2026 match predictor. Newest entries first.

---

## 2026-06-12 — Squad-value features + competitive-flag ablation

**What was built**
- `download_squad_values.py`: fetches transfermarkt-datasets `players.csv.gz` + `player_valuations.csv.gz`; builds quarterly point-in-time snapshots (top-25 citizenship proxy, 18-month lookback) into `squad_values` table (13,574 rows).
- `feature_engineering.py`: three new features — `home_squad_value_log`, `away_squad_value_log`, `squad_value_log_diff` (log1p); squad values stored in `team_ratings` (cutoff-aware).
- `train.py`: four-configuration experiment grid on the shared 2,245-match competitive test set; generalized feature-list experiments; squad mirroring via `SWAP_COLUMNS`.
- `main.py`: squad-value refresh wired after match download (skip if present).
- `predict.py`: reads `squad_value_log` from `team_ratings`; mirrors squad slot features on neutral venues.

**Four-way experiment results** (XGBoost, symmetrized test set):

| Configuration | Features | log_loss | Brier | accuracy |
|---------------|----------|----------|-------|----------|
| All matches, full | 18 | 0.8343 | 0.4880 | 63.2% |
| Competitive-only, full | 18 | 0.8444 | 0.4911 | 63.6% |
| All matches, no competitive flag | 17 | **0.8327** | **0.4872** | 63.3% |
| All matches, no squad | 15 | 0.8387 | 0.4911 | 63.3% |

**Decisions:** production model = all matches, 17 features (squad kept, competitive flag dropped). Squad features improve log loss by ~0.004 vs the 15-feature set; competitive flag is inert (Δ ≈ 0.002, within noise). XGBoost now beats the Elo baseline (0.8327 vs 0.8355).

**Verified**
- Latest snapshots: England EUR 1.63bn, France EUR 1.40bn, Brazil EUR 939m.
- 2022 WC final (ARG–FRA, penalties): outcome = Argentina win (not draw).
- Pre-2004 matches: all squad features NaN, no crash.
- `FRA BRA --neutral`: France 41.8% / Draw 22.3% / Brazil 35.9%, identical in both orderings.

---

## 2026-06-12 — Shootout targets, tiered K-factors, calibration check

**Decisions from methodology review** (questions answered inline in `METHODOLOGY.md`; deferred work planned in `TODO.md`):

- **Target is now the match winner regardless of how it was decided.** Joined martj42 `shootouts.csv` (678 shootouts, 677 matched to results); matches level after extra time but settled on penalties are labeled with the shootout winner instead of draw. Elo still updates on the on-field result — shootouts are near-coin-flips and say little about strength. Note: martj42 scores include extra time, so the previous "90-minute result" wording was imprecise.
- **Full tiered K-factor** per eloratings.net: 60 WC finals / 50 continental finals / 40 qualifiers + Nations League / 30 other tournaments / 20 friendlies (was 40/20). The `competitive` flag is now defined as K >= 40. Elo top-10 shifted: England up to #4, Mexico enters at #10.
- **Calibration check added** to `train.py`: per-class reliability tables on the test set, printed and stored in `model_meta.json`.

**New results** (test set now 2,245 competitive matches from 2023+):

| Configuration | log_loss | Brier | accuracy |
|---------------|----------|-------|----------|
| Baseline, all matches | 0.8355 | 0.4888 | 62.8% |
| Baseline, competitive-only | 0.8350 | 0.4892 | 62.8% |
| XGBoost, all matches | 0.8387 | 0.4911 | **63.3%** |
| XGBoost, competitive-only | 0.8498 | 0.4950 | 63.2% |

All metrics improved vs the previous run (e.g. XGBoost log loss 0.8433 → 0.8387) — the tiered K and shootout-aware labels are both worth keeping. Friendlies-in-training still wins for XGBoost; baseline still narrowly ahead on log loss.

**Calibration:** home/away win well calibrated across the range; draws never predicted above ~0.40 (the true ceiling), good in the bulk, slightly under at 0.1–0.2 and over at 0.3–0.4. No recalibration layer needed; residual draw miscalibration motivates the planned Poisson model.

- Sample prediction (`FRA BRA --neutral`): France 39.8% / Draw 19.9% / Brazil 40.2%.
- New `TODO.md` tracks deferred plans: feature importance (permutation + gain, not PCA), Poisson goals model, competitive-flag ablation, hyperparameter tuning.

---

## 2026-06-12 — Schedule-aware `main.py` orchestrator

**What was built**
- `download_schedule.py`: fetches WC 2026 fixtures from fixturedownload.com JSON feed into SQLite `schedule` table; `find_fixture()` for team-pair lookup; venue→host-country map for neutral inference; standalone reload prints placeholder resolutions and new results.
- `main.py`: primary entry point — `python main.py MEX RSA` runs the full pipeline with `cutoff = min(today, match_date)` so predicting a past opener never sees its result in Elo.
- `download_data.py`: skips re-download when data is current (accepts 1-day martj42 lag); `--force` to override.
- `feature_engineering.py` / `train.py`: `--cutoff` for point-in-time features; train skips refit when cutoff unchanged (`--retrain` to force).

**Verified**
- `MEX RSA`: cutoff 2026-06-11, home advantage for Mexico at Mexico City, 49,403 matches (June 11 result excluded).
- `FRA SEN`: cutoff today, neutral at New York venue.
- `FRA BRA --neutral`: no fixture, falls back to today.
- Second `MEX RSA` run: skips download and retraining (~7s vs ~20s).

---

## 2026-06-12 — FIFA code input

- `predict.py` now accepts official FIFA three-letter codes (`python predict.py FRA BRA --neutral`), case-insensitive; full names still work as a fallback.
- New `fifa_codes.py` maps all 211 FIFA member associations to the dataset's canonical team names (e.g. CIV → Ivory Coast, KOR → South Korea, CHN → China, TPE → Taiwan, IRL → Republic of Ireland). Verified programmatically that every code resolves to a team present in `team_ratings`.

---

## 2026-06-12 — Neutral-venue symmetrization (mirror-and-average)

**Problem.** The model is not structurally symmetric: on neutral ground, `predict.py "France" "Brazil"` and `predict.py "Brazil" "France"` described the same match but returned different probabilities, because one team occupies the arbitrary "home" slot.

**Fix.** For neutral matches, predict both slot orderings, reverse the mirrored output (home-win and away-win swap), and average. Mirroring negates all `*_diff` features and swaps `home_elo`/`away_elo` and the rest-days columns. Applied in `predict.py` (deployment) and in `train.py` evaluation for both models, so reported metrics describe what the deployed predictor actually outputs. Non-neutral matches are untouched — home advantage there is real. Verified: both orderings of France vs Brazil now return identical mirrored distributions.

**Results on the shared competitive test set (2,138 matches), symmetrized:**

| Configuration | log_loss | Brier | accuracy |
|---------------|----------|-------|----------|
| Baseline (logistic on elo_diff) | **0.8399** | **0.4930** | 62.2% |
| XGBoost, train on all matches | 0.8433 | 0.4948 | **62.3%** |
| XGBoost, train competitive-only | 0.8537 | 0.4989 | 61.9% |

**Honest finding.** Symmetrization *helped* the baseline (0.8428 → 0.8399) but *hurt* XGBoost (0.8396 → 0.8433), and the baseline now narrowly leads on log loss. Interpretation: part of XGBoost's apparent edge came from exploiting the nominal home-slot designation in neutral matches — an artifact, not signal. The friendlies conclusion is unchanged (all-matches still beats competitive-only everywhere). XGBoost stays as the production model for its richer feature interface, but its margin over plain Elo is effectively zero — a candidate for future work (tuning, calibration) rather than a settled win.

- Sample prediction (`France vs Brazil --neutral`): France 31.2% / Draw 40.5% / Brazil 28.3%, identical in both orderings.

---

## 2026-06-12 — Goal features, friendlies experiment, production refit

**What was built**
- New rolling features in `feature_engineering.py`: goals for and goals against over the last 5 and 10 matches (per team, plus home-minus-away diffs). Goal difference alone conflated attack and defense; this separates them.
- `train.py` restructured as an experiment harness: trains two configurations and compares them, then refits a production model on **all** data through the present (previously the saved model only knew pre-2023 matches).
- `predict.py` updated for the new features; predictions now come from the refit production model.

**Experiment: should friendlies be in the training data?**

Both configurations evaluated on the *same* test set — competitive matches from 2023 onward (2,138 matches), since that is the target domain for World Cup 2026.

| Configuration | log_loss | Brier | accuracy |
|---------------|----------|-------|----------|
| Baseline (logistic on elo_diff) | 0.8428 | 0.4953 | 61.4% |
| XGBoost, train on all matches (28,689) | **0.8396** | **0.4932** | **62.2%** |
| XGBoost, train competitive-only (13,517) | 0.8574 | 0.5009 | 61.3% |

**Conclusion: keep friendlies in training.** Dropping them halves the training data and hurts every metric; the competitive-only XGBoost even loses to the simple Elo baseline. The `competitive` flag remains a feature, so the model can still treat the two match types differently.

**Methodology note.** The first version of this experiment compared each configuration on its own test set (all test matches vs competitive test matches), which made competitive-only look better simply because its test set differed. Comparing on a shared test set flipped the conclusion — a useful reminder that experiment results are only comparable on identical evaluation data.

**Production model**
- Refit on all 32,288 matches (1990 through 2026-06-11) with the winning configuration.
- Sample prediction (`France vs Brazil --neutral`): France 28.6% / Draw 36.2% / Brazil 35.2%. The shift from the previous run reflects both the new features and a model that now sees data through mid-2026.

**Known issues / next steps**
- During the tournament, re-run the pipeline after each matchday so Elo absorbs group-stage results before knockout predictions (workflow documented in README).
- Possible future experiments: recency-weighted training samples, probability calibration check, squad/player-level data.

---

## 2026-06-12 — Project setup

**What was built**
- Project scaffold: `requirements.txt`, `data/`, `models/`, pipeline scripts (`download_data.py`, `feature_engineering.py`, `train.py`, `predict.py`).
- SQLite storage at `data/worldcup.db` (chosen over flat files to practice SQL and keep a single queryable source of truth).
- Updated `README.md` with setup and usage instructions.

**Design decisions**
- **Global model, not per-matchup**: one model trained on all international matches; team strength encoded in features (Elo, form).
- **martj42 only**: single source for international match history (through mid-2026); no external API dependency.
- **Point-in-time features**: Elo and rolling form computed chronologically to avoid leakage.
- **Temporal train/test split**: train on matches before 2023-01-01, test on 2023+.
- **Baseline before XGBoost**: logistic regression on Elo difference; XGBoost must beat it to be worth keeping.

**Data facts**
- martj42 CSV: 49,407 rows after dropping scheduled/unplayed matches (null scores).
- Saved 49,405 matches to SQLite (1872-11-30 to 2026-06-11).
- martj42 dataset includes data through mid-2026.
- 336 teams in `team_ratings`; 49,405 feature rows.
- Top Elo (post full history): Spain 2069, Argentina 2042, France 1992, Brazil 1958, Portugal 1948.

**Results** (train < 2023-01-01, test >= 2023-01-01, matches from 1990+)

| Model | log_loss | Brier | accuracy |
|-------|----------|-------|----------|
| Baseline (logistic on elo_diff) | 0.8771 | 0.5168 | 59.8% |
| XGBoost | 0.8712 | 0.5135 | 60.5% |

XGBoost beats baseline on all three metrics. Sample prediction (`France vs Brazil --neutral`): France 25.2% / Draw 32.0% / Brazil 42.9%.

**Known issues / next steps**
- Draw prediction remains hard (~32% in sample); probabilities are more useful than argmax labels.
- Consider adding FIFA ranking or squad-strength features for World Cup 2026 specifically.
