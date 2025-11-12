import os
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from axv_gw.metrics import hmac_bad_ts


class HMACTimeSkewMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, skew_s: int | None = None):
        super().__init__(app)
        # domyślnie ±5 min
        self.max_skew = int(
            os.getenv("HMAC_MAX_SKEW_S", str(skew_s if skew_s is not None else 300))
        )

    async def dispatch(self, request: Request, call_next):
        # tylko dla /hooks/*
        path = request.url.path
        if not path.startswith("/hooks/"):
            return await call_next(request)

        # akceptuj oba warianty nagłówka
        ts = request.headers.get("X-AXV-Timestamp") or request.headers.get(
            "X-Signature-Timestamp"
        )

        # brak TS → przepuść; downstream (hmac_verify) zdecyduje
        if not ts:
            return await call_next(request)

        # TS musi być intem (epoch seconds)
        try:
            ts_i = int(ts)
        except Exception:
            hmac_bad_ts.labels(path=path).inc()
            return JSONResponse({"ok": False, "error": "bad timestamp"}, status_code=401)

        now = int(time.time())
        if abs(now - ts_i) > self.max_skew:
            hmac_bad_ts.labels(path=path).inc()
            return JSONResponse({"ok": False, "error": "bad timestamp"}, status_code=401)

        return await call_next(request)
