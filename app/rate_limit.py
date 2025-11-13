import time
from collections import defaultdict, deque
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit_hooks=5, limit_default=60):
        super().__init__(app)
        self.limit_hooks = int(limit_hooks)
        self.limit_default = int(limit_default)
        self.window_s = 1.0
        self.store = defaultdict(deque)

    async def dispatch(self, request, call_next):
        path = request.url.path
        limit = self.limit_hooks if path.startswith("/hooks/") else self.limit_default
        if limit <= 0:
            return await call_next(request)

        now = time.time()
        dq = self.store[path]
        cutoff = now - self.window_s
        while dq and dq[0] < cutoff:
            dq.popleft()

        if len(dq) >= limit:
            # zlicz metrykę w app.state
            try:
                d = getattr(self.app.state, "rl_dropped", None)
                if d is None:
                    d = {}
                    self.app.state.rl_dropped = d
                d[path] = float(d.get(path, 0.0)) + 1.0
            except Exception:
                pass
            return JSONResponse({"detail": "rate limit exceeded"}, status_code=429)

        dq.append(now)
        return await call_next(request)
