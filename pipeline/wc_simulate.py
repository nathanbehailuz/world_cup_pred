"""Live WC 2026 match simulation using the production model (not holdout rows)."""

from __future__ import annotations

import math
import sqlite3
from functools import lru_cache

import numpy as np
import xgboost as xgb

from .download_schedule import (
    Fixture,
    ensure_schedule_table,
    find_fixture,
    infer_neutral,
    is_real_team,
    venue_host_country,
)
from .fifa_codes import FIFA_CODE_TO_TEAM
from .paths import DB_PATH, META_PATH, MODEL_PATH
from .predict import (
    build_feature_vector,
    load_prematch_markets,
    load_team_rating,
    mirror_market,
    resolve_team,
)

OUTCOME_NAMES = ("home_win", "draw", "away_win")
TEAM_TO_FIFA_CODE = {team: code for code, team in FIFA_CODE_TO_TEAM.items()}
DISCLAIMER = (
    "Probabilities are research outputs, not betting advice. "
    "Knockout labels use advancement (ET/penalties); group draws remain possible."
)


def team_code(name: str) -> str:
    return TEAM_TO_FIFA_CODE.get(name, name[:3].upper())


@lru_cache(maxsize=1)
def load_model() -> xgb.XGBClassifier:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found at {MODEL_PATH}. Run pipeline.train first."
        )
    model = xgb.XGBClassifier()
    model.load_model(MODEL_PATH)
    return model


def outcome_from_scores(home_score: int, away_score: int) -> int:
    if home_score > away_score:
        return 0
    if home_score < away_score:
        return 2
    return 1


def actual_label(outcome: int, home: str, away: str) -> str:
    if outcome == 0:
        return home
    if outcome == 2:
        return away
    return "Draw"


def match_log_loss(proba: np.ndarray, outcome: int) -> float:
    p = float(np.clip(proba[outcome], 1e-15, 1.0))
    return float(-math.log(p))


def narrative(
    home: str,
    away: str,
    elo_diff: float,
    predicted: int,
    actual: int | None,
    correct: bool | None,
) -> str:
    if abs(elo_diff) < 25:
        favorite_clause = "Near coin-flip on Elo"
    elif elo_diff > 0:
        favorite_clause = f"Favored {home} on Elo"
    else:
        favorite_clause = f"Favored {away} on Elo"

    pred_label = actual_label(predicted, home, away)
    if actual is None:
        return f"{favorite_clause}; model leans {pred_label}."
    realized = actual_label(actual, home, away)
    if correct:
        return f"{favorite_clause}; {realized} realized."
    return f"{favorite_clause}; surprise {realized} realized."


def list_wc_fixtures(conn: sqlite3.Connection | None = None) -> list[Fixture]:
    close = False
    if conn is None:
        if not DB_PATH.exists():
            raise FileNotFoundError(f"{DB_PATH} not found.")
        conn = sqlite3.connect(DB_PATH)
        close = True
    try:
        ensure_schedule_table(conn)
        rows = conn.execute(
            """
            SELECT match_number, date, location, home_team, away_team,
                   round_name, group_name, home_score, away_score
            FROM schedule
            ORDER BY date ASC, match_number ASC
            """
        ).fetchall()
        fixtures: list[Fixture] = []
        for row in rows:
            home, away = row[3], row[4]
            if not is_real_team(home) or not is_real_team(away):
                continue
            fixtures.append(
                Fixture(
                    match_number=row[0],
                    date=row[1],
                    location=row[2] or "",
                    home_team=home,
                    away_team=away,
                    round_name=row[5] or "",
                    group_name=row[6],
                    home_score=row[7],
                    away_score=row[8],
                )
            )
        return fixtures
    finally:
        if close:
            conn.close()


def venue_label(home: str, away: str, location: str, neutral: bool) -> str:
    if neutral:
        host = venue_host_country(location)
        if host:
            return f"Neutral ({location})"
        return "Neutral"
    host = venue_host_country(location) or home
    return f"Home advantage · {host}"


