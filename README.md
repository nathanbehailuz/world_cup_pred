# world_cup_pred

Predict World Cup 2026 football match outcomes (home win / draw / away win) using historical international match data.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Pipeline

Run in order:

```bash
python download_data.py
python feature_engineering.py
python train.py
python predict.py "France" "Brazil" --neutral
```

## Project layout

| File | Purpose |
|------|---------|
| `download_data.py` | Fetch martj42 international results into SQLite |
| `feature_engineering.py` | Compute point-in-time Elo, form features |
| `train.py` | Train baseline + XGBoost, evaluate, save model |
| `predict.py` | Predict W/D/L probabilities for two teams |
| `data/worldcup.db` | SQLite database (matches, features, ratings) |
| `models/xgb_model.json` | Trained XGBoost model |
| `DEVLOG.md` | Running project documentation |

## Keeping predictions current during the tournament

The model's inputs (Elo, recent form) are computed from the latest data in the
database. To make knockout-stage predictions reflect group-stage results,
re-run the data and feature steps after each matchday:

```bash
python download_data.py        # pulls latest results
python feature_engineering.py  # updates Elo and form ratings
python train.py                # optional: refit production model
python predict.py "France" "Brazil" --neutral
```

Note: World Cup 2026 hosts (USA, Mexico, Canada) play true home matches —
omit `--neutral` for those.

## Data source

- [martj42/international_results](https://github.com/martj42/international_results) — international match history through mid-2026
