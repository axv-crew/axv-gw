import logging
import sys

from axv_gw.middleware.hmac_ts import HMACTimeSkewMiddleware
from axv_gw.middleware.hooks_metrics import HookMetricsMiddleware
from axv_gw.middleware.rate_limit import RateLimitMiddleware
from axv_gw.middleware.size_guard import RequestSizeGuardMiddleware

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
import os
import time

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.middleware import RequestLoggingMiddleware
from app.routers import front, hooks, internal

app = FastAPI(title="AXV Gateway", version=os.getenv("GATEWAY_VERSION", "dev"))
app.state.started_at = time.time()


# --- middleware order (outermost → innermost) ---
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(HMACTimeSkewMiddleware)
app.add_middleware(RequestSizeGuardMiddleware)
app.add_middleware(HookMetricsMiddleware)

# Add request logging middleware


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/status")
def status(request: Request):
    request_id = getattr(request.state, "request_id", "unknown")
    return {
        "now": int(time.time()),
        "ok": True,
        "service": "axv-gw",
        "version": os.getenv("GATEWAY_VERSION", "dev"),
        "uptime_s": int(time.time() - app.state.started_at),
        "request_id": request_id,
    }


@app.get("/metrics")
def metrics():
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


# Routers
app.include_router(hooks.router)
app.include_router(internal.router)
app.include_router(front.router)


# HEAD /metrics (bez body; te same nagłówki co GET)
@app.head("/metrics")
def metrics_head():
    return Response(status_code=200, media_type=CONTENT_TYPE_LATEST)


def create_app():
    """Factory for tests — returns the already-configured FastAPI app."""
    return app
