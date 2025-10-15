# Setup Guide - Observability Stack

Complete installation and configuration guide for the Copilotos Bridge observability stack.

---

## Prerequisites

- Docker and Docker Compose installed
- Copilotos Bridge application running
- At least 2 GB free RAM
- At least 5 GB free disk space

## Installation

### 1. Start Main Application

```bash
# Start the main application first
make dev

# Verify API is running
curl http://localhost:8001/api/health
```

### 2. Start Monitoring Stack

```bash
# Start all monitoring services
make obs-up
```

This will start:
- Prometheus (port 9090)
- Grafana (port 3001)
- Loki (port 3100)
- Promtail
- cAdvisor (port 8080)

### 3. Verify Services

```bash
# Check service status
make obs-status

# Should show all 5 services as "Up"
```

### 4. Access Grafana

1. Open http://localhost:3001
2. Login with:
   - **Username**: `admin`
   - **Password**: `admin`
3. Skip password change (for local development)

### 5. View Pre-configured Dashboard

1. Go to **Dashboards** (left sidebar)
2. Navigate to **Copilotos Bridge** folder
3. Click **Copilotos Bridge API**
4. See real-time metrics!

---

## Configuration Files

### Location

All configuration files are in `infra/monitoring/`:

```
infra/monitoring/
├── prometheus.yml           # Prometheus scrape config
├── loki.yml                 # Loki storage config
├── promtail.yml             # Log collection config
└── grafana/
    ├── provisioning/
    │   ├── datasources/     # Prometheus + Loki datasources
    │   └── dashboards/      # Dashboard provider
    └── dashboards/
        └── copilotos-api.json  # Pre-built API dashboard
```

### Prometheus Configuration

**File**: `infra/monitoring/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  # FastAPI application metrics
  - job_name: 'copilotos-api'
    static_configs:
      - targets: ['api:8001']
    metrics_path: '/api/metrics'
    scrape_interval: 10s

  # Container metrics
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
```

**Key settings**:
- Scrapes API every 10 seconds
- Metrics endpoint: `/api/metrics` (not `/metrics`)
- 7-day retention period
- Scrapes container metrics from cAdvisor

### Loki Configuration

**File**: `infra/monitoring/loki.yml`

```yaml
auth_enabled: false

server:
  http_listen_port: 3100

common:
  storage:
    filesystem:
      chunks_directory: /tmp/loki/chunks
      rules_directory: /tmp/loki/rules

limits_config:
  retention_period: 168h  # 7 days
```

**Key settings**:
- 7-day log retention
- Filesystem storage
- No authentication (local development)

### Promtail Configuration

**File**: `infra/monitoring/promtail.yml`

```yaml
scrape_configs:
  - job_name: docker
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        filters:
          - name: label
            values: ["com.docker.compose.project=copilotos-bridge"]

    relabel_configs:
      # Extract container name
      - source_labels: ['__meta_docker_container_name']
        regex: '/(.*)'
        target_label: 'container'

      # Extract service name
      - source_labels: ['__meta_docker_container_label_com_docker_compose_service']
        target_label: 'service'
```

**Key settings**:
- Automatically discovers Docker containers
- Filters for `copilotos-bridge` project only
- Adds `container` and `service` labels
- Reads logs via Docker socket

### Grafana Datasources

**File**: `infra/monitoring/grafana/provisioning/datasources/datasources.yml`

```yaml
apiVersion: 1

datasources:
  # Prometheus - Metrics
  - name: Prometheus
    type: prometheus
    url: http://prometheus:9090
    isDefault: true

  # Loki - Logs
  - name: Loki
    type: loki
    url: http://loki:3100
```

**Automatically configured** on Grafana startup.

---

## Resource Limits

All services have resource limits configured in `docker-compose.resources.yml`:

| Service | CPU Limit | Memory Limit | Reservation |
|---------|-----------|--------------|-------------|
| Prometheus | 0.5 cores | 512 MB | 128 MB |
| Grafana | 0.5 cores | 256 MB | 64 MB |
| Loki | 0.5 cores | 256 MB | 64 MB |
| Promtail | 0.25 cores | 128 MB | 32 MB |
| cAdvisor | 0.5 cores | 256 MB | 64 MB |

**Total**: 2.25 cores max, 1.4 GB memory max

### Adjusting Limits

Edit `infra/docker-compose.resources.yml`:

```yaml
prometheus:
  deploy:
    resources:
      limits:
        cpus: '1.0'      # Increase to 1 core
        memory: 1G       # Increase to 1 GB
```

Then restart:

```bash
make obs-restart
```

---

## Storage Configuration

### Disk Usage

Expected disk usage after 7 days:

