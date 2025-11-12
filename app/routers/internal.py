from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Any, Optional
import hmac, hashlib, json
from app.config import settings

router = APIRouter(prefix="/internal", tags=["internal"])

class HMACSignRequest(BaseModel):
    ts: str
    body: Any  # akceptuje string albo obiekt

class HMACSignResponse(BaseModel):
    signature: str

@router.post("/hmac-sign", response_model=HMACSignResponse)
async def hmac_sign(req: HMACSignRequest, x_axv_signer: Optional[str] = Header(None)):
    # prosty guard na localhost-only use case (opcjonalny)
    expect = (getattr(settings, "INTERNAL_SIGNER_TOKEN", "") or "").strip()
    if expect and (x_axv_signer or "") != expect:
        raise HTTPException(status_code=403, detail="forbidden")

    secret = (settings.AXV_HMAC_SECRET or "").encode("utf-8")
    # Jeśli body jest stringiem — użyj go; jeśli obiektem — kanonizuj JSON
    if isinstance(req.body, str):
        body_s = req.body
    else:
        body_s = json.dumps(req.body, separators=(",", ":"), ensure_ascii=False)

    msg = f"{req.ts}.{body_s}".encode("utf-8")
    sig = hmac.new(secret, msg, hashlib.sha256).hexdigest()
    return HMACSignResponse(signature=f"sha256={sig}")
