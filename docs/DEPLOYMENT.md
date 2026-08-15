# Deployment — WC 2026 Predictor

How this repo ships to **Vercel** as one project with two services: a Vite frontend and a FastAPI predict API.

Local web setup lives in [`web/README.md`](../web/README.md). Product/IA notes: [`WEBSITE.md`](./WEBSITE.md).

---

## Architecture

Repo-root [`vercel.json`](../vercel.json) defines **Vercel Services**:

| Service | Root | Role |
|---------|------|------|
| `frontend` | `web/frontend` | React + Vite SPA (framework: `vite`) |
| `backend` | `.` (repo root) | FastAPI app `web.api.main:app` |

Top-level rewrites:

- `/api/*` → **backend** (path rewritten so FastAPI sees `/health`, `/predict`, etc.)
- everything else → **frontend** (SPA fallback to `index.html`)

The browser always calls `/api/...`. On Vercel that hits the Python service; in local Vite, a proxy rewrites `/api` → `http://127.0.0.1:8000`.

```text
Browser
  ├── /          → Vite static (frontend service)
  └── /api/*     → FastAPI (backend service)
                      ├── GET  /health
                      ├── GET  /wc2026/fixtures
                      ├── POST /predict
                      └── POST /wc2026/simulate   (maxDuration 60s)
```

Backend install/runtime:

- `installCommand`: `pip install --no-cache-dir -r requirements-api.txt` (fastapi + pydantic only)
- Serve path: `pipeline.wc_serve` reads `data/wc2026_predictions.json` (no xgboost on Vercel)
- Entrypoint also noted in [`pyproject.toml`](../pyproject.toml) (`[tool.vercel]`)
- Full training stack stays in `requirements.txt` and is **not** required on Vercel
- Project **Root Directory** in the Vercel dashboard must be empty (repo root). If it is `web/frontend`, only the SPA builds and `/api` 404s

---

## What must be in the deploy

The API loads a **precomputed** WC 2026 predictions artifact (no XGBoost on the server — Linux wheels exceed Vercel’s ~225MB function limit):

| Artifact | Path | Purpose |
|----------|------|---------|
| Predictions | `data/wc2026_predictions.json` | Fixture list + probs for `/predict` and `/wc2026/simulate` |
| Meta (optional) | `models/model_meta.json` | Local/docs; not required at serve time |

Regenerate after retrain / schedule refresh:

```bash
.venv/bin/python -m pipeline.export_wc_predictions
```

Do **not** ship `data/worldcup.db` or raw caches — they are ignored (see [`.gitignore`](../.gitignore) and [`.vercelignore`](../.vercelignore)).

Live model inference (`pipeline.wc_simulate` + xgboost) remains available **locally** with the full `requirements.txt` stack.

---

## One-time / infrequent setup

1. Install the [Vercel CLI](https://vercel.com/docs/cli) (optional but useful):

   ```bash
   npm i -g vercel
   ```

2. In the Vercel project **Settings → General / Build & Development**:

   - **Root Directory:** leave empty (repository root). Do **not** set `web/frontend` — that deploys the SPA only, so `/predict` 404s without an SPA rewrite and `/api` never exists.
   - **Framework Preset:** **Services** (required for the root `vercel.json` `services` block).
   - **Build Command:** leave empty or `npm run build` — never `npm run dev` / `vite` (that hangs until the 45m timeout).

3. From the **repo root**, link the project once:

   ```bash
   vercel link
   ```

4. Prefer connecting the GitHub repo in the Vercel dashboard so pushes create preview/production deploys automatically. CLI deploys still work without that.

No special env vars are required for the default setup: the frontend uses relative `/api`, and the backend reads models/DB from disk.

Optional: set `VITE_API_BASE` at **build** time only if the API is hosted on a different origin (not needed for the Services layout in `vercel.json`).

---

## Refresh prediction artifacts before shipping model/data changes

After you regenerate the full pipeline DB or retrain:

```bash
.venv/bin/python -m pipeline.export_inference_db   # optional, for local live model
.venv/bin/python -m pipeline.export_wc_predictions # required for Vercel API
```

Commit the updated `data/wc2026_predictions.json`, then deploy.

---

## Deploy

Always run from the **repository root** (where `vercel.json` lives).

### Preview

```bash
npx vercel
# or: vercel deploy
```

Gives a unique preview URL for the current tree.

### Production

```bash
npx vercel --prod
# or: vercel deploy --prod
```

### Git-based flow

With the project linked to GitHub:

- Push to a non-production branch → preview deployment
- Merge / push to the production branch → production deployment

Same `vercel.json` services and rewrites apply.

---

## Local parity (before deploy)

**API** (repo root):

```bash
.venv/bin/pip install -r requirements.txt   # or at least requirements-api.txt + pipeline needs
.venv/bin/uvicorn web.api.main:app --reload --port 8000
```

**Frontend**:

```bash
cd web/frontend
npm install
npm run dev    # http://localhost:5173 — proxies /api → :8000
```

Smoke-check:

- `GET http://127.0.0.1:8000/health` → `{"ok":true}`
- Predict UI against a WC 2026 pairing
- Optional: `POST /wc2026/simulate` (can take tens of seconds; Vercel allows up to 60s)

---

## What Vercel excludes

[`.vercelignore`](../.vercelignore) keeps the upload lean, including:

- `.venv`, `node_modules`, `dist`, `__pycache__`
- `docs/`, `results/`
- Full `data/worldcup.db` and raw CSV caches
- `.env`

Inference DB + model JSON stay included so the backend can load them at runtime.

---

## Checklist

Before a production ship that touches the model or ratings:

1. Pipeline / train complete; `models/xgb_model.json` and `model_meta.json` updated if needed
2. `python -m pipeline.export_inference_db` run; `data/inference.db` committed
3. Local: uvicorn + `npm run dev` — `/health` and Predict work
4. `npx vercel` preview; hit `/api/health` and one predict on the preview URL
5. `npx vercel --prod` (or merge to the production branch)

---

## Troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| Predict 503 / “file not found” | Missing `models/*` or `data/inference.db` in the deployment |
| `/` works but `/predict` is Vercel `NOT_FOUND` | SPA deep link with no rewrite. Usually Root Directory was set to `web/frontend`. Use repo root + Framework **Services**, or ship `web/frontend/vercel.json` SPA rewrite to `index.html` |
| `/api/*` 404 on Vercel | Root Directory is `web/frontend` (frontend-only), Framework is not **Services**, or deploy was not from the repo root |
| Frontend loads, API fails CORS | Unlikely with same-origin `/api`; check rewrite / service status in Vercel |
| `/wc2026/simulate` times out | Workload exceeds function `maxDuration` (60s); reduce work or raise limit on a plan that allows it |
| Huge upload / install | Confirm `.vercelignore` is present; backend should install `requirements-api.txt` only |
| Build hangs ~45min / logs show `vite` “ready” | Build ran `npm run dev` instead of `npm run build`. Frontend service must set `buildCommand: npm run build` (see root `vercel.json`); clear a mistaken Build Command in the dashboard |

Inspect a deployment in the Vercel dashboard (build logs, runtime logs) or with the CLI (`vercel inspect`, `vercel logs`) once the CLI is installed and the project is linked.
