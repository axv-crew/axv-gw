import time

from fastapi import FastAPI
from starlette.testclient import TestClient

from axv_gw.middleware.hmac_ts import HMACTimeSkewMiddleware


def _app():
    app = FastAPI()
    app.add_middleware(HMACTimeSkewMiddleware)

    @app.post("/hooks/ping")
    def ping():
        return {"ok": True}

    @app.get("/status")
    def status():
        return {"ok": True}

    return app


def test_hmac_ts_accepts_within_skew(monkeypatch):
    fixed_now = 2_000_000_000
    monkeypatch.setattr(time, "time", lambda: fixed_now)

    c = TestClient(_app())
    # ts == now -> 200
    r = c.post("/hooks/ping", headers={"X-Signature-Timestamp": str(fixed_now)})
    assert r.status_code == 200


def test_hmac_ts_rejects_future_beyond_skew(monkeypatch):
    fixed_now = 2_000_000_000
    monkeypatch.setattr(time, "time", lambda: fixed_now)

    c = TestClient(_app())
    # default skew 300 -> now + 400 powinno dać 401
    r = c.post("/hooks/ping", headers={"X-Signature-Timestamp": str(fixed_now + 400)})
    assert r.status_code == 401
    assert r.json()["error"] == "bad timestamp"


def test_hmac_ts_rejects_past_beyond_skew(monkeypatch):
    fixed_now = 2_000_000_000
    monkeypatch.setattr(time, "time", lambda: fixed_now)

    c = TestClient(_app())
    r = c.post("/hooks/ping", headers={"X-Signature-Timestamp": str(fixed_now - 400)})
    assert r.status_code == 401
    assert r.json()["error"] == "bad timestamp"
