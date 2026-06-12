"""Download transfermarkt player valuations and build squad-value snapshots.

Source: transfermarkt-datasets (players + player_valuations CSVs).
For each national team (proxied by player citizenship), we sum the market
values of the top-25 most valuable players at quarterly snapshot dates.
Each player's value is their latest valuation within the prior 18 months.
"""

from __future__ import annotations

import argparse
import io
import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd
import requests

from download_data import DB_PATH, get_connection, normalize_team_name

PLAYERS_URL = (
    "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/players.csv.gz"
)
VALUATIONS_URL = (
    "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/player_valuations.csv.gz"
)

SNAPSHOT_START = "2004-01-01"
LOOKBACK_MONTHS = 18
TOP_N = 25

# Transfermarkt citizenship labels that differ from martj42 canonical names.
CITIZENSHIP_ALIASES = {
    "Korea, South": "South Korea",
    "Korea, North": "North Korea",
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "China": "China",
    "China PR": "China",
    "Chinese Taipei": "Taiwan",
    "Hongkong": "Hong Kong",
    "Ireland": "Republic of Ireland",
    "Brunei Darussalam": "Brunei",
    "Macao": "Macau",
    "Neukaledonien": "New Caledonia",
    "Saint-Martin": "Saint Martin",
    "Sao Tome and Principe": "São Tomé and Príncipe",
    "Southern Sudan": "South Sudan",
    "St. Kitts & Nevis": "Saint Kitts and Nevis",
    "St. Lucia": "Saint Lucia",
    "St. Vincent & Grenadinen": "Saint Vincent and the Grenadines",
    "The Gambia": "Gambia",
    "Curacao": "Curaçao",
}


def map_citizenship(country: str | None) -> str | None:
    if country is None or (isinstance(country, float) and pd.isna(country)):
        return None
    name = str(country).strip()
    if not name:
        return None
    name = CITIZENSHIP_ALIASES.get(name, name)
    return normalize_team_name(name)


def squad_values_exist(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='squad_values'"
    ).fetchone()
    return row is not None


def download_csv(url: str, label: str) -> pd.DataFrame:
    print(f"Downloading {label} from {url} ...")
    response = requests.get(url, timeout=300)
    response.raise_for_status()
    return pd.read_csv(io.BytesIO(response.content), compression="gzip")


def quarter_end_dates(start: str, end: str) -> list[pd.Timestamp]:
    """Quarter-end dates from start through end (inclusive)."""
    periods = pd.period_range(start=start, end=end, freq="Q")
    return [p.end_time.normalize() for p in periods]


def latest_values_in_window(
    valuations: pd.DataFrame, snapshot: pd.Timestamp, lookback_months: int
) -> pd.DataFrame:
    """Per player: latest valuation in (snapshot - lookback, snapshot]."""
    window_start = snapshot - pd.DateOffset(months=lookback_months)
    window = valuations[
        (valuations["date"] > window_start) & (valuations["date"] <= snapshot)
    ]
    if window.empty:
        return window
    return (
        window.sort_values("date")
        .groupby("player_id", as_index=False)
        .tail(1)
    )


def squad_totals_for_snapshot(latest: pd.DataFrame) -> pd.DataFrame:
    """Sum top-N player values per team at one snapshot."""
    if latest.empty:
        return pd.DataFrame(
            columns=["team", "snapshot_date", "total_value_top25", "n_players_valued"]
        )

    rows: list[dict] = []
    for team, group in latest.groupby("team"):
        valued = group["market_value_in_eur"].dropna()
        valued = valued[valued > 0]
        if valued.empty:
            continue
        top = valued.nlargest(TOP_N)
        rows.append(
            {
                "team": team,
                "total_value_top25": float(top.sum()),
                "n_players_valued": int(len(top)),
            }
        )
    out = pd.DataFrame(rows)
    return out


def build_snapshots(
    players: pd.DataFrame, valuations: pd.DataFrame
) -> tuple[pd.DataFrame, list[str]]:
    players = players[["player_id", "country_of_citizenship"]].copy()
    players["team"] = players["country_of_citizenship"].map(map_citizenship)
    unmatched = sorted(
        players.loc[players["team"].isna(), "country_of_citizenship"]
        .dropna()
        .unique()
        .tolist()
    )
    players = players.dropna(subset=["team"])

    valuations = valuations[["player_id", "date", "market_value_in_eur"]].copy()
    valuations["date"] = pd.to_datetime(valuations["date"])
    valuations = valuations.merge(players, on="player_id", how="inner")
    valuations = valuations.sort_values("date")

    end = date.today().isoformat()
    snapshots = quarter_end_dates(SNAPSHOT_START, end)

    frames: list[pd.DataFrame] = []
    for snapshot in snapshots:
        latest = latest_values_in_window(
            valuations, snapshot, lookback_months=LOOKBACK_MONTHS
        )
        totals = squad_totals_for_snapshot(latest)
        if totals.empty:
            continue
        totals["snapshot_date"] = snapshot.strftime("%Y-%m-%d")
        frames.append(totals)

    if not frames:
        return pd.DataFrame(
            columns=["team", "snapshot_date", "total_value_top25", "n_players_valued"]
        ), unmatched

    out = pd.concat(frames, ignore_index=True)
    out = out[["team", "snapshot_date", "total_value_top25", "n_players_valued"]]
    out = out.sort_values(["team", "snapshot_date"]).reset_index(drop=True)
    return out, unmatched


def save_squad_values(conn: sqlite3.Connection, df: pd.DataFrame) -> None:
    df.to_sql("squad_values", conn, if_exists="replace", index=False)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_squad_values_team_date "
        "ON squad_values (team, snapshot_date)"
    )
    conn.commit()


def run_squad_download(force: bool = False) -> bool:
    """Refresh squad_values table. Returns True if download/build ran."""
    conn = get_connection()
    if squad_values_exist(conn) and not force:
        count = conn.execute("SELECT COUNT(*) FROM squad_values").fetchone()[0]
        print(
            f"squad_values table already exists ({count} rows; "
            f"use --force to refresh)."
        )
        conn.close()
        return False

    players = download_csv(PLAYERS_URL, "players")
    valuations = download_csv(VALUATIONS_URL, "player_valuations")
    print(f"  players: {len(players):,} rows")
    print(f"  valuations: {len(valuations):,} rows")

    snapshots, unmatched = build_snapshots(players, valuations)
    save_squad_values(conn, snapshots)
    conn.close()

    print(f"\nWrote {len(snapshots):,} squad snapshot rows to {DB_PATH}")
    if not snapshots.empty:
        latest_date = snapshots["snapshot_date"].max()
        latest = snapshots[snapshots["snapshot_date"] == latest_date]
        print(f"Latest snapshot: {latest_date} ({len(latest)} teams)")
        for team in ("France", "England", "Brazil", "Argentina"):
            row = latest[latest["team"] == team]
            if not row.empty:
                val = row.iloc[0]["total_value_top25"]
                print(f"  {team}: EUR {val:,.0f} (top {TOP_N})")

    if unmatched:
        print(
            f"\nUnmatched citizenship countries ({len(unmatched)}): "
            + ", ".join(unmatched[:20])
            + (" ..." if len(unmatched) > 20 else "")
        )
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download transfermarkt squad values into SQLite."
    )
    parser.add_argument(
        "--force", action="store_true", help="Rebuild squad_values even if present"
    )
    args = parser.parse_args()
    run_squad_download(force=args.force)


if __name__ == "__main__":
    main()
