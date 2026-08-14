"""Backtest the train.py model on FIFA World Cup 2026 finals matches.

Trains on the original temporal split (date < 2023-01-01) and scores all
WC 2026 matches using point-in-time feature rows (no post-match leakage).
"""

from __future__ import annotations

import sqlite3

import numpy as np
import pandas as pd
import xgboost as xgb

from .download_data import DB_PATH
from .paths import WC2026_BACKTEST_PATH
from .train import (
    FULL_WITH_MARKET_COLUMNS,
    MIN_MATCH_DATE,
    OUTCOME_NAMES,
    TRAIN_CUTOFF,
    XGB_PARAMS,
    compute_metrics,
    evaluate,
    mirror_features,
    symmetrize_neutral,
)

WC_START = "2026-06-11"
GROUP_STAGE_END = "2026-06-27"
OUT_PATH = WC2026_BACKTEST_PATH


def load_feature_frame(conn: sqlite3.Connection) -> pd.DataFrame:
    df = pd.read_sql_query(
        """
        SELECT
            f.*,
            m.tournament,
            m.home_score,
            m.away_score,
            s.round_name,
            s.group_name
        FROM features f
        JOIN matches m
          ON f.date = m.date
         AND f.home_team = m.home_team
         AND f.away_team = m.away_team
        LEFT JOIN schedule s
          ON f.date = s.date
         AND f.home_team = s.home_team
         AND f.away_team = s.away_team
        WHERE f.date >= ?
        """,
        conn,
        params=(MIN_MATCH_DATE,),
    )
    return df


def stage_label(date: str, round_name, group_name) -> str:
    if pd.notna(group_name) and str(group_name).strip():
        return "group"
    if pd.notna(round_name) and str(round_name).strip():
        # Fixture feed uses numeric RoundNumber; groups are 1–3, KO from 4+.
        try:
            if int(str(round_name).strip()) <= 3:
                return "group"
            return "knockout"
        except ValueError:
            pass
    return "group" if date <= GROUP_STAGE_END else "knockout"


def home_advantage_label(neutral, home_team: str) -> str:
    """Country with venue home advantage, or 'none' for true neutrals."""
    if int(neutral) == 0:
        return home_team
    return "none"


def print_confusion(y_true: np.ndarray, y_pred: np.ndarray) -> None:
    print("\nConfusion (rows=actual, cols=predicted):")
    header = " " * 12 + "".join(f"{name:>12s}" for name in OUTCOME_NAMES)
    print(header)
    for i, actual in enumerate(OUTCOME_NAMES):
        counts = [(y_true == i) & (y_pred == j) for j in range(3)]
        row = "".join(f"{int(c.sum()):>12d}" for c in counts)
        print(f"{actual:<12s}{row}")


def print_stage_metrics(eval_df: pd.DataFrame, proba: np.ndarray) -> None:
    print("\n=== By stage ===")
    for stage in ("group", "knockout"):
        mask = (eval_df["stage"] == stage).values
        n = int(mask.sum())
        if n == 0:
            continue
        metrics = compute_metrics(eval_df.loc[mask, "outcome"].values, proba[mask])
        print(f"\n{stage} (n={n})")
        for key, value in metrics.items():
            print(f"  {key}: {value:.4f}")


def run_backtest() -> pd.DataFrame:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"{DB_PATH} not found. Run download_data.py first.")

    conn = sqlite3.connect(DB_PATH)
    df = load_feature_frame(conn)
    conn.close()

    feature_columns = list(FULL_WITH_MARKET_COLUMNS)
    missing = [c for c in feature_columns if c not in df.columns]
    if missing:
        raise ValueError(f"Missing feature columns: {missing}")

    train = df[df["date"] < TRAIN_CUTOFF].copy()
    eval_df = df[
        (df["tournament"] == "FIFA World Cup") & (df["date"] >= WC_START)
    ].copy()
    eval_df = eval_df.sort_values(["date", "home_team", "away_team"]).reset_index(
        drop=True
    )
    eval_df["stage"] = [
        stage_label(d, r, g)
        for d, r, g in zip(
            eval_df["date"], eval_df["round_name"], eval_df["group_name"]
        )
    ]
    eval_df["home_advantage"] = [
        home_advantage_label(n, h)
        for n, h in zip(eval_df["neutral"], eval_df["home_team"])
    ]

    if train.empty:
        raise RuntimeError(f"No training rows before {TRAIN_CUTOFF}")
    if eval_df.empty:
        raise RuntimeError(
            "No WC 2026 feature rows found. Re-run feature_engineering.py "
            "with no cutoff."
        )

    print(f"Train: {len(train)} matches (date < {TRAIN_CUTOFF})")
    print(f"Eval:  {len(eval_df)} FIFA World Cup 2026 matches")
    print(f"Features: {len(feature_columns)}")

    model = xgb.XGBClassifier(**XGB_PARAMS)
    model.fit(
        train[feature_columns].values,
        train["outcome"].values,
        verbose=False,
    )

    proba = model.predict_proba(eval_df[feature_columns].values)
    proba_mirrored = model.predict_proba(
        mirror_features(eval_df, feature_columns)[feature_columns].values
    )
    proba = symmetrize_neutral(proba, proba_mirrored, eval_df)
    y_true = eval_df["outcome"].values.astype(int)
    y_pred = proba.argmax(axis=1)

    evaluate("WC 2026 backtest (XGB, train < 2023)", y_true, proba)
    print_confusion(y_true, y_pred)
    print_stage_metrics(eval_df, proba)

    outcome_labels = list(OUTCOME_NAMES)
    results = pd.DataFrame(
        {
            "date": eval_df["date"].values,
            "home_team": eval_df["home_team"].values,
            "away_team": eval_df["away_team"].values,
            "home_advantage": eval_df["home_advantage"].values,
            "round": eval_df["round_name"].values,
            "group_name": eval_df["group_name"].values,
            "stage": eval_df["stage"].values,
            "home_score": eval_df["home_score"].values,
            "away_score": eval_df["away_score"].values,
            "actual_outcome": [outcome_labels[i] for i in y_true],
            "p_home": proba[:, 0],
            "p_draw": proba[:, 1],
            "p_away": proba[:, 2],
            "predicted_outcome": [outcome_labels[i] for i in y_pred],
            "correct": y_pred == y_true,
        }
    )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUT_PATH, index=False)
    print(f"\nWrote {len(results)} rows to {OUT_PATH}")
    return results


def main() -> None:
    run_backtest()


if __name__ == "__main__":
    main()
