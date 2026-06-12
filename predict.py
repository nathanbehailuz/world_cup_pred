"""Predict match outcome probabilities for two teams."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import numpy as np
import xgboost as xgb

from download_data import normalize_team_name

DB_PATH = Path(__file__).parent / "data" / "worldcup.db"
MODEL_PATH = Path(__file__).parent / "models" / "xgb_model.json"
META_PATH = Path(__file__).parent / "models" / "model_meta.json"

OUTCOME_LABELS = ("home_win", "draw", "away_win")


def load_team_rating(conn: sqlite3.Connection, team: str) -> dict:
    row = conn.execute(
        "SELECT team, elo, form_pts_5, form_gd_5, form_pts_10, form_gd_10, "
        "last_match_date FROM team_ratings WHERE team = ?",
        (team,),
    ).fetchone()
    if row is None:
        known = conn.execute(
            "SELECT team FROM team_ratings WHERE team LIKE ? LIMIT 5",
            (f"%{team}%",),
        ).fetchall()
        hint = ", ".join(r[0] for r in known) if known else "no close matches"
        raise ValueError(f"Unknown team '{team}'. Did you mean: {hint}?")
    return {
        "team": row[0],
        "elo": row[1],
        "form_pts_5": row[2],
        "form_gd_5": row[3],
        "form_pts_10": row[4],
        "form_gd_10": row[5],
        "last_match_date": row[6],
    }


def build_feature_vector(
    home: dict, away: dict, neutral: bool, competitive: bool = True
) -> np.ndarray:
    meta = json.loads(META_PATH.read_text())
    columns = meta["feature_columns"]

    values = {
        "elo_diff": home["elo"] - away["elo"],
        "form_pts_5_diff": home["form_pts_5"] - away["form_pts_5"],
        "form_gd_5_diff": home["form_gd_5"] - away["form_gd_5"],
        "form_pts_10_diff": home["form_pts_10"] - away["form_pts_10"],
        "form_gd_10_diff": home["form_gd_10"] - away["form_gd_10"],
        "home_days_since_last": 30.0,
        "away_days_since_last": 30.0,
        "neutral": int(neutral),
        "competitive": int(competitive),
        "home_elo": home["elo"],
        "away_elo": away["elo"],
    }
    return np.array([[values[col] for col in columns]], dtype=np.float32)


def predict(home_team: str, away_team: str, neutral: bool) -> dict[str, float]:
    home_team = normalize_team_name(home_team)
    away_team = normalize_team_name(away_team)

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found at {MODEL_PATH}. Run train.py first."
        )

    conn = sqlite3.connect(DB_PATH)
    home = load_team_rating(conn, home_team)
    away = load_team_rating(conn, away_team)
    conn.close()

    features = build_feature_vector(home, away, neutral=neutral)

    model = xgb.XGBClassifier()
    model.load_model(MODEL_PATH)
    proba = model.predict_proba(features)[0]

    return {
        f"{home_team}_win": float(proba[0]),
        "draw": float(proba[1]),
        f"{away_team}_win": float(proba[2]),
    }


def format_probs(home_team: str, away_team: str, probs: dict[str, float]) -> str:
    home_key = f"{home_team}_win"
    away_key = f"{away_team}_win"
    return (
        f"{home_team} {probs[home_key]:.1%} / "
        f"Draw {probs['draw']:.1%} / "
        f"{away_team} {probs[away_key]:.1%}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Predict W/D/L probabilities for an international match."
    )
    parser.add_argument("home_team", help="Home team name (team A)")
    parser.add_argument("away_team", help="Away team name (team B)")
    parser.add_argument(
        "--neutral",
        action="store_true",
        help="Match played on neutral ground (typical for World Cup)",
    )
    args = parser.parse_args()

    home_team = normalize_team_name(args.home_team)
    away_team = normalize_team_name(args.away_team)
    probs = predict(home_team, away_team, neutral=args.neutral)

    print(format_probs(home_team, away_team, probs))
    print("\nDetailed probabilities:")
    for label, outcome in zip(OUTCOME_LABELS, (home_team, "Draw", away_team)):
        key = (
            f"{home_team}_win"
            if outcome == home_team
            else f"{away_team}_win"
            if outcome == away_team
            else "draw"
        )
        print(f"  {outcome} ({label}): {probs[key]:.4f}")


if __name__ == "__main__":
    main()
