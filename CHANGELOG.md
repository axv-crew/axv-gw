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
