import os
import time
import asyncio
from collections import defaultdict, deque
from typing import Deque, Dict, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from axv_gw.metrics import rate_limit_dropped

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window 60s rate limit per (client_ip, path).
    ENV:
      RATE_LIMIT_DEFAULT (int/min), RATE_LIMIT_HOOKS (int/min for /hooks/*)
    429 JSON + Retry-After.
    """
    def __init__(self, app, default_limit: int | None = None,
                 hooks_limit: int | None = None, window_seconds: int = 60):
        super().__init__(app)
        self.window = window_seconds
        self.default_limit = int(os.getenv("RATE_LIMIT_DEFAULT",
            str(default_limit if default_limit is not None else 60)))
        self.hooks_limit = int(os.getenv("RATE_LIMIT_HOOKS",
            str(hooks_limit if hooks_limit is not None else 5)))
        self.buckets: Dict[Tuple[str, str], Deque[float]] = defaultdict(deque)
        self.lock = asyncio.Lock()

    def _client_ip(self, request: Request) -> str:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            first = xff.split(",")[0].strip()
            if first:
                return first
        return request.headers.get('X-Forwarded-For', request.client.host if request.client else '') if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        client_ip = self._client_ip(request)
        limit = self.hooks_limit if path.startswith("/hooks/") else self.default_limit

        now = time.monotonic()
        key = (client_ip, path)

        async with self.lock:
            dq = self.buckets[key]
            cutoff = now - self.window
            while dq and dq[0] <= cutoff:
                dq.popleft()

            if len(dq) >= limit:
                retry_after = max(int(dq[0] + self.window - now) + 1, 1)
                rate_limit_dropped.labels(path=path).inc()
                return JSONResponse(
                    {"ok": False, "error": "rate_limited", "retry_after_s": retry_after},
                    status_code=429,
                    headers={"Retry-After": str(retry_after)},
                )
            dq.append(now)

        return await call_next(request)
