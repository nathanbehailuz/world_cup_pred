# Website

Public site plan: [`docs/WEBSITE.md`](../docs/WEBSITE.md). Visual reference: [`docs/design.html`](../docs/design.html).

| Path | Role |
|------|------|
| `frontend/` | React + Vite + Tailwind UI |
| `api/` | FastAPI wrapping `pipeline.wc_simulate` |

## API (required for Predict)

From the **repo root**:

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn web.api.main:app --reload --port 8000
```

Endpoints:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness |
| GET | `/wc2026/fixtures` | Schedule (resolved teams only) |
| POST | `/predict` | Body `{ team_a, team_b }` — live model, venue from schedule |
| POST | `/wc2026/simulate` | Live model on every WC 2026 fixture |

Venue / home-away are inferred from the fixture + host country (USA / Mexico / Canada). Pairings must appear on the WC 2026 schedule.

## Deploy (Vercel Services)

Repo-root `vercel.json` ships the Vite frontend and FastAPI backend together:

```bash
npx vercel        # preview
npx vercel --prod # production
```

Inference artifacts committed for the API: `models/xgb_model.json`, `models/model_meta.json`, `data/inference.db` (team_ratings + schedule only). After regenerating the full pipeline DB, refresh the slim DB:

```bash
.venv/bin/python -m pipeline.export_inference_db
```

Frontend calls `/api/*`; Vercel rewrites that to the FastAPI service (`maxDuration` 60s for `/wc2026/simulate`).

## Frontend

```bash
cd web/frontend
npm install
npm run dev      # http://localhost:5173  (proxies /api → :8000)
npm run build
```

### Routes

| Route | Page |
|-------|------|
| `/` | Home |
| `/methodology` | Methodology |
| `/predict` | WC 2026 simulator (live model via API) |
| `/evaluate` | Holdout explorer (precomputed artifact) |
| `/results` | Performance dashboard |
| `/wc2026` | Schedule view |
| `/features` | Feature glossary |
| `/limitations` | Caveats |
| `/about` | Sources & stack |

Predict has two modes: **Single match** (auto venue) and **Run all WC 2026** (step-reveal table + live accuracy / log loss / confusion on played matches).
