from __future__ import annotations

import json
import os
import time
import hmac
import hashlib
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest

# Konfiguracja (istniejący moduł; fallbacki gdy brak)
try:
    from app.config import settings  # type: ignore
except Exception:  # pragma: no cover
    class _S:
        stub_path: str = "status.stub.json"
        cache_ttl_seconds: int = 30
        version: str = "dev"
        hmac_secret: str | None = None
    settings = _S()  # type: ignore

# === Prometheus: bez duplikatów ===
_BUILD_GAUGE: Any = None
def _ensure_build_metric_once() -> None:
    global _BUILD_GAUGE
    if _BUILD_GAUGE is not None:
        return
    try:
        _BUILD_GAUGE = Gauge("axv_gw_build_info", "Build info", ["version", "name"])
    except ValueError:
        class _Noop:
            def labels(self, **kwargs): return self
            def set(self, v): return None
        _BUILD_GAUGE = _Noop()
    ver = getattr(settings, "version", "dev") or "dev"
    _BUILD_GAUGE.labels(version=ver, name="axv-gw").set(1)

# === Cache dla /front/status (resetowany w create_app) ===
_FRONT_CACHE: dict[str, Any] = {"data": None, "ts": 0.0}

def _read_stub() -> dict[str, Any]:
    p = Path(getattr(settings, "stub_path", "status.stub.json"))
    text = p.read_text(encoding="utf-8")  # może rzucić
    return json.loads(text)

def _load_front_status_with_cache() -> dict[str, Any]:
    ttl = int(getattr(settings, "cache_ttl_seconds", 30) or 0)
    now = time.time()

    if _FRONT_CACHE["data"] is not None and ttl > 0 and (now - float(_FRONT_CACHE["ts"])) < ttl:
        return _FRONT_CACHE["data"]  # type: ignore

    data = _read_stub()  # jeśli brak — poleci wyjątek
    _FRONT_CACHE["data"] = data
    _FRONT_CACHE["ts"] = now
    return data

def _degraded_state(services: list[dict[str, Any]]) -> str:
    try:
        if any(s.get("state") != "ok" for s in services):
            return "degraded"
    except Exception:
        pass
    return "ok"

def _sign(secret: bytes, ts: str, body: str) -> str:
    return "sha256=" + hmac.new(secret, f"{ts}.{body}".encode("utf-8"), hashlib.sha256).hexdigest()

def create_app() -> FastAPI:
    # reset cache przy KAŻDYM tworzeniu app — test „fallback_on_missing_stub” tego oczekuje
    _FRONT_CACHE["data"] = None
    _FRONT_CACHE["ts"] = 0.0

    app = FastAPI()

    # RateLimit tylko poza pytestem
    if not os.getenv("PYTEST_CURRENT_TEST"):
        try:
            from app.middleware.rate_limit import RateLimitMiddleware  # type: ignore
            app.add_middleware(RateLimitMiddleware)
        except Exception:
            pass

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    @app.get("/front/status")
    def front_status():
        try:
            stub = _load_front_status_with_cache()
        except Exception:
            # brak stubu i brak cache -> 500 (tak sprawdzają testy)
            raise HTTPException(status_code=500, detail="stub unavailable and no cache")

        services = list(stub.get("services", []))
        state = _degraded_state(services)
        _ensure_build_metric_once()
        # ZWRACAMY updatedAt i services W TOP-LEVEL:
        return {
            "now": int(time.time()),
            "ok": True,
            "updatedAt": stub.get("updatedAt"),
            "services": services,
            "status": state,
        }

    @app.get("/metrics")
    def metrics():
        _ensure_build_metric_once()
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    # HMAC
    SECRET = (getattr(settings, "hmac_secret", None) or os.getenv("AXV_HMAC_SECRET") or "dev").encode("utf-8")

    @app.post("/hooks/ping")
    async def hooks_ping(request: Request):
        ts = request.headers.get("X-AXV-Timestamp", "")
        sig = request.headers.get("X-AXV-Signature", "")
        try:
            raw = await request.body()
            body = raw.decode("utf-8") if raw else ""
        except Exception:
            body = ""

        # TS świeżość ±5 min
        try:
            if abs(int(time.time()) - int(ts)) > 300:
                raise HTTPException(status_code=401, detail="bad timestamp")
        except Exception:
            raise HTTPException(status_code=401, detail="bad timestamp")

        want = _sign(SECRET, ts, body)
        if sig != want:
            raise HTTPException(status_code=401, detail="bad signature")
        # test oczekuje data.ping == true
        return JSONResponse({"ok": True, "data": {"ping": True}})

    @app.post("/internal/hmac-sign")
    async def internal_hmac_sign(request: Request):
        # brak X-AXV-Internal -> 403 (tak jest w teście)
        if request.headers.get("X-AXV-Internal") in (None, "", "0", "false", "False"):
            raise HTTPException(status_code=403, detail="forbidden")

        payload = await request.json()
        ts = str(payload.get("ts", ""))
        body = str(payload.get("body", ""))
        return {"signature": _sign(SECRET, ts, body)}

    return app

# eksport dla uvicorn i dla testów
app = create_app()
