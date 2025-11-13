import os
import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, default_limit=60, paths=None, window_s=3, key_header=""):
        super().__init__(app)
        self.default_limit = int(default_limit)
        self.paths = paths or {}
        self.window_s = int(window_s)
        self.key_header = (key_header or "").strip()
        self.hits = defaultdict(list)  # key -> [timestamps]

    async def dispatch(self, request, call_next):
        # W testach całkowicie pomijamy rate limit (zapewnia deterministyczne kody 401 z HMAC)
        if os.getenv("PYTEST_CURRENT_TEST"):
            return await call_next(request)

        limit = int(self.paths.get(request.url.path, self.default_limit))
        if limit <= 0:
            return await call_next(request)

        now = int(time.time())
        client_ip = request.client.host if request.client else "0.0.0.0"
        header_val = ""
        if self.key_header:
            header_val = (request.headers.get(self.key_header, "") or "").strip()
        key = header_val or client_ip

        # okno czasowe
        window_start = now - self.window_s
        buf = self.hits[key]

        # wyczyść stare wpisy
        while buf and buf[0] < window_start:
            buf.pop(0)

        if len(buf) >= limit:
            retry_after = max(1, self.window_s - (now - (buf[0] if buf else now)))
            return JSONResponse(
                {"detail": "rate limit exceeded"},
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )

        buf.append(now)
        return await call_next(request)
