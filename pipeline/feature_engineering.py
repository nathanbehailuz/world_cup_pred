"""Compute point-in-time Elo ratings and rolling form features."""

from __future__ import annotations

import argparse
import math
import sqlite3
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd

from .paths import DB_PATH

INITIAL_ELO = 1500.0
HOME_ADVANTAGE = 100.0

# Continental championship finals and major intercontinental tournaments.
CONTINENTAL_FINALS_KEYWORDS = (
    "uefa euro",
    "european championship",
    "copa américa",
    "copa america",
    "african cup of nations",
    "africa cup of nations",
    "afc asian cup",
    "asian cup",
    "gold cup",
    "concacaf championship",
    "oceania nations cup",
    "ofc nations cup",
    "confederations cup",
)


@dataclass
class TeamState:
    elo: float = INITIAL_ELO
    last_date: str | None = None
    # deque of (date, points, goal_diff, goals_for, goals_against)
    history: deque = field(default_factory=lambda: deque(maxlen=10))


def k_factor(tournament: str | None) -> float:
    """Tiered K following the eloratings.net convention.

    60 World Cup finals; 50 continental finals and major intercontinental
    tournaments; 40 qualifiers and Nations League; 30 other tournaments;
    20 friendlies.
    """
    if not tournament:
        return 20.0
    name = tournament.lower()
    if "friendly" in name:
        return 20.0
    if "qualif" in name or "nations league" in name:
        return 40.0
    if "fifa world cup" in name or name == "world cup":
        return 60.0
    if any(keyword in name for keyword in CONTINENTAL_FINALS_KEYWORDS):
        return 50.0
    return 30.0


def is_competitive(tournament: str | None) -> bool:
    """Major-competition flag: qualifiers, Nations League, and finals (K >= 40)."""
    return k_factor(tournament) >= 40.0


def expected_score(rating_a: float, rating_b: float) -> float:
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


def actual_score(home_score: int, away_score: int, for_home: bool) -> float:
    if home_score == away_score:
        return 0.5
    home_won = home_score > away_score
    return 1.0 if home_won == for_home else 0.0


def match_points(home_score: int, away_score: int, for_home: bool) -> int:
    if home_score == away_score:
        return 1
    home_won = home_score > away_score
    return 3 if home_won == for_home else 0


def goal_diff(home_score: int, away_score: int, for_home: bool) -> int:
    return (home_score - away_score) if for_home else (away_score - home_score)


def rolling_stats(history: deque, window: int) -> tuple[float, float, float, float]:
    """Return (points, goal_diff, goals_for, goals_against) over the window."""
    if not history:
        return 0.0, 0.0, 0.0, 0.0
    recent = list(history)[-window:]
    points = sum(item[1] for item in recent)
    gd = sum(item[2] for item in recent)
    gf = sum(item[3] for item in recent)
    ga = sum(item[4] for item in recent)
    return float(points), float(gd), float(gf), float(ga)


def days_since(last_date: str | None, current_date: str) -> float:
    if not last_date:
        return 365.0
    d0 = datetime.strptime(last_date, "%Y-%m-%d")
    d1 = datetime.strptime(current_date, "%Y-%m-%d")
    return float((d1 - d0).days)


def outcome_label(
    home_score: int,
    away_score: int,
    shootout_winner: str | None,
    home_team: str,
    away_team: str,
) -> int:
    """0 = home win, 1 = draw, 2 = away win.

    The target is the match WINNER regardless of how it was decided: a match
    level after extra time but settled on penalties is labeled with the
    shootout winner, not a draw. Draws are matches with no winner at all.
    """
    if home_score > away_score:
        return 0
    if home_score < away_score:
        return 2
    if shootout_winner == home_team:
        return 0
    if shootout_winner == away_team:
        return 2
    return 1


def load_squad_snapshots(conn: sqlite3.Connection) -> pd.DataFrame | None:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='squad_values'"
    ).fetchone()
    if row is None:
        return None
    df = pd.read_sql_query(
        "SELECT team, snapshot_date, total_value_top25 "
        "FROM squad_values ORDER BY team, snapshot_date",
        conn,
    )
    if df.empty:
        return None
    return df


def squad_value_as_of(
    snapshots: pd.DataFrame, team: str, as_of: str
) -> float | None:
    """Latest squad total strictly before as_of; None if unavailable."""
    team_snaps = snapshots[snapshots["team"] == team]
    if team_snaps.empty:
        return None
    prior = team_snaps[team_snaps["snapshot_date"] < as_of]
    if prior.empty:
        return None
    return float(prior.iloc[-1]["total_value_top25"])


def squad_value_log(value: float | None) -> float:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return float("nan")
    return float(np.log1p(value))


def load_matches(conn: sqlite3.Connection, cutoff: str | None = None) -> pd.DataFrame:
    query = (
        "SELECT date, home_team, away_team, home_score, away_score, "
        "tournament, neutral, shootout_winner FROM matches"
    )
    params: tuple = ()
    if cutoff:
        query += " WHERE date < ?"
        params = (cutoff,)
    query += " ORDER BY date ASC"
    df = pd.read_sql_query(query, conn, params=params)
    return df


