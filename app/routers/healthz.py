"""Health check endpoint."""

import logging
from typing import Any

from fastapi import APIRouter
from prometheus_client import Counter

logger = logging.getLogger(__name__)
router = APIRouter()

# Metrics
healthz_requests = Counter(
    "axv_gw_healthz_requests_total", "Total health check requests"
)


@router.get("/healthz")
async def healthz() -> dict[str, Any]:
    """
    Health check endpoint.

    Returns:
        Simple OK response indicating service is alive.
    """
    healthz_requests.inc()
    logger.debug("Health check called")
    return {"ok": True}
