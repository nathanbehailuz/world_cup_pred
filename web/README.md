# Website

Public site plan: [`docs/WEBSITE.md`](../docs/WEBSITE.md). Visual reference: [`docs/design.html`](../docs/design.html).

| Path | Role |
|------|------|
| `frontend/` | React + Vite + Tailwind UI (implemented) |
| `api/` | Predict / evaluate API wrapping `pipeline` (not built yet) |

## Frontend

```bash
cd web/frontend
npm install
npm run dev      # http://localhost:5173
npm run build    # production build → dist/
```

### Stack

- React 19 + TypeScript + Vite
- React Router 7
- Tailwind CSS v4 (`@tailwindcss/vite`)
- Design tokens / layout mirrored from `docs/design.html`

### Routes

| Route | Page |
|-------|------|
| `/` | Home |
| `/methodology` | Methodology |
| `/predict` | Single-match predict (mock) |
| `/evaluate` | Holdout explorer (mock) |
| `/results` | Performance dashboard (`model_meta` snapshot) |
| `/wc2026` | WC 2026 schedule & predictions (backtest JSON) |
| `/features` | Feature glossary |
| `/limitations` | Caveats |
| `/about` | Sources & stack |

### Mock / API swap

Pages call `src/api/client.ts`. With no `VITE_API_BASE`, responses come from local placeholders:

- `src/data/teams.json` — FIFA codes
- `src/data/model_meta.json` — slimmed from `models/model_meta.json`
- `src/data/wc2026_fixtures.json` — from `results/wc2026_backtest.csv`
- `src/data/holdout.ts` — Evaluate table rows

When the API exists:

```bash
VITE_API_BASE=http://localhost:8000 npm run dev
```

The client will `fetch` `/predict`, `/evaluate/holdout`, `/model/meta`, `/wc2026/fixtures`, `/teams`.
