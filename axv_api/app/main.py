from time import time

from fastapi import FastAPI

app = FastAPI()
@app.get("/axv/healthz")
def healthz(): return {"ok": True}
@app.get("/axv/readyz")
def readyz(): return {"ok": True}
@app.get("/axv/status")
def status(): return {"now": int(time()), "ok": True, "status": {"api":"ok","version":"stub-2025-11-09"}}
