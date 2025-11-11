# AXV Gateway - Deployment Quick Guide

## Build & Push (via GitHub Actions)

1. Push to branch `feat/k1-gateway`:
```bash
git push origin feat/k1-gateway
```

2. GitHub Actions automatically:
   - Runs `ruff check` (linting)
   - Runs `pytest` (all tests)
   - Builds Docker image
   - Pushes to GHCR: `ghcr.io/axv-crew/axv-gw:<commit-sha>`

## Manual Docker Build & Run

### Build locally

```bash
docker build -t axv-gw:latest .
```

### Run locally

```bash
docker run -p 8000:8000 axv-gw:latest
```

### Run with custom configuration

```bash
docker run \
  -e AXV_GW_CACHE_TTL_SECONDS=30 \
  -e AXV_GW_LOG_LEVEL=debug \
  -p 8000:8000 \
  axv-gw:latest
```

### Run with custom stub

```bash
docker run \
  -e AXV_GW_STUB_PATH=/app/custom.json \
  -v $(pwd)/my-status.json:/app/custom.json \
  -p 8000:8000 \
  axv-gw:latest
```

## Production Deployment (K2 Planned)

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: axv-gw
  namespace: axv
spec:
  replicas: 2
  selector:
    matchLabels:
      app: axv-gw
  template:
    metadata:
      labels:
        app: axv-gw
    spec:
      containers:
      - name: axv-gw
        image: ghcr.io/axv-crew/axv-gw:<commit-sha>
        ports:
        - containerPort: 8000
        env:
        - name: AXV_GW_CACHE_TTL_SECONDS
          value: "60"
        - name: AXV_GW_LOG_LEVEL
          value: "info"
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 3
          periodSeconds: 5
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: axv-gw
  namespace: axv
spec:
  type: ClusterIP
  ports:
  - port: 8000
    targetPort: 8000
  selector:
    app: axv-gw
```

### Nginx Configuration (gw.axv.life)

```nginx
upstream axv_gw {
    server axv-gw.axv.svc.cluster.local:8000;
}

server {
    listen 443 ssl http2;
    server_name gw.axv.life;

    ssl_certificate /etc/letsencrypt/live/gw.axv.life/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/gw.axv.life/privkey.pem;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req zone=api_limit burst=20 nodelay;

    location / {
        proxy_pass http://axv_gw;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 5s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;
    }

    location /metrics {
        # Restrict metrics to internal networks only
        allow 10.0.0.0/8;
        deny all;
        
        proxy_pass http://axv_gw;
    }
}
```

## Monitoring

### Prometheus Scrape Config

```yaml
scrape_configs:
  - job_name: 'axv-gw'
    static_configs:
      - targets: ['axv-gw.axv.svc.cluster.local:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### Key Metrics to Monitor

- `axv_gw_front_status_requests_total{status_code="500"}` - Error rate
- `axv_gw_front_status_fetch_seconds` - Response time
- `axv_gw_front_status_cache_hits_total` / `cache_misses_total` - Cache hit ratio
- `axv_gw_front_status_degraded` - Service degradation indicator

### Alerting Rules

```yaml
groups:
  - name: axv-gw
    rules:
      - alert: AXVGatewayDown
        expr: up{job="axv-gw"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "AXV Gateway is down"
          
      - alert: AXVGatewayHighErrorRate
        expr: rate(axv_gw_front_status_requests_total{status_code="500"}[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate in AXV Gateway"
          
      - alert: AXVGatewayDegraded
        expr: axv_gw_front_status_degraded == 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "AXV services in degraded mode"
```

## Logs

Access structured JSON logs:

```bash
# Kubernetes
kubectl logs -n axv deployment/axv-gw -f

# Docker
docker logs -f <container-id>
```

Example log entry:
```json
{
  "timestamp": "2025-11-11 16:05:00,123",
  "level": "INFO",
  "logger": "app.routers.front",
  "message": "Successfully loaded and cached status data"
}
```

## Troubleshooting

### Gateway returns 500

1. Check logs for stub loading errors
2. Verify stub file exists and is valid JSON
3. Check cache state via metrics endpoint

### High latency

1. Check cache hit ratio - should be >90%
2. Verify cache TTL is appropriate
3. Monitor Prometheus `fetch_seconds` histogram

### Degraded mode always on

1. Review stub data - ensure services have `state: "ok"`
2. Check application logs for warnings
3. Verify `axv_gw_front_status_degraded` metric

## Health Checks

```bash
# Basic health
curl https://gw.axv.life/healthz

# Full status
curl https://gw.axv.life/front/status

# Metrics (internal only)
curl http://axv-gw.axv.svc.cluster.local:8000/metrics
```

---

**Ready for production deployment to gw.axv.life** ✅
