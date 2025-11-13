from fastapi import Request, HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED
import hmac, hashlib, time, json, os

async def hmac_verify(request: Request):
    """
    HMAC verify (AXV):
      * Timestamp: X-AXV-Timestamp lub X-Signature-Timestamp
      * Signature: X-AXV-Signature (prefer) lub X-Signature
      * Wiadomość: f"{ts}.{payload}"
      * payload:
          - dla application/json → json.loads → json.dumps(..., separators=(',', ':'), ensure_ascii=False)
          - w innym wypadku → raw body (decode UTF-8)
    """
    # 1) pobierz nagłówki (oba warianty)
    ts = request.headers.get("X-AXV-Timestamp") or request.headers.get("X-Signature-Timestamp")
    sig = request.headers.get("X-AXV-Signature") or request.headers.get("X-Signature")

    if not ts:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="bad timestamp")
    if not sig:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="missing signature")

    # 2) drift
    try:
        ts_i = int(ts)
    except ValueError:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="bad timestamp")

    now = int(time.time())
    drift = int(os.getenv("AXV_HMAC_DRIFT_S", os.getenv("HMAC_MAX_SKEW_S", "300")))
    if abs(now - ts_i) > drift:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="bad timestamp")

    # 3) payload (kanonizacja jak w signerze)
    raw = await request.body()
    payload: str
    ctype = (request.headers.get("Content-Type") or "").lower()
    if "application/json" in ctype:
        try:
            obj = json.loads(raw.decode() if isinstance(raw, (bytes, bytearray)) else raw)
            payload = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
        except Exception:
            # w razie niepoprawnego JSON – wróć do raw
            payload = raw.decode() if isinstance(raw, (bytes, bytearray)) else str(raw)
    else:
        payload = raw.decode() if isinstance(raw, (bytes, bytearray)) else str(raw)

    # 4) oblicz spodziewany podpis
    secret = (os.getenv("AXV_HMAC_SECRET") or "").encode()
    calc = hmac.new(secret, f"{ts}.{payload}".encode(), hashlib.sha256).hexdigest()
    expected = f"sha256={calc}"

    # 5) stała porównywarka
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="bad signature")

    return
