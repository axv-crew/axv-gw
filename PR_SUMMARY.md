# PR: feat(gw): K1 gateway for FrontStatusV1 (+healthz, metrics)

## Summary

Implementacja K1.5 gateway dla https://gw.axv.life - HTTP API dostarczające JSON dla frontendu AXV. Gateway zapewnia endpointy `/front/status`, `/healthz` i `/metrics` z caching, fallbackiem i detekcją trybu degraded.

## What was added

### Core Application Files

**`app/main.py`** - FastAPI application factory z:
- JSON structured logging (JSONFormatter dla stdout)
- Integracja Prometheus metrics endpoint
- Lifespan management
- Router registration

**`app/config.py`** - Environment-based configuration:
- `AXV_GW_STUB_PATH` - path do stub JSON (default: `app/data/status.stub.json`)
- `AXV_GW_CACHE_TTL_SECONDS` - cache TTL (default: 60s)
- `AXV_GW_REQUEST_TIMEOUT_SECONDS` - timeout dla przyszłych zewnętrznych wywołań (2s)
- `AXV_GW_REQUEST_MAX_RETRIES` - max retry (1)
- Konfiguracja servera (host, port, log level)

**`app/routers/healthz.py`** - Health check endpoint:
- `GET /healthz` → `{"ok": true}`
- Prometheus counter dla healthcheck requests

**`app/routers/front.py`** - Frontend status endpoint:
- `GET /front/status` → FrontStatusV1 contract
- In-memory cache z TTL (default 60s)
- Fallback do stale cache przy błędach
- Degraded mode detection (any service state != "ok")
- Prometheus metrics:
  - `axv_gw_front_status_requests_total{status_code}`
  - `axv_gw_front_status_fetch_seconds`
  - `axv_gw_front_status_cache_hits_total`
  - `axv_gw_front_status_cache_misses_total`
  - `axv_gw_front_status_degraded` (0 or 1)

**`app/schemas/status.py`** - Pydantic schemas:
- `ServiceState` enum: `ok`, `warn`, `down`, `unknown`
- `ServiceStatus` model
- `FrontStatusV1` contract z ISO 8601 timestamp

**`app/data/status.stub.json`** - Example stub data:
- 5 example services (k8s-cluster, n8n-automation, axv-pulse, axv-taskboard, cli-brat)
- One service in `warn` state for degraded mode testing

### Testing

**`tests/test_healthz.py`** - Healthz endpoint tests:
- Basic OK response
- Multiple calls

**`tests/test_front_status.py`** - Front status endpoint tests:
- Contract validation (FrontStatusV1)
- Stub data loading
- Caching behavior
- Fallback on missing stub
- Cache TTL configuration
- Degraded mode detection
- Metrics endpoint

Fixture: `clear_cache` (autouse) - czyszczenie cache między testami

### Infrastructure

**`Dockerfile`** - Multi-stage production build:
- Stage 1: Builder z build dependencies
- Stage 2: Slim runtime image
- Non-root user (axvgw:1000)
- Health check endpoint
- Port 8000 exposed

**`.github/workflows/ci.yml`** - CI/CD pipeline:
- **Lint job**: ruff check
- **Test job**: pytest
- **Build job**: Docker build + push to GHCR
  - Tags: `ghcr.io/axv-crew/axv-gw:<sha>`, `ghcr.io/axv-crew/axv-gw:<branch>`
  - Caching z GitHub Actions cache
  - Triggered on push to any branch and PRs to main

**`openapi/front_status.yaml`** - OpenAPI 3.1 specification:
- Full API documentation
- Schema definitions for FrontStatusV1
- Example responses

### Documentation

**`README.md`** - Comprehensive documentation:
- Quickstart (local + Docker)
- API endpoints documentation
- Configuration guide (env variables)
- How to change stub data
- Cache configuration
- Fallback behavior explanation
- Development guide (tests, linting)
- Project structure
- CI/CD pipeline description
- Deployment notes

**`CHANGELOG.md`** - v0.1.0 release notes

### Configuration

**`pyproject.toml`** - Project metadata + dependencies:
- FastAPI 0.115+
- Uvicorn 0.32+
- Pydantic 2.9+
- prometheus-client 0.21+
- httpx 0.27+
- Dev dependencies: pytest, pytest-asyncio, ruff

**`.dockerignore`** - Optimized Docker context

**`.gitignore`** - Python standard gitignore

## How to change the stub

### Option 1: Edit stub file directly

Edit `app/data/status.stub.json`:

```json
{
  "updatedAt": "2025-11-11T16:05:00Z",
  "services": [
    {
      "id": "my-service",
      "label": "My Service",
      "state": "ok",
      "note": "Custom note"
    }
  ]
}
```

### Option 2: Use custom stub path

Set environment variable:

```bash
export AXV_GW_STUB_PATH=/path/to/custom/status.json
python -m app.main
```

Or with Docker:

