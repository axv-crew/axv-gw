import os, time
from typing import Dict, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_per_minute: int = 60):
        super().__init__(app)
        self.max_per_minute = max_per_minute
        self._buckets: Dict[Tuple[str,str,int], int] = {}

    async def dispatch(self, request, call_next):
        if os.getenv("AXV_TEST_MODE") == "1":
            return await call_next(request)
        now_bucket = int(time.time() // 60)
        client = request.client.host if request.client else "local"
        key = (client, request.url.path, now_bucket)
        self._buckets[key] = self._buckets.get(key, 0) + 1
        if self._buckets[key] > self.max_per_minute:
            return JSONResponse({"detail": "rate limit"}, status_code=429)
        return await call_next(request)
