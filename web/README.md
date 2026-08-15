# Website

Public site plan: [`docs/WEBSITE.md`](../docs/WEBSITE.md). Visual reference: [`docs/design.html`](../docs/design.html). Deploy: [`docs/DEPLOYMENT.md`](../docs/DEPLOYMENT.md).

| Path | Role |
|------|------|
| `frontend/` | React + Vite + Tailwind UI (Vercel) |
| `api/` | FastAPI wrapping `pipeline.wc_simulate` |
| `modal_app.py` | Modal ASGI deploy of `web.api.main:app` + model weights |

## API (required for Predict)

### Local

From the **repo root**:

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn web.api.main:app --reload --port 8000
```

### Modal (production)

```bash
.venv/bin/modal deploy web/modal_app.py
# → https://nathanbehailuz--world-cup-pred-api.modal.run
```

After regenerating ratings / schedule:

```bash
.venv/bin/python -m pipeline.export_inference_db
.venv/bin/modal deploy web/modal_app.py
```

Endpoints (same locally and on Modal):

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness |
| GET | `/wc2026/fixtures` | Schedule (resolved teams only) |
| POST | `/predict` | Body `{ team_a, team_b }` — live model, venue from schedule |
| POST | `/wc2026/simulate` | Live model on every WC 2026 fixture |

Venue / home-away are inferred from the fixture + host country (USA / Mexico / Canada). Pairings must appear on the WC 2026 schedule.

## Deploy frontend (Vercel)

SPA only — set build env `VITE_API_BASE` to the Modal URL:

```bash
npx vercel --prod
```

Artifacts for Modal: `models/xgb_model.json`, `models/model_meta.json`, `data/inference.db`.

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