def build_features(
    matches: pd.DataFrame,
    squad_snapshots: pd.DataFrame | None = None,
    ratings_as_of: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    teams: dict[str, TeamState] = {}
    feature_rows: list[dict] = []

    for row in matches.itertuples(index=False):
        home = row.home_team
        away = row.away_team
        match_date = row.date
        neutral = bool(row.neutral)
        competitive = is_competitive(row.tournament)

        if home not in teams:
            teams[home] = TeamState()
        if away not in teams:
            teams[away] = TeamState()

        home_state = teams[home]
        away_state = teams[away]

        home_elo_pre = home_state.elo
        away_elo_pre = away_state.elo

        home_pts_5, home_gd_5, home_gf_5, home_ga_5 = rolling_stats(
            home_state.history, 5
        )
        away_pts_5, away_gd_5, away_gf_5, away_ga_5 = rolling_stats(
            away_state.history, 5
        )
        home_pts_10, home_gd_10, home_gf_10, home_ga_10 = rolling_stats(
            home_state.history, 10
        )
        away_pts_10, away_gd_10, away_gf_10, away_ga_10 = rolling_stats(
            away_state.history, 10
        )

        if squad_snapshots is not None:
            home_squad = squad_value_as_of(squad_snapshots, home, match_date)
            away_squad = squad_value_as_of(squad_snapshots, away, match_date)
            home_squad_log = squad_value_log(home_squad)
            away_squad_log = squad_value_log(away_squad)
            squad_diff = (
                home_squad_log - away_squad_log
                if not (math.isnan(home_squad_log) or math.isnan(away_squad_log))
                else float("nan")
            )
        else:
            home_squad_log = away_squad_log = squad_diff = float("nan")

        feature_rows.append(
            {
                "date": match_date,
                "home_team": home,
                "away_team": away,
                "home_elo": home_elo_pre,
                "away_elo": away_elo_pre,
                "elo_diff": home_elo_pre - away_elo_pre,
                "home_form_pts_5": home_pts_5,
                "away_form_pts_5": away_pts_5,
                "form_pts_5_diff": home_pts_5 - away_pts_5,
                "home_form_gd_5": home_gd_5,
                "away_form_gd_5": away_gd_5,
                "form_gd_5_diff": home_gd_5 - away_gd_5,
                "home_form_pts_10": home_pts_10,
                "away_form_pts_10": away_pts_10,
                "form_pts_10_diff": home_pts_10 - away_pts_10,
                "home_form_gd_10": home_gd_10,
                "away_form_gd_10": away_gd_10,
                "form_gd_10_diff": home_gd_10 - away_gd_10,
                "home_form_gf_5": home_gf_5,
                "away_form_gf_5": away_gf_5,
                "form_gf_5_diff": home_gf_5 - away_gf_5,
                "home_form_ga_5": home_ga_5,
                "away_form_ga_5": away_ga_5,
                "form_ga_5_diff": home_ga_5 - away_ga_5,
                "home_form_gf_10": home_gf_10,
                "away_form_gf_10": away_gf_10,
                "form_gf_10_diff": home_gf_10 - away_gf_10,
                "home_form_ga_10": home_ga_10,
                "away_form_ga_10": away_ga_10,
                "form_ga_10_diff": home_ga_10 - away_ga_10,
                "home_days_since_last": days_since(home_state.last_date, match_date),
                "away_days_since_last": days_since(away_state.last_date, match_date),
                "neutral": int(neutral),
                "competitive": int(competitive),
                "home_squad_value_log": home_squad_log,
                "away_squad_value_log": away_squad_log,
                "squad_value_log_diff": squad_diff,
                "outcome": outcome_label(
                    row.home_score,
                    row.away_score,
                    row.shootout_winner,
                    home,
                    away,
                ),
            }
        )

        # Update Elo after recording pre-match features. Ratings use the
        # on-field result (a shootout is a near-coin-flip tiebreaker and
        # carries little information about team strength).
        k = k_factor(row.tournament)
        home_adj = home_elo_pre + (0.0 if neutral else HOME_ADVANTAGE)
        away_adj = away_elo_pre

        exp_home = expected_score(home_adj, away_adj)
        act_home = actual_score(row.home_score, row.away_score, for_home=True)
        delta = k * (act_home - exp_home)

        home_state.elo += delta
        away_state.elo -= delta

        home_pts = match_points(row.home_score, row.away_score, for_home=True)
        away_pts = match_points(row.home_score, row.away_score, for_home=False)
        home_gd_val = goal_diff(row.home_score, row.away_score, for_home=True)
        away_gd_val = goal_diff(row.home_score, row.away_score, for_home=False)

        home_state.history.append(
            (match_date, home_pts, home_gd_val, row.home_score, row.away_score)
        )
        away_state.history.append(
            (match_date, away_pts, away_gd_val, row.away_score, row.home_score)
        )
        home_state.last_date = match_date
        away_state.last_date = match_date

    features_df = pd.DataFrame(feature_rows)

    squad_lookup_date = ratings_as_of
    if squad_lookup_date is None and not matches.empty:
        squad_lookup_date = matches["date"].max()

    rating_rows = []
    for team, state in teams.items():
        pts_5, gd_5, gf_5, ga_5 = rolling_stats(state.history, 5)
        pts_10, gd_10, gf_10, ga_10 = rolling_stats(state.history, 10)
        squad_raw = (
            squad_value_as_of(squad_snapshots, team, squad_lookup_date)
            if squad_snapshots is not None and squad_lookup_date
            else None
        )
        rating_rows.append(
            {
                "team": team,
                "elo": state.elo,
                "form_pts_5": pts_5,
                "form_gd_5": gd_5,
                "form_gf_5": gf_5,
                "form_ga_5": ga_5,
                "form_pts_10": pts_10,
                "form_gd_10": gd_10,
                "form_gf_10": gf_10,
                "form_ga_10": ga_10,
                "last_match_date": state.last_date,
                "squad_value_top25": squad_raw,
                "squad_value_log": squad_value_log(squad_raw),
            }
        )
    ratings_df = pd.DataFrame(rating_rows).sort_values("elo", ascending=False)

    return features_df, ratings_df


def attach_prematch_markets(
    features: pd.DataFrame, conn: sqlite3.Connection
) -> pd.DataFrame:
    """Left-join pre-match odds and Predictz signals onto every feature row."""
    out = features.copy()

    odds_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='prematch_odds'"
    ).fetchone()
    if odds_exists:
        odds_df = pd.read_sql_query(
            """
            SELECT date, home_team, away_team,
                   home_odds AS market_home_odds,
                   draw_odds AS market_draw_odds,
                   away_odds AS market_away_odds,
                   implied_home AS market_implied_home,
                   implied_draw AS market_implied_draw,
                   implied_away AS market_implied_away,
                   implied_diff AS market_implied_diff
            FROM prematch_odds
            """,
            conn,
        )
        out = out.merge(
            odds_df,
            on=["date", "home_team", "away_team"],
            how="left",
        )
    else:
        for col in (
            "market_home_odds",
            "market_draw_odds",
            "market_away_odds",
            "market_implied_home",
            "market_implied_draw",
            "market_implied_away",
            "market_implied_diff",
        ):
            out[col] = float("nan")

    preds_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='prematch_predictions'"
    ).fetchone()
    if preds_exists:
        pred_df = pd.read_sql_query(
            """
            SELECT date, home_team, away_team,
                   pred_home_pct AS predictz_home_pct,
                   pred_draw_pct AS predictz_draw_pct,
                   pred_away_pct AS predictz_away_pct
            FROM prematch_predictions
            """,
            conn,
        )
        out = out.merge(
            pred_df,
            on=["date", "home_team", "away_team"],
            how="left",
        )
    else:
        out["predictz_home_pct"] = float("nan")
        out["predictz_draw_pct"] = float("nan")
        out["predictz_away_pct"] = float("nan")

    if "market_home_odds" in out.columns:
        out["has_prematch_odds"] = out["market_home_odds"].notna().astype(int)
    else:
        out["has_prematch_odds"] = 0
    return out


