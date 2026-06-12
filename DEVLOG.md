# Development Log

Running documentation for the World Cup 2026 match predictor. Newest entries first.

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