def predict_fixture(
    fixture: Fixture,
    *,
    model: xgb.XGBClassifier | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict:
    """Run the production model on one WC fixture; return Evaluate-shaped row + extras."""
    close = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        close = True
    model = model or load_model()

    home = fixture.home_team
    away = fixture.away_team
    neutral = infer_neutral(home, away, fixture.location)

    try:
        home_r = load_team_rating(conn, home)
        away_r = load_team_rating(conn, away)
        market = load_prematch_markets(conn, home, away, fixture.date)
        features = build_feature_vector(home_r, away_r, neutral=neutral, market=market)
        proba = model.predict_proba(features)[0]
        if neutral:
            mirrored = build_feature_vector(
                away_r, home_r, neutral=True, market=mirror_market(market)
            )
            proba_mirrored = model.predict_proba(mirrored)[0][::-1]
            proba = (proba + proba_mirrored) / 2.0
    finally:
        if close:
            conn.close()

    predicted = int(np.argmax(proba))
    elo_diff = float(home_r["elo"] - away_r["elo"])
    elo_gap = abs(elo_diff)

    played = fixture.is_played
    actual: int | None = None
    correct: bool | None = None
    log_loss: float | None = None
    score: str | None = None
    actual_lab: str | None = None

    if played and fixture.home_score is not None and fixture.away_score is not None:
        actual = outcome_from_scores(fixture.home_score, fixture.away_score)
        correct = predicted == actual
        log_loss = match_log_loss(proba, actual)
        score = f"{fixture.home_score} - {fixture.away_score}"
        actual_lab = actual_label(actual, home, away)

    return {
        "id": f"{fixture.match_number}|{fixture.date}|{home}|{away}",
        "match_number": fixture.match_number,
        "date": fixture.date,
        "location": fixture.location,
        "team_a": home,
        "team_b": away,
        "team_a_code": team_code(home),
        "team_b_code": team_code(away),
        "tournament": "FIFA World Cup",
        "group_name": fixture.group_name,
        "round": fixture.round_name,
        "competitive": True,
        "neutral": neutral,
        "venue_label": venue_label(home, away, fixture.location, neutral),
        "probabilities": {
            "p_a": float(proba[0]),
            "p_draw": float(proba[1]),
            "p_b": float(proba[2]),
        },
        "predicted": OUTCOME_NAMES[predicted],
        "actual": OUTCOME_NAMES[actual] if actual is not None else None,
        "actual_label": actual_lab,
        "correct": correct,
        "log_loss": log_loss,
        "elo_gap": float(elo_gap),
        "score": score,
        "status": "final" if played else "upcoming",
        "narrative": narrative(home, away, elo_diff, predicted, actual, correct),
        "features": [
            {
                "metric": "Current Elo",
                "team_a": round(float(home_r["elo"]), 1),
                "team_b": round(float(away_r["elo"]), 1),
            },
            {
                "metric": "Form (L5 pts)",
                "team_a": home_r["form_pts_5"],
                "team_b": away_r["form_pts_5"],
            },
            {
                "metric": "Squad value (log)",
                "team_a": (
                    None
                    if math.isnan(float(home_r.get("squad_value_log", float("nan"))))
                    else round(float(home_r["squad_value_log"]), 2)
                ),
                "team_b": (
                    None
                    if math.isnan(float(away_r.get("squad_value_log", float("nan"))))
                    else round(float(away_r["squad_value_log"]), 2)
                ),
            },
        ],
        "disclaimer": DISCLAIMER,
        "source": "api",
    }


def simulate_pair(team_a: str, team_b: str) -> dict:
    """Resolve WC fixture from team names/codes and run the model."""
    a = resolve_team(team_a)
    b = resolve_team(team_b)
    if a == b:
        raise ValueError("Select two different teams")

    if not DB_PATH.exists():
        raise FileNotFoundError(f"{DB_PATH} not found.")

    conn = sqlite3.connect(DB_PATH)
    try:
        fixture = find_fixture(conn, a, b)
        if fixture is None:
            raise ValueError(
                f"No FIFA World Cup 2026 fixture found for {a} vs {b}."
            )
        return predict_fixture(fixture, conn=conn)
    finally:
        conn.close()


def simulate_all_wc() -> dict:
    """Run the production model on every resolved WC 2026 fixture."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"{DB_PATH} not found.")
    if not META_PATH.exists():
        raise FileNotFoundError(f"{META_PATH} not found.")

    model = load_model()
    conn = sqlite3.connect(DB_PATH)
    try:
        fixtures = list_wc_fixtures(conn)
        matches = [
            predict_fixture(fx, model=model, conn=conn) for fx in fixtures
        ]
    finally:
        conn.close()

    played = [m for m in matches if m["status"] == "final" and m["log_loss"] is not None]
    n_played = len(played)
    if n_played:
        accuracy = sum(1 for m in played if m["correct"]) / n_played
        mean_log_loss = sum(m["log_loss"] for m in played) / n_played
        labels = list(OUTCOME_NAMES)
        confusion = [
            [
                sum(
                    1
                    for m in played
                    if m["predicted"] == pred and m["actual"] == act
                )
                for act in labels
            ]
            for pred in labels
        ]
    else:
        accuracy = 0.0
        mean_log_loss = 0.0
        confusion = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]

    return {
        "matches": matches,
        "summary": {
            "n": len(matches),
            "n_played": n_played,
            "accuracy": accuracy,
            "mean_log_loss": mean_log_loss,
            "confusion": confusion,
        },
    }


def fixtures_payload() -> list[dict]:
    return [
        {
            "match_number": f.match_number,
            "date": f.date,
            "location": f.location,
            "home_team": f.home_team,
            "away_team": f.away_team,
            "home_code": team_code(f.home_team),
            "away_code": team_code(f.away_team),
            "round": f.round_name,
            "group_name": f.group_name,
            "home_score": f.home_score,
            "away_score": f.away_score,
            "status": "final" if f.is_played else "upcoming",
            "neutral": infer_neutral(f.home_team, f.away_team, f.location),
            "venue_label": venue_label(
                f.home_team,
                f.away_team,
                f.location,
                infer_neutral(f.home_team, f.away_team, f.location),
            ),
        }
        for f in list_wc_fixtures()
    ]
