# AXV Gateway - Quick Reference Card

## 🚀 Quick Start

```bash
# Local development
pip install -e ".[dev]"
python -m app.main

# Docker
docker build -t axv-gw:latest .
docker run -p 8000:8000 axv-gw:latest

# Test
./test_gateway.sh http://127.0.0.1:8000
```

## 📡 API Endpoints

| Endpoint | Method | Description | Response |
|----------|--------|-------------|----------|
| `/healthz` | GET | Health check | `{"ok": true}` |
| `/front/status` | GET | Service status | FrontStatusV1 JSON |
| `/metrics` | GET | Prometheus metrics | Text format |

## 📦 FrontStatusV1 Contract

```typescript
{
  updatedAt: string;        // ISO 8601 timestamp
  services: Array<{
    id: string;             // Service identifier
    label: string;          // Human-readable name
    state: "ok" | "warn" | "down" | "unknown";
    note?: string;          // Optional status note
  }>;
}
```

## ⚙️ Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AXV_GW_STUB_PATH` | `app/data/status.stub.json` | Path to stub JSON |
| `AXV_GW_CACHE_TTL_SECONDS` | `60` | Cache TTL in seconds |
| `AXV_GW_LOG_LEVEL` | `info` | Logging level |
| `AXV_GW_HOST` | `0.0.0.0` | Server bind address |
| `AXV_GW_PORT` | `8000` | Server port |

## 📊 Key Metrics

```promql
# Request rate by status code
rate(axv_gw_front_status_requests_total[5m])

# Cache hit rate
rate(axv_gw_front_status_cache_hits_total[5m]) / 
(rate(axv_gw_front_status_cache_hits_total[5m]) + 
 rate(axv_gw_front_status_cache_misses_total[5m]))

# Response time p95
histogram_quantile(0.95, axv_gw_front_status_fetch_seconds_bucket)

# Degraded mode status
axv_gw_front_status_degraded
```

## 🧪 Testing

```bash
# Run all tests
pytest -v tests/

# Run specific test
pytest tests/test_healthz.py -v

# With coverage
pytest --cov=app --cov-report=html

# Linting
ruff check app/ tests/
ruff check --fix app/ tests/
```

## 🐛 Troubleshooting

### Gateway returns 500
```bash
# Check stub file
cat app/data/status.stub.json | python3 -m json.tool

# Verify path
echo $AXV_GW_STUB_PATH

# Check logs
tail -f /tmp/gw.log
```

### Cache not working
```bash
# Verify TTL setting
echo $AXV_GW_CACHE_TTL_SECONDS

# Check metrics
curl http://127.0.0.1:8000/metrics | grep cache
```

### Degraded mode stuck on
```bash
# Check service states in stub
cat app/data/status.stub.json | grep '"state"'

# Verify all are "ok"
python3 -c "import json; data=json.load(open('app/data/status.stub.json')); print([s for s in data['services'] if s['state'] != 'ok'])"
```

## 📝 Common Tasks

### Change stub data
```bash
# Edit stub
vim app/data/status.stub.json

# Or use custom stub
export AXV_GW_STUB_PATH=/path/to/custom.json
```

### Adjust cache TTL
```bash
# 30 second cache
export AXV_GW_CACHE_TTL_SECONDS=30

# Disable cache
export AXV_GW_CACHE_TTL_SECONDS=0
```

### Enable debug logging
```bash
export AXV_GW_LOG_LEVEL=debug
python -m app.main
```

### Check health
```bash
curl http://127.0.0.1:8000/healthz
```

### Get status
```bash
curl http://127.0.0.1:8000/front/status | jq
```

### View metrics
```bash
curl http://127.0.0.1:8000/metrics | grep axv_gw
```

## 🔄 CI/CD Pipeline

```
Push to branch → GitHub Actions
  ↓
[Lint] ruff check app/ tests/
  ↓
[Test] pytest -v tests/
  ↓
[Build] docker build -t ghcr.io/axv-crew/axv-gw:<sha>
  ↓
[Push] docker push ghcr.io/axv-crew/axv-gw:<sha>
```

## 📂 Project Structure

```
axv-gw/
├── app/
│   ├── main.py              # FastAPI app factory
│   ├── config.py            # Settings
│   ├── routers/
│   │   ├── healthz.py       # Health check
│   │   └── front.py         # Status endpoint
│   ├── schemas/
│   │   └── status.py        # Pydantic models
│   └── data/
│       └── status.stub.json # Stub data
├── tests/                   # Test suite
├── Dockerfile               # Production build
├── .github/workflows/       # CI/CD
└── README.md               # Full documentation
```

## 🎯 K1.5 Scope

✅ Stub-based data (no cluster integration)
✅ In-memory caching with TTL
✅ Fallback to stale cache
✅ Degraded mode detection
✅ Prometheus metrics
✅ JSON structured logging
✅ Health checks
❌ Authentication (K2 scope)
❌ Real-time cluster polling (K2 scope)

## 🔗 Links

- Repo: `axv-crew/axv-gw`
- Branch: `feat/k1-gateway`
- Production URL: `https://gw.axv.life` (planned)
- Container: `ghcr.io/axv-crew/axv-gw`
- OpenAPI spec: `openapi/front_status.yaml`

## 📞 Support

Questions? Check the full README.md or contact AXV Crew.

---
**Built with ❤️ by AXV Crew** | Captain: Wojtek | AI: Aster & Claude
