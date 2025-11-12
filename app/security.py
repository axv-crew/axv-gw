from fastapi import Request, HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED
import hmac, hashlib, time, json
from app.config import settings

async def hmac_verify(request: Request):
    ts = request.headers.get("X-AXV-Timestamp")
    sig_hdr = request.headers.get("X-AXV-Signature", "")

    if not ts or not sig_hdr.startswith("sha256="):
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="missing signature")

    try:
        ts_i = int(ts)
    except Exception:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="bad timestamp")

    drift = int(getattr(settings, "AXV_HMAC_DRIFT_S", 300))
    if abs(int(time.time()) - ts_i) > drift:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="timestamp drift")

    body = await request.body()
    # re-inject body for downstream
    async def _receive():
        return {"type": "http.request", "body": body, "more_body": False}
    request._receive = _receive

    provided = sig_hdr.split("=", 1)[1]
    secret = (settings.AXV_HMAC_SECRET or "").encode("utf-8")
    raw = body.decode("utf-8")

    def calc(payload: str) -> str:
        msg = f"{ts}.{payload}".encode("utf-8")
        return hmac.new(secret, msg, hashlib.sha256).hexdigest()

    # 1) spróbuj dokładnie tak, jak przyszło (RAW)
    if hmac.compare_digest(provided, calc(raw)):
        return True

    # 2) jeśli to JSON, policz na postaci kanonicznej (minified, stała separacja)
    try:
        canon = json.dumps(json.loads(raw), separators=(",", ":"), ensure_ascii=False)
        if hmac.compare_digest(provided, calc(canon)):
            return True
    except Exception:
        pass

    raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="bad signature")
