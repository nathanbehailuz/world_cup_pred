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
python -m pipeline.main MEX RSA          # schedule-aware full pipeline
python -m pipeline.main FRA SEN          # looks up fixture date + venue
python -m pipeline.main FRA BRA --neutral   # no WC fixture: uses today's data
```

`pipeline.main` resolves FIFA codes, reloads the WC 2026 schedule, caps historical
data at `min(today, match date)` for point-in-time correctness, then runs
download → squad values → features → train → predict.

**Pipeline caching:** each stage skips work when already current:
- `pipeline.download_data` — skips if martj42 data covers today (use `--force-download` to override)
- `pipeline.download_squad_values` — skips if `squad_values` table exists (use `--force-download` to refresh)
- `pipeline.train` — skips retraining if the same cutoff was used and analysis is already in `model_meta.json` (use `--retrain` to force)

Predictions are reported as **Team A win / Draw / Team B win**; internally the model uses home/away slots from historical data, with mirror-averaging on neutral venues.

Teams are given as official FIFA three-letter codes (FRA, BRA, MEX, RSA, ...);
full names ("France") also work. The mapping lives in `pipeline/fifa_codes.py`.

### Manual pipeline (step by step)

```bash
python -m pipeline.download_data
python -m pipeline.feature_engineering
python -m pipeline.train
python -m pipeline.predict FRA BRA --neutral
```

## Project layout

| Path | Purpose |
|------|---------|
| `pipeline/` | ML code: download, features, train, predict, backtest |
| `pipeline/main.py` | Primary entry — full schedule-aware pipeline |
| `pipeline/paths.py` | Shared paths to `data/`, `models/`, `results/` |
| `data/worldcup.db` | SQLite database (matches, features, ratings) |
| `models/xgb_model.json` | Trained XGBoost model |
| `results/` | Backtest and evaluation artifacts |
| `docs/` | `METHODOLOGY.md`, `DEVLOG.md`, `WEBSITE.md`, `TODO.md` |
| `web/` | Website scaffold (`api/`, `frontend/` — stack TBD) |

## Keeping predictions current during the tournament

After each matchday, reload the schedule (picks up results and knockout
placeholders resolving to real teams), then predict:

```bash
python -m pipeline.download_schedule    # reload fixtures + print what changed
python -m pipeline.main FRA SEN         # full pipeline with fresh data
```

Or use `pipeline.main` alone — it refreshes the schedule automatically on every run.

`pipeline.main` infers home advantage for USA/Mexico/Canada host venues; override
with `--neutral` or `--home` if needed.

## Data source

- [martj42/international_results](https://github.com/martj42/international_results) — international match history through mid-2026
