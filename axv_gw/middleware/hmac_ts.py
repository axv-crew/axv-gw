import os, time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from axv_gw.metrics import hmac_bad_ts

class HMACTimeSkewMiddleware(BaseHTTPMiddleware):
    """
    Enforce HMAC timestamp tolerance for /hooks/*.
    Header: X-Signature-Timestamp (epoch seconds, int).
    ENV: HMAC_MAX_SKEW_S (default 300).
    Out-of-range or missing -> 401 JSON {"ok":false,"error":"bad timestamp"}.
    """

    def __init__(self, app, header_name: str = "X-Signature-Timestamp", skew_default: int = 300):
        super().__init__(app)
        self.header = header_name
        self.skew_s = int(os.getenv("HMAC_MAX_SKEW_S", str(skew_default)))

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith("/hooks/"):
            return await call_next(request)

        ts_raw = request.headers.get(self.header)
        try:
            ts = int(ts_raw) if ts_raw is not None else None
        except ValueError:
            ts = None

        now = int(time.time())
        if ts is None or abs(now - ts) > self.skew_s:
            hmac_bad_ts.labels(path=path).inc()
            return JSONResponse({"ok": False, "error": "bad timestamp"}, status_code=401)

        return await call_next(request)
