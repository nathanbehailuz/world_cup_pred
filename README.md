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

## Data source

- [martj42/international_results](https://github.com/martj42/international_results) — international match history through mid-2026
