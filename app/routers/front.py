"""Frontend status endpoint with caching and fallback."""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from prometheus_client import Counter, Gauge, Histogram

from app.config import settings
from app.schemas.status import FrontStatusV1, ServiceState

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/front")

# Metrics
status_requests = Counter(
    "axv_gw_front_status_requests_total", "Total front status requests", ["status_code"]
)
status_fetch_duration = Histogram(
    "axv_gw_front_status_fetch_seconds", "Time to fetch status data"
)
cache_hits = Counter(
    "axv_gw_front_status_cache_hits_total", "Cache hits for status data"
)
cache_misses = Counter(
    "axv_gw_front_status_cache_misses_total", "Cache misses for status data"
)
degraded_mode = Gauge(
    "axv_gw_front_status_degraded", "Whether service is in degraded mode (1=yes, 0=no)"
)

# In-memory cache
_cache: dict | None = None
_cache_timestamp: datetime | None = None


def _load_stub() -> dict:
    """
    Load status data from stub JSON file.

    Returns:
        Parsed JSON data from stub file.

    Raises:
        HTTPException: If stub file cannot be loaded.
    """
    stub_path = Path(settings.stub_path)

    try:
        with open(stub_path, encoding="utf-8") as f:
            data = json.load(f)
            logger.info(f"Loaded stub data from {stub_path}")
            return data
    except FileNotFoundError:
        logger.error(f"Stub file not found: {stub_path}")
        raise HTTPException(status_code=500, detail=f"Stub file not found: {stub_path}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in stub file: {e}")
        raise HTTPException(status_code=500, detail=f"Invalid JSON in stub file: {e}")


def _is_cache_valid() -> bool:
    """Check if cached data is still valid based on TTL."""
    if _cache is None or _cache_timestamp is None:
        return False

    now = datetime.now(UTC)
    age_seconds = (now - _cache_timestamp).total_seconds()

    return age_seconds < settings.cache_ttl_seconds


def _apply_degraded_mode(data: dict) -> dict:
    """
    Apply degraded mode banner by checking service states.

    If any service state is not "ok", this is considered degraded mode.

    Args:
        data: Status data to check

    Returns:
        Original data (modified in place is acceptable but we return for clarity)
    """
    services = data.get("services", [])
    has_issues = any(svc.get("state") != ServiceState.OK.value for svc in services)

    if has_issues:
        degraded_mode.set(1)
        logger.warning("Service in degraded mode - non-ok states detected")
    else:
        degraded_mode.set(0)

    return data


@router.get("/status", response_model=FrontStatusV1)
async def get_front_status() -> FrontStatusV1:
    """
    Get current frontend status.

    Data flow:
    1. Check cache (TTL-based)
    2. If cache miss, load from stub
    3. Apply degraded mode check
    4. Return validated response

    Fallback strategy:
    - On any error loading stub, return cached data if available
    - If no cache available, raise 500 error

    Returns:
        Frontend status following FrontStatusV1 contract
    """
    global _cache, _cache_timestamp

    with status_fetch_duration.time():
        # Check cache first
        if _is_cache_valid():
            cache_hits.inc()
            logger.debug("Cache hit - returning cached status")
            status_requests.labels(status_code="200").inc()
            return FrontStatusV1(**(_cache or {}))

        cache_misses.inc()
        logger.debug("Cache miss - fetching fresh data")

        # Try to load fresh data from stub
        try:
            data = _load_stub()

            # Update cache
            _cache = data
            _cache_timestamp = datetime.now(UTC)

            # Apply degraded mode check
            _apply_degraded_mode(data)

            # Validate and return
            response = FrontStatusV1(**(data or {}))
            status_requests.labels(status_code="200").inc()
            logger.info("Successfully loaded and cached status data")

            return response

        except Exception as e:
            logger.error(f"Error loading stub: {e}")

            # Fallback to stale cache if available
            if _cache is not None:
                logger.warning("Falling back to stale cache due to error")
                degraded_mode.set(1)
                status_requests.labels(status_code="200").inc()
                return FrontStatusV1(**(_cache or {}))

            # No cache available - fail
            logger.error("No cache available for fallback")
            status_requests.labels(status_code="500").inc()
            raise
