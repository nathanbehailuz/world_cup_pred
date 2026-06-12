"""Train baseline and XGBoost models on international match features.

Runs a four-configuration experiment grid on a temporal split, all evaluated
on the same competitive-only test set. The best configuration is refit on all
available data as the production model.
"""

from __future__ import annotations

import argparse
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

SQUAD_FEATURE_COLUMNS = [
    "home_squad_value_log",
    "away_squad_value_log",
    "squad_value_log_diff",
]

BASE_FEATURE_COLUMNS = [
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

FULL_FEATURE_COLUMNS = BASE_FEATURE_COLUMNS + SQUAD_FEATURE_COLUMNS

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

OUTCOME_NAMES = ("home_win", "draw", "away_win")


def diff_columns(feature_columns: list[str]) -> list[str]:
    return [c for c in feature_columns if c.endswith("_diff")]


def swap_columns(feature_columns: list[str]) -> list[tuple[str, str]]:
    swaps = [
        ("home_days_since_last", "away_days_since_last"),
        ("home_elo", "away_elo"),
    ]
    if "home_squad_value_log" in feature_columns:
        swaps.append(("home_squad_value_log", "away_squad_value_log"))
    return swaps


def mirror_features(
    df: pd.DataFrame, feature_columns: list[str]
) -> pd.DataFrame:
    """Swap the home and away slots (meaningful only for neutral-venue rows)."""
    mirrored = df.copy()
    for col in diff_columns(feature_columns):
        mirrored[col] = -df[col]
    for a, b in swap_columns(feature_columns):
        mirrored[a] = df[b].values
        mirrored[b] = df[a].values
    return mirrored


def symmetrize_neutral(
    proba: np.ndarray, proba_mirrored: np.ndarray, test: pd.DataFrame
) -> np.ndarray:
    """Average mirrored predictions for neutral-venue rows."""
    out = proba.copy()
    mask = (test["neutral"] == 1).values
    out[mask] = (proba[mask] + proba_mirrored[mask, ::-1]) / 2.0
    return out


def brier_score_multiclass(y_true: np.ndarray, proba: np.ndarray) -> float:
    one_hot = np.zeros_like(proba)
    one_hot[np.arange(len(y_true)), y_true] = 1.0
    return float(np.mean(np.sum((proba - one_hot) ** 2, axis=1)))


def calibration_table(
    y_true: np.ndarray, proba: np.ndarray, class_idx: int, n_bins: int = 10
) -> list[dict]:
    """Bin predicted probability for one class vs empirical frequency."""
    p = proba[:, class_idx]
    hits = (y_true == class_idx).astype(float)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_idx = np.clip(np.digitize(p, edges[1:-1]), 0, n_bins - 1)
    rows = []
    for b in range(n_bins):
        mask = bin_idx == b
        n = int(mask.sum())
        if n == 0:
            continue
        rows.append(
            {
                "bin": f"{edges[b]:.1f}-{edges[b + 1]:.1f}",
                "n": n,
                "mean_predicted": float(p[mask].mean()),
                "empirical": float(hits[mask].mean()),
            }
        )
    return rows


def print_calibration(y_true: np.ndarray, proba: np.ndarray) -> dict:
    """Print per-class calibration tables; return them for the metadata file."""
    tables: dict = {}
    print("\n=== Calibration check (production config, test set) ===")
    for idx, name in enumerate(OUTCOME_NAMES):
        rows = calibration_table(y_true, proba, idx)
        tables[name] = rows
        print(f"\n  {name}:")
        print("    bin        n     predicted  empirical")
        for row in rows:
            print(
                f"    {row['bin']:<9s}{row['n']:>6d}     "
                f"{row['mean_predicted']:.3f}      {row['empirical']:.3f}"
            )
    return tables


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
    proba_mirrored = model.predict_proba(
        scaler.transform(-test[["elo_diff"]].values)
    )
    proba = symmetrize_neutral(proba, proba_mirrored, test)
    return evaluate(
        f"[{label}] Baseline (logistic on elo_diff)",
        test["outcome"].values,
        proba,
    )


def train_xgboost(
    train: pd.DataFrame,
    test: pd.DataFrame,
    label: str,
    feature_columns: list[str],
) -> tuple[xgb.XGBClassifier, dict, np.ndarray]:
    model = xgb.XGBClassifier(**XGB_PARAMS)
    model.fit(
        train[feature_columns].values,
        train["outcome"].values,
        eval_set=[(test[feature_columns].values, test["outcome"].values)],
        verbose=False,
    )
    proba = model.predict_proba(test[feature_columns].values)
    proba_mirrored = model.predict_proba(
        mirror_features(test, feature_columns)[feature_columns].values
    )
    proba = symmetrize_neutral(proba, proba_mirrored, test)
    metrics = evaluate(f"[{label}] XGBoost", test["outcome"].values, proba)
    return model, metrics, proba


def run_experiment(
    df: pd.DataFrame,
    test: pd.DataFrame,
    *,
    competitive_only: bool,
    feature_columns: list[str],
    label: str,
) -> dict:
    """Train on the chosen subset; evaluate on the shared competitive test set."""
    train_pool, _ = temporal_split(df)
    train = (
        train_pool[train_pool["competitive"] == 1] if competitive_only else train_pool
    )

    print(f"\n=== Experiment: {label} ===")
    print(f"Features:     {len(feature_columns)} ({', '.join(feature_columns)})")
    print(f"Training set: {len(train)} matches (< {TRAIN_CUTOFF})")
    print(f"Test set:     {len(test)} competitive matches (>= {TRAIN_CUTOFF})")

    baseline_metrics = train_baseline(train, test, label)
    _, xgb_metrics, xgb_proba = train_xgboost(
        train, test, label, feature_columns=feature_columns
    )

    return {
        "label": label,
        "competitive_only": competitive_only,
        "feature_columns": feature_columns,
        "n_features": len(feature_columns),
        "n_train": len(train),
        "n_test": len(test),
        "baseline_metrics": baseline_metrics,
        "xgb_metrics": xgb_metrics,
        "_xgb_proba": xgb_proba,
    }


def refit_production_model(
    df: pd.DataFrame,
    competitive_only: bool,
    feature_columns: list[str],
) -> tuple[xgb.XGBClassifier, int]:
    """Refit on ALL available data (no holdout) for real-world predictions."""
    data = df[df["competitive"] == 1] if competitive_only else df
    model = xgb.XGBClassifier(**XGB_PARAMS)
    model.fit(data[feature_columns].values, data["outcome"].values, verbose=False)
    return model, len(data)


def load_model_meta() -> dict | None:
    if not META_PATH.exists():
        return None
    return json.loads(META_PATH.read_text())


def training_is_current(cutoff: str | None, retrain: bool) -> bool:
    if retrain or not MODEL_PATH.exists():
        return False
    meta = load_model_meta()
    if meta is None:
        return False
    if meta.get("feature_cutoff") != cutoff:
        return False
    # Require the four-experiment ablation grid from this pipeline version.
    return len(meta.get("experiments") or []) >= 4


def run_train(cutoff: str | None = None, retrain: bool = False) -> bool:
    """Train production model. Returns True if training ran."""
    if training_is_current(cutoff, retrain=retrain):
        print(
            f"Model already trained for cutoff={cutoff!r} "
            f"(use --retrain to force)."
        )
        return False

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"{DB_PATH} not found. Run feature_engineering.py first."
        )

    conn = sqlite3.connect(DB_PATH)
    df = load_features(conn)
    conn.close()

    _, test_pool = temporal_split(df)
    test = test_pool[test_pool["competitive"] == 1].copy()

    no_competitive_features = [c for c in FULL_FEATURE_COLUMNS if c != "competitive"]
    no_squad_features = BASE_FEATURE_COLUMNS

    experiments = [
        run_experiment(
            df,
            test,
            competitive_only=False,
            feature_columns=FULL_FEATURE_COLUMNS,
            label="train-all-matches-full",
        ),
        run_experiment(
            df,
            test,
            competitive_only=True,
            feature_columns=FULL_FEATURE_COLUMNS,
            label="train-competitive-only-full",
        ),
        run_experiment(
            df,
            test,
            competitive_only=False,
            feature_columns=no_competitive_features,
            label="train-all-matches-no-competitive-flag",
        ),
        run_experiment(
            df,
            test,
            competitive_only=False,
            feature_columns=no_squad_features,
            label="train-all-matches-no-squad",
        ),
    ]

    print("\n=== Experiment comparison (same competitive test set) ===")
    for exp in experiments:
        m = exp["xgb_metrics"]
        print(
            f"  {exp['label']}: log_loss={m['log_loss']:.4f}, "
            f"brier={m['brier_score']:.4f}, acc={m['accuracy']:.4f}"
        )

    best = min(experiments, key=lambda e: e["xgb_metrics"]["log_loss"])
    print(f"\nBest configuration by log loss: {best['label']}")

    calibration = print_calibration(test["outcome"].values, best["_xgb_proba"])
    for exp in experiments:
        exp.pop("_xgb_proba", None)

    prod_features = best["feature_columns"]
    model, n_fit = refit_production_model(
        df, best["competitive_only"], feature_columns=prod_features
    )
    print(
        f"Refit production model on all {n_fit} matches "
        f"({best['label']}, through {df['date'].max()})."
    )

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(MODEL_PATH)

    meta = {
        "feature_columns": prod_features,
        "feature_cutoff": cutoff,
        "train_cutoff": TRAIN_CUTOFF,
        "min_match_date": MIN_MATCH_DATE,
        "selected_config": best["label"],
        "competitive_only": best["competitive_only"],
        "production_fit_rows": n_fit,
        "production_fit_through": df["date"].max(),
        "experiments": experiments,
        "calibration": calibration,
        "outcome_labels": ["home_win", "draw", "away_win"],
    }
    META_PATH.write_text(json.dumps(meta, indent=2))
    print(f"\nSaved production XGBoost model to {MODEL_PATH}")
    print(f"Saved metadata to {META_PATH}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Train XGBoost production model.")
    parser.add_argument(
        "--cutoff",
        metavar="YYYY-MM-DD",
        help="Feature cutoff used in feature_engineering (stored in metadata)",
    )
    parser.add_argument(
        "--retrain", action="store_true", help="Force retraining even if cutoff matches"
    )
    args = parser.parse_args()
    run_train(cutoff=args.cutoff, retrain=args.retrain)


if __name__ == "__main__":
    main()
