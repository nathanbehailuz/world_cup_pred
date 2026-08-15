# Website — World Cup 2026 Match Predictor

Public site for this project: what we predict, how we built it, how well it works, and interactive ways to run the model. Product-clear tone on Home / Predict; research register on Methodology / Model Analysis.

**Stack:** React + Vite + Tailwind frontend (`web/frontend`); FastAPI predict/meta API (`web/api`). Brand: **WC 2026 Predictor** with an original WC26 mark (`public/favicon.svg`) in nav and as favicon (not FIFA trademark art).

---

## Site goals

1. Explain the problem and approach without requiring the reader to open the repo.
2. Let visitors run predictions for a specific fixture and browse WC 2026 schedule forecasts.
3. Show where the model is right, where it is wrong, and how confident those calls were.
4. Ground claims in the evaluation protocol (temporal split, log loss, calibration, ablations).

**Out of scope for v1:** live betting, user accounts, retraining in the browser, real-time odds scraping from the UI.

---

## Information architecture

| # | Route | Page | Status |
|---|--------|------|--------|
| 1 | `/` | Home | Shipped |
| 2 | `/methodology` | Scientific process | Shipped |
| 3 | `/predict` | Single-match predict + WC 2026 schedule / live scorecard | Shipped |
| 4 | `/evaluate` | Holdout explorer (hits, misses, surprise) | Shipped |
| 5 | `/analysis` | Model performance dashboard | Shipped |
| 6 | `/features` | Feature & data glossary | Shipped |
| 7 | `/limitations` | Caveats & future work | Shipped |
| 8 | `/about` | Project & sources | Shipped |
| — | `/results` | Redirect → `/analysis` | Compat |
| — | `/wc2026` | Removed; WC surface lives on `/predict` | — |

**Primary nav:** Home · Methodology · Predict · Evaluate · Model Analysis

**More (collapsible):** About · Features · Limitations (desktop dropdown; mobile nested section)

