# Website Plan — World Cup 2026 Match Predictor

A public site that presents this project: what we predict, how we built it, how well it works, and interactive ways to run the model. Tone splits by page — product-clear on Home / Predict; research-register on Methodology / Results.

---

## Site goals

1. Explain the problem and approach without requiring the reader to open the repo.
2. Let visitors run predictions for a specific fixture and for a batch of matches.
3. Show where the model is right, where it is wrong, and how confident those calls were.
4. Ground claims in the evaluation protocol (temporal split, log loss, calibration, ablations).

**Out of scope for v1:** live betting, user accounts, retraining in the browser, real-time odds scraping from the UI.

---

## Information architecture

| # | Route | Page | Priority |
|---|--------|------|----------|
| 1 | `/` | Home | P0 |
| 2 | `/methodology` | Scientific process | P0 |
| 3 | `/predict` | Run model — single match | P0 |
| 4 | `/evaluate` | Run / browse — all matches & correctness | P0 |
| 5 | `/results` | Model performance dashboard | P1 |
| 6 | `/wc2026` | World Cup 2026 schedule & predictions | P1 |
| 7 | `/features` | Feature & data explorer | P2 |
| 8 | `/limitations` | Caveats & future work | P2 |
| 9 | `/about` | Project & sources | P2 |

Shared chrome: nav (Home · Methodology · Predict · Evaluate · Results · WC 2026), short footer with data sources and “probabilities ≠ bets.”

---

## 1. Home — `/`

**Purpose:** One-screen pitch: what this is, one headline metric, clear paths into Predict / Methodology / Evaluate.

### Content

- **Hero:** Project name + one sentence — e.g. probabilistic W/D/L forecasts for international (and WC 2026) matches from point-in-time features.
- **What we predict:** Team A win / Draw / Team B win as a probability vector, not a hard label. Note knockout vs group draw semantics briefly; link to Methodology.
- **Headline numbers** (from `model_meta.json` / METHODOLOGY §6): test-set size, primary log loss vs Elo baseline, optional accuracy — with “competitive matches, 2023+” context.
- **How it works (3 steps):** historical results → Elo / form / squad value → XGBoost softprob (+ neutral symmetrization).
- **CTAs:** Predict a match · Read the methodology · See where we were wrong.
- **Optional strip:** 1–2 featured WC 2026 fixtures with live probabilities (if schedule API/backend is wired).

### Components

- Hero block, metric strip, 3-step process, CTA row, optional fixture cards.

---

## 2. Methodology — `/methodology`

**Purpose:** Research-tone write-up of the scientific process. Primary source: `METHODOLOGY.md`; site can render that report as structured sections (not a raw dump of the whole repo).

### Content outline (research register)

1. **Abstract** — problem, approach, main finding in ~150 words.
2. **Problem formulation** — three-way outcome; shootout / advancement labels; why probabilities over argmax; global model vs per-pairing.
3. **Data** — martj42 international results + shootouts; coverage; cleaning; 1990+ fit window; Elo uses full history.
4. **Feature engineering** — point-in-time Elo (tiered K, home offset), rolling form (5/10), rest days, neutral flag, squad market value (proxy + limitations), optional market-implied features if in production config.
5. **Models** — constant-prior and Elo logistic baselines; XGBoost `multi:softprob`; neutral mirror-and-average.
6. **Evaluation protocol** — temporal split (train ≤2022, test 2023+); competitive test set; log loss (primary), Brier, accuracy; bootstrap CIs; model-selection caveat.
7. **Experiments & ablations** — friendlies vs competitive-only; squad on/off; market features if present; what entered production and why.
8. **Calibration & error analysis** — draw calibration; slices by Elo gap / match type (from training analysis).
9. **Limitations & future work** — pointer to full Limitations page / TODO (Poisson goals, SHAP, rolling CV, confederation slices).
10. **Reproducibility** — pipeline stages, cutoffs, seed, link to GitHub / `README.md`.

### Components

- Sticky section nav, equation/notation callouts where useful, tables (feature list, experiment grid), footnotes for sources, “Download methodology PDF” later if desired.

---

## 3. Predict — single match — `/predict`

**Purpose:** Interactive “run the model” for two teams (and venue), matching `predict.py` / `main.py` behavior.

### Content & UX

- **Inputs:** Team A, Team B (FIFA code or searchable name), venue mode (neutral / home advantage for A / infer from WC schedule if fixture exists).
- **Optional:** Match date / cutoff (default: today; for schedule fixtures, `min(today, match_date)`).
- **Output:** Probability bar or pie for A win / Draw / B win; stated favorite + confidence (e.g. max prob); Elo and key feature snapshot used for the call.
- **Explainability (v1 light):** top features by global importance from `model_meta.json`; per-match SHAP only if/when implemented.
- **Copy:** short disclaimer — model uncertainty, label definition, not betting advice.
- **Empty / error states:** unknown team, same team twice, missing features for a side.

### Components

- Team pickers, venue toggle, “Predict” action, probability viz, feature snapshot panel, disclaimer.

### Backend note

- API wrapping existing predict path (preloaded model + feature DB), not retrain-on-request for v1.

---

## 4. Evaluate — batch & correctness — `/evaluate`

**Purpose:** Run or browse predictions over many matches and see hits vs misses — the “where we got it right and wrong” surface.

### Modes

