"""Request logging middleware with correlation ID."""

import json
import logging
import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to:
    - Generate/extract X-Request-ID
    - Log requests in JSON format
    - Measure request duration
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Store in request state for downstream use
        request.state.request_id = request_id

        # Start timer
        start_time = time.time()

        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            logger.exception(f"Request failed: {e}")
            status_code = 500
            raise
        finally:
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Log in JSON format
            log_data = {
                "ts": int(time.time()),
                "method": request.method,
                "path": request.url.path,
                "status": status_code,
                "duration_ms": duration_ms,
                "req_id": request_id,
                "ua": request.headers.get("User-Agent", ""),
                "ip": request.client.host if request.client else "",
            }

            # Log as JSON
            logger.info(json.dumps(log_data))

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response
