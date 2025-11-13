import hashlib
import hmac
import json
import os
from typing import Any

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter(prefix="/internal", tags=["internal"])


class HMACSignRequest(BaseModel):
    ts: str
    body: Any


class HMACSignResponse(BaseModel):
    signature: str


@router.post("/hmac-sign", response_model=HMACSignResponse)
async def hmac_sign(
    req: HMACSignRequest,
    x_axv_signer: str | None = Header(None, alias="X-AXV-Signer"),
) -> HMACSignResponse:
    # Token strażnika (local-only signer)
    expect = (os.getenv("INTERNAL_SIGNER_TOKEN") or "").strip()
    if expect and (x_axv_signer or "").strip() != expect:
        return JSONResponse({"ok": False, "error": "forbidden"}, status_code=403)

    # Sekret HMAC (wspólny z gatewayem)
    secret = (os.getenv("AXV_HMAC_SECRET") or "").encode()

    # Body: kanoniczny JSON dla dict/list, w innym razie raw string
    if isinstance(req.body, (dict, list)):
        body_s = json.dumps(req.body, separators=(",", ":"), ensure_ascii=False)
    else:
        body_s = str(req.body)

    # Wiadomość: f"{ts}.{payload}"
    msg = f"{req.ts}.{body_s}".encode()
    sig = hmac.new(secret, msg, hashlib.sha256).hexdigest()
    return HMACSignResponse(signature=f"sha256={sig}")
