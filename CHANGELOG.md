# Changelog

All notable changes to AXV Gateway will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-11-11

### Added

- Initial K1.5 gateway implementation
- `GET /healthz` endpoint for health checks
- `GET /front/status` endpoint returning FrontStatusV1 contract
- `GET /metrics` endpoint for Prometheus metrics exposition
- In-memory caching with configurable TTL (default 60s)
- Fallback to stale cache on stub loading errors
- Degraded mode detection based on service states
- Structured JSON logging to stdout
- Stub-based data source (`app/data/status.stub.json`)
- Multi-stage Dockerfile for optimized production builds
- GitHub Actions CI/CD pipeline (lint, test, build, push to GHCR)
- Comprehensive test suite with pytest
- OpenAPI 3.1 specification for API contract
- Environment-based configuration via `AXV_GW_*` variables
- Prometheus metrics:
  - `axv_gw_healthz_requests_total`
  - `axv_gw_front_status_requests_total`
  - `axv_gw_front_status_fetch_seconds`
  - `axv_gw_front_status_cache_hits_total`
  - `axv_gw_front_status_cache_misses_total`
  - `axv_gw_front_status_degraded`

### Technical Details

- Python 3.11+ with FastAPI + Uvicorn
- Pydantic v2 for schema validation
- Conventional commits for Git history
- Branch: `feat/k1-gateway`
- Container registry: `ghcr.io/axv-crew/axv-gw`

### Known Limitations (K1.5 Scope)

- No cluster integration - stub data only
- No authentication - rate limiting handled by upstream Nginx
- No external API calls - reserved for K2 scope
- Single-process deployment (no multiprocess worker support yet)

[0.1.0]: https://github.com/axv-crew/axv-gw/releases/tag/v0.1.0

## v0.1.10 — 2025-11-13 (K2 — Gateway Hardening & Ops)
- K2.1: Rate limiting middleware — sliding window per (IP+path). ENV: `RATE_LIMIT_DEFAULT` (domyślnie 60/min), `RATE_LIMIT_HOOKS` (np. 5/min). 429 JSON: `{"ok":false,"error":"rate_limited","retry_after_s":N}` + nagłówek `Retry-After`. Testy unit/e2e.
- K2.2: HMAC timestamp tolerance — ENV: `HMAC_MAX_SKEW_S=300` (±5 min). Poza oknem: 401 `{"ok":false,"error":"bad timestamp"}`. Testy.
- K2.3: Request size guard — ENV: `MAX_BODY_KB` (np. 64). Przekroczenie: 413 `{"ok":false,"error":"body_too_large","limit_kb":N}`. Testy.
- K2.4: n8n tidy — sekrety przeniesione do Credentials; workflow **bez credów** wyeksportowany do `ops/n8n/k2_webhook_sign_and_send.json`.
- K2.5: Metrics — Prometheus liczniki: `gw_rate_limit_dropped_total`, `gw_hmac_bad_ts_total`, `gw_hooks_ok_total`; histogram `gw_hooks_duration_ms`. (Uwaga: wzbogacenie logów o `client_ip` z `X-Forwarded-For` zostawiamy na mały follow-up.)
- K2.6: CI polish — workflow `ci-k2.yml`: pytest + coverage (artefakt `test-coverage.txt`), ruff/black/mypy w trybie lenient.

**ENV checklist (prod):**  
`GATEWAY_VERSION=0.1.10`, `RATE_LIMIT_DEFAULT=60`, `RATE_LIMIT_HOOKS=5`, `HMAC_MAX_SKEW_S=300`, `MAX_BODY_KB=64`
