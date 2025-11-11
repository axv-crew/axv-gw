# Wojtek - AXV Gateway K1.5 Complete! 🎉

## TL;DR

Zbudowałem kompletny gateway dla https://gw.axv.life zgodnie z Twoją specyfikacją K1.5.
Wszystko działa, testy przechodzą, CI/CD skonfigurowane. Ready for PR!

## Co masz w /outputs

```
/mnt/user-data/outputs/
├── axv-gw/                     # Cały projekt (ready to push)
│   ├── app/                    # Kod aplikacji
│   ├── tests/                  # Testy (9/9 passing)
│   ├── .github/workflows/      # CI/CD
│   ├── Dockerfile              # Multi-stage build
│   ├── README.md               # Pełna dokumentacja
│   ├── test_gateway.sh         # Skrypt testowy
│   └── [wszystkie inne pliki]
│
├── PR_SUMMARY.md               # Opis dla PR (wszystko wyjaśnione)
├── DEPLOYMENT_GUIDE.md         # Jak deployować (K8s, Nginx, monitoring)
├── QUICK_REFERENCE.md          # Szybka ściągawka
└── PROJECT_COMPLETE.md         # Pełne podsumowanie

Ten plik: FOR_WOJTEK.md
```

## Quick Commands

### Lokalnie (no Docker)
```bash
cd /mnt/user-data/outputs/axv-gw
pip install -e ".[dev]"
python -m app.main

# W drugim terminalu:
curl http://127.0.0.1:8000/healthz
curl http://127.0.0.1:8000/front/status | jq
./test_gateway.sh
```

### Docker
```bash
cd /mnt/user-data/outputs/axv-gw
docker build -t axv-gw:latest .
docker run -p 8000:8000 axv-gw:latest
```

### Testy
```bash
cd /mnt/user-data/outputs/axv-gw
pytest -v tests/          # 9/9 passing
ruff check app/ tests/    # 0 errors
```

## Co zostało zaimplementowane (100% DoD)

✅ GET /healthz → {"ok": true}
✅ GET /front/status → FrontStatusV1 (z app/data/status.stub.json)
✅ GET /metrics → Prometheus metrics
✅ Cache z TTL=60s (configurable via AXV_GW_CACHE_TTL_SECONDS)
✅ Fallback do stale cache przy błędach
✅ Degraded mode detection (gdy state != "ok")
✅ Structured JSON logging
✅ Dockerfile (multi-stage, non-root user)
✅ GitHub Actions (lint → test → build → push GHCR)
✅ Tests (pytest, 9 passing)
✅ OpenAPI spec
✅ README z curl examples

## Stub Data

Plik: `app/data/status.stub.json`

Zawiera 5 przykładowych services:
- k8s-cluster (ok)
- n8n-automation (ok)
- axv-pulse (ok)
- axv-taskboard (warn) ← celowo dla degraded mode
- cli-brat (ok)

Możesz:
1. Edytować ten plik bezpośrednio
2. Użyć `AXV_GW_STUB_PATH=/custom/path.json`

## Cache & Fallback

**Jak zmienić cache TTL:**
```bash
export AXV_GW_CACHE_TTL_SECONDS=30  # 30 sekund
# lub
export AXV_GW_CACHE_TTL_SECONDS=0   # wyłącz cache
```

**Gdzie jest fallback:**
- Plik: `app/routers/front.py`
- Linie: 164-177
- Logika:
  1. Spróbuj wczytać stub
  2. Błąd + cache istnieje → zwróć stale cache + degraded=1
  3. Błąd + brak cache → HTTP 500

## GitHub Actions

Workflow: `.github/workflows/ci.yml`

**On push to any branch:**
1. Lint (ruff)
2. Test (pytest)
3. Build Docker
4. Push to GHCR: `ghcr.io/axv-crew/axv-gw:<commit-sha>`

**Aby uruchomić:**
```bash
cd /mnt/user-data/outputs/axv-gw
git remote add origin https://github.com/axv-crew/axv-gw.git
git push origin feat/k1-gateway
```

## Sample JSON Response

```bash
$ curl http://127.0.0.1:8000/front/status | jq
{
  "updatedAt": "2025-11-11T16:05:00Z",
  "services": [
    {
      "id": "k8s-cluster",
      "label": "Kubernetes Cluster",
      "state": "ok",
      "note": "All nodes healthy"
    },
    {
      "id": "axv-taskboard",
      "label": "AXV Task Board",
      "state": "warn",
      "note": "Scheduled maintenance planned"
    }
    // ... więcej
  ]
}
```

