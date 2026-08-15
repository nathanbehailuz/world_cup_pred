"""Download and reload the FIFA World Cup 2026 fixture schedule."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .download_data import get_connection, normalize_team_name
from .paths import DB_PATH

if TYPE_CHECKING:
    import pandas as pd

SCHEDULE_URL = "https://fixturedownload.com/feed/json/fifa-world-cup-2026"

# Substrings in stadium/location names mapped to host nation in dataset.
VENUE_HOST_KEYWORDS: dict[str, str] = {
    "Mexico City": "Mexico",
    "Guadalajara": "Mexico",
    "Monterrey": "Mexico",
    "Toronto": "Canada",
    "Vancouver": "Canada",
    "Los Angeles": "USA",
    "San Francisco": "USA",
    "Seattle": "USA",
    "Boston": "USA",
    "New York": "USA",
    "Philadelphia": "USA",
    "Miami": "USA",
    "Atlanta": "USA",
    "Houston": "USA",
    "Dallas": "USA",
    "Kansas City": "USA",
}

PLACEHOLDER_PATTERN = re.compile(
    r"^(to be announced|\d+[a-z]|\d+[a-z]{2,3}|\d+)$", re.IGNORECASE
)


@dataclass
class Fixture:
    match_number: int
    date: str
    location: str
    home_team: str
    away_team: str
    round_name: str
    group_name: str | None
    home_score: int | None
    away_score: int | None

    @property
    def is_played(self) -> bool:
        return self.home_score is not None and self.away_score is not None


def ensure_schedule_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schedule (
            match_number INTEGER PRIMARY KEY,
            date TEXT NOT NULL,
            location TEXT,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            round_name TEXT,
            group_name TEXT,
            home_score INTEGER,
            away_score INTEGER
        )
        """
    )


def is_real_team(name: str) -> bool:
    if not name or not name.strip():
        return False
    return not PLACEHOLDER_PATTERN.match(name.strip())


def venue_host_country(location: str) -> str | None:
    for keyword, country in VENUE_HOST_KEYWORDS.items():
        if keyword.lower() in location.lower():
            return country
    return None


def infer_neutral(home_team: str, away_team: str, location: str) -> bool:
    """True unless one team is the venue's host nation."""
    host = venue_host_country(location)
    if host is None:
        return True
    return home_team != host and away_team != host


def fetch_schedule_json() -> list[dict]:
    import requests

    print(f"Fetching WC 2026 schedule from {SCHEDULE_URL} ...")
    response = requests.get(SCHEDULE_URL, timeout=60)
    response.raise_for_status()
    return response.json()


def parse_fixtures(raw: list[dict]) -> list[Fixture]:
    fixtures: list[Fixture] = []
    for row in raw:
        home = normalize_team_name(row.get("HomeTeam", ""))
        away = normalize_team_name(row.get("AwayTeam", ""))
        date_utc = row.get("DateUtc", "")
        match_date = date_utc[:10] if date_utc else ""
        home_score = row.get("HomeTeamScore")
        away_score = row.get("AwayTeamScore")
        fixtures.append(
            Fixture(
                match_number=int(row["MatchNumber"]),
                date=match_date,
                location=row.get("Location", ""),
                home_team=home,
                away_team=away,
                round_name=str(row.get("RoundNumber", "")),
                group_name=row.get("Group") or None,
                home_score=int(home_score) if home_score is not None else None,
                away_score=int(away_score) if away_score is not None else None,
            )
        )
    return fixtures


def load_existing_schedule(conn: sqlite3.Connection) -> pd.DataFrame:
    import pandas as pd

    ensure_schedule_table(conn)
    try:
        return pd.read_sql_query("SELECT * FROM schedule", conn)
    except pd.errors.DatabaseError:
        return pd.DataFrame()


