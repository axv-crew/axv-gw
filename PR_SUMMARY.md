# K2 — Gateway Hardening & Ops (v0.1.10)

**Scope:** K2.1–K2.6  
- RL per IP+path (429 JSON + Retry-After), HMAC TS window (±5m), body size guard (413 JSON).  
- Prometheus metrics (counters + /hooks histogram).  
- n8n: credentials > Credentials; export workflow bez credów.  
- CI: pytest+coverage, ruff/black/mypy (lenient).

**Sanity plan:**  
1) `/status` → version=0.1.10  
2) `/metrics` → wiersze `gw_hmac_bad_ts_total`, `gw_rate_limit_dropped_total`, histogram buckets  
3) 2× podpisany webhook (200) + 1× zły TS (401)  
4) n8n run (HTTP Request creds) → OK

**Rollback 60s:**  
- `git checkout v0.1.9` (lub przełącz obraz na poprzedni tag) → restart usługi → weryfikacja `/status.version=0.1.9`.