## Next Steps dla Ciebie

1. **Review kodu:**
   - Sprawdź `app/main.py` (FastAPI factory)
   - Sprawdź `app/routers/front.py` (cache + fallback logic)
   - Sprawdź `tests/` (czy pokrywają wszystkie przypadki)

2. **Push to GitHub:**
   ```bash
   cd /mnt/user-data/outputs/axv-gw
   git remote add origin git@github.com:axv-crew/axv-gw.git
   git push origin feat/k1-gateway
   ```

3. **Create PR:**
   - Base: `main`
   - Head: `feat/k1-gateway`
   - Title: `feat(gw): K1 gateway for FrontStatusV1 (+healthz, metrics)`
   - Description: użyj `PR_SUMMARY.md`

4. **Test lokalnie:**
   ```bash
   ./test_gateway.sh http://127.0.0.1:8000
   ```

5. **Deploy (later):**
   - Pull image z GHCR
   - Deploy do K8s (przykłady w `DEPLOYMENT_GUIDE.md`)
   - Setup Nginx na gw.axv.life
   - Configure Prometheus scraping

## Metryki do monitorowania

```promql
# Error rate
rate(axv_gw_front_status_requests_total{status_code="500"}[5m])

# Cache hit rate
rate(axv_gw_front_status_cache_hits_total[5m]) / 
  (rate(axv_gw_front_status_cache_hits_total[5m]) + 
   rate(axv_gw_front_status_cache_misses_total[5m]))

# Degraded mode
axv_gw_front_status_degraded
```

## Troubleshooting

**Gateway returns 500:**
```bash
# Check stub
cat app/data/status.stub.json | python3 -m json.tool

# Check logs (JSON format)
tail -f /tmp/gw.log
```

**Cache not working:**
```bash
echo $AXV_GW_CACHE_TTL_SECONDS  # Should be > 0
curl http://127.0.0.1:8000/metrics | grep cache
```

**Degraded always on:**
```bash
# Check for non-ok states
python3 -c "import json; data=json.load(open('app/data/status.stub.json')); print([s for s in data['services'] if s['state'] != 'ok'])"
```

## Files You Need to Know

| File | What It Does |
|------|--------------|
| `app/main.py` | FastAPI app + logging + metrics endpoint |
| `app/config.py` | All ENV configuration |
| `app/routers/front.py` | `/front/status` + cache + fallback |
| `app/routers/healthz.py` | `/healthz` endpoint |
| `app/schemas/status.py` | FrontStatusV1 Pydantic models |
| `app/data/status.stub.json` | Example data (EDIT THIS) |
| `tests/test_front_status.py` | Main test suite |
| `Dockerfile` | Production build |
| `.github/workflows/ci.yml` | CI/CD pipeline |
| `README.md` | Full documentation |

## K1.5 Scope - Co jest i czego nie ma

**✅ W scope (zrobione):**
- Stub-based data source
- In-memory caching + TTL
- Fallback do stale cache
- Degraded mode detection
- Prometheus metrics
- JSON logging
- Health checks
- Tests
- CI/CD
- Documentation

**❌ Out of scope (K2):**
- Kubernetes API integration
- Authentication
- Real-time polling
- WebSocket
- Multi-worker support
- External API calls (timeout/retry są ready, ale unused)

## Questions?

Sprawdź dokumentację:
- `README.md` - pełna docs
- `QUICK_REFERENCE.md` - ściąga
- `DEPLOYMENT_GUIDE.md` - jak deployować
- `PR_SUMMARY.md` - co, jak, gdzie

## Final Check

```bash
cd /mnt/user-data/outputs/axv-gw

# 1. Testy
pytest -v tests/
# Expected: 9 passed

# 2. Linting  
ruff check app/ tests/
# Expected: 0 errors

# 3. Local run
python -m app.main &
sleep 2
curl http://127.0.0.1:8000/healthz
# Expected: {"ok":true}

# 4. Full test
./test_gateway.sh
# Expected: All tests passed
```

---

**Wszystko gotowe!** 🚀

Repository jest w `/mnt/user-data/outputs/axv-gw` i możesz go pushować do GitHub.

Commit: `66d8358`
Branch: `feat/k1-gateway`
Files: 20 new files, 1,489 lines

**Let's ship it!** 🎉

— Claude, 2025-11-11