**A. Holdout explorer (default, no live compute)**  
Browse precomputed predictions on the competitive 2023+ test set (or a stored backtest artifact).

- Filters: date range, tournament/friendly, Elo gap bins, outcome type, correct vs incorrect, high vs low confidence.
- Table: date, teams, predicted probs, predicted class, actual result, correct?, log loss contribution / surprise.
- Summary chips: overall accuracy, log loss on filtered subset, confusion-style counts (pred × actual).
- Detail drawer: one match → full probability vector, features, short narrative (“favored A by Elo; draw realized”).

**B. Custom batch (optional v1.1)**  
Upload or select a list of fixtures → return predictions +, if results exist, correctness. Cap batch size; rate-limit.

**C. WC 2026 live scorecard (ties to `/wc2026`)**  
As the tournament progresses: scheduled predictions vs completed results; running tally of correct argmax and average log loss on played matches.

### Components

- Mode tabs, filter bar, results table, summary metrics, match detail panel, confusion / calibration mini-charts for the current filter.

---

## 5. Results — `/results` (recommended)

**Purpose:** Static-but-data-driven performance dashboard so Methodology stays prose-first and numbers live here.

### Content

- Headline comparison: constant prior vs Elo logistic vs production XGBoost (log loss, Brier, accuracy + CIs if available).
- Ablation table (configs from training grid).
- Feature importance: permutation + gain charts.
- Calibration plots / tables by outcome (especially draws).
- Error slices: by Elo difference, neutral vs home, match competitiveness (whatever `train.py` already exports).

### Components

- Metric cards, comparison table, charts, “as of cutoff date” stamp from `model_meta.json`.

---

## 6. World Cup 2026 — `/wc2026` (recommended)

**Purpose:** Tournament-facing view of the same model.

### Content

- Schedule list/grid from `download_schedule.py` data: group stage → knockouts as resolved.
- Per fixture: date, venue/host inference, predicted probabilities, status (upcoming / final).
- After kickoff: actual result + correct/incorrect badge.
- Optional: simple “group outlook” or “most likely surprise” based on current probs (careful wording).

### Components

- Stage filter, fixture list, probability chips, sync note (“schedule last refreshed …”).

---

## 7. Features & data — `/features` (nice to have)

**Purpose:** Make the feature store legible without reading `feature_engineering.py`.

### Content

- Glossary of each production feature (definition, point-in-time rule, missingness).
- Squad-value proxy explained with its known biases.
- Optional: pick a team → current Elo, form window, squad value snapshot (read-only from DB).

---

## 8. Limitations — `/limitations` (nice to have)

**Purpose:** Honest research framing; builds trust.

### Content

- Label mixture (90′ vs ET/penalties); draw unavailability in knockouts.
- Squad value and dual-national issues.
- Untuned hyperparameters; holdout reuse caveat.
- No in-match / injury / lineup features.
- Deferred work from `TODO.md` (Poisson goals, SHAP, rolling CV, confederation slices).

Can be a section of Methodology instead of a separate route if you want a smaller IA; separate page helps Home stay short.

---

## 9. About — `/about` (nice to have)

### Content

- One paragraph project origin; link to GitHub.
- Data credits: martj42, transfermarkt-datasets, eloratings.net scheme, FIFA codes.
- Stack: Python pipeline, XGBoost, SQLite; web stack TBD.
- Contact / how to cite (optional).

---

## What else (beyond your three asks)

Recommended additions, ranked:

1. **Results dashboard** — methodology prose ≠ charts; visitors expect a numbers page.
2. **WC 2026 hub** — natural product surface for this repo; Evaluate can feed off the same store.
3. **Limitations** — research tone without burying caveats in an appendix nobody opens.
4. **Feature glossary / team snapshot** — answers “why these inputs?” without reading code.
5. **About & sources** — attribution and reproducibility entry point.

Optional later:

- **Compare to market** — if prematch odds stay in the pipeline, show model vs bookmaker implied probs on Evaluate / Predict.
- **Export** — CSV of filtered evaluate rows; citeable methodology PDF.
- **API docs** — if you expose predict for others.

Defer: user accounts, social share cards as a product focus, live odds trading UI, browser-side training.

---

## Cross-cutting content rules

| Rule | Detail |
|------|--------|
| Probabilities first | Always show full (p_A, p_D, p_B); argmax is secondary. |
| Point-in-time honesty | Show feature cutoff / “as of” date on every prediction. |
| Label clarity | One reusable callout: group draws vs knockout advancement. |
| No overclaim | Prefer “log loss on competitive 2023+ holdout” over “we predict the World Cup.” |
| Mobile | Predict and Evaluate tables must work on small screens (stacked detail > wide grids). |

---

## Suggested v1 build order

1. Home (static) + Methodology (from `METHODOLOGY.md`) + About footer sources.
2. Predict (single match API + UI).
3. Results (charts from `model_meta.json`).
4. Evaluate holdout explorer (precomputed predictions).
5. WC 2026 schedule page.
6. Features / Limitations polish; market comparison if data is solid.

---

## Open decisions (resolve before implementation)

- **Web stack:** static site + small predict API vs full-stack app.
- **Hosting model artifact:** load `xgb_model.json` + feature DB on server; never ship training DB to the client if large/sensitive.
- **Freshness:** how often to refresh schedule and refit production model during the tournament.
- **Branding name:** product title vs repo name `world_cup_pred`.
