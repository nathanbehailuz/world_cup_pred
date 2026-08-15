# Deployment — WC 2026 Predictor

**Frontend** on Vercel (Vite SPA). **Backend** (live XGBoost) on [Modal](https://modal.com/apps/nathanbehailuz/main/deployed/world-cup-pred).

Local web setup: [`web/README.md`](../web/README.md). Product/IA: [`WEBSITE.md`](./WEBSITE.md).

---

## Architecture

```text
Browser
  ├── https://world-cup-26-pred.vercel.app/   → Vite SPA (Vercel)
  └── VITE_API_BASE (Modal)                  → FastAPI web.api.main:app
        ├── GET  /health
        ├── GET  /wc2026/fixtures
        ├── POST /predict
        └── POST /wc2026/simulate
```

| Piece | Host | Config |
|-------|------|--------|
| SPA | Vercel | Root [`vercel.json`](../vercel.json) builds `web/frontend` |
| API + weights | Modal | [`web/modal_app.py`](../web/modal_app.py) |

Production API base (set as Vercel env `VITE_API_BASE` at **build** time):

`https://nathanbehailuz--world-cup-pred-api.modal.run`

Locally, Vite proxies `/api` → `uvicorn` on `:8000` (no `VITE_API_BASE` needed).

---

## Modal (backend + weights)

App name: `world-cup-pred`. Image installs numpy / xgboost / scikit-learn / fastapi / pydantic and mounts:

| Path | Role |
|------|------|
| `models/xgb_model.json` | Production XGBoost |
| `models/model_meta.json` | Meta |
| `data/inference.db` | `team_ratings` + `schedule` |
| `pipeline/`, `web/api/` | Live `pipeline.wc_simulate` |

### Deploy / iterate

```bash
# from repo root (Modal token already configured)
.venv/bin/modal deploy web/modal_app.py   # persistent
.venv/bin/modal serve web/modal_app.py    # ephemeral + hot reload
```

After retrain or schedule refresh:

```bash
.venv/bin/python -m pipeline.export_inference_db
.venv/bin/modal deploy web/modal_app.py
```

Smoke:

```bash
curl https://nathanbehailuz--world-cup-pred-api.modal.run/health
curl -X POST https://nathanbehailuz--world-cup-pred-api.modal.run/predict \
  -H 'Content-Type: application/json' \
  -d '{"team_a":"MEX","team_b":"RSA"}'
```

Dashboard: https://modal.com/apps/nathanbehailuz/main/deployed/world-cup-pred

---

## Vercel (frontend only)

Repo-root [`vercel.json`](../vercel.json) builds the Vite app under `web/frontend` with an SPA rewrite. There is **no** Python service on Vercel (xgboost wheels exceed the serverless bundle limit).

```bash
npx vercel        # preview
npx vercel --prod # production
```

### Required env

In the Vercel project **Settings → Environment Variables** (Production / Preview):

| Name | Value |
|------|--------|
| `VITE_API_BASE` | `https://nathanbehailuz--world-cup-pred-api.modal.run` |

Must be present at **build** time (Vite inlines it). Redeploy the frontend after changing it.

Root Directory in the dashboard can stay empty (repo root); `vercel.json` points install/build/output at `web/frontend`.

---

## Local parity

```bash
# API
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn web.api.main:app --reload --port 8000

# Frontend
cd web/frontend && npm install && npm run dev
```

---

## Checklist

1. `export_inference_db` + `modal deploy web/modal_app.py`
2. Modal `/health` and `/predict` OK
3. Vercel `VITE_API_BASE` set to Modal URL
4. `npx vercel --prod` (or git push)
5. Confirm Predict on `world-cup-26-pred.vercel.app` calls Modal (network tab)

### Optional offline artifact

`python -m pipeline.export_wc_predictions` / `pipeline.wc_serve` remain available for offline JSON serving; they are **not** used in production Modal/Vercel.
