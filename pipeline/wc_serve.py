"""Serve WC 2026 predictions from a precomputed JSON artifact (no xgboost)."""

from __future__ import annotations

import json
from functools import lru_cache

from .download_data import normalize_team_name
from .fifa_codes import FIFA_CODE_TO_TEAM
from .paths import WC2026_PREDICTIONS_PATH


def resolve_team(token: str) -> str:
    code = token.strip().upper()
    if code in FIFA_CODE_TO_TEAM:
        return FIFA_CODE_TO_TEAM[code]
    return normalize_team_name(token)


@lru_cache(maxsize=1)
def _load_payload() -> dict:
    if not WC2026_PREDICTIONS_PATH.exists():
        raise FileNotFoundError(
            f"{WC2026_PREDICTIONS_PATH} not found. "
            "Run: python -m pipeline.export_wc_predictions"
        )
    return json.loads(WC2026_PREDICTIONS_PATH.read_text(encoding="utf-8"))


def fixtures_payload() -> list[dict]:
    return list(_load_payload()["fixtures"])


def simulate_all_wc() -> dict:
    return dict(_load_payload()["simulate"])


def simulate_pair(team_a: str, team_b: str) -> dict:
    a = resolve_team(team_a)
    b = resolve_team(team_b)
    if a == b:
        raise ValueError("Select two different teams")

    matches = _load_payload()["simulate"]["matches"]
    for match in matches:
        if {match["team_a"], match["team_b"]} == {a, b}:
            return dict(match)

    raise ValueError(f"No FIFA World Cup 2026 fixture found for {a} vs {b}.")