| Component | Size | Location |
|-----------|------|----------|
| Prometheus data | ~1.4 GB | `copilotos_prometheus_data` volume |
| Loki data | ~700 MB | `copilotos_loki_data` volume |
| Grafana config | ~10 MB | `copilotos_grafana_data` volume |
| **Total** | **~2.1 GB** | |

### Adjusting Retention

**Prometheus** - Edit `infra/monitoring/prometheus.yml`:

```yaml
command:
  - '--storage.tsdb.retention.time=30d'  # Change to 30 days
```

**Loki** - Edit `infra/monitoring/loki.yml`:

```yaml
limits_config:
  retention_period: 720h  # Change to 30 days (720 hours)
```

Restart after changes:

```bash
make obs-restart
```

---

## Network Configuration

### Docker Network

All monitoring services connect to the existing `copilotos-network`:

```yaml
networks:
  copilotos-network:
    external: true
```

This allows monitoring services to communicate with the main application.

### Port Mappings

| Service | Internal Port | Host Port | Public? |
|---------|---------------|-----------|---------|
| Prometheus | 9090 | 9090 | ❌ No |
| Grafana | 3000 | 3001 | ⚠️ Localhost only |
| Loki | 3100 | 3100 | ❌ No |
| cAdvisor | 8080 | 8080 | ❌ No |

**Security**: In production, only expose Grafana through a reverse proxy with authentication.

---

## Customization

### Adding Custom Dashboards

1. Create dashboard in Grafana UI
2. Export as JSON
3. Save to `infra/monitoring/grafana/dashboards/`
4. Restart Grafana: `docker restart copilotos-grafana`

### Adding Scrape Targets

Edit `infra/monitoring/prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'my-service'
    static_configs:
      - targets: ['my-service:8000']
    metrics_path: '/metrics'
```

Restart Prometheus:

```bash
docker restart copilotos-prometheus
```

### Custom Log Filters

Edit `infra/monitoring/promtail.yml` to add filters:

```yaml
relabel_configs:
  - source_labels: ['__meta_docker_container_name']
    regex: '.*(redis|mongodb).*'
    action: drop  # Don't collect logs from redis/mongodb
```

---

## Verification

### Check Prometheus Targets

1. Open http://localhost:9090/targets
2. Verify all targets are "UP":
   - `copilotos-api` (api:8001)
   - `cadvisor` (cadvisor:8080)
   - `prometheus` (localhost:9090)

### Check Loki Logs

In Grafana:
1. Go to **Explore**
2. Select **Loki** datasource
3. Query: `{service="api"}`
4. Should see API logs

### Check Metrics

```bash
# Check API metrics endpoint
curl http://localhost:8001/api/metrics | head -20

# Should see Prometheus format:
# copilotos_requests_total{method="GET",endpoint="/api/health",status_code="200"} 42
```

---

## Upgrading

### Update Service Versions

Edit `infra/docker-compose.resources.yml`:

```yaml
prometheus:
  image: prom/prometheus:v2.50.0  # Update version

grafana:
  image: grafana/grafana:10.3.0   # Update version
```

Pull new images and restart:

```bash
docker compose -f infra/docker-compose.resources.yml pull
make obs-restart
```

### Backup Before Upgrade

```bash
# Backup Grafana dashboards
docker cp copilotos-grafana:/var/lib/grafana/dashboards ./grafana-backup/

# Backup Prometheus data (optional)
docker cp copilotos-prometheus:/prometheus ./prometheus-backup/
```

---

## Uninstallation

### Stop Services

```bash
make obs-down
```

### Remove Data Volumes

```bash
# WARNING: This deletes all metrics and logs
make obs-clean

# Or manually:
docker volume rm copilotos_prometheus_data
docker volume rm copilotos_grafana_data
docker volume rm copilotos_loki_data
```

### Remove Configuration

```bash
rm -rf infra/monitoring/
```

---

## Troubleshooting

### Services Won't Start

```bash
# Check Docker resources
docker system df

# Clean up if needed
make docker-cleanup

# Restart
make obs-restart
```

### Port Conflicts

If ports 3001, 9090, or 8080 are in use:

Edit `infra/docker-compose.resources.yml`:

```yaml
grafana:
  ports:
    - "3002:3000"  # Change to 3002
```

### Metrics Not Appearing

1. Check API is exposing metrics:
   ```bash
   curl http://localhost:8001/api/metrics
   ```

2. Check Prometheus is scraping:
   - Open http://localhost:9090/targets
   - Verify `copilotos-api` is UP

3. Check Grafana datasource:
   - Configuration → Data Sources → Prometheus → Test

---

## Next Steps

- [View available metrics](./metrics.md)
- [Learn about dashboards](./dashboards.md)
- [Troubleshooting guide](./troubleshooting.md)
- [Production deployment](./production.md)
