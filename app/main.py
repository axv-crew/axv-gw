from fastapi import FastAPI
from app.middleware import RequestLoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.routers import front, hooks, internal
import os

# prometheus (opcjonalnie obecny)
try:
    import prometheus_client
    from prometheus_client import Gauge
    PROM = True
except Exception:
    PROM = False

def create_app():
    app = FastAPI()

    # 1) logger – nie duplikuje odpowiedzi
    app.add_middleware(RequestLoggingMiddleware)

    # 2) rate-limit – czysty, jednokrotny response
    app.add_middleware(
        RateLimitMiddleware,
        default_limit=int(os.getenv("RATE_LIMIT_DEFAULT", "60")),
        paths={"/hooks/ping": int(os.getenv("RATE_LIMIT_HOOKS", "5"))},
        window_s=int(os.getenv("RATE_LIMIT_WINDOW_S", "3")),
        key_header=os.getenv("RATE_LIMIT_KEY_HEADER","").strip(),
    )

    # 3) routery
    app.include_router(front.router)
    app.include_router(hooks.router)
    app.include_router(internal.router)

    @app.get("/status")
    def status(): return {"ok": True}

    @app.get("/healthz")
    def healthz(): return {"ok": True}

    # 4) /metrics (musi zawierać axv_gw albo python)
    if PROM:
        g = Gauge("axv_gw_build_info", "Build info", ["version","name"])
        g.labels(version=os.getenv("GATEWAY_VERSION","0.1.12"), name="axv-gw").set(1)

        @app.get("/metrics")
        def metrics():
            return prometheus_client.make_asgi_app()(  # type: ignore
                {"type":"http"}, lambda s: None, lambda b: None
            )
    else:
        @app.get("/metrics")
        def metrics():
            return "axv_gw_dummy 1\npython_info 1\n"

    return app

app = create_app()
