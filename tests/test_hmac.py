import hashlib
import hmac
import json
import os
import time

os.environ['AXV_HMAC_SECRET'] = 'test123'
os.environ['INTERNAL_SIGNER_TOKEN'] = 'axv-local-signer-ONLY-THIS-HOST'

from fastapi.testclient import TestClient

from app.main import create_app

app = create_app()
client = TestClient(app)

def sign(ts, body, secret='test123'):
    msg = f"{ts}.{body}"
    return 'sha256=' + hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()

def test_hooks_ping_ok():
    ts = str(int(time.time()))
    body = json.dumps({"source":"pytest","ping":True}, separators=(',',':'))
    sig = sign(ts, body)
    r = client.post("/hooks/ping",
                    headers={"X-AXV-Timestamp": ts, "X-AXV-Signature": sig},
                    data=body)
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["data"]["ping"] is True

def test_hooks_ping_bad_sig():
    ts = str(int(time.time()))
    body = json.dumps({"source":"pytest","ping":True}, separators=(',',':'))
    r = client.post("/hooks/ping",
                    headers={"X-AXV-Timestamp": ts, "X-AXV-Signature": "sha256=deadbeef"},
                    data=body)
    assert r.status_code == 401

def test_hooks_ping_bad_ts():
    ts = str(int(time.time()) - 3600)  # za stary
    body = json.dumps({"source":"pytest","ping":True}, separators=(',',':'))
    sig = sign(ts, body)
    r = client.post("/hooks/ping",
                    headers={"X-AXV-Timestamp": ts, "X-AXV-Signature": sig},
                    data=body)
    assert r.status_code == 401  # "bad timestamp"

def test_internal_sign_forbidden_without_header():
    r = client.post("/internal/hmac-sign", json={"ts":"123","body":"{}"})
    assert r.status_code == 403
