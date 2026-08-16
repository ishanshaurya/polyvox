"""PolyVox API — product HTTP surface (Phase 0 scaffold)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import health, projects
from app.settings import settings

app = FastAPI(
    title="PolyVox API",
    version="0.1.0",
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


@app.get("/")
def root() -> dict:
    return {
        "product": "PolyVox",
        "docs": "/docs",
        "hosting": "white-glove",
        "default_retention_days": settings.default_retention_days,
    }
