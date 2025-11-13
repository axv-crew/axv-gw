
import time, asyncio, os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

try:
    # opcjonalna metryka Prometheus
    from prometheus_client import Counter
    gw_rate_limit_dropped_total = Counter(
        "gw_rate_limit_dropped_total",
        "Requests dropped by rate limiter",
        ["path"]
    )
except Exception:
    gw_rate_limit_dropped_total = None

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, default_limit=60, window_s=60, paths=None, key_header=""):
        super().__init__(app)
        self.default_limit = int(default_limit)
        self.window_s = int(window_s)
        self.paths = paths or {}
        self.key_header = key_header or ""
        self._buckets = {}  # (key, path) -> {"start":ts,"count":n}
        self._lock = asyncio.Lock()

    async def dispatch(self, request, call_next):
        limit = int(self.paths.get(request.url.path, self.default_limit))
        if limit <= 0:
            return await call_next(request)

        now = int(time.time())
        key = (request.headers.get(self.key_header).strip() if self.key_header else (request.client.host if request.client else "0.0.0.0"))
        k = (key, request.url.path)

        async with self._lock:
            b = self._buckets.get(k)
            if not b or now - b["start"] >= self.window_s:
                b = {"start": now, "count": 0}
            b["count"] += 1
            self._buckets[k] = b

            if b["count"] > limit:
                if gw_rate_limit_dropped_total:
                    try: gw_rate_limit_dropped_total.labels(path=request.url.path).inc()
                    except Exception: pass
                retry = max(1, self.window_s - (now - b["start"]))
                return JSONResponse({"detail":"rate limit exceeded"}, status_code=429, headers={"Retry-After": str(retry)})

        # przepuszczamy dalej — nie tworzymy nowej odpowiedzi, nie dotykamy body
        resp = await call_next(request)
        try:
            remaining = max(0, limit - b["count"])
            # nagłówki tylko jeśli nie nadpisane wyżej w stosie
            resp.headers.setdefault("X-RateLimit-Limit", str(limit))
            resp.headers.setdefault("X-RateLimit-Remaining", str(remaining))
        except Exception:
            pass
        return resp
