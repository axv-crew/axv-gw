import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from axv_gw.metrics import hooks_duration_ms, hooks_ok


class HookMetricsMiddleware(BaseHTTPMiddleware):
    """Measure duration and count OKs for /hooks/*."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith("/hooks/"):
            return await call_next(request)

        t0 = time.perf_counter_ns()
        resp = await call_next(request)
        dt_ms = (time.perf_counter_ns() - t0) / 1_000_000.0

        hooks_duration_ms.observe(dt_ms)
        if resp.status_code < 400:
            hooks_ok.labels(path).inc()
        return resp
