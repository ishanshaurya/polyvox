"""PolyVox API — product HTTP surface."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import init_db
from app.routers import health, projects
from app.settings import settings

app = FastAPI(
    title="PolyVox API",
    version="0.2.0",
    description="Call QA product API. White-glove hosting; short retention (see docs/HOSTING.md).",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(projects.router, prefix="/v1")


@app.on_event("startup")
def on_startup() -> None:
    Path(settings.data_root).mkdir(parents=True, exist_ok=True)
    init_db()


@app.get("/")
def root() -> dict:
    return {
        "product": "PolyVox",
        "docs": "/docs",
        "hosting": "white-glove",
        "default_retention_days": settings.default_retention_days,
        "default_rubric_pack": settings.default_rubric_pack,
    }
