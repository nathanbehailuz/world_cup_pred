"""Compute point-in-time Elo ratings and rolling form features."""

from __future__ import annotations

import sqlite3
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).parent / "data" / "worldcup.db"

INITIAL_ELO = 1500.0
HOME_ADVANTAGE = 100.0
K_FRIENDLY = 20.0
K_COMPETITIVE = 40.0

COMPETITIVE_KEYWORDS = (
    "world cup",
    "european championship",
    "euro",
    "copa america",
    "african cup",
    "asian cup",
    "nations league",
    "qualif",
    "olympic",
    "confederations",
)


@dataclass
class TeamState:
    elo: float = INITIAL_ELO
    last_date: str | None = None
    # deque of (date, points, goal_diff)
    history: deque = field(default_factory=lambda: deque(maxlen=10))


def is_competitive(tournament: str | None) -> bool:
    if not tournament:
        return False
    name = tournament.lower()
    if "friendly" in name:
        return False
    return any(keyword in name for keyword in COMPETITIVE_KEYWORDS)


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


def rolling_stats(history: deque, window: int) -> tuple[float, float]:
    if not history:
        return 0.0, 0.0
    recent = list(history)[-window:]
    points = sum(item[1] for item in recent)
    gd = sum(item[2] for item in recent)
    return float(points), float(gd)


def days_since(last_date: str | None, current_date: str) -> float:
    if not last_date:
        return 365.0
    d0 = datetime.strptime(last_date, "%Y-%m-%d")
    d1 = datetime.strptime(current_date, "%Y-%m-%d")
    return float((d1 - d0).days)


def outcome_label(home_score: int, away_score: int) -> int:
    """0 = home win, 1 = draw, 2 = away win."""
    if home_score > away_score:
        return 0
    if home_score == away_score:
        return 1
    return 2


def load_matches(conn: sqlite3.Connection) -> pd.DataFrame:
    df = pd.read_sql_query(
        "SELECT date, home_team, away_team, home_score, away_score, "
        "tournament, neutral FROM matches ORDER BY date ASC",
        conn,
    )
    return df


def build_features(matches: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
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

        home_pts_5, home_gd_5 = rolling_stats(home_state.history, 5)
        away_pts_5, away_gd_5 = rolling_stats(away_state.history, 5)
        home_pts_10, home_gd_10 = rolling_stats(home_state.history, 10)
        away_pts_10, away_gd_10 = rolling_stats(away_state.history, 10)

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
                "home_days_since_last": days_since(home_state.last_date, match_date),
                "away_days_since_last": days_since(away_state.last_date, match_date),
                "neutral": int(neutral),
                "competitive": int(competitive),
                "outcome": outcome_label(row.home_score, row.away_score),
            }
        )

        # Update Elo after recording pre-match features.
        k = K_COMPETITIVE if competitive else K_FRIENDLY
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

        home_state.history.append((match_date, home_pts, home_gd_val))
        away_state.history.append((match_date, away_pts, away_gd_val))
        home_state.last_date = match_date
        away_state.last_date = match_date

    features_df = pd.DataFrame(feature_rows)

    rating_rows = []
    for team, state in teams.items():
        pts_5, gd_5 = rolling_stats(state.history, 5)
        pts_10, gd_10 = rolling_stats(state.history, 10)
        rating_rows.append(
            {
                "team": team,
                "elo": state.elo,
                "form_pts_5": pts_5,
                "form_gd_5": gd_5,
                "form_pts_10": pts_10,
                "form_gd_10": gd_10,
                "last_match_date": state.last_date,
            }
        )
    ratings_df = pd.DataFrame(rating_rows).sort_values("elo", ascending=False)

    return features_df, ratings_df


def save_tables(
    conn: sqlite3.Connection, features: pd.DataFrame, ratings: pd.DataFrame
) -> None:
    features.to_sql("features", conn, if_exists="replace", index=False)
    ratings.to_sql("team_ratings", conn, if_exists="replace", index=False)
    conn.commit()


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"{DB_PATH} not found. Run download_data.py first."
        )

    conn = sqlite3.connect(DB_PATH)
    matches = load_matches(conn)
    print(f"Loaded {len(matches)} matches for feature engineering.")

    features, ratings = build_features(matches)
    save_tables(conn, features, ratings)

    print(f"Wrote {len(features)} rows to features table.")
    print(f"Wrote {len(ratings)} teams to team_ratings table.")
    print(f"Top 5 Elo: {ratings.head()[['team', 'elo']].to_string(index=False)}")

    conn.close()


if __name__ == "__main__":
    main()
