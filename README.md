# AXV Gateway

Status API gateway for [axv.life](https://axv.life) frontend.

## Overview

AXV Gateway provides a simple JSON API for the frontend to query the status of AXV services. In the K1.5 scope, data is sourced from a stub JSON file (no cluster integration yet).

**Features:**
- ✅ `/front/status` - Service status endpoint (FrontStatusV1 contract)
- ✅ `/healthz` - Health check endpoint
- ✅ `/metrics` - Prometheus metrics
- ✅ In-memory caching with configurable TTL
- ✅ Fallback to stale cache on errors
- ✅ Degraded mode detection
- ✅ Structured JSON logging
- ✅ Multi-stage Docker build

## Quickstart

### Prerequisites

- Python 3.11+
- Docker (optional)

### Local Development

1. **Clone the repository:**

```bash
git clone https://github.com/axv-crew/axv-gw.git
cd axv-gw
git checkout feat/k1-gateway
```

2. **Install dependencies:**

```bash
pip install -e ".[dev]"
```

3. **Run the server:**

```bash
python -m app.main
```

Or with uvicorn directly:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. **Test the endpoints:**

```bash
# Health check
curl -fsS http://127.0.0.1:8000/healthz

# Frontend status
curl -fsS http://127.0.0.1:8000/front/status | jq

# Prometheus metrics
curl -fsS http://127.0.0.1:8000/metrics
```

### Docker

1. **Build the image:**

```bash
docker build -t axv-gw:latest .
```

2. **Run the container:**

```bash
docker run -p 8000:8000 axv-gw:latest
```

3. **Test:**

```bash
curl -fsS http://127.0.0.1:8000/healthz
curl -fsS http://127.0.0.1:8000/front/status | jq
```

## API Endpoints

### `GET /healthz`

Simple health check endpoint.

**Response:**
```json
{
  "ok": true
}
```

### `GET /front/status`

Returns current status of AXV services following the FrontStatusV1 contract.

**Response Contract (FrontStatusV1):**
```json
{
  "updatedAt": "2025-11-11T16:05:00Z",
  "services": [
    {
      "id": "k8s-cluster",
      "label": "Kubernetes Cluster",
      "state": "ok",
      "note": "All nodes healthy"
    }
  ]
}
```

**Service States:**
- `ok` - Service is operating normally
- `warn` - Service has non-critical issues
- `down` - Service is unavailable
- `unknown` - Service state cannot be determined

**Example Response:**
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

### `GET /metrics`

Prometheus metrics endpoint in text format.

**Metrics exposed:**
- `axv_gw_healthz_requests_total` - Total health check requests
- `axv_gw_front_status_requests_total` - Total front status requests
- `axv_gw_front_status_fetch_seconds` - Time to fetch status data
- `axv_gw_front_status_cache_hits_total` - Cache hits
- `axv_gw_front_status_cache_misses_total` - Cache misses
- `axv_gw_front_status_degraded` - Degraded mode indicator (0 or 1)

## Configuration

Configuration is managed via environment variables with the `AXV_GW_` prefix.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AXV_GW_STUB_PATH` | `app/data/status.stub.json` | Path to stub JSON file |
| `AXV_GW_CACHE_TTL_SECONDS` | `60` | Cache TTL in seconds |
| `AXV_GW_REQUEST_TIMEOUT_SECONDS` | `2.0` | Request timeout (reserved for K2) |
| `AXV_GW_REQUEST_MAX_RETRIES` | `1` | Max retries (reserved for K2) |
| `AXV_GW_HOST` | `0.0.0.0` | Server bind host |
| `AXV_GW_PORT` | `8000` | Server port |
| `AXV_GW_LOG_LEVEL` | `info` | Log level (debug/info/warning/error) |

### Changing the Stub Data

**Option 1: Edit the stub file directly**

Edit `app/data/status.stub.json` with your desired service statuses:

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

**Option 2: Use a custom stub file**

Set the `AXV_GW_STUB_PATH` environment variable:

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

### Cache Configuration

The cache TTL controls how long status data is cached in memory before refreshing from the stub.

**To change cache TTL:**

```bash
# Cache for 30 seconds
export AXV_GW_CACHE_TTL_SECONDS=30
python -m app.main

# Disable caching (TTL=0)
export AXV_GW_CACHE_TTL_SECONDS=0
python -m app.main
```

### Fallback Behavior

The fallback mechanism is automatically enabled in `app/routers/front.py`:

**Fallback logic:**
1. Try to load fresh data from stub
2. On error:
   - If cache available → return stale cached data + set `degraded_mode=1`
   - If no cache → return HTTP 500 error

**Degraded mode detection:**
- Any service with `state != "ok"` triggers degraded mode
- Exposed via `axv_gw_front_status_degraded` metric (0=normal, 1=degraded)

**Location of fallback code:** `app/routers/front.py` lines 140-158

## Development

### Running Tests

```bash
# Run all tests
pytest -v

# Run specific test file
pytest tests/test_healthz.py -v

# Run with coverage
pytest --cov=app --cov-report=html
```

### Linting

```bash
# Check code style
ruff check app/ tests/

# Auto-fix issues
ruff check --fix app/ tests/
```

### Project Structure

```
axv-gw/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI factory + JSON logging
│   ├── config.py            # Environment configuration
│   ├── data/
│   │   └── status.stub.json # Stub data source
│   ├── routers/
│   │   ├── healthz.py       # Health check endpoint
│   │   └── front.py         # Frontend status endpoint + cache + fallback
│   └── schemas/
│       └── status.py        # FrontStatusV1 Pydantic models
├── tests/
│   ├── test_healthz.py
│   └── test_front_status.py
├── openapi/
│   └── front_status.yaml    # OpenAPI specification
├── .github/
│   └── workflows/
│       └── ci.yml           # GitHub Actions CI/CD
├── Dockerfile               # Multi-stage production build
├── pyproject.toml          # Dependencies and project metadata
└── README.md
```

## CI/CD

GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every push:

1. **Lint** - Code style checks with ruff
2. **Test** - Run pytest suite
3. **Build** - Build Docker image and push to GHCR

**Container Registry:**
- `ghcr.io/axv-crew/axv-gw:<sha>` - Git commit SHA tag
- `ghcr.io/axv-crew/axv-gw:<branch>` - Branch name tag

## Deployment

### Pull from GHCR

```bash
# Login to GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Pull specific version
docker pull ghcr.io/axv-crew/axv-gw:abc123def456...

# Run
docker run -p 8000:8000 ghcr.io/axv-crew/axv-gw:abc123def456...
```

### Production Deployment (Planned)

Deployment to `gw.axv.life` will be handled via:
- Kubernetes deployment manifest
- Nginx reverse proxy with rate limiting
- SSL/TLS termination
- Horizontal pod autoscaling

## Architecture Notes

### K1.5 Scope Limitations

- ❌ No cluster integration - data from stub only
- ❌ No authentication - rate limiting at Nginx layer
- ❌ No external API calls - reserved for K2
- ✅ Cache + fallback implemented for future integration

### Future K2 Scope

- Cluster health checks via Kubernetes API
- Real-time service status polling
- Authentication/authorization
- Advanced caching strategies
- WebSocket support for live updates

## License

Internal AXV Crew project.

## Support

For issues or questions, contact the AXV Crew team or open an issue in the repository.

---

**Built with ❤️ by AXV Crew** | Captain: Wojtek | AI Partners: Aster & Claude
