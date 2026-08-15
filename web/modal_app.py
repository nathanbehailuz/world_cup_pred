"""Modal web app: live XGBoost FastAPI for WC 2026 Predict."""

from __future__ import annotations

from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parents[1]

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "numpy>=1.24.0",
        "xgboost>=2.0.0",
        "scikit-learn>=1.3.0",
        "fastapi>=0.115.0",
        "pydantic>=2.0.0",
    )
    .add_local_dir(
        ROOT / "pipeline",
        remote_path="/root/pipeline",
        ignore=["**/__pycache__", "**/*.pyc"],
    )
    .add_local_dir(
        ROOT / "web",
        remote_path="/root/web",
        ignore=[
            "**/__pycache__",
            "**/*.pyc",
            "frontend/**",
            "modal_app.py",
        ],
    )
    .add_local_file(
        ROOT / "models" / "xgb_model.json",
        remote_path="/root/models/xgb_model.json",
    )
    .add_local_file(
        ROOT / "models" / "model_meta.json",
        remote_path="/root/models/model_meta.json",
    )
    .add_local_file(
        ROOT / "data" / "inference.db",
        remote_path="/root/data/inference.db",
    )
)

app = modal.App("world-cup-pred", image=image)


@app.function(
    scaledown_window=300,
    timeout=120,
)
@modal.concurrent(max_inputs=20)
@modal.asgi_app()
def api():
    import sys

    if "/root" not in sys.path:
        sys.path.insert(0, "/root")

    from web.api.main import app as fastapi_app

    return fastapi_app
