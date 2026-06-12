"""Schedule-aware orchestrator: refresh data, features, model, and predict."""

from __future__ import annotations

import argparse
from datetime import date

from download_data import get_connection, run_download
from download_squad_values import run_squad_download
from download_schedule import find_fixture, infer_neutral, refresh_schedule
from feature_engineering import run_feature_engineering
from predict import OUTCOME_LABELS, format_probs, predict, resolve_team
from train import run_train


def compute_cutoff(match_date: str | None) -> str:
    today = date.today().isoformat()
    if match_date is None:
        return today
    return min(today, match_date)


def resolve_neutral(
    fixture,
    team_a: str,
    team_b: str,
    force_neutral: bool | None,
) -> tuple[bool, str, str]:
    """Return (neutral, home_team, away_team) for prediction."""
    if fixture is None:
        neutral = force_neutral if force_neutral is not None else True
        return neutral, team_a, team_b

    home, away = fixture.home_team, fixture.away_team
    if force_neutral is not None:
        neutral = force_neutral
    else:
        neutral = infer_neutral(home, away, fixture.location)

    if team_a != home:
        print(
            f"Note: you listed {team_a} first, but the schedule has "
            f"{home} as the home team — using schedule order."
        )
    return neutral, home, away


def print_fixture(fixture) -> None:
    if fixture is None:
        return
    result = ""
    if fixture.is_played:
        result = f" [{fixture.home_score}-{fixture.away_score}]"
    group = f", {fixture.group_name}" if fixture.group_name else ""
    print(
        f"Fixture: {fixture.home_team} vs {fixture.away_team} on "
        f"{fixture.date} at {fixture.location} "
        f"(round {fixture.round_name}{group}){result}"
    )


def run_pipeline(
    team_a: str,
    team_b: str,
    force_neutral: bool | None = None,
    retrain: bool = False,
    force_download: bool = False,
) -> None:
    team_a = resolve_team(team_a)
    team_b = resolve_team(team_b)

    print(f"Predicting: {team_a} vs {team_b}\n")

    conn = get_connection()
    refresh_schedule(conn)
    fixture = find_fixture(conn, team_a, team_b)
    conn.close()

    if fixture is None:
        print("No scheduled WC 2026 fixture found for this pairing.")
    else:
        print_fixture(fixture)

    cutoff = compute_cutoff(fixture.date if fixture else None)
    neutral, home_team, away_team = resolve_neutral(
        fixture, team_a, team_b, force_neutral
    )

    print(
        f"Data cutoff: {cutoff}  |  "
        f"Venue: {'neutral' if neutral else 'home advantage for ' + home_team}"
    )
    print()

    print("=== Download matches ===")
    run_download(force=force_download, min_date=date.today().isoformat())

    print("\n=== Download squad values ===")
    run_squad_download(force=force_download)

    print("\n=== Feature engineering ===")
    run_feature_engineering(cutoff=cutoff)

    print("\n=== Train model ===")
    run_train(cutoff=cutoff, retrain=retrain)

    print("\n=== Prediction ===")
    probs = predict(home_team, away_team, neutral=neutral)
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the full WC prediction pipeline for two teams."
    )
    parser.add_argument("team_a", help="Team A as FIFA code (e.g. MEX) or full name")
    parser.add_argument("team_b", help="Team B as FIFA code (e.g. RSA) or full name")
    venue = parser.add_mutually_exclusive_group()
    venue.add_argument(
        "--neutral",
        action="store_true",
        help="Force neutral venue (overrides schedule inference)",
    )
    venue.add_argument(
        "--home",
        action="store_true",
        help="Force home advantage for the scheduled/listing home team",
    )
    parser.add_argument(
        "--retrain", action="store_true", help="Force model retraining"
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Re-download martj42 data even if already current",
    )
    args = parser.parse_args()

    force_neutral: bool | None = None
    if args.neutral:
        force_neutral = True
    elif args.home:
        force_neutral = False

    run_pipeline(
        args.team_a,
        args.team_b,
        force_neutral=force_neutral,
        retrain=args.retrain,
        force_download=args.force_download,
    )


if __name__ == "__main__":
    main()
