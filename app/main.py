"""FastAPI application factory and configuration."""
from app.routers import internal

import json
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest, multiprocess

from app.config import settings
from app.routers import front, healthz


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "extra"):
            log_data.update(record.extra)

        return json.dumps(log_data)


def setup_logging() -> None:
    """Configure JSON structured logging."""
    # Remove existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Create JSON handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    # Configure root logger
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level.upper())

    # Reduce noise from uvicorn
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger = logging.getLogger(__name__)
    logger.info("AXV Gateway starting up", extra={"version": "0.1.0"})
    yield
    logger.info("AXV Gateway shutting down")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    # Setup logging first
    setup_logging()

    app = FastAPI(
app.include_router(internal.router)

        title="AXV Gateway",
        description="Status API gateway for axv.life frontend",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Include routers
    app.include_router(healthz.router, tags=["health"])
    app.include_router(front.router, tags=["frontend"])

    # Prometheus metrics endpoint
    @app.get("/metrics")
    async def metrics() -> Response:
        """
        Prometheus metrics endpoint.

        Returns:
            Prometheus metrics in text format.
        """
        # Try multiprocess mode first (for production with multiple workers)
        registry = CollectorRegistry()
        try:
            multiprocess.MultiProcessCollector(registry)
            data = generate_latest(registry)
        except Exception:
            # Fallback to default registry for single process
            data = generate_latest()

        return Response(content=data, media_type=CONTENT_TYPE_LATEST)

    return app


# Application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        reload=False,
    )

# --- /status (Aster patch) ---
import time, os
STARTED_AT = globals().get("STARTED_AT", time.time())

@app.get("/status")
def status():
    return {
        "now": int(time.time()),
        "ok": True,
        "service": getattr(settings, "service", "axv-gw"),
        "version": getattr(settings, "version", os.getenv("GATEWAY_VERSION", "0.1.0")),
        "uptime_s": int(time.time() - STARTED_AT),
    }
# --- end patch ---
from app.routers.hooks import router as hooks_router
app.include_router(hooks_router)
