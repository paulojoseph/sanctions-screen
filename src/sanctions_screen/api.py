"""Small HTTP wrapper. Meant to run on localhost, next to whatever calls it."""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import __version__, config, match
from .screen import get_index, hit_to_dict, screen_name

app = FastAPI(title="sanctions-screen", version=__version__)


class ScreenRequest(BaseModel):
    name: str
    dob: str | None = None
    country: str | None = None
    threshold: float | None = None  # 0-1, same scale as the library
    mode: str = "balanced"
    customer_id: str | None = None


def _index():
    path = os.environ.get("SANCTIONS_SCREEN_INDEX", str(config.DEFAULT_INDEX_PATH))
    try:
        return get_index(path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/health")
def health():
    idx = _index()
    return {
        "status": "ok",
        "version": __version__,
        "entities": len(idx.entities),
        "sources": idx.sources,
        "index_built_at": idx.built_at,
    }


@app.post("/screen")
def screen(req: ScreenRequest):
    if req.mode not in match.MODES:
        raise HTTPException(status_code=422, detail=f"mode must be one of {match.MODES}")
    try:
        hits = screen_name(
            _index(), req.name, dob=req.dob, country=req.country, threshold=req.threshold,
            mode=req.mode, customer_id=req.customer_id,
            decisions_path=config.DEFAULT_DECISIONS_PATH,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"query": req.name, "hits": [hit_to_dict(h) for h in hits]}
