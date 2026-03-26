"""Health check endpoint."""

from __future__ import annotations

import os

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    """Return server health status."""
    return {
        "status": "ok",
        "repo_url": os.environ.get("REPO_URL", ""),
        "branch": os.environ.get("DEFAULT_BRANCH", "main"),
    }
