from fastapi import FastAPI
from starlette.testclient import TestClient

from axv_gw.middleware.size_guard import RequestSizeGuardMiddleware


def _app():
    app = FastAPI()
    app.add_middleware(RequestSizeGuardMiddleware)

    @app.post("/hooks/ping")
    def ping():
        return {"ok": True}

    return app


def test_size_under_limit_ok(monkeypatch):
    monkeypatch.setenv("MAX_BODY_KB", "1")  # 1 KB
    c = TestClient(_app())
    body = b"a" * 900  # < 1024
    r = c.post("/hooks/ping", data=body)
    assert r.status_code == 200


def test_size_over_limit_413(monkeypatch):
    monkeypatch.setenv("MAX_BODY_KB", "1")  # 1 KB
    c = TestClient(_app())
    body = b"b" * (1024 + 1)  # > 1 KB
    r = c.post("/hooks/ping", data=body)
    assert r.status_code == 413
    j = r.json()
    assert j["ok"] is False and j["error"] == "body_too_large" and j["limit_kb"] == 1
