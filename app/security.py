import hashlib
import hmac
import json
import os
import time

from fastapi import HTTPException, Request
from starlette.status import HTTP_401_UNAUTHORIZED


def _canonical_payload(ct: str, body_bytes: bytes) -> str:
    if ct and 'application/json' in ct.lower():
        try:
            obj = json.loads(body_bytes.decode())
            return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
        except Exception:
            pass
    return body_bytes.decode()

async def hmac_verify(request: Request):
    # headers (oba warianty)
    ts = request.headers.get("X-AXV-Timestamp") or request.headers.get("X-Signature-Timestamp")
    sig = request.headers.get("X-AXV-Signature") or request.headers.get("X-Signature")

    if not ts:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="bad timestamp")
    if not sig:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="missing signature")

    # drift
    try:
        ts_i = int(ts)
    except ValueError:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="bad timestamp")

    now = int(time.time())
    drift = int(os.getenv("AXV_HMAC_DRIFT_S", os.getenv("HMAC_MAX_SKEW_S", "300")))
    if abs(now - ts_i) > drift:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="bad timestamp")

    # canonical payload
    body = await request.body()
    payload = _canonical_payload(request.headers.get("content-type", ""), body)

    # expected signature
    secret = (os.getenv("AXV_HMAC_SECRET") or "").encode()
    expected_hex = hmac.new(secret, f"{ts}.{payload}".encode(), hashlib.sha256).hexdigest()

    # akceptuj 'sha256=<hex>' i '<hex>'
    provided = sig.split("=", 1)[1] if sig.lower().startswith("sha256=") else sig

    if not hmac.compare_digest(expected_hex, provided):
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="bad signature")
