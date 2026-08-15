"""Download international match data into SQLite."""

from __future__ import annotations

import argparse
import sqlite3
from datetime import date
from io import StringIO
from typing import TYPE_CHECKING

from .paths import DB_PATH

if TYPE_CHECKING:
    import pandas as pd

MARTJ42_URL = (
    "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
)
SHOOTOUTS_URL = (
    "https://raw.githubusercontent.com/martj42/international_results/master/shootouts.csv"
)

# Canonical team name aliases used across the pipeline.
TEAM_NAME_MAP = {
    "United States": "USA",
    "United States of America": "USA",
    "Korea Republic": "South Korea",
    "Republic of Korea": "South Korea",
    "Korea DPR": "North Korea",
    "Côte d'Ivoire": "Ivory Coast",
    "Cote d'Ivoire": "Ivory Coast",
    "Czechia": "Czech Republic",
    "IR Iran": "Iran",
    "Türkiye": "Turkey",
    "Cabo Verde": "Cape Verde",
    "Congo DR": "DR Congo",
    "Congo-Kinshasa": "DR Congo",
    "Congo-Brazzaville": "Congo",
    "Bosnia & Herzegovina": "Bosnia and Herzegovina",
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "D.R. Congo": "DR Congo",
    "United States of America": "USA",
    "Curacao": "Curaçao",
}


def normalize_team_name(name: str) -> str:
    name = (name or "").strip()
    return TEAM_NAME_MAP.get(name, name)


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            home_score INTEGER NOT NULL,
            away_score INTEGER NOT NULL,
            tournament TEXT,
            neutral INTEGER NOT NULL DEFAULT 0,
            source TEXT NOT NULL,
            shootout_winner TEXT,
            UNIQUE(date, home_team, away_team)
        )
        """
    )
    # Migrate DBs created before the shootout_winner column existed.
    columns = [row[1] for row in conn.execute("PRAGMA table_info(matches)")]
    if "shootout_winner" not in columns:
        conn.execute("ALTER TABLE matches ADD COLUMN shootout_winner TEXT")
    return conn


def download_martj42() -> pd.DataFrame:
    import pandas as pd
    import requests

    print(f"Downloading martj42 results from {MARTJ42_URL} ...")
    response = requests.get(MARTJ42_URL, timeout=120)
    response.raise_for_status()
    df = pd.read_csv(StringIO(response.text))
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df["home_team"] = df["home_team"].map(normalize_team_name)
    df["away_team"] = df["away_team"].map(normalize_team_name)
    df["neutral"] = df["neutral"].astype(str).str.upper().eq("TRUE").astype(int)
    df["source"] = "martj42"
    df["home_score"] = pd.to_numeric(df["home_score"], errors="coerce")
    df["away_score"] = pd.to_numeric(df["away_score"], errors="coerce")
    df = df.dropna(subset=["home_score", "away_score"])
    df["home_score"] = df["home_score"].astype(int)
    df["away_score"] = df["away_score"].astype(int)
    # Team-name normalization can make distinct raw rows collide on the
    # (date, home_team, away_team) unique key; keep the first occurrence.
    before = len(df)
    df = df.drop_duplicates(subset=["date", "home_team", "away_team"], keep="first")
    dropped = before - len(df)
    if dropped:
        print(f"  Dropped {dropped} duplicate fixture(s) after name normalization.")
    return df[
        [
            "date",
            "home_team",
            "away_team",
            "home_score",
            "away_score",
            "tournament",
            "neutral",
            "source",
        ]
    ]


def download_shootouts() -> pd.DataFrame:
    import pandas as pd
    import requests

    print(f"Downloading shootout results from {SHOOTOUTS_URL} ...")
    response = requests.get(SHOOTOUTS_URL, timeout=120)
    response.raise_for_status()
    df = pd.read_csv(StringIO(response.text))
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df["home_team"] = df["home_team"].map(normalize_team_name)
    df["away_team"] = df["away_team"].map(normalize_team_name)
    df["shootout_winner"] = df["winner"].map(normalize_team_name)
    df = df.drop_duplicates(subset=["date", "home_team", "away_team"], keep="first")
    print(f"  {len(df)} shootouts found.")
    return df[["date", "home_team", "away_team", "shootout_winner"]]


def merge_shootouts(matches: pd.DataFrame, shootouts: pd.DataFrame) -> pd.DataFrame:
    merged = matches.merge(
        shootouts, on=["date", "home_team", "away_team"], how="left"
    )
    matched = merged["shootout_winner"].notna().sum()
    print(f"  Attached shootout winners to {matched} matches.")
    return merged


def save_matches(conn: sqlite3.Connection, df: pd.DataFrame) -> None:
    conn.execute("DELETE FROM matches")
    df.to_sql("matches", conn, if_exists="append", index=False)
    conn.commit()


def get_max_match_date(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT MAX(date) FROM matches").fetchone()
    return row[0] if row and row[0] else None


def data_is_current(min_date: str, force: bool = False) -> bool:
    """Return True if matches table already covers min_date (no download needed)."""
    if force or not DB_PATH.exists():
        return False
    conn = sqlite3.connect(DB_PATH)
    try:
        count = conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
        max_date = get_max_match_date(conn)
        shootouts = conn.execute(
            "SELECT COUNT(*) FROM matches WHERE shootout_winner IS NOT NULL"
        ).fetchone()[0]
    except sqlite3.OperationalError:
        max_date = None
        count = 0
        shootouts = 0
    finally:
        conn.close()
    if not max_date or count < 1000 or shootouts == 0:
        return False
    if max_date >= min_date:
        return True
    # martj42 can lag by a day; avoid re-downloading if we already have yesterday.
    needed = date.fromisoformat(min_date)
    latest = date.fromisoformat(max_date)
    return (needed - latest).days <= 1


def run_download(force: bool = False, min_date: str | None = None) -> bool:
    """Download martj42 data if needed. Returns True if a download ran."""
    needed_through = min_date or date.today().isoformat()
    if data_is_current(needed_through, force=force):
        print(
            f"Match data already current through {needed_through} "
            f"(use --force to re-download)."
        )
        return False

    df = download_martj42()
    print(f"  martj42: {len(df)} matches "
          f"({df['date'].min()} to {df['date'].max()})")

    shootouts = download_shootouts()
    df = merge_shootouts(df, shootouts)

    conn = get_connection()
    save_matches(conn, df)

    cursor = conn.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM matches")
    count, min_d, max_d = cursor.fetchone()
    conn.close()

    print(f"\nSaved {count} matches to {DB_PATH}")
    print(f"Date range: {min_d} to {max_d}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Download international match data.")
    parser.add_argument(
        "--force", action="store_true", help="Re-download even if data is current"
    )
    parser.add_argument(
        "--min-date",
        default=date.today().isoformat(),
        help="Require match data through this date (YYYY-MM-DD)",
    )
    args = parser.parse_args()
    run_download(force=args.force, min_date=args.min_date)


if __name__ == "__main__":
    main()
