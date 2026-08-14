"""Export competitive 2023+ holdout predictions for the Evaluate page.

Retrains on the temporal holdout protocol (date < TRAIN_CUTOFF) — never the
production refit in models/xgb_model.json, which would leak test-period data.
"""

from __future__ import annotations

import json
import math
import sqlite3

import numpy as np
import pandas as pd
import xgboost as xgb

from .fifa_codes import FIFA_CODE_TO_TEAM
from .paths import (
    DB_PATH,
    FRONTEND_HOLDOUT_PATH,
    HOLDOUT_EVALUATE_PATH,
    META_PATH,
)
from .train import (
    MIN_MATCH_DATE,
    OUTCOME_NAMES,
    TRAIN_CUTOFF,
    XGB_PARAMS,
    compute_metrics,
    elo_baseline_proba,
    evaluate,
    load_model_meta,
    mirror_features,
    symmetrize_neutral,
)

TEAM_TO_FIFA_CODE = {team: code for code, team in FIFA_CODE_TO_TEAM.items()}


def load_feature_frame(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(
        """
        SELECT
            f.*,
            m.tournament,
            m.home_score,
            m.away_score
        FROM features f
        JOIN matches m
          ON f.date = m.date
         AND f.home_team = m.home_team
         AND f.away_team = m.away_team
        WHERE f.date >= ?
        """,
        conn,
        params=(MIN_MATCH_DATE,),
    )


def team_code(name: str) -> str:
    return TEAM_TO_FIFA_CODE.get(name, name[:3].upper())


def actual_label(outcome: int, home: str, away: str) -> str:
    if outcome == 0:
        return home
    if outcome == 2:
        return away
    return "Draw"


def match_log_loss(proba_row: np.ndarray, outcome: int) -> float:
    p = float(np.clip(proba_row[outcome], 1e-15, 1.0))
    return float(-math.log(p))


def narrative_for_row(
    home: str,
    away: str,
    elo_diff: float,
    outcome: int,
    correct: bool,
) -> str:
    if abs(elo_diff) < 25:
        favorite = "Neither side"
        favorite_clause = "near coin-flip on Elo"
    elif elo_diff > 0:
        favorite = home
        favorite_clause = f"Favored {home} on Elo"
    else:
        favorite = away
        favorite_clause = f"Favored {away} on Elo"

    realized = actual_label(outcome, home, away)
    if correct:
        return f"{favorite_clause}; {realized} realized."
    if favorite == "Neither side":
        return f"Close Elo matchup; {realized} realized."
    return f"{favorite_clause}; surprise {realized} realized."


def build_match_row(row: pd.Series, proba_row: np.ndarray) -> dict:
    outcome = int(row["outcome"])
    y_pred = int(proba_row.argmax())
    home = str(row["home_team"])
    away = str(row["away_team"])
    elo_diff = float(row["elo_diff"])
    correct = y_pred == outcome
    hs = row["home_score"]
    aws = row["away_score"]
    score = None
    if pd.notna(hs) and pd.notna(aws):
        score = f"{int(hs)} - {int(aws)}"

    return {
        "id": f"{row['date']}|{home}|{away}",
        "date": str(row["date"]),
        "team_a": home,
        "team_b": away,
        "team_a_code": team_code(home),
        "team_b_code": team_code(away),
        "tournament": str(row["tournament"]),
        "competitive": bool(int(row["competitive"])),
        "probabilities": {
            "p_a": float(proba_row[0]),
            "p_draw": float(proba_row[1]),
            "p_b": float(proba_row[2]),
        },
        "predicted": OUTCOME_NAMES[y_pred],
        "actual": OUTCOME_NAMES[outcome],
        "actual_label": actual_label(outcome, home, away),
        "correct": bool(correct),
        "log_loss": match_log_loss(proba_row, outcome),
        "elo_gap": float(abs(elo_diff)),
        "score": score,
        "narrative": narrative_for_row(home, away, elo_diff, outcome, correct),
    }


def export_holdout() -> dict:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"{DB_PATH} not found. Run feature_engineering.py first."
        )
    meta = load_model_meta()
    if meta is None:
        raise FileNotFoundError(
            f"{META_PATH} not found. Run train.py first to select features."
        )

    feature_columns = list(meta["feature_columns"])
    selected_config = meta.get("selected_config", "unknown")
    competitive_only = bool(meta.get("competitive_only", False))

    conn = sqlite3.connect(DB_PATH)
    df = load_feature_frame(conn)
    conn.close()

    missing = [c for c in feature_columns if c not in df.columns]
    if missing:
        raise ValueError(f"Missing feature columns: {missing}")

    train_pool = df[df["date"] < TRAIN_CUTOFF].copy()
    train = (
        train_pool[train_pool["competitive"] == 1]
        if competitive_only
        else train_pool
    )
    eval_df = df[
        (df["date"] >= TRAIN_CUTOFF) & (df["competitive"] == 1)
    ].copy()
    eval_df = eval_df.sort_values(
        ["date", "home_team", "away_team"]
    ).reset_index(drop=True)

    if train.empty:
        raise RuntimeError(f"No training rows before {TRAIN_CUTOFF}")
    if eval_df.empty:
        raise RuntimeError(f"No competitive eval rows on/after {TRAIN_CUTOFF}")

    print(f"Selected config: {selected_config}")
    print(f"Features:        {len(feature_columns)}")
    print(f"Train:           {len(train)} matches (date < {TRAIN_CUTOFF})")
    print(
        f"Eval:            {len(eval_df)} competitive matches "
        f"(date >= {TRAIN_CUTOFF})"
    )

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
    metrics = evaluate(
        "Holdout XGBoost (temporal, no production leak)",
        y_true,
        proba,
    )

    elo_proba, _, _ = elo_baseline_proba(train, eval_df)
    elo_metrics = compute_metrics(y_true, elo_proba)
    print("\nElo logistic baseline")
    for key, value in elo_metrics.items():
        print(f"  {key}: {value:.4f}")

    matches = [
        build_match_row(eval_df.iloc[i], proba[i])
        for i in range(len(eval_df))
    ]
    tournaments = sorted({m["tournament"] for m in matches})

    artifact = {
        "meta": {
            "train_cutoff": TRAIN_CUTOFF,
            "n_matches": len(matches),
            "feature_columns": feature_columns,
            "selected_config": selected_config,
            "metrics": metrics,
            "baseline_accuracy": float(elo_metrics["accuracy"]),
            "tournaments": tournaments,
        },
        "matches": matches,
    }

    payload = json.dumps(artifact, indent=2)
    HOLDOUT_EVALUATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    HOLDOUT_EVALUATE_PATH.write_text(payload)
    FRONTEND_HOLDOUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    FRONTEND_HOLDOUT_PATH.write_text(payload)

    print(f"\nWrote {len(matches)} matches to {HOLDOUT_EVALUATE_PATH}")
    print(f"Copied artifact to {FRONTEND_HOLDOUT_PATH}")
    return artifact


def main() -> None:
    export_holdout()


if __name__ == "__main__":
    main()
