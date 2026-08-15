# WC 2026 Predictor

Who's lifting the trophy? Ask the model — not your group chat.

**Live site → [world-cup-26-pred.vercel.app](https://world-cup-26-pred.vercel.app/)**

- [Predict a match](https://world-cup-26-pred.vercel.app/predict)
- [How it works](https://world-cup-26-pred.vercel.app/methodology)
- [Did we miss?](https://world-cup-26-pred.vercel.app/evaluate)
- [Model guts](https://world-cup-26-pred.vercel.app/analysis)

XGBoost forecasts for FIFA World Cup 2026 — home win / draw / away win — from Elo, form, rest days, and squad value. Point-in-time features so we don't peek at the future (tempting as that is).

## Run it yourself

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pipeline.main MEX RSA    # schedule-aware: download → train → predict
```

FIFA codes (`FRA`, `BRA`) or full names both work. Add `--neutral` when there's no WC fixture / no home edge.

## Layout

| Path | What |
|------|------|
| `pipeline/` | download, features, train, predict |
| `web/` | site (Vite) + API (Modal) |
| `docs/` | methodology, deployment, todo |

Data: [martj42/international_results](https://github.com/martj42/international_results).  
Built with love by [Nathan](https://nathanbehailu.vercel.app/).
