# AXV Status Endpoint - K4.1

> **Single Source of Truth** dla stanu systemu AXV

[![Version](https://img.shields.io/badge/version-0.1.9-blue.svg)](https://github.com/axv-crew/axv-api)
[![Python](https://img.shields.io/badge/python-3.11+-green.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)

## 📖 Spis Treści

- [Przegląd](#przegląd)
- [Funkcje](#funkcje)
- [Szybki Start](#szybki-start)
- [Architektura](#architektura)
- [API Reference](#api-reference)
- [Integracje](#integracje)
- [Monitoring](#monitoring)
- [Rozwój](#rozwój)
- [FAQ](#faq)

---

## 🎯 Przegląd

**AXV Status Endpoint** (`GET /axv/status`) to zunifikowany endpoint zwracający kompletny stan całego ekosystemu AXV. Jest zaprojektowany jako **Single Source of Truth** dla:

- 🔍 **Monitoringu** - Grafana, Prometheus, Datadog
- 📊 **Status Page** - publicznego i wewnętrznego
- 🤖 **Automatyzacji** - n8n workflows, alerting
- 🚨 **Alertów** - PagerDuty, Slack, Email

### Dlaczego to ważne?

Przed K4.1 każdy system miał własny sposób raportowania statusu:
- Gateway miał `/healthz`
- n8n miał własny endpoint
- API miał inny format
- Brak spójnej logiki dla "degraded" vs "down"

**K4.1 rozwiązuje to**, dostarczając:
- ✅ Jeden endpoint do sprawdzenia stanu WSZYSTKIEGO
- ✅ Ustandaryzowany format (ok/degraded/down/unknown)
- ✅ Spójna logika "overall status"
- ✅ Gotowe do integracji z monitoring tools

---

## ✨ Funkcje

### Główne Komponenty

- **API Status** - stan samego axv_api
- **Gateway Status** - stan axv_gw (reverse proxy)
- **n8n Status** - stan workflow automation engine
- **RAG Status** - stan Atlas EDGE RAG system
- **Nodes List** - lista wszystkich nodów w klastrze AXV

### Kluczowe Features

- ⚡ **Fast** - <2s response time, concurrent health checks
- 🔒 **Secure** - brak eksponowania sensitive data
- 📈 **Scalable** - gotowe do tysięcy requestów/minutę
- 🛡️ **Reliable** - graceful degradation, timeout handling
- 🔌 **Pluggable** - łatwa integracja nowych komponentów

### Status Values

| Value | Znaczenie | Użycie |
|-------|-----------|--------|
| `ok` | Działa poprawnie | Zielony status |
| `degraded` | Problemy, ale działa | Żółty warning |
| `down` | Nie odpowiada | Czerwony alert |
| `unknown` | Brak danych | Szary, do implementacji |

---

## 🚀 Szybki Start

### Wymagania

- Python 3.11+
- FastAPI
- httpx
- Docker (opcjonalnie)

### Instalacja (1 minuta)

```bash
# Clone repo
git clone https://github.com/axv-crew/axv-api.git
cd axv-api

# Install
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your URLs

# Run
uvicorn main:app --reload --port 8080
```

### Pierwszy Test

```bash
# Basic check
curl http://localhost:8080/axv/status | jq

# Expected output:
{
  "now": 1762714225,
  "ok": true,
  "version": "0.1.9",
  "overall_status": null,
  "status": {
    "api": "ok",
    "gateway": "ok",
    "n8n": "ok",
    "rag": "unknown"
  },
  "nodes": []
}
```

**Więcej:** Zobacz [QUICKSTART.md](QUICKSTART.md) dla szczegółów

---

## 🏗️ Architektura

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Applications                     │
│  (Grafana, Status Page, n8n, Prometheus, PagerDuty, etc.)  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ GET /axv/status
                         │
                    ┌────▼────┐
                    │         │
                    │ AXV API │ ◄── Main Status Endpoint
                    │         │
                    └────┬────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
     ┌────▼────┐    ┌───▼───┐    ┌────▼────┐
     │ Gateway │    │  n8n  │    │   RAG   │
     │ Health  │    │ Health│    │  Health │
     └─────────┘    └───────┘    └─────────┘
```

### Workflow

1. **Request** - Client wywołuje `GET /axv/status`
2. **Parallel Checks** - Async sprawdzenie wszystkich komponentów (concurrent)
3. **Aggregation** - Zebranie statusów i obliczenie overall status
4. **Response** - Zwrot ujednoliconego JSON

### Components

```python
axv_status_endpoint.py        # Główny moduł z endpoint
├── check_api_health()        # API health check
├── check_gateway_health()    # Gateway HTTP check
├── check_n8n_health()        # n8n HTTP check  
├── check_rag_health()        # RAG check (stub)
├── get_nodes_status()        # Nodes list
└── calculate_overall_status()# Overall logic
```

**Więcej:** Zobacz [K4.1_AXV_STATUS_ENDPOINT.md](K4.1_AXV_STATUS_ENDPOINT.md)

---

## 📡 API Reference

### Endpoint

```
GET /axv/status
```

### Response

```json
{
  "now": 1762714225,
  "ok": true,
  "version": "0.1.9",
  "overall_status": null,
  "status": {
    "api": "ok",
    "gateway": "ok",
    "n8n": "ok",
    "rag": "unknown"
  },
  "nodes": [
    {
      "id": "aster",
      "role": "edge",
      "host": "asus",
      "ok": true,
      "status": "ok",
      "age_s": 12,
      "last_seen": 1762714225
    }
  ]
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `now` | integer | Unix timestamp |
| `ok` | boolean | Overall status (true = system OK) |
| `version` | string | API version |
| `overall_status` | string\|null | "degraded" when system has issues but ok=true |
| `status` | object | Component statuses (api, gateway, n8n, rag) |
| `nodes` | array | Cluster nodes list |

### Status Logic

```python
if any(component == "down"):
    ok = False
elif any(component == "degraded"):
    ok = True
    overall_status = "degraded"
else:
    ok = True
    overall_status = None
```

**Dokumentacja interaktywna:** `http://localhost:8080/docs`

---

## 🔌 Integracje

### Grafana Dashboard

```bash
# Import dashboard
grafana-cli dashboard import grafana-dashboard.json
```

### Prometheus Metrics

```yaml
# prometheus.yml
- job_name: 'axv_status'
  scrape_interval: 30s
  static_configs:
    - targets: ['axv_api:8080']
```

### n8n Workflow

```json
{
  "nodes": [{
    "name": "Check AXV",
    "type": "httpRequest",
    "parameters": {
      "url": "http://api.axv.life/axv/status"
    }
  }]
}
```

### Status Page

```html
<script>
fetch('/axv/status')
  .then(r => r.json())
  .then(data => {
    document.getElementById('status').className = 
      data.ok ? 'status-ok' : 'status-down';
  });
</script>
```

**Więcej przykładów:** Zobacz [K4.1_AXV_STATUS_ENDPOINT.md](K4.1_AXV_STATUS_ENDPOINT.md)

---

## 📊 Monitoring

### Live Monitor (Terminal UI)

```bash
# Start rich terminal monitor
python monitor_axv_status.py \
  --url http://localhost:8080/axv/status \
  --interval 15 \
  --alert-webhook https://hooks.slack.com/...
```

### Automated Testing

```bash
# Run test script
./test_axv_status.sh http://localhost:8080

# Expected: All tests passed ✓
```

### Continuous Monitoring

```bash
# Watch in loop
watch -n 15 'curl -s http://localhost:8080/axv/status | jq ".ok"'
```

---

## 🛠️ Rozwój

### Setup Dev Environment

```bash
# Clone
git clone https://github.com/axv-crew/axv-api.git
cd axv-api

# Install dev dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest test_axv_status.py -v --cov
```

### Run Tests

```bash
# Unit tests
pytest test_axv_status.py -v

# Integration tests  
docker-compose -f docker-compose.test.yml up -d
pytest test_integration_*.py -v

# Coverage
pytest --cov=axv_status_endpoint --cov-report=html
```

### Contributing

1. Fork repo
2. Create feature branch: `git checkout -b feature/K4.X`
3. Commit changes: `git commit -am 'Add K4.X feature'`
4. Push: `git push origin feature/K4.X`
5. Create Pull Request

**Guidelines:** Zobacz [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📁 Struktura Projektu

```
.
├── axv_status_endpoint.py      # Główny moduł K4.1
├── integration_example.py      # Przykład integracji z FastAPI
├── test_axv_status.py          # Unit tests
├── test_axv_status.sh          # Bash test script
├── monitor_axv_status.py       # Terminal monitoring tool
├── Dockerfile                  # Docker image
├── docker-compose.yml          # Full stack setup
├── requirements.txt            # Python dependencies
├── prometheus.yml              # Prometheus config
├── grafana-alerts.yml          # Grafana alert rules
├── K4.1_AXV_STATUS_ENDPOINT.md # Pełna dokumentacja
├── QUICKSTART.md               # Quick start guide
└── README.md                   # Ten plik
```

---

## ❓ FAQ

### Q: Czy mogę dodać własne komponenty do status?

**A:** Tak! Dodaj nową funkcję health check:

```python
async def check_my_component_health() -> StatusValue:
    # your logic
    return "ok"

# Dodaj do endpointu
status_dict["my_component"] = await check_my_component_health()
```

### Q: Co jeśli mój komponent nie ma /healthz?

**A:** Zwróć `"unknown"` lub implementuj custom check (np. ping, TCP connect)

### Q: Jak często mogę odpytywać endpoint?

**A:** Bezpiecznie co 15-30s. Endpoint jest zoptymalizowany (2s timeout, concurrent checks)

### Q: Czy mogę cache'ować odpowiedź?

**A:** Tak, ale max 30-60s. Status zmienia się dynamicznie

### Q: Gdzie są logi?

**A:** 
```bash
# Docker
docker logs axv-api -f

# Local
tail -f logs/axv-api.log
```

---

## 📞 Wsparcie

### Kontakt

- 📧 **Email:** family@axv.life
- 💬 **Slack:** #axv-crew (internal)
- 🐛 **Issues:** [github.com/axv-crew/axv-api/issues](https://github.com/axv-crew/axv-api/issues)

### Dokumentacja

- 📖 **Docs:** [docs.axv.systems](https://docs.axv.systems)
- 📊 **Status Page:** [status.axv.life](https://status.axv.life)
- 🎯 **API Docs:** [api.axv.life/docs](https://api.axv.life/docs)

### Team

**AXV Crew:**
- 👨‍💻 Wojtek (Captain, Infrastructure)
- 🤖 Aster (ChatGPT, Automation)
- 🤖 Claude (Documentation, Development)

---

## 📝 Changelog

### [0.1.9] - 2025-11-16 (K4.1)

**Added:**
- ✨ Unified `/axv/status` endpoint
- 🔍 Health checks for api, gateway, n8n, rag
- 📊 Nodes list integration
- 🎯 Overall status calculation logic
- 📈 Grafana alerts and dashboard
- 🐳 Docker & Docker Compose setup
- 🧪 Comprehensive test suite
- 📖 Full documentation

**Technical:**
- Async concurrent health checks
- 2s timeout per check
- Graceful degradation on errors
- Pydantic models for validation

---

## 📄 License

MIT License - zobacz [LICENSE](LICENSE) dla szczegółów

---

## 🙏 Podziękowania

- FastAPI team za awesome framework
- Anthropic za Claude (który napisał większość tego kodu! 😄)
- AXV Crew za feedback i testing

---

**Made with ❤️ by AXV Crew**

[⬆ Powrót do góry](#axv-status-endpoint---k41)
