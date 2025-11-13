import os
import time

from prometheus_client import Counter
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# Prometheus counter (kompatybilny z wcześniejszą nazwą):
rl_dropped = Counter(
    "gw_rate_limit_dropped_total",
    "Requests dropped by rate limiter",
    ["path"],
)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Prosty RL: okno 1s, limit z ENV:
      - RATE_LIMIT_HOOKS (dla ścieżek /hooks/*) domyślnie 5
      - RATE_LIMIT_DEFAULT (dla reszty) domyślnie 60
    Klucz: (ip, path, floor(now)).
    """
    _buckets: dict[tuple[str,str,int], int] = {}

    def _limit_for_path(self, path: str) -> int:
        if path.startswith("/hooks/"):
            return int(os.getenv("RATE_LIMIT_HOOKS", "5"))
        return int(os.getenv("RATE_LIMIT_DEFAULT", "60"))

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        limit = self._limit_for_path(path)
        now = int(time.time())
        ip = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
        if not ip:
            ip = request.client.host if request.client else ""

        key = (ip, path, now)
        cnt = self._buckets.get(key, 0) + 1
        self._buckets[key] = cnt

        if cnt > limit:
            rl_dropped.labels(path=path).inc()
            return JSONResponse({"detail": "rate limited"}, status_code=429)

        return await call_next(request)
