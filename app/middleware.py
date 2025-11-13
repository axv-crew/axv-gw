from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        # Store in request state for downstream use
        request.state.request_id = request_id
        # Start timer
        start_time = time.time()

        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
        except Exception as exc:  # noqa: BLE001
            logger.exception("Request failed: %s", exc)
            raise
        finally:
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            # Resolve client IP (prefer X-Forwarded-For)
            xff = request.headers.get("X-Forwarded-For")
            client_ip = (
                xff.split(",")[0].strip()
                if xff
                else (request.client.host if request.client else "")
            )
            # Log in JSON format
            log_data = {
                "ts": int(time.time()),
                "method": request.method,
                "path": request.url.path,
                "status": status,
                "duration_ms": duration_ms,
                "req_id": request_id,
                "ua": request.headers.get("User-Agent", ""),
                "ip": request.client.host if request.client else "",
                "client_ip": client_ip,
            }
            logger.info(json.dumps(log_data))

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        return response
