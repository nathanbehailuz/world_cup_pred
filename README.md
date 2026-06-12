# world_cup_pred

Predict World Cup 2026 football match outcomes (home win / draw / away win) using historical international match data.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Quick start

```bash
python main.py MEX RSA          # schedule-aware full pipeline
python main.py FRA SEN          # looks up fixture date + venue
python main.py FRA BRA --neutral   # no WC fixture: uses today's data
```

`main.py` resolves FIFA codes, reloads the WC 2026 schedule, caps historical
data at `min(today, match date)` for point-in-time correctness, then runs
download → squad values → features → train → predict.

**Pipeline caching:** each stage skips work when already current:
- `download_data.py` — skips if martj42 data covers today (use `--force-download` to override)
- `download_squad_values.py` — skips if `squad_values` table exists (use `--force-download` to refresh)
- `train.py` — skips retraining if the same cutoff was used and analysis is already in `model_meta.json` (use `--retrain` to force)

Predictions are reported as **Team A win / Draw / Team B win**; internally the model uses home/away slots from historical data, with mirror-averaging on neutral venues.

Teams are given as official FIFA three-letter codes (FRA, BRA, MEX, RSA, ...);
full names ("France") also work. The mapping lives in `fifa_codes.py`.

### Manual pipeline (step by step)

```bash
python download_data.py
python feature_engineering.py
python train.py
python predict.py FRA BRA --neutral
```

## Project layout

| File | Purpose |
|------|---------|
| `main.py` | **Primary entry point** — full schedule-aware pipeline |
| `download_schedule.py` | Fetch/reload WC 2026 fixtures (run after each matchday) |
| `download_data.py` | Fetch martj42 international results into SQLite |
| `feature_engineering.py` | Compute point-in-time Elo, form features |
| `download_squad_values.py` | Fetch transfermarkt valuations, build squad snapshots |
| `train.py` | Train baselines + XGBoost, ablation grid, analysis, save model |
| `predict.py` | Predict W/D/L probabilities for two teams |
| `fifa_codes.py` | Official FIFA three-letter codes mapped to team names |
| `data/worldcup.db` | SQLite database (matches, features, ratings) |
| `models/xgb_model.json` | Trained XGBoost model |
| `DEVLOG.md` | Running project documentation |
| `METHODOLOGY.md` | Report on features, models, and evaluation protocol |

## Keeping predictions current during the tournament

After each matchday, reload the schedule (picks up results and knockout
placeholders resolving to real teams), then predict:

```bash
python download_schedule.py    # reload fixtures + print what changed
python main.py FRA SEN         # full pipeline with fresh data
```

Or use `main.py` alone — it refreshes the schedule automatically on every run.

`main.py` infers home advantage for USA/Mexico/Canada host venues; override
with `--neutral` or `--home` if needed.

## Data source

- [martj42/international_results](https://github.com/martj42/international_results) — international match history through mid-2026