**Footer:** Data Sources / Limitations / Features / Methodology links; research disclaimer (“probabilities ≠ bets”); credit line *Built with love by [Nathan](https://nathanbehailu.vercel.app/)*.

---

## 1. Home — `/`

**Purpose:** One-screen pitch: what this is, headline metrics, paths into Predict / Methodology / Evaluate / Analysis.

### Content

- **Hero:** Brand + headline + short support line (point-in-time W/D/L from Elo, form, squad value). CTAs: Predict a Match · View Methodology.
- **Metric plane:** Model (XGBoost), holdout size, log loss vs Elo, verified competitive test note. Avoid dense research footers (no cutoff / accuracy meta strip on the landing page; detail lives on Model Analysis).
- **What we predict:** Probability vector over Team A win / Draw / Team B win; knockout vs group draw semantics; link to Methodology.
- **Featured forecasts:** Sample WC 2026 group fixtures with probability bars (from schedule API / static fixtures).
- **How it works (3 steps):** data ingestion → feature engineering → XGBoost inference (neutral mirror-and-average).
- **CTAs:** Predict a match · Evaluate predictions · Model analysis.

### Components

- Hero block, metric tiles, featured fixture cards (`TeamFlag` / `ProbabilityBar`), 3-step pipeline, CTA row.

---

## 2. Methodology — `/methodology`

**Purpose:** Research-tone write-up of the scientific process. Content is structured JSON (`web/frontend/src/data/methodology.json`) derived from `docs/METHODOLOGY.md`, not a raw markdown dump.

### Content outline (research register)

1. **Abstract** — problem, approach, main finding in ~150 words.
2. **Problem formulation** — three-way outcome; shootout / advancement labels; why probabilities over argmax; global model vs per-pairing.
3. **Data** — martj42 international results + shootouts; coverage; cleaning; 1990+ fit window; Elo uses full history.
4. **Feature engineering** — point-in-time Elo (tiered K, home offset), rolling form (5/10), rest days, neutral flag, squad market value (proxy + limitations).
5. **Models** — constant-prior and Elo logistic baselines; XGBoost `multi:softprob`; neutral mirror-and-average.
6. **Evaluation protocol** — temporal split (train ≤2022, test 2023+); competitive test set; log loss (primary), Brier, accuracy; bootstrap CIs; model-selection caveat.
7. **Experiments & ablations** — friendlies vs competitive-only; squad on/off; what entered production and why.
8. **Calibration & error analysis** — draw calibration; slices by Elo gap / match type.
9. **Limitations & future work** — pointer to Limitations page / TODO (Poisson goals, SHAP, rolling CV, confederation slices).
10. **Reproducibility** — pipeline stages, cutoffs, seed, link to GitHub / `README.md`.

### Components

- Sticky section nav, **KaTeX** display math for notation callouts and light `$...$` inline math in paragraphs, tables (feature list, experiment grid), footnotes for sources.

---

## 3. Predict — `/predict`

**Purpose:** Interactive “run the model” for two teams, plus the World Cup 2026 schedule / live scorecard surface (formerly a separate `/wc2026` page).

### Content & UX

- **Single match:** Team A, Team B (searchable names / FIFA codes via team list), venue mode (neutral / home advantage / infer from WC schedule when applicable).
- **Output:** Probability bar for A win / Draw / B win; Elo and key feature snapshot when available.
- **WC 2026:** Schedule list from `download_schedule.py` artifacts / API; per fixture date, venue inference, predicted probabilities, status; as matches complete, actual result and running tally (correct argmax, mean log loss on played matches).
- **Copy:** short disclaimer — model uncertainty, label definition, not betting advice.
- **Empty / error states:** unknown team, same team twice, missing features for a side.

### Components

- Team pickers (`TeamFlag`), venue controls, Predict action, probability viz, fixture list / live summary, disclaimer.

### Backend note

- API wraps existing predict path (preloaded model + feature DB); no retrain-on-request for v1. Mock fallback for meta/holdout when API is down; live predict requires the backend.

---

## 4. Evaluate — `/evaluate`

**Purpose:** Browse precomputed predictions on the competitive 2023+ holdout and see hits vs misses.

### Modes

**Holdout explorer (shipped)**  
Filters, table (date, teams, probs, predicted class, actual, correct?, log loss), summary metrics, match detail panel.

**Custom batch (optional later)**  
Upload or select fixtures → predictions (+ correctness if results exist). Cap batch size; rate-limit.

### Components

- Filter bar, results table, summary metrics, match detail panel, confusion matrix where useful.

---

## 5. Model Analysis — `/analysis`

**Purpose:** Performance dashboard so Methodology stays prose-first and numbers live here. Replaces the planned `/results` route (`/results` redirects here).

### Content

- Headline comparison: constant prior vs Elo logistic vs production XGBoost (log loss, Brier, accuracy + CIs when available).
- Ablation table (configs from training grid).
- Feature importance: permutation + gain.
- Calibration by outcome (especially draws).
- Error slices: by Elo difference, neutral vs home, true outcome class.
- “As of” cutoffs from `model_meta.json`.

### Components

- Metric cards, comparison tables, importance lists, calibration / slice panels, sample predictions.

---

## 6. Features & data — `/features`

**Purpose:** Make the feature store legible without reading `feature_engineering.py`.

### Content

- Glossary of production features (definition, point-in-time rule, missingness).
- Squad-value proxy explained with known biases.
- Optional later: pick a team → current Elo, form window, squad value snapshot.

---

## 7. Limitations — `/limitations`

**Purpose:** Honest research framing; builds trust.

### Content

- Label mixture (90′ vs ET/penalties); draw unavailability in knockouts.
- Squad value and dual-national issues.
- Untuned hyperparameters; holdout reuse caveat.
- No in-match / injury / lineup features.
- Deferred work from `TODO.md` (Poisson goals, SHAP, rolling CV, confederation slices).

---

## 8. About — `/about`

### Content

- Project origin; link to GitHub.
- Data credits: martj42, transfermarkt-datasets, eloratings.net scheme, FIFA codes.
- Stack: Python pipeline, XGBoost, SQLite; React / Vite / Tailwind frontend; FastAPI API.
- Optional contact / how to cite.

---

## Cross-cutting content rules

| Rule | Detail |
|------|--------|
| Probabilities first | Always show full (p_A, p_D, p_B); argmax is secondary. |
| Point-in-time honesty | Show feature cutoff / “as of” date on predictions and Model Analysis; keep Home free of dense meta footers. |
| Label clarity | Reusable callout: group draws vs knockout advancement. |
| No overclaim | Prefer “log loss on competitive 2023+ holdout” over “we predict the World Cup.” |
| Product copy | Prefer clear product language on Home / Predict; reserve research jargon for Methodology / Analysis. |
| Mobile | Predict and Evaluate tables must work on small screens (stacked detail > wide grids). |
| Branding | Use WC 2026 Predictor + original mark; do not ship official FIFA World Cup crest artwork. |

---

## Suggested follow-ups (optional)

1. Lazy-load KaTeX on Methodology only (smaller first-paint JS).
2. Custom batch evaluate upload.
3. Compare to market odds if prematch odds stay in the pipeline.
4. Export CSV of filtered evaluate rows; citeable methodology PDF.
5. API docs if predict is exposed publicly.

Defer: user accounts, social share as a product focus, live odds trading UI, browser-side training.

---

## Resolved decisions

- **Web stack:** React + Vite frontend + FastAPI predict/meta API.
- **Hosting model artifact:** load model + feature DB on the server; client gets JSON meta / holdout / fixtures as needed.
- **Branding name:** **WC 2026 Predictor**.
- **WC surface:** folded into `/predict` rather than a standalone `/wc2026` page.
- **Results vs analysis:** `/analysis` is the dashboard; `/results` redirects for old links.
