from fastapi import APIRouter, Depends

from app.security import hmac_verify

router = APIRouter(prefix="/hooks", dependencies=[Depends(hmac_verify)])

@router.post("/ping")
async def hooks_ping(payload: dict):
    return {"ok": True, "data": payload}
