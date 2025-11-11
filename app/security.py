import hmac, hashlib, time
from fastapi import Request, HTTPException, status
from app.config import settings

async def hmac_verify(request: Request) -> None:
    secret = settings.AXV_HMAC_SECRET
    drift  = int(getattr(settings, "AXV_HMAC_DRIFT_S", 300))

    if not secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="HMAC secret missing")

    ts_hdr = request.headers.get("X-AXV-Timestamp")
    sig_hdr = request.headers.get("X-AXV-Signature","")
    if not ts_hdr or not sig_hdr.startswith("sha256="):
        raise HTTPException(status_code=401, detail="Missing HMAC headers")

    try:
        ts = int(ts_hdr)
    except ValueError:
        raise HTTPException(status_code=401, detail="Bad timestamp")

    if abs(int(time.time()) - ts) > drift:
        raise HTTPException(status_code=401, detail="Stale timestamp")

    body = await request.body()
    mac = hmac.new(secret.encode(), f"{ts_hdr}.".encode() + body, hashlib.sha256).hexdigest()
    given = sig_hdr.split("=",1)[1]
    if not hmac.compare_digest(mac, given):
        raise HTTPException(status_code=401, detail="Bad signature")
