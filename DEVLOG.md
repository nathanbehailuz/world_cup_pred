# Development Log

Running documentation for the World Cup 2026 match predictor. Newest entries first.

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