```bash
docker run -e AXV_GW_STUB_PATH=/app/custom.json \
  -v /path/to/custom.json:/app/custom.json \
  -p 8000:8000 axv-gw:latest
```

## Cache TTL configuration

Cache TTL is controlled by `AXV_GW_CACHE_TTL_SECONDS` environment variable (default: 60s).

**To change cache TTL:**

```bash
# Cache for 30 seconds
export AXV_GW_CACHE_TTL_SECONDS=30
python -m app.main

# Disable caching (always fetch fresh)
export AXV_GW_CACHE_TTL_SECONDS=0
python -m app.main
```

**Cache behavior:**
- Cache hit → return cached data immediately
- Cache miss → load from stub, cache result, return
- Age check: `(now - cache_timestamp) < cache_ttl_seconds`

## Fallback mechanism

**Location:** `app/routers/front.py`, function `get_front_status()`, lines 164-177

**Fallback logic:**

```python
try:
    data = _load_stub()
    _cache = data
    _cache_timestamp = datetime.now(UTC)
    _apply_degraded_mode(data)
    return FrontStatusV1(**data)
except Exception as e:
    logger.error(f"Error loading stub: {e}")
    
    # Fallback to stale cache if available
    if _cache is not None:
        logger.warning("Falling back to stale cache due to error")
        degraded_mode.set(1)
        return FrontStatusV1(**_cache)
    
    # No cache available - fail
    logger.error("No cache available for fallback")
    raise
```

**Behavior:**
1. Primary: Load fresh data from stub
2. On error + cache exists: Return stale cache + set degraded mode
3. On error + no cache: Return HTTP 500

**Degraded mode detection:**
- Triggered when any service has `state != "ok"`
- Sets `axv_gw_front_status_degraded` metric to 1
- Logged as WARNING

## Sample JSON response

**`GET /front/status`:**

```json
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
      "id": "n8n-automation",
      "label": "n8n Automation",
      "state": "ok",
      "note": "Running at n8n.axv.life"
    },
    {
      "id": "axv-pulse",
      "label": "AXV Pulse",
      "state": "ok",
      "note": "Timeline system operational"
    },
    {
      "id": "axv-taskboard",
      "label": "AXV Task Board",
      "state": "warn",
      "note": "Scheduled maintenance planned"
    },
    {
      "id": "cli-brat",
      "label": "CLI-brat Agent",
      "state": "ok",
      "note": "Autonomous agent active"
    }
  ]
}
```

## Testing

All tests pass (9/9):

```bash
$ pytest -v tests/
tests/test_front_status.py::test_front_status_returns_valid_contract PASSED
tests/test_front_status.py::test_front_status_loads_stub_data PASSED
tests/test_front_status.py::test_front_status_caching PASSED
tests/test_front_status.py::test_front_status_fallback_on_missing_stub PASSED
tests/test_front_status.py::test_front_status_cache_ttl PASSED
tests/test_front_status.py::test_front_status_degraded_mode_detection PASSED
tests/test_front_status.py::test_metrics_endpoint PASSED
tests/test_healthz.py::test_healthz_returns_ok PASSED
tests/test_healthz.py::test_healthz_multiple_calls PASSED
```

## Local verification

```bash
# Install
pip install -e ".[dev]"

# Run server
python -m app.main

# Test endpoints
curl -fsS http://127.0.0.1:8000/healthz
# {"ok":true}

curl -fsS http://127.0.0.1:8000/front/status | jq
# Returns FrontStatusV1 JSON

curl -fsS http://127.0.0.1:8000/metrics | head -20
# Returns Prometheus metrics
```

## Definition of Done (DoD)

✅ 1. `GET /healthz` → 200 `{"ok": true}`
✅ 2. `GET /front/status` → 200, zgodny z FrontStatusV1, zasilany stubem
✅ 3. `/metrics` działa lokalnie (Prometheus format)
✅ 4. `docker build` przechodzi (Dockerfile ready)
✅ 5. GitHub Actions CI configured (lint + test + build + push GHCR)
✅ 6. README ma sekcję "Quickstart" + curl przykłady

## Next steps (K2 scope)

- [ ] Integration z Kubernetes API (rzeczywiste health checks)
- [ ] Authentication/authorization
- [ ] Real-time polling z cluster nodes
- [ ] Advanced retry strategies
- [ ] WebSocket support dla live updates
- [ ] Multi-worker deployment z multiprocess metrics

## Technical notes

- **Python 3.11+** required
- **Pydantic v2** for schema validation
- **FastAPI async** for performance
- **Prometheus client** for observability
- **Structured JSON logging** for production monitoring
- **Multi-stage Docker** for optimized image size (~150MB)
- **Non-root container** for security
- **Health check** in Dockerfile for orchestrator integration

---

**Branch:** `feat/k1-gateway`
**Commit:** `66d8358`
**Files changed:** 20 files, 1489 insertions
**Test coverage:** 9 tests passing

Ready for review! 🚀
