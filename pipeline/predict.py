"""Predict match outcome probabilities for two teams."""

from __future__ import annotations

import argparse
import json
import sqlite3

import numpy as np
import xgboost as xgb

from .download_data import normalize_team_name
from .fifa_codes import FIFA_CODE_TO_TEAM
from .paths import DB_PATH, META_PATH, MODEL_PATH

OUTCOME_LABELS = ("home_win", "draw", "away_win")


def resolve_team(token: str) -> str:
    """Resolve a FIFA three-letter code (e.g. FRA, BRA) to the full team name.

    Full team names are also accepted and pass through unchanged.
    """
    code = token.strip().upper()
    if code in FIFA_CODE_TO_TEAM:
        return FIFA_CODE_TO_TEAM[code]
    return normalize_team_name(token)


def load_team_rating(conn: sqlite3.Connection, team: str) -> dict:
    columns = [
        row[1]
        for row in conn.execute("PRAGMA table_info(team_ratings)")
    ]
    has_squad = "squad_value_log" in columns
    query = (
        "SELECT team, elo, form_pts_5, form_gd_5, form_gf_5, form_ga_5, "
        "form_pts_10, form_gd_10, form_gf_10, form_ga_10, last_match_date"
    )
    if has_squad:
        query += ", squad_value_log"
    query += " FROM team_ratings WHERE team = ?"

    row = conn.execute(query, (team,)).fetchone()
    if row is None:
        known = conn.execute(
            "SELECT team FROM team_ratings WHERE team LIKE ? LIMIT 5",
            (f"%{team}%",),
        ).fetchall()
        hint = ", ".join(r[0] for r in known) if known else "no close matches"
        raise ValueError(f"Unknown team '{team}'. Did you mean: {hint}?")
    result = {
        "team": row[0],
        "elo": row[1],
        "form_pts_5": row[2],
        "form_gd_5": row[3],
        "form_gf_5": row[4],
        "form_ga_5": row[5],
        "form_pts_10": row[6],
        "form_gd_10": row[7],
        "form_gf_10": row[8],
        "form_ga_10": row[9],
        "last_match_date": row[10],
        "squad_value_log": float("nan"),
    }
    if has_squad:
        squad_log = row[11]
        if squad_log is not None:
            result["squad_value_log"] = float(squad_log)
    return result


def load_prematch_markets(
    conn: sqlite3.Connection,
    home_team: str,
    away_team: str,
    match_date: str | None = None,
) -> dict[str, float]:
    """Load bookmaker implied probs for a fixture, or NaN if unavailable."""
    nan = float("nan")
    empty = {
        "market_implied_home": nan,
        "market_implied_draw": nan,
        "market_implied_away": nan,
        "market_implied_diff": nan,
    }
    table = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='prematch_odds'"
    ).fetchone()
    if table is None:
        return empty

    if match_date:
        row = conn.execute(
            """
            SELECT implied_home, implied_draw, implied_away, implied_diff
            FROM prematch_odds
            WHERE date = ? AND home_team = ? AND away_team = ?
            """,
            (match_date, home_team, away_team),
        ).fetchone()
    else:
        row = conn.execute(
            """
            SELECT implied_home, implied_draw, implied_away, implied_diff
            FROM prematch_odds
            WHERE home_team = ? AND away_team = ?
            ORDER BY date DESC
            LIMIT 1
            """,
            (home_team, away_team),
        ).fetchone()
    if row is None:
        return empty
    return {
        "market_implied_home": float(row[0]) if row[0] is not None else nan,
        "market_implied_draw": float(row[1]) if row[1] is not None else nan,
        "market_implied_away": float(row[2]) if row[2] is not None else nan,
        "market_implied_diff": float(row[3]) if row[3] is not None else nan,
    }


def mirror_market(market: dict[str, float]) -> dict[str, float]:
    """Swap home/away market slots for neutral-venue symmetrization."""
    home = market.get("market_implied_home", float("nan"))
    away = market.get("market_implied_away", float("nan"))
    diff = market.get("market_implied_diff", float("nan"))
    return {
        "market_implied_home": away,
        "market_implied_draw": market.get("market_implied_draw", float("nan")),
        "market_implied_away": home,
        "market_implied_diff": -diff if not np.isnan(diff) else float("nan"),
    }