def save_tables(
    conn: sqlite3.Connection, features: pd.DataFrame, ratings: pd.DataFrame
) -> None:
    features.to_sql("features", conn, if_exists="replace", index=False)
    ratings.to_sql("team_ratings", conn, if_exists="replace", index=False)
    conn.commit()


def run_feature_engineering(cutoff: str | None = None) -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"{DB_PATH} not found. Run download_data.py first."
        )

    conn = sqlite3.connect(DB_PATH)
    matches = load_matches(conn, cutoff=cutoff)
    squad_snapshots = load_squad_snapshots(conn)
    label = f" (before {cutoff})" if cutoff else ""
    print(f"Loaded {len(matches)} matches for feature engineering{label}.")
    if squad_snapshots is None:
        print("No squad_values table found; squad features will be NaN.")
    else:
        print(f"Loaded {len(squad_snapshots):,} squad snapshot rows.")

    features, ratings = build_features(
        matches,
        squad_snapshots=squad_snapshots,
        ratings_as_of=cutoff,
    )
    features = attach_prematch_markets(features, conn)
    save_tables(conn, features, ratings)

    n_with_odds = int(features["has_prematch_odds"].sum())
    print(f"Wrote {len(features)} rows to features table.")
    print(f"  Pre-match odds attached: {n_with_odds} rows.")
    print(f"Wrote {len(ratings)} teams to team_ratings table.")
    print("\nTop 10 by Elo:")
    for rank, row in enumerate(ratings.head(10).itertuples(index=False), start=1):
        print(f"  {rank:2d}. {row.team:<20s} {row.elo:7.1f}")

    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute Elo and form features.")
    parser.add_argument(
        "--cutoff",
        metavar="YYYY-MM-DD",
        help="Only use matches strictly before this date (point-in-time ratings)",
    )
    args = parser.parse_args()
    run_feature_engineering(cutoff=args.cutoff)


if __name__ == "__main__":
    main()
