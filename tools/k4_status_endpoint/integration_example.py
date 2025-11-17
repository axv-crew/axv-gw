"""
Przykład integracji /axv/status endpoint z główną aplikacją FastAPI

Umieść ten kod w swoim main.py lub app.py
"""

from fastapi import FastAPI
from axv_status_endpoint import router as status_router, configure_status_endpoint
import os

# ============================================================================
# App Setup
# ============================================================================

app = FastAPI(
    title="AXV API",
    version="0.1.9",
    description="AXV Cluster API with unified status endpoint"
)

# ============================================================================
# Configuration
# ============================================================================

# Załaduj konfigurację z ENV lub pliku config
config = {
    "gateway_healthz_url": os.getenv("GATEWAY_HEALTHZ_URL", "http://127.0.0.1:8000/axv/healthz"),
    "n8n_healthz_url": os.getenv("N8N_HEALTHZ_URL", "http://n8n.axv.life/healthz"),
    "healthcheck_timeout": float(os.getenv("HEALTHCHECK_TIMEOUT", "2.0")),
}

# Konfiguruj status endpoint
configure_status_endpoint(app, config)

# ============================================================================
# Include Routers
# ============================================================================

# Status endpoint
app.include_router(status_router)

# Twoje inne routery...
# app.include_router(other_router)


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint - redirect to /axv/status"""
    return {
        "service": "axv-api",
        "version": "0.1.9",
        "status_endpoint": "/axv/status",
        "docs": "/docs"
    }


# ============================================================================
# Startup/Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup"""
    print("🚀 AXV API starting up...")
    print(f"📊 Status endpoint available at: /axv/status")
    print(f"🔍 Gateway healthz: {config['gateway_healthz_url']}")
    print(f"⚡ n8n healthz: {config['n8n_healthz_url']}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("👋 AXV API shutting down...")


# ============================================================================
# Run
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True  # Tylko w dev
    )
