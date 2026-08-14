"""Download pre-match betting odds and prediction signals into SQLite.

Sources (in merge priority, lowest to highest):
  1. HuggingFace international odds archive (~7.7k matches)
  2. football-data.co.uk international CSV (recent friendlies/qualifiers)
  3. BetExplorer World Cup pages (OddsPortal sister site; WC 1994–2026)

Predictz (predictz.com) is attempted but usually blocked by Cloudflare; optional
manual cache at data/predictz_predictions.csv is supported.
"""

from __future__ import annotations

import argparse
import re
import sqlite3
from datetime import date
from io import StringIO

import pandas as pd
import requests

from .download_data import DB_PATH, get_connection, normalize_team_name
from .paths import HUGGINGFACE_CACHE, PREDICTZ_CACHE

HUGGINGFACE_ODDS_URL = (
    "https://huggingface.co/datasets/adibmed/football-dataset/"
    "resolve/main/output/02_matches_with_odds.csv"
)
FOOTBALL_DATA_INTERNATIONAL_URL = "https://www.football-data.co.uk/worldcup2022.csv"
PREDICTZ_URL = "https://www.predictz.com/predictions/world-cup/"

BETEXPLORER_WC_SLUGS = {
    2026: "world-championship-2026",
    2022: "world-cup-2022",
    2018: "world-cup-2018",
    2014: "world-cup-2014",
    2010: "world-cup-2010",
    2006: "world-cup-2006",
    2002: "world-cup-2002",
    1998: "world-cup-1998",
    1994: "world-cup-1994",
}

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Extra aliases seen on odds sites but not in martj42 normalization.
ODDS_TEAM_NAME_MAP = {
    "Bosnia & Herzegovina": "Bosnia and Herzegovina",
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "D.R. Congo": "DR Congo",
    "Democratic Republic of Congo": "DR Congo",
    "United States of America": "USA",
    "Korea Republic": "South Korea",
    "Republic of Korea": "South Korea",
    "Korea DPR": "North Korea",
    "Côte d'Ivoire": "Ivory Coast",
    "Cote d'Ivoire": "Ivory Coast",
    "IR Iran": "Iran",
    "Türkiye": "Turkey",
    "Cabo Verde": "Cape Verde",
    "Congo DR": "DR Congo",
    "Congo-Kinshasa": "DR Congo",
    "Congo-Brazzaville": "Congo",
    "Curacao": "Curaçao",
}


def normalize_odds_team(name: str) -> str:
    name = (name or "").strip()
    name = re.sub(r"<[^>]+>", "", name)
    name = name.replace("&amp;", "&")
    mapped = ODDS_TEAM_NAME_MAP.get(name, name)
    return normalize_team_name(mapped)


def implied_probs(home_odds: float, draw_odds: float, away_odds: float) -> tuple[float, float, float]:
    """Overround-normalized implied 1X2 probabilities."""
    inv = [1.0 / home_odds, 1.0 / draw_odds, 1.0 / away_odds]
    total = sum(inv)
    return inv[0] / total, inv[1] / total, inv[2] / total


def enrich_odds_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    implied_home: list[float] = []
    implied_draw: list[float] = []
    implied_away: list[float] = []
    implied_diff: list[float] = []
    for _, row in out.iterrows():
        h_o, d_o, a_o = row["home_odds"], row["draw_odds"], row["away_odds"]
        if (
            pd.notna(h_o)
            and pd.notna(d_o)
            and pd.notna(a_o)
            and h_o > 1
            and d_o > 1
            and a_o > 1
        ):
            h, d, a = enrich_odds_frame_row(float(h_o), float(d_o), float(a_o))
            implied_home.append(h)
            implied_draw.append(d)
            implied_away.append(a)
            implied_diff.append(h - a)
        else:
            implied_home.append(float("nan"))
            implied_draw.append(float("nan"))
            implied_away.append(float("nan"))
            implied_diff.append(float("nan"))
    out["implied_home"] = implied_home
    out["implied_draw"] = implied_draw
    out["implied_away"] = implied_away
    out["implied_diff"] = implied_diff
    return out


def enrich_odds_frame_row(
    home_odds: float, draw_odds: float, away_odds: float
) -> tuple[float, float, float]:
    h, d, a = implied_probs(home_odds, draw_odds, away_odds)
    return h, d, a


