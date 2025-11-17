# K4.1 Quick Start Guide

## 🚀 Szybki Start (5 minut)

### 1. Podstawowa Instalacja

```bash
# Clone lub skopiuj pliki
git clone https://github.com/axv-crew/axv-api.git
cd axv-api

# Zainstaluj dependencies
pip install -r requirements.txt

# Skopiuj główne pliki
cp axv_status_endpoint.py ./
cp integration_example.py main.py  # jeśli nie masz jeszcze main.py
```

### 2. Konfiguracja

Stwórz `.env`:

```bash
cat > .env << 'EOF'
# AXV Status Endpoint Configuration
GATEWAY_HEALTHZ_URL=http://127.0.0.1:8000/axv/healthz
N8N_HEALTHZ_URL=http://n8n.axv.life/healthz
HEALTHCHECK_TIMEOUT=2.0
LOG_LEVEL=INFO
EOF
```

### 3. Uruchom API

```bash
# Development mode
uvicorn main:app --reload --port 8080

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8080 --workers 4
```

### 4. Test

```bash
# Basic test
curl http://localhost:8080/axv/status | jq

# Automated test
./test_axv_status.sh http://localhost:8080

# Continuous monitoring
python monitor_axv_status.py --url http://localhost:8080/axv/status
```

---

## 🐳 Docker Quick Start

### Build & Run

```bash
# Build image
docker build -t axv-api:0.1.9 .

# Run container
docker run -d \
  --name axv-api \
  -p 8080:8080 \
  -e GATEWAY_HEALTHZ_URL=http://gateway:8000/axv/healthz \
  axv-api:0.1.9

# Check logs
docker logs -f axv-api

# Test
curl http://localhost:8080/axv/status | jq
```

### Docker Compose (Pełny Stack)

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f axv_api

# Stop
docker-compose down
```

---

## 🔧 Integracja z Istniejącym Projektem

### Krok 1: Dodaj moduł

```python
# main.py (istniejący)
from axv_status_endpoint import router as status_router, configure_status_endpoint

# Your existing FastAPI app
app = FastAPI()

# Configure status endpoint
config = {
    "gateway_healthz_url": os.getenv("GATEWAY_HEALTHZ_URL"),
    "n8n_healthz_url": os.getenv("N8N_HEALTHZ_URL"),
    "healthcheck_timeout": float(os.getenv("HEALTHCHECK_TIMEOUT", "2.0")),
}
configure_status_endpoint(app, config)

# Add router
app.include_router(status_router)
```

### Krok 2: Integracja z /axv/status/nodes

Jeśli masz już endpoint `/axv/status/nodes`:

```python
# W axv_status_endpoint.py, zaktualizuj get_nodes_status()

from your_existing_module import get_all_nodes  # import twojej logiki

async def get_nodes_status() -> List[NodeStatus]:
    """Pobiera status nodów z istniejącej logiki"""
    nodes_data = await get_all_nodes()  # użyj istniejącej funkcji
    return [NodeStatus(**node) for node in nodes_data]
```

### Krok 3: Dodaj health checks

```python
# Dla check_api_health() - dodaj sprawdzenie DB
async def check_api_health() -> StatusValue:
    try:
        # Sprawdź połączenie z DB
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return "ok"
    except Exception as e:
        logger.error(f"DB health check failed: {e}")
        return "degraded"
```

---

## 📊 Monitoring Setup

### Grafana Dashboard

1. Import dashboard:
   - Grafana UI → Dashboards → Import
   - Upload `grafana-dashboard.json` (TODO: create)
   
2. Configure data source:
   - Prometheus URL: `http://prometheus:9090`

### Prometheus Scraping

```yaml
# prometheus.yml - dodaj do scrape_configs
- job_name: 'axv_status'
  scrape_interval: 30s
  static_configs:
    - targets: ['axv_api:8080']
```

### Alerts

```bash
# Import alerts do Grafany
curl -X POST http://grafana:3000/api/ruler/grafana/api/v1/rules/axv \
  -H "Content-Type: application/yaml" \
  -d @grafana-alerts.yml
```

---

## 🧪 Testing

### Unit Tests

```bash
# Run all tests
pytest test_axv_status.py -v

# With coverage
pytest test_axv_status.py --cov=axv_status_endpoint --cov-report=html

# View coverage
open htmlcov/index.html
```

### Integration Tests

```bash
# Start test environment
docker-compose -f docker-compose.test.yml up -d

# Run tests
pytest test_integration_axv_status.py -v

# Cleanup
docker-compose -f docker-compose.test.yml down
```

### Load Testing

```bash
# Install hey
go install github.com/rakyll/hey@latest

# Test status endpoint
hey -n 1000 -c 10 http://localhost:8080/axv/status

# Expected: <1s p99, no errors
```

---

## 🔍 Troubleshooting

### Problem: 404 Not Found

**Rozwiązanie:**
```bash
# Sprawdź czy router jest załadowany
curl http://localhost:8080/docs  # Zobacz dostępne endpointy

# Sprawdź logi
docker logs axv-api | grep "status"
```

### Problem: Gateway shows "down"

**Rozwiązanie:**
```bash
# Test gateway bezpośrednio
curl http://127.0.0.1:8000/axv/healthz

# Sprawdź network connectivity
docker exec axv-api ping gateway -c 3
```

### Problem: Endpoint bardzo wolny

**Diagnoza:**
```bash
# Measure response time
time curl http://localhost:8080/axv/status

# Check logs for timeout warnings
docker logs axv-api | grep -i timeout
```

**Rozwiązanie:**
```python
# Zmniejsz timeout w config
config = {"healthcheck_timeout": 1.0}  # było 2.0
```

---

## 📚 Następne Kroki

Po uruchomieniu podstawowego endpointu:

1. **Status Page** - stwórz publiczny status page (K4.2)
2. **RAG Health** - zaimplementuj check dla Atlas EDGE
3. **DB Check** - dodaj sprawdzenie connection pool
4. **Cache** - dodaj Redis cache dla częstych zapytań
5. **Metrics** - eksportuj do Prometheus/Grafana

---

## 💬 Wsparcie

- 📧 Email: family@axv.life
- 💬 Slack: #axv-crew (internal)
- 📖 Docs: docs.axv.systems
- 🐛 Issues: github.com/axv-crew/axv-api/issues

---

**Version:** 0.1.9  
**Updated:** 2025-11-16  
**Authors:** AXV Crew (Wojtek, Aster, Claude)
