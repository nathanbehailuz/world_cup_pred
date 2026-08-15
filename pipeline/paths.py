"""Repo-root artifact paths shared by pipeline modules."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = ROOT / "data"
MODELS_DIR = ROOT / "models"
RESULTS_DIR = ROOT / "results"

DB_PATH = DATA_DIR / "worldcup.db"
# Slim DB for live predict (team_ratings + schedule). Prefer this when present.
INFERENCE_DB_PATH = DATA_DIR / "inference.db"
# Precomputed WC 2026 API payload (no xgboost needed at serve time).
WC2026_PREDICTIONS_PATH = DATA_DIR / "wc2026_predictions.json"
MODEL_PATH = MODELS_DIR / "xgb_model.json"
META_PATH = MODELS_DIR / "model_meta.json"


def resolve_inference_db() -> Path:
    """DB used by predict / wc_simulate (slim inference.db when available)."""
    if INFERENCE_DB_PATH.exists():
        return INFERENCE_DB_PATH
    return DB_PATH

HUGGINGFACE_CACHE = DATA_DIR / "raw_matches_with_odds.csv"
PREDICTZ_CACHE = DATA_DIR / "predictz_predictions.csv"
WC2026_BACKTEST_PATH = RESULTS_DIR / "wc2026_backtest.csv"
HOLDOUT_EVALUATE_PATH = RESULTS_DIR / "holdout_evaluate.json"
FRONTEND_HOLDOUT_PATH = ROOT / "web" / "frontend" / "src" / "data" / "holdout.json"
