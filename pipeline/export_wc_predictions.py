"""Export precomputed WC 2026 predictions for the slim Vercel API."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .paths import WC2026_PREDICTIONS_PATH
from .wc_simulate import fixtures_payload, simulate_all_wc


def export_wc_predictions(dest: Path = WC2026_PREDICTIONS_PATH) -> Path:
    simulate = simulate_all_wc()
    fixtures = fixtures_payload()
    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "fixtures": fixtures,
        "simulate": simulate,
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    size = dest.stat().st_size
    print(
        f"Wrote {dest} ({size:,} bytes) — "
        f"{len(fixtures)} fixtures, {len(simulate['matches'])} predictions"
    )
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export WC 2026 predictions JSON for the web API / Vercel."
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=WC2026_PREDICTIONS_PATH,
        help=f"Output path (default: {WC2026_PREDICTIONS_PATH})",
    )
    args = parser.parse_args()
    export_wc_predictions(args.dest)


if __name__ == "__main__":
    main()