def save_schedule(conn: sqlite3.Connection, fixtures: list[Fixture]) -> None:
    import pandas as pd

    ensure_schedule_table(conn)
    conn.execute("DELETE FROM schedule")
    rows = [
        {
            "match_number": f.match_number,
            "date": f.date,
            "location": f.location,
            "home_team": f.home_team,
            "away_team": f.away_team,
            "round_name": f.round_name,
            "group_name": f.group_name,
            "home_score": f.home_score,
            "away_score": f.away_score,
        }
        for f in fixtures
    ]
    pd.DataFrame(rows).to_sql("schedule", conn, if_exists="append", index=False)
    conn.commit()


def summarize_changes(before: pd.DataFrame, after: list[Fixture]) -> None:
    if before.empty:
        print(f"  Loaded {len(after)} fixtures (initial import).")
        return

    before_by_num = {int(r.match_number): r for r in before.itertuples()}
    resolved: list[str] = []
    new_results: list[str] = []

    for fixture in after:
        prev = before_by_num.get(fixture.match_number)
        if prev is None:
            continue
        prev_home_real = is_real_team(prev.home_team)
        prev_away_real = is_real_team(prev.away_team)
        now_home_real = is_real_team(fixture.home_team)
        now_away_real = is_real_team(fixture.away_team)
        if (not prev_home_real or not prev_away_real) and now_home_real and now_away_real:
            resolved.append(
                f"  Match {fixture.match_number}: "
                f"{fixture.home_team} vs {fixture.away_team} ({fixture.date})"
            )
        prev_played = prev.home_score is not None and prev.away_score is not None
        if fixture.is_played and not prev_played:
            new_results.append(
                f"  Match {fixture.match_number}: "
                f"{fixture.home_team} {fixture.home_score}-{fixture.away_score} "
                f"{fixture.away_team} ({fixture.date})"
            )

    print(f"  Reloaded {len(after)} fixtures.")
    if resolved:
        print(f"  Placeholders resolved ({len(resolved)}):")
        for line in resolved[:10]:
            print(line)
        if len(resolved) > 10:
            print(f"  ... and {len(resolved) - 10} more")
    else:
        print("  No placeholder-to-team updates.")
    if new_results:
        print(f"  New results recorded ({len(new_results)}):")
        for line in new_results[:10]:
            print(line)
        if len(new_results) > 10:
            print(f"  ... and {len(new_results) - 10} more")
    else:
        print("  No new results since last reload.")


def refresh_schedule(conn: sqlite3.Connection | None = None) -> list[Fixture]:
    """Fetch schedule, save to DB, print change summary. Returns parsed fixtures."""
    close_conn = conn is None
    if conn is None:
        conn = get_connection()
        ensure_schedule_table(conn)

    before = load_existing_schedule(conn)
    fixtures = parse_fixtures(fetch_schedule_json())
    save_schedule(conn, fixtures)
    summarize_changes(before, fixtures)

    if close_conn:
        conn.close()
    return fixtures


def find_fixture(
    conn: sqlite3.Connection, team_a: str, team_b: str
) -> Fixture | None:
    """Return the earliest scheduled match between two teams (either slot order)."""
    ensure_schedule_table(conn)
    rows = conn.execute(
        """
        SELECT match_number, date, location, home_team, away_team,
               round_name, group_name, home_score, away_score
        FROM schedule
        WHERE (
            (home_team = ? AND away_team = ?)
            OR (home_team = ? AND away_team = ?)
        )
        ORDER BY date ASC
        """,
        (team_a, team_b, team_b, team_a),
    ).fetchall()

    for row in rows:
        home, away = row[3], row[4]
        if not is_real_team(home) or not is_real_team(away):
            continue
        return Fixture(
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
    return None


def main() -> None:
    refresh_schedule()
    print(f"\nSchedule saved to {DB_PATH} (table: schedule)")
    print("Re-run after each matchday to pick up results and resolved knockout ties.")


if __name__ == "__main__":
    main()
