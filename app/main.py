
from __future__ import annotations
import os, sys, time, threading, platform
from typing import Dict, Tuple
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse

## --- Prosty, samowystarczalny RateLimiter (ASGI, bez zewn. importów) ---
class SimpleRateLimiterMiddleware:
    def __init__(self, app, default_limit:int=60, paths:dict|None=None,
                 window_s:int=3, key_header:str="",
                 metrics:dict|None=None):
        self.app = app
        self.default_limit = int(default_limit)
        self.paths = dict(paths or {})
        self.window_s = int(window_s)
        self.key_header = key_header or ""
        self.metrics = metrics if metrics is not None else {"gw_rate_limit_dropped_total": {}}
        self._lock = threading.Lock()
        # (key, path, window) -> count
        self._buckets: Dict[Tuple[str,str,int], int] = {}

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # przygotuj wywołanie next
        async def call_next():
            response_body = []
            status = {"code": 200}
            headers = []

            async def _send(message):
                if message["type"] == "http.response.start":
                    status["code"] = message["status"]
                    hdrs = message.get("headers", [])
                    headers.extend(hdrs)
                elif message["type"] == "http.response.body":
                    response_body.append(message.get("body", b""))
                await send(message)

            await self.app(scope, receive, _send)
            return status["code"], headers, b"".join(response_body)

        path = scope.get("path", "/")
        limit = int(self.paths.get(path, self.default_limit))
        if limit <= 0:
            # RL disabled
            await self.app(scope, receive, send)
            return

        # Klucz: nagłówek lub IP
        headers = dict((k.decode().lower(), v.decode()) for k, v in scope.get("headers", []))
        key = headers.get(self.key_header.lower()) if self.key_header else (scope.get("client") or ["",""])[0]
        key = key or "unknown"

        now = int(time.time())
        window = now - (now % self.window_s)
        bucket = (key, path, window)

        with self._lock:
            cnt = self._buckets.get(bucket, 0) + 1
            self._buckets[bucket] = cnt
            remaining = max(0, limit - cnt)
            over = cnt > limit

        # Przy 429: zwróć od razu JSON + nagłówki limitu
        if over:
            retry_after = (window + self.window_s) - now
            with self._lock:
                self.metrics["gw_rate_limit_dropped_total"][path] = \
                    self.metrics["gw_rate_limit_dropped_total"].get(path, 0) + 1
            body = JSONResponse({"detail": "rate limit exceeded"}, status_code=429)
            body.headers["X-RateLimit-Limit"] = str(limit)
            body.headers["X-RateLimit-Remaining"] = "0"
            body.headers["Retry-After"] = str(max(0, retry_after))
            await body(scope, receive, send)
            return

        # normalne przejście
        status_code, hdrs, body_bytes = await call_next()

        # Doklej nagłówki RL
        hdr_map = {k.decode().lower(): v.decode() for k, v in hdrs}
        if "x-ratelimit-limit" not in hdr_map:
            hdrs.append((b"x-ratelimit-limit", str(limit).encode()))
        if "x-ratelimit-remaining" not in hdr_map:
            hdrs.append((b"x-ratelimit-remaining", str(remaining).encode()))

        # wyślij start + body (ponownie), bo interceptowaliśmy call_next
        await send({
            "type": "http.response.start",
            "status": status_code,
            "headers": hdrs,
        })
        await send({
            "type": "http.response.body",
            "body": body_bytes,
        })

## --- Aplikacja ---
def create_app() -> FastAPI:
    app = FastAPI(title="axv-gw")

    # Metryki (w prostym słowniku)
    metrics = {
        "build": {"version": os.getenv("GATEWAY_VERSION", "0.1.11"), "name": "axv-gw"},
        "python": {"version": platform.python_version()},
        "gw_rate_limit_dropped_total": {},  # {path: count}
    }

    # Routers (best-effort — jeśli są, to dołączamy)
    try:
        from app.routers import front
        app.include_router(front.router)
    except Exception:
        pass
    try:
        from app.routers import hooks
        app.include_router(hooks.router)
    except Exception:
        pass
    try:
        from app.routers import internal
        app.include_router(internal.router)
    except Exception:
        pass

    # Proste /status i /healthz (żeby zawsze były)
    @app.get("/status")
    async def status():
        return {"ok": True}

    @app.get("/healthz")
    async def healthz():
        return {"ok": True}

    # Prometheus metrics (tekstem)
    @app.get("/metrics", response_class=PlainTextResponse)
    async def metrics_endpoint():
        lines = []
        # build info
        lines.append("# HELP axv_gw_build_info Build info")
        lines.append("# TYPE axv_gw_build_info gauge")
        lines.append(f'axv_gw_build_info{{version="{metrics["build"]["version"]}",name="{metrics["build"]["name"]}"}} 1')
        # python info
        lines.append("# HELP python_info Python runtime info")
        lines.append("# TYPE python_info gauge")
        lines.append(f'python_info{{version="{metrics["python"]["version"]}"}} 1')
        # rl counter
        lines.append("# HELP gw_rate_limit_dropped_total Requests dropped by rate limiter")
        lines.append("# TYPE gw_rate_limit_dropped_total counter")
        for pth, cnt in metrics["gw_rate_limit_dropped_total"].items():
            lines.append(f'gw_rate_limit_dropped_total{{path="{pth}"}} {cnt}')
        return "\n".join(lines) + "\n"

    # Rate limiting — konfiguracja z ENV
    default_limit = int(os.getenv("RATE_LIMIT_DEFAULT", "60"))
    per_path = {
        "/hooks/ping": int(os.getenv("RATE_LIMIT_HOOKS", "5")),
    }
    window_s = int(os.getenv("RATE_LIMIT_WINDOW_S", "3"))
    key_hdr = os.getenv("RATE_LIMIT_KEY_HEADER", "")  # pusty => per-IP

    # Wpięcie naszego middleware A/B testowo — zawsze działa, bo jest w tym pliku
    app.add_middleware = getattr(app, "add_middleware")
    app.add_middleware(SimpleRateLimiterMiddleware,
                       default_limit=default_limit,
                       paths=per_path,
                       window_s=window_s,
                       key_header=key_hdr,
                       metrics=metrics)

    return app

app = create_app()
