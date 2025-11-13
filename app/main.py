from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os

# Routers
from app.routers import front, hooks, internal

# Opcjonalne logi żądań (nie wywalaj jeśli brak)
try:
    from app.middleware import RequestLoggingMiddleware
except Exception:
    RequestLoggingMiddleware = None

app = FastAPI(title="AXV Gateway")

# Middleware (jeśli dostępny)
if RequestLoggingMiddleware:
    app.add_middleware(RequestLoggingMiddleware)

# Rejestracja routerów (zachowuje istniejące ścieżki: /front/status, /hooks/ping, /internal/hmac-sign)
app.include_router(front.router)
app.include_router(hooks.router)
app.include_router(internal.router)

# Lekki alias /status (fallback; nie woła frontu, tylko zwraca prostą odpowiedź 200)
@app.get("/status")
async def status_alias():
    version = os.getenv("GATEWAY_VERSION") or os.getenv("GW_VERSION") or os.getenv("VERSION") or "dev"
    return JSONResponse({"ok": True, "status": {"api": "ok", "version": version}})
