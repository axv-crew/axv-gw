from fastapi import FastAPI
from starlette.testclient import TestClient

from axv_gw.middleware.rate_limit import RateLimitMiddleware


def _build_app():
    app = FastAPI()

    @app.get("/status")
    def status():
        return {"ok": True}

    @app.post("/hooks/ping")
    def ping():
        return {"ok": True}

    app.add_middleware(RateLimitMiddleware)
    return app


def test_rate_limit_default_per_ip_path(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_DEFAULT", "3")
    monkeypatch.setenv("RATE_LIMIT_HOOKS", "2")

    app = _build_app()
    c = TestClient(app)
    headers = {"X-Forwarded-For": "1.2.3.4"}

    for _ in range(3):
        r = c.get("/status", headers=headers)
        assert r.status_code == 200

    r = c.get("/status", headers=headers)
    assert r.status_code == 429
    body = r.json()
    assert body["ok"] is False and body["error"] == "rate_limited"
    assert "retry_after_s" in body


def test_hooks_have_stricter_limit(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_DEFAULT", "60")
    monkeypatch.setenv("RATE_LIMIT_HOOKS", "2")

    app = _build_app()
    c = TestClient(app)
    h = {"X-Forwarded-For": "5.6.7.8"}

    for _ in range(2):
        assert c.post("/hooks/ping", headers=h).status_code == 200

    r = c.post("/hooks/ping", headers=h)
    assert r.status_code == 429
