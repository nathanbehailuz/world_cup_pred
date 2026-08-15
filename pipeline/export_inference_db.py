"""Export a slim SQLite DB for API inference (team_ratings + schedule only)."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from .paths import DB_PATH, INFERENCE_DB_PATH

TABLES = ("team_ratings", "schedule")


def export_inference_db(
    source: Path = DB_PATH,
    dest: Path = INFERENCE_DB_PATH,
) -> Path:
    if not source.exists():
        raise FileNotFoundError(
            f"{source} not found. Run the pipeline (download + features) first."
        )

    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()

    src = sqlite3.connect(source)
    out = sqlite3.connect(dest)
    try:
        for table in TABLES:
            row = src.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            ).fetchone()
            if row is None:
                raise FileNotFoundError(f"Table '{table}' missing from {source}")
            out.execute(row[0])
            cols = [r[1] for r in src.execute(f"PRAGMA table_info({table})")]
            col_list = ", ".join(cols)
            rows = src.execute(f"SELECT {col_list} FROM {table}").fetchall()
            placeholders = ", ".join("?" * len(cols))
            out.executemany(
                f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})",
                rows,
            )
            print(f"  {table}: {len(rows)} rows")

        for (idx_sql,) in src.execute(
            """
            SELECT sql FROM sqlite_master
            WHERE type = 'index'
              AND tbl_name IN ('team_ratings', 'schedule')
              AND sql IS NOT NULL
            """
        ):
            out.execute(idx_sql)

        out.commit()
        out.execute("VACUUM")
    finally:
        out.close()
        src.close()

    print(f"Wrote {dest} ({dest.stat().st_size:,} bytes)")
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export slim inference DB for the web API / Vercel."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DB_PATH,
        help="Full pipeline SQLite DB (default: data/worldcup.db)",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=INFERENCE_DB_PATH,
        help="Output path (default: data/inference.db)",
    )
    args = parser.parse_args()
    export_inference_db(source=args.source, dest=args.dest)


if __name__ == "__main__":
    main()
