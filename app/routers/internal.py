import hashlib
import hmac
import json
import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/internal", tags=["internal"])


class HMACSignRequest(BaseModel):
    ts: str
    body: Any  # akceptuje string albo obiekt


class HMACSignResponse(BaseModel):
    signature: str


@router.post("/hmac-sign", response_model=HMACSignResponse)
async def hmac_sign(
    req: HMACSignRequest,
    x_axv_signer: str | None = Header(None, alias="X-AXV-Signer"),
):
    # prosty guard na localhost-only use case (opcjonalny)
    expect = (os.getenv("INTERNAL_SIGNER_TOKEN") or "").strip()
    if expect and (x_axv_signer or "") != expect:
        raise HTTPException(status_code=403, detail="forbidden")

    secret = (os.getenv("AXV_HMAC_SECRET") or "").encode()
    # Jeśli body jest stringiem — użyj go; jeśli obiektem — kanonizuj JSON
    if isinstance(req.body, str):
        body_s = req.body
    else:
        body_s = json.dumps(req.body, separators=(",", ":"), ensure_ascii=False)

    msg = f"{req.ts}.{body_s}".encode()
    sig = hmac.new(secret, msg, hashlib.sha256).hexdigest()
    return HMACSignResponse(signature=f"sha256={sig}")
