"""Train baseline and XGBoost models on international match features.

Runs two experiments on a temporal split (training on all matches vs
competitive-only). Both are evaluated on the SAME competitive-only test set,
since the target domain (World Cup matches) is competitive. The better
configuration is then refit on all available data as the production model.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss
from sklearn.preprocessing import StandardScaler

DB_PATH = Path(__file__).parent / "data" / "worldcup.db"
MODEL_PATH = Path(__file__).parent / "models" / "xgb_model.json"
META_PATH = Path(__file__).parent / "models" / "model_meta.json"

TRAIN_CUTOFF = "2023-01-01"
MIN_MATCH_DATE = "1990-01-01"

FEATURE_COLUMNS = [
    "elo_diff",
    "form_pts_5_diff",
    "form_gd_5_diff",
    "form_pts_10_diff",
    "form_gd_10_diff",
    "form_gf_5_diff",
    "form_ga_5_diff",
    "form_gf_10_diff",
    "form_ga_10_diff",
    "home_days_since_last",
    "away_days_since_last",
    "neutral",
    "competitive",
    "home_elo",
    "away_elo",
]

XGB_PARAMS = dict(
    objective="multi:softprob",
    num_class=3,
    max_depth=4,
    learning_rate=0.1,
    n_estimators=300,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    eval_metric="mlogloss",
)


def brier_score_multiclass(y_true: np.ndarray, proba: np.ndarray) -> float:
    one_hot = np.zeros_like(proba)
    one_hot[np.arange(len(y_true)), y_true] = 1.0
    return float(np.mean(np.sum((proba - one_hot) ** 2, axis=1)))


def load_features(conn: sqlite3.Connection) -> pd.DataFrame:
    df = pd.read_sql_query("SELECT * FROM features", conn)
    df = df[df["date"] >= MIN_MATCH_DATE].copy()
    return df


def temporal_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    train = df[df["date"] < TRAIN_CUTOFF].copy()
    test = df[df["date"] >= TRAIN_CUTOFF].copy()
    return train, test


def evaluate(name: str, y_true: np.ndarray, proba: np.ndarray) -> dict:
    preds = proba.argmax(axis=1)
    metrics = {
        "log_loss": float(log_loss(y_true, proba, labels=[0, 1, 2])),
        "brier_score": brier_score_multiclass(y_true, proba),
        "accuracy": float(accuracy_score(y_true, preds)),
    }
    print(f"\n{name}")
    for key, value in metrics.items():
        print(f"  {key}: {value:.4f}")
    return metrics


def train_baseline(train: pd.DataFrame, test: pd.DataFrame, label: str) -> dict:
    scaler = StandardScaler()
    x_train = scaler.fit_transform(train[["elo_diff"]].values)
    x_test = scaler.transform(test[["elo_diff"]].values)

    model = LogisticRegression(max_iter=1000, random_state=42)
    model.fit(x_train, train["outcome"].values)
    proba = model.predict_proba(x_test)
    return evaluate(f"[{label}] Baseline (logistic on elo_diff)",
                    test["outcome"].values, proba)


def train_xgboost(
    train: pd.DataFrame, test: pd.DataFrame, label: str
) -> tuple[xgb.XGBClassifier, dict]:
    model = xgb.XGBClassifier(**XGB_PARAMS)
    model.fit(
        train[FEATURE_COLUMNS].values,
        train["outcome"].values,
        eval_set=[(test[FEATURE_COLUMNS].values, test["outcome"].values)],
        verbose=False,
    )
    proba = model.predict_proba(test[FEATURE_COLUMNS].values)
    metrics = evaluate(f"[{label}] XGBoost", test["outcome"].values, proba)
    return model, metrics


def run_experiment(
    df: pd.DataFrame, test: pd.DataFrame, competitive_only: bool
) -> dict:
    """Train on the chosen subset; evaluate on the shared competitive test set."""
    label = "train-competitive-only" if competitive_only else "train-all-matches"
    train_pool, _ = temporal_split(df)
    train = (
        train_pool[train_pool["competitive"] == 1] if competitive_only else train_pool
    )

    print(f"\n=== Experiment: {label} ===")
    print(f"Training set: {len(train)} matches (< {TRAIN_CUTOFF})")
    print(f"Test set:     {len(test)} competitive matches (>= {TRAIN_CUTOFF})")

    baseline_metrics = train_baseline(train, test, label)
    _, xgb_metrics = train_xgboost(train, test, label)

    return {
        "label": label,
        "competitive_only": competitive_only,
        "n_train": len(train),
        "n_test": len(test),
        "baseline_metrics": baseline_metrics,
        "xgb_metrics": xgb_metrics,
    }


def refit_production_model(
    df: pd.DataFrame, competitive_only: bool
) -> tuple[xgb.XGBClassifier, int]:
    """Refit on ALL available data (no holdout) for real-world predictions."""
    data = df[df["competitive"] == 1] if competitive_only else df
    model = xgb.XGBClassifier(**XGB_PARAMS)
    model.fit(data[FEATURE_COLUMNS].values, data["outcome"].values, verbose=False)
    return model, len(data)


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"{DB_PATH} not found. Run feature_engineering.py first."
        )

    conn = sqlite3.connect(DB_PATH)
    df = load_features(conn)
    conn.close()

    # Shared test set: competitive matches only (the target domain for 2026).
    _, test_pool = temporal_split(df)
    test = test_pool[test_pool["competitive"] == 1].copy()

    experiments = [
        run_experiment(df, test, competitive_only=False),
        run_experiment(df, test, competitive_only=True),
    ]

    print("\n=== Experiment comparison (same competitive test set) ===")
    for exp in experiments:
        m = exp["xgb_metrics"]
        print(f"  {exp['label']}: log_loss={m['log_loss']:.4f}, "
              f"brier={m['brier_score']:.4f}, acc={m['accuracy']:.4f}")

    best = min(experiments, key=lambda e: e["xgb_metrics"]["log_loss"])
    print(f"\nBest configuration by log loss: {best['label']}")

    model, n_fit = refit_production_model(df, best["competitive_only"])
    print(f"Refit production model on all {n_fit} matches "
          f"({best['label']}, through {df['date'].max()}).")

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(MODEL_PATH)

    meta = {
        "feature_columns": FEATURE_COLUMNS,
        "train_cutoff": TRAIN_CUTOFF,
        "min_match_date": MIN_MATCH_DATE,
        "selected_config": best["label"],
        "competitive_only": best["competitive_only"],
        "production_fit_rows": n_fit,
        "production_fit_through": df["date"].max(),
        "experiments": experiments,
        "outcome_labels": ["home_win", "draw", "away_win"],
    }
    META_PATH.write_text(json.dumps(meta, indent=2))
    print(f"\nSaved production XGBoost model to {MODEL_PATH}")
    print(f"Saved metadata to {META_PATH}")


if __name__ == "__main__":
    main()
