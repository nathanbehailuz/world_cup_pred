"""FastAPI wrapping pipeline.wc_simulate for the WC 2026 Predict UI."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Allow `uvicorn web.api.main:app` from repo root
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.wc_simulate import (  # noqa: E402
    fixtures_payload,
    simulate_all_wc,
    simulate_pair,
)

app = FastAPI(title="WC 2026 Predictor API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PredictBody(BaseModel):
    team_a: str = Field(..., description="FIFA code or team name")
    team_b: str = Field(..., description="FIFA code or team name")


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/wc2026/fixtures")
def wc_fixtures() -> dict:
    try:
        return {"fixtures": fixtures_payload()}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/predict")
def predict_match(body: PredictBody) -> dict:
    try:
        return simulate_pair(body.team_a, body.team_b)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/wc2026/simulate")
def simulate_tournament() -> dict:
    """Run the production model on every resolved WC 2026 fixture."""
    try:
        return simulate_all_wc()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
