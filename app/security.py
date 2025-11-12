from fastapi import Request, HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED
import hmac
import hashlib
import time
import json
import os


async def hmac_verify(request: Request):
    """
    Dependency: weryfikacja HMAC
    - Czyta nagłówki z aliasami:
      * Timestamp: X-AXV-Timestamp lub X-Signature-Timestamp
      * Signature: X-AXV-Signature lub X-Signature
    - Sekret i parametry z ENV:
      * AXV_HMAC_SECRET  (wymagany do poprawnej weryfikacji)
      * AXV_HMAC_DRIFT_S (opcjonalne; nieegzekwowane tu — robi to middleware TS)
    """
    ts = request.headers.get("X-AXV-Timestamp") or request.headers.get("X-Signature-Timestamp")
    sig = request.headers.get("X-AXV-Signature") or request.headers.get("X-Signature")
    if not ts or not sig:
        raise HTTPException(HTTP_401_UNAUTHORIZED, "missing signature")

    secret = (os.getenv("AXV_HMAC_SECRET") or "").encode()
    if not secret:
        # Brak sekretu = traktujemy jak złą konfigurację podpisu
        raise HTTPException(HTTP_401_UNAUTHORIZED, "bad signature")

    try:
        body_bytes = await request.body()
    except Exception:
        body_bytes = b""
    payload = body_bytes.decode() if isinstance(body_bytes, (bytes, bytearray)) else str(body_bytes)

    # Liczymy "sha256=<hexdigest>" zgodnie z kontraktem
    def calc(p: str) -> str:
        msg = f"{ts}.{p}".encode()
        return "sha256=" + hmac.new(secret, msg, hashlib.sha256).hexdigest()

    expected = calc(payload)

    # Stałe porównanie — akceptujemy wyłącznie format z prefiksem "sha256="
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(HTTP_401_UNAUTHORIZED, "bad signature")
