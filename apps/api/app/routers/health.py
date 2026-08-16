from __future__ import annotations

from fastapi import APIRouter

from app.settings import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "retention_days_default": settings.default_retention_days,
        "data_root": settings.data_root,
    }