def build_feature_vector(
    home: dict,
    away: dict,
    neutral: bool,
    competitive: bool = True,
    market: dict[str, float] | None = None,
) -> np.ndarray:
    meta = json.loads(META_PATH.read_text())
    columns = meta["feature_columns"]

    home_squad_log = home.get("squad_value_log", float("nan"))
    away_squad_log = away.get("squad_value_log", float("nan"))
    squad_diff = (
        home_squad_log - away_squad_log
        if not (np.isnan(home_squad_log) or np.isnan(away_squad_log))
        else float("nan")
    )
    market = market or {}

    values = {
        "elo_diff": home["elo"] - away["elo"],
        "form_pts_5_diff": home["form_pts_5"] - away["form_pts_5"],
        "form_gd_5_diff": home["form_gd_5"] - away["form_gd_5"],
        "form_pts_10_diff": home["form_pts_10"] - away["form_pts_10"],
        "form_gd_10_diff": home["form_gd_10"] - away["form_gd_10"],
        "form_gf_5_diff": home["form_gf_5"] - away["form_gf_5"],
        "form_ga_5_diff": home["form_ga_5"] - away["form_ga_5"],
        "form_gf_10_diff": home["form_gf_10"] - away["form_gf_10"],
        "form_ga_10_diff": home["form_ga_10"] - away["form_ga_10"],
        "home_days_since_last": 30.0,
        "away_days_since_last": 30.0,
        "neutral": int(neutral),
        "competitive": int(competitive),
        "home_elo": home["elo"],
        "away_elo": away["elo"],
        "home_squad_value_log": home_squad_log,
        "away_squad_value_log": away_squad_log,
        "squad_value_log_diff": squad_diff,
        "market_implied_home": market.get("market_implied_home", float("nan")),
        "market_implied_draw": market.get("market_implied_draw", float("nan")),
        "market_implied_away": market.get("market_implied_away", float("nan")),
        "market_implied_diff": market.get("market_implied_diff", float("nan")),
    }
    return np.array([[values[col] for col in columns]], dtype=np.float32)


def predict(
    home_team: str,
    away_team: str,
    neutral: bool,
    match_date: str | None = None,
) -> dict[str, float]:
    home_team = resolve_team(home_team)
    away_team = resolve_team(away_team)

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found at {MODEL_PATH}. Run train.py first."
        )

    conn = sqlite3.connect(DB_PATH)
    home = load_team_rating(conn, home_team)
    away = load_team_rating(conn, away_team)
    market = load_prematch_markets(conn, home_team, away_team, match_date)
    conn.close()

    features = build_feature_vector(home, away, neutral=neutral, market=market)

    model = xgb.XGBClassifier()
    model.load_model(MODEL_PATH)
    proba = model.predict_proba(features)[0]

    # On neutral ground the slot assignment is arbitrary, but the model is not
    # structurally symmetric. Averaging with the mirrored prediction guarantees
    # that A vs B and B vs A return identical distributions.
    if neutral:
        mirrored = build_feature_vector(
            away, home, neutral=True, market=mirror_market(market)
        )
        proba_mirrored = model.predict_proba(mirrored)[0][::-1]
        proba = (proba + proba_mirrored) / 2.0

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
    parser.add_argument(
        "home_team", help="Team A as FIFA code (e.g. FRA) or full name"
    )
    parser.add_argument(
        "away_team", help="Team B as FIFA code (e.g. BRA) or full name"
    )
    parser.add_argument(
        "--neutral",
        action="store_true",
        help="Match played on neutral ground (typical for World Cup)",
    )
    args = parser.parse_args()

    home_team = resolve_team(args.home_team)
    away_team = resolve_team(args.away_team)
    probs = predict(home_team, away_team, neutral=args.neutral)

    print(format_probs(home_team, away_team, probs))
    print("\nDetailed probabilities:")
    print(f"  {home_team} win: {probs[f'{home_team}_win']:.4f}")
    print(f"  Draw: {probs['draw']:.4f}")
    print(f"  {away_team} win: {probs[f'{away_team}_win']:.4f}")


if __name__ == "__main__":
    main()
