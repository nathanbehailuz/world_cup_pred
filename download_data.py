"""Download international match data into SQLite."""

from __future__ import annotations

import sqlite3
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

DB_PATH = Path(__file__).parent / "data" / "worldcup.db"
MARTJ42_URL = (
    "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
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
            UNIQUE(date, home_team, away_team)
        )
        """
    )
    return conn


def download_martj42() -> pd.DataFrame:
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


def save_matches(conn: sqlite3.Connection, df: pd.DataFrame) -> None:
    conn.execute("DELETE FROM matches")
    df.to_sql("matches", conn, if_exists="append", index=False)
    conn.commit()


def main() -> None:
    df = download_martj42()
    print(f"  martj42: {len(df)} matches "
          f"({df['date'].min()} to {df['date'].max()})")

    conn = get_connection()
    save_matches(conn, df)

    cursor = conn.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM matches")
    count, min_date, max_date = cursor.fetchone()
    conn.close()

    print(f"\nSaved {count} matches to {DB_PATH}")
    print(f"Date range: {min_date} to {max_date}")


if __name__ == "__main__":
    main()
