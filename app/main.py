import logging, sys
from axv_gw.middleware.hooks_metrics import HookMetricsMiddleware
from axv_gw.middleware.size_guard import RequestSizeGuardMiddleware
from axv_gw.middleware.hmac_ts import HMACTimeSkewMiddleware
from axv_gw.middleware.rate_limit import RateLimitMiddleware
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
import os, time
from fastapi import FastAPI, Response, Request
from app.config import settings
from app.routers import hooks, internal
from app.middleware import RequestLoggingMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

app = FastAPI(title="AXV Gateway", version=os.getenv("GATEWAY_VERSION", "dev"))
app.state.started_at = time.time()

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(HMACTimeSkewMiddleware)
app.add_middleware(RequestSizeGuardMiddleware)

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

# HEAD /metrics (bez body; te same nagłówki co GET)
@app.head("/metrics")
def metrics_head():
    return Response(status_code=200, media_type=CONTENT_TYPE_LATEST)
app.add_middleware(HookMetricsMiddleware)
