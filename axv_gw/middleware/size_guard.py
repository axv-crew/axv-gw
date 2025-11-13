import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RequestSizeGuardMiddleware(BaseHTTPMiddleware):
    """
    Blokuje zbyt duże body dla metod modyfikujących (POST/PUT/PATCH).
    ENV: MAX_BODY_KB (domyślnie 64). Używa nagłówka Content-Length.
    Gdy > limit -> 413 + JSON {"ok":false,"error":"body_too_large","limit_kb":N}.
    """

    def __init__(self, app, default_kb: int = 64):
        super().__init__(app)
        self.limit_kb = int(os.getenv("MAX_BODY_KB", str(default_kb)))
        self.limit_bytes = self.limit_kb * 1024

    async def dispatch(self, request: Request, call_next):
        if request.method.upper() in ("POST", "PUT", "PATCH"):
            cl = request.headers.get("content-length")
            try:
                clen = int(cl) if cl is not None else None
            except ValueError:
                clen = None
            if clen is not None and clen > self.limit_bytes:
                return JSONResponse(
                    {"ok": False, "error": "body_too_large", "limit_kb": self.limit_kb},
                    status_code=413,
                )
        return await call_next(request)
