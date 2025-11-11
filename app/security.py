import os, hmac, hashlib, time
from fastapi import Request, HTTPException
from app.config import settings

async def hmac_verify(request: Request):
    ts = request.headers.get("X-AXV-Timestamp")
    sig = request.headers.get("X-AXV-Signature", "")
    if not ts or not sig.startswith("sha256="):
        raise HTTPException(status_code=401, detail="missing headers")

    try:
        ts_int = int(ts)
    except Exception:
        raise HTTPException(status_code=401, detail="bad timestamp")

    now = int(time.time())
    drift = (
        getattr(settings, "AXV_HMAC_DRIFT_S", None)
        or getattr(settings, "HMAC_DRIFT_S", None)
        or 300
    )
    if abs(now - ts_int) > int(drift):
        raise HTTPException(status_code=401, detail="timestamp drift")

    # ❶ Najpierw bez-prefiksowe pole (gdy model ma env_prefix="AXV_")
    # ❷ Następnie próba pola z prefiksem (gdy ktoś tak zdefiniował w Settings)
    # ❸ Potem ENV (najpewniejsze w kontenerze)
    secret = (
        getattr(settings, "HMAC_SECRET", "")
        or getattr(settings, "AXV_HMAC_SECRET", "")
        or os.getenv("AXV_HMAC_SECRET", "")
        or os.getenv("HMAC_SECRET", "")
    )
    if not secret:
        raise HTTPException(status_code=401, detail="no secret configured")

    body = await request.body()  # dokładny bajtowy payload
    msg = f"{ts_int}.".encode() + body
    expected = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
    provided = sig.split("=", 1)[1]

    if not hmac.compare_digest(expected, provided):
        raise HTTPException(status_code=401, detail="bad signature")
    # ok: request przechodzi
