import os
import sys

from fastapi import FastAPI
from starlette.responses import PlainTextResponse

from app.routers import front, healthz, hooks, internal


def create_app() -> FastAPI:
    app = FastAPI(title="AXV Gateway", version=os.getenv("GATEWAY_VERSION", "0.1.x"))

    # opcjonalne logowanie żądań, jeśli dostępne
    try:
        from app.middleware import RequestLoggingMiddleware
        app.add_middleware(RequestLoggingMiddleware)
    except Exception:
        pass

    # Routers
    app.include_router(front.router)
    app.include_router(hooks.router)
    app.include_router(internal.router)
    app.include_router(healthz.router)

    @app.get("/status")
    async def status():
        return {"ok": True}

    @app.get("/metrics")
    async def metrics():
        version = os.getenv("GATEWAY_VERSION", "0.1.x")
        name = os.getenv("GATEWAY_NAME", "axv-gw")
        pyver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        body = (
            "# HELP axv_gw_build_info Build info\n"
            "# TYPE axv_gw_build_info gauge\n"
            f'axv_gw_build_info{{version="{version}",name="{name}"}} 1\n'
            "# HELP python_info Python runtime info\n"
            "# TYPE python_info gauge\n"
            f'python_info{{version="{pyver}"}} 1\n'
        )
        return PlainTextResponse(body, media_type="text/plain; version=0.0.4")

    return app

app = create_app()
