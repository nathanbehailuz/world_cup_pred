"""Train baseline and XGBoost models on international match features."""

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
    "home_days_since_last",
    "away_days_since_last",
    "neutral",
    "competitive",
    "home_elo",
    "away_elo",
]


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


def train_baseline(
    train: pd.DataFrame, test: pd.DataFrame
) -> tuple[LogisticRegression, StandardScaler, dict]:
    x_train = train[["elo_diff"]].values
    x_test = test[["elo_diff"]].values
    y_train = train["outcome"].values
    y_test = test["outcome"].values

    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_test_scaled = scaler.transform(x_test)

    model = LogisticRegression(
        max_iter=1000,
        random_state=42,
    )
    model.fit(x_train_scaled, y_train)
    proba = model.predict_proba(x_test_scaled)
    metrics = evaluate("Baseline (logistic regression on elo_diff)", y_test, proba)
    return model, scaler, metrics


def train_xgboost(
    train: pd.DataFrame, test: pd.DataFrame
) -> tuple[xgb.XGBClassifier, dict]:
    x_train = train[FEATURE_COLUMNS].values
    x_test = test[FEATURE_COLUMNS].values
    y_train = train["outcome"].values
    y_test = test["outcome"].values

    model = xgb.XGBClassifier(
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
    model.fit(
        x_train,
        y_train,
        eval_set=[(x_test, y_test)],
        verbose=False,
    )
    proba = model.predict_proba(x_test)
    metrics = evaluate("XGBoost", y_test, proba)
    return model, metrics


def save_model(
    model: xgb.XGBClassifier,
    baseline_model: LogisticRegression,
    baseline_scaler: StandardScaler,
    baseline_metrics: dict,
    xgb_metrics: dict,
) -> None:
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(MODEL_PATH)

    meta = {
        "feature_columns": FEATURE_COLUMNS,
        "train_cutoff": TRAIN_CUTOFF,
        "min_match_date": MIN_MATCH_DATE,
        "baseline_metrics": baseline_metrics,
        "xgb_metrics": xgb_metrics,
        "outcome_labels": ["home_win", "draw", "away_win"],
    }
    META_PATH.write_text(json.dumps(meta, indent=2))
    print(f"\nSaved XGBoost model to {MODEL_PATH}")
    print(f"Saved metadata to {META_PATH}")


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"{DB_PATH} not found. Run feature_engineering.py first."
        )

    conn = sqlite3.connect(DB_PATH)
    df = load_features(conn)
    conn.close()

    train, test = temporal_split(df)
    print(f"Training set: {len(train)} matches (< {TRAIN_CUTOFF})")
    print(f"Test set:     {len(test)} matches (>= {TRAIN_CUTOFF})")

    if len(train) == 0 or len(test) == 0:
        raise ValueError("Train or test set is empty. Check date filters.")

    baseline_model, baseline_scaler, baseline_metrics = train_baseline(train, test)
    xgb_model, xgb_metrics = train_xgboost(train, test)

    print("\nComparison (lower is better for log_loss / brier_score):")
    for metric in ("log_loss", "brier_score", "accuracy"):
        b = baseline_metrics[metric]
        x = xgb_metrics[metric]
        winner = "XGBoost" if (
            (metric != "accuracy" and x < b) or (metric == "accuracy" and x > b)
        ) else "Baseline"
        print(f"  {metric}: baseline={b:.4f}, xgb={x:.4f} -> {winner}")

    save_model(
        xgb_model,
        baseline_model,
        baseline_scaler,
        baseline_metrics,
        xgb_metrics,
    )


if __name__ == "__main__":
    main()