def ensure_prematch_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS prematch_odds (
            date TEXT NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            home_odds REAL,
            draw_odds REAL,
            away_odds REAL,
            implied_home REAL,
            implied_draw REAL,
            implied_away REAL,
            implied_diff REAL,
            source TEXT NOT NULL,
            captured_at TEXT NOT NULL,
            PRIMARY KEY (date, home_team, away_team)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS prematch_predictions (
            date TEXT NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            pred_home_pct REAL,
            pred_draw_pct REAL,
            pred_away_pct REAL,
            tip_text TEXT,
            source TEXT NOT NULL,
            captured_at TEXT NOT NULL,
            PRIMARY KEY (date, home_team, away_team)
        )
        """
    )


def _http_get(url: str, timeout: int = 120) -> requests.Response:
    response = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()
    return response


def download_huggingface_odds(force: bool = False) -> pd.DataFrame:
    if HUGGINGFACE_CACHE.exists() and not force:
        print(f"  Using cached HuggingFace odds: {HUGGINGFACE_CACHE.name}")
        df = pd.read_csv(HUGGINGFACE_CACHE, low_memory=False)
    else:
        print(f"  Downloading HuggingFace odds archive ...")
        response = _http_get(HUGGINGFACE_ODDS_URL, timeout=180)
        HUGGINGFACE_CACHE.parent.mkdir(parents=True, exist_ok=True)
        HUGGINGFACE_CACHE.write_bytes(response.content)
        df = pd.read_csv(StringIO(response.text), low_memory=False)
        print(f"  Cached to {HUGGINGFACE_CACHE}")

    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    rows = pd.DataFrame(
        {
            "date": df["date"],
            "home_team": df["home_team"].map(normalize_odds_team),
            "away_team": df["away_team"].map(normalize_odds_team),
            "home_odds": pd.to_numeric(df["odds_avg_h"], errors="coerce"),
            "draw_odds": pd.to_numeric(df["odds_avg_d"], errors="coerce"),
            "away_odds": pd.to_numeric(df["odds_avg_a"], errors="coerce"),
            "source": "huggingface",
        }
    )
    rows = rows.dropna(subset=["home_odds", "draw_odds", "away_odds"])
    print(f"  HuggingFace: {len(rows)} rows with 1X2 odds.")
    return rows


def download_football_data_international() -> pd.DataFrame:
    print(f"  Downloading football-data.co.uk international odds ...")
    response = _http_get(FOOTBALL_DATA_INTERNATIONAL_URL)
    raw = pd.read_csv(
        StringIO(response.content.decode("utf-8-sig")),
        parse_dates=["Date"],
        dayfirst=True,
    )
    rows = pd.DataFrame(
        {
            "date": raw["Date"].dt.strftime("%Y-%m-%d"),
            "home_team": raw["Home"].map(normalize_odds_team),
            "away_team": raw["Away"].map(normalize_odds_team),
            "home_odds": pd.to_numeric(raw["H_Avg"], errors="coerce"),
            "draw_odds": pd.to_numeric(raw["D_Avg"], errors="coerce"),
            "away_odds": pd.to_numeric(raw["A_Avg"], errors="coerce"),
            "source": "football-data.co.uk",
        }
    )
    rows = rows.dropna(subset=["home_odds", "draw_odds", "away_odds"])
    print(f"  football-data.co.uk: {len(rows)} rows.")
    return rows


def _parse_betexplorer_odds_from_fragment(fragment: str) -> list[float]:
    odds = re.findall(r'data-odd="([0-9.]+)"', fragment)
    if len(odds) >= 3:
        return [float(x) for x in odds[:3]]
    nested = re.findall(r'data-odd="([0-9.]+)"', fragment)
    if len(nested) >= 3:
        return [float(x) for x in nested[:3]]
    return []


def _parse_betexplorer_date(token: str, default_year: int) -> str | None:
    token = token.strip()
    if not token or token == "&nbsp;":
        return None
    if token.lower().startswith("today"):
        return date.today().isoformat()
    m = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", token)
    if m:
        d, mo, y = m.groups()
        return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
    m = re.match(r"(\d{1,2})\.(\d{1,2})\.", token)
    if m:
        d, mo = m.groups()
        return f"{default_year:04d}-{int(mo):02d}-{int(d):02d}"
    return None


def parse_betexplorer_fixtures(html: str, year: int) -> list[dict]:
    rows: list[dict] = []
    pattern = re.compile(
        r"<tr>\s*"
        r'<td class="table-main__datetime">([^<]*)</td>\s*'
        r'<td class="h-text-left"><a href="/football/world/[^"]+" class="in-match">'
        r"<span>([^<]+)</span>\s*-\s*<span>([^<]+)</span></a></td>"
        r"(.*?)</tr>",
        re.S,
    )
    for dt_raw, home, away, rest in pattern.findall(html):
        match_date = _parse_betexplorer_date(dt_raw, default_year=year)
        if match_date is None:
            continue
        odds = _parse_betexplorer_odds_from_fragment(rest)
        if len(odds) < 3:
            continue
        rows.append(
            {
                "date": match_date,
                "home_team": normalize_odds_team(home),
                "away_team": normalize_odds_team(away),
                "home_odds": odds[0],
                "draw_odds": odds[1],
                "away_odds": odds[2],
                "source": f"betexplorer_wc{year}",
            }
        )
    return rows


def parse_betexplorer_results(html: str) -> list[dict]:
    rows: list[dict] = []
    for row_html in re.findall(r"<tr>(.*?)</tr>", html, re.S):
        if 'class="in-match"' not in row_html:
            continue
        teams = re.search(
            r'class="in-match"[^>]*>\s*'
            r'(?:<span>(?:<strong>)?([^<]+?)(?:</strong>)?</span>\s*-\s*)'
            r'(?:<span>(?:<strong>)?([^<]+?)(?:</strong>)?</span>)',
            row_html,
            re.S,
        )
        dt = re.search(
            r'<td class="h-text-right h-text-no-wrap">(\d{1,2}\.\d{1,2}\.\d{4})</td>',
            row_html,
        )
        if not teams or not dt:
            continue
        odds = _parse_betexplorer_odds_from_fragment(row_html)
        if len(odds) < 3:
            continue
        match_date = _parse_betexplorer_date(dt.group(1), default_year=2000)
        if match_date is None:
            continue
        rows.append(
            {
                "date": match_date,
                "home_team": normalize_odds_team(teams.group(1)),
                "away_team": normalize_odds_team(teams.group(2)),
                "home_odds": odds[0],
                "draw_odds": odds[1],
                "away_odds": odds[2],
                "source": "betexplorer_results",
            }
        )
    return rows


def download_betexplorer_world_cups(years: list[int] | None = None) -> pd.DataFrame:
    years = years or list(BETEXPLORER_WC_SLUGS)
    all_rows: list[dict] = []
    for year in years:
        slug = BETEXPLORER_WC_SLUGS[year]
        if year == 2026:
            pages = ("fixtures",)
        else:
            pages = ("results",)
        for page in pages:
            url = f"https://www.betexplorer.com/football/world/{slug}/{page}/"
            try:
                html = _http_get(url, timeout=60).text
            except requests.RequestException as exc:
                print(f"  BetExplorer WC{year} {page}: fetch failed ({exc})")
                continue
            if page == "fixtures":
                parsed = parse_betexplorer_fixtures(html, year=year)
            else:
                parsed = parse_betexplorer_results(html)
            print(f"  BetExplorer WC{year} {page}: {len(parsed)} rows.")
            all_rows.extend(parsed)
    if not all_rows:
        return pd.DataFrame(
            columns=[
                "date",
                "home_team",
                "away_team",
                "home_odds",
                "draw_odds",
                "away_odds",
                "source",
            ]
        )
    return pd.DataFrame(all_rows)


def download_predictz_predictions() -> pd.DataFrame:
    """Return Predictz-style prediction rows if available."""
    if PREDICTZ_CACHE.exists():
        print(f"  Loading Predictz cache: {PREDICTZ_CACHE.name}")
        raw = pd.read_csv(PREDICTZ_CACHE)
        raw["date"] = pd.to_datetime(raw["date"]).dt.strftime("%Y-%m-%d")
        raw["home_team"] = raw["home_team"].map(normalize_odds_team)
        raw["away_team"] = raw["away_team"].map(normalize_odds_team)
        return raw

    try:
        response = _http_get(PREDICTZ_URL, timeout=30)
    except requests.RequestException as exc:
        print(f"  Predictz fetch failed ({exc}); skipping predictions.")
        return pd.DataFrame()

    if "Just a moment" in response.text or "cloudflare" in response.text.lower():
        print(
            "  Predictz blocked by Cloudflare. "
            f"Add manual predictions to {PREDICTZ_CACHE.name} if needed."
        )
        return pd.DataFrame()

    # Lightweight parse if the page ever becomes accessible.
    rows: list[dict] = []
    for block in re.findall(
        r'<div class="ptip">.*?</div>\s*</div>\s*</div>',
        response.text,
        re.S,
    ):
        teams = re.search(r"([A-Za-z .&]+)\s+v\s+([A-Za-z .&]+)", block)
        percents = re.findall(r"(\d+)%", block)
        tip = re.search(r"Tip:\s*([^<]+)", block)
        if teams and len(percents) >= 3:
            rows.append(
                {
                    "date": date.today().isoformat(),
                    "home_team": normalize_odds_team(teams.group(1)),
                    "away_team": normalize_odds_team(teams.group(2)),
                    "pred_home_pct": float(percents[0]) / 100.0,
                    "pred_draw_pct": float(percents[1]) / 100.0,
                    "pred_away_pct": float(percents[2]) / 100.0,
                    "tip_text": tip.group(1).strip() if tip else None,
                    "source": "predictz.com",
                }
            )
    print(f"  Predictz: parsed {len(rows)} rows.")
    return pd.DataFrame(rows)


def merge_odds_sources(frames: list[pd.DataFrame]) -> pd.DataFrame:
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(
        subset=["date", "home_team", "away_team"], keep="last"
    )
    return enrich_odds_frame(combined)


def save_prematch_odds(conn: sqlite3.Connection, odds: pd.DataFrame) -> None:
    ensure_prematch_tables(conn)
    conn.execute("DELETE FROM prematch_odds")
    if odds.empty:
        conn.commit()
        return
    captured = date.today().isoformat()
    odds = odds.copy()
    odds["captured_at"] = captured
    odds[
        [
            "date",
            "home_team",
            "away_team",
            "home_odds",
            "draw_odds",
            "away_odds",
            "implied_home",
            "implied_draw",
            "implied_away",
            "implied_diff",
            "source",
            "captured_at",
        ]
    ].to_sql("prematch_odds", conn, if_exists="append", index=False)
    conn.commit()


def save_prematch_predictions(conn: sqlite3.Connection, preds: pd.DataFrame) -> None:
    ensure_prematch_tables(conn)
    conn.execute("DELETE FROM prematch_predictions")
    if preds.empty:
        conn.commit()
        return
    captured = date.today().isoformat()
    preds = preds.copy()
    preds["captured_at"] = captured
    if "source" not in preds.columns:
        preds["source"] = "predictz.com"
    preds[
        [
            "date",
            "home_team",
            "away_team",
            "pred_home_pct",
            "pred_draw_pct",
            "pred_away_pct",
            "tip_text",
            "source",
            "captured_at",
        ]
    ].to_sql("prematch_predictions", conn, if_exists="append", index=False)
    conn.commit()


def load_prematch_odds(conn: sqlite3.Connection) -> pd.DataFrame:
    ensure_prematch_tables(conn)
    try:
        return pd.read_sql_query("SELECT * FROM prematch_odds", conn)
    except pd.errors.DatabaseError:
        return pd.DataFrame()


def load_prematch_predictions(conn: sqlite3.Connection) -> pd.DataFrame:
    ensure_prematch_tables(conn)
    try:
        return pd.read_sql_query("SELECT * FROM prematch_predictions", conn)
    except pd.errors.DatabaseError:
        return pd.DataFrame()


def run_prematch_download(force: bool = False) -> None:
    print("=== Download pre-match odds ===")
    hf = download_huggingface_odds(force=force)
    fd = download_football_data_international()
    be = download_betexplorer_world_cups()
    odds = merge_odds_sources([hf, fd, be])

    print("\n=== Download pre-match predictions (Predictz) ===")
    preds = download_predictz_predictions()

    conn = get_connection()
    save_prematch_odds(conn, odds)
    save_prematch_predictions(conn, preds)

    if not odds.empty:
        features_exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='features'"
        ).fetchone()
        if features_exists:
            matched = conn.execute(
                """
                SELECT COUNT(*)
                FROM features f
                INNER JOIN prematch_odds p
                  ON f.date = p.date
                 AND f.home_team = p.home_team
                 AND f.away_team = p.away_team
                """
            ).fetchone()[0]
            total = conn.execute("SELECT COUNT(*) FROM features").fetchone()[0]
            print(
                f"\nSaved {len(odds)} prematch_odds rows "
                f"({matched}/{total} feature rows matched)."
            )
        else:
            print(f"\nSaved {len(odds)} prematch_odds rows.")
    else:
        print("\nNo prematch odds rows saved.")

    if not preds.empty:
        print(f"Saved {len(preds)} prematch_predictions rows.")
    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Download pre-match odds/predictions.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download HuggingFace odds cache",
    )
    args = parser.parse_args()
    run_prematch_download(force=args.force)


if __name__ == "__main__":
    main()
