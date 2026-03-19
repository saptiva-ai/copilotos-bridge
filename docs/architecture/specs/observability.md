# Architecture Overview

Technical architecture of the Copilotos Bridge observability stack.

---

## System Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    User/Developer                        │
│                   (Web Browser)                          │
└────────────┬────────────────────────────────────────────┘
             │
             │ HTTPS (port 3001)
             ▼
┌─────────────────────────────────────────────────────────┐
│                      Grafana                             │
│              (Visualization Layer)                       │
│  • Dashboards                                           │
│  • Alerts                                               │
│  • User Management                                      │
└────────┬────────────────────────┬───────────────────────┘
         │                        │
         │ Query Prometheus       │ Query Loki
         │ (HTTP)                 │ (HTTP)
         ▼                        ▼
┌─────────────────┐      ┌─────────────────┐
│   Prometheus    │      │      Loki       │
│  (Metrics DB)   │      │   (Logs DB)     │
│                 │      │                 │
│  • TSDB         │      │  • BoltDB       │
│  • 7d retention │      │  • 7d retention │
│  • Scraper      │      │  • Ingester     │
└────────┬────────┘      └────────▲────────┘
         │                        │
         │ Scrape /metrics        │ Push logs
         │ (HTTP)                 │ (HTTP)
         ▼                        │
┌─────────────────┐      ┌────────┴────────┐
│  Copilotos API  │      │    Promtail     │
│  (FastAPI app)  │      │ (Log Collector) │
│                 │      │                 │
│  • /api/metrics │      │  • Docker SD    │
│  • Custom       │      │  • Filtering    │
│    registry     │      │  • Relabeling   │
└─────────────────┘      └────────┬────────┘
                                  │
                                  │ Read logs
                                  │ (Docker API)
                                  ▼
                         ┌─────────────────┐
                         │  Docker Socket  │
                         │ /var/run/docker │
                         │     .sock       │
                         └────────┬────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                    ▼             ▼             ▼
              ┌──────────┐  ┌──────────┐  ┌──────────┐
              │   API    │  │   Web    │  │  Mongo   │
              │Container │  │Container │  │Container │
              └──────────┘  └──────────┘  └──────────┘

                    ┌─────────────────┐
                    │    cAdvisor     │ ◄─── Scraped by Prometheus
                    │(Container Metrics)│
                    │                 │
                    │  • CPU usage    │
                    │  • Memory       │
                    │  • Network      │
                    │  • Disk I/O     │
                    └─────────────────┘
                            │
                            │ Reads container stats
                            ▼
                    ┌─────────────────┐
                    │  Docker Engine  │
                    └─────────────────┘
```

---

## Components

### 1. FastAPI Application

**Role**: Metrics source

**Responsibilities**:
- Expose Prometheus metrics at `/api/metrics`
- Track HTTP requests, latency, errors
- Track business metrics (research, intent, tools)
- Maintain custom Prometheus registry

**Technology**:
- FastAPI with `prometheus_client`
- Custom telemetry module (`src/core/telemetry.py`)
- Custom registry for metric isolation

**Metrics Exposed**:
- 24 metric families
- Histograms, counters, gauges
- See [metrics reference](./metrics.md)

### 2. Prometheus

**Role**: Metrics collection and storage

**Responsibilities**:
- Scrape `/api/metrics` every 10-15 seconds
- Store time-series data in TSDB
- Evaluate alert rules
- Provide PromQL query interface

**Storage**:
- **Type**: Time-Series Database (TSDB)
- **Location**: `/prometheus` in container
- **Volume**: `copilotos_prometheus_data`
- **Retention**: 7 days (configurable)
- **Compression**: Automatic block compression

**Configuration**:
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'copilotos-api'
    static_configs:
      - targets: ['api:8001']
    metrics_path: '/api/metrics'
    scrape_interval: 10s
```

### 3. Grafana

**Role**: Visualization and dashboarding

**Responsibilities**:
- Query Prometheus for metrics
- Query Loki for logs
- Render dashboards
- Handle user authentication
- Send alerts (with Alertmanager)

**Datasources**:
- **Prometheus**: Metrics (default)
- **Loki**: Logs

**Provisioning**:
- Datasources auto-configured on startup
- Dashboards loaded from JSON files
- Located in `infra/monitoring/grafana/`

### 4. Loki

**Role**: Log aggregation and storage

**Responsibilities**:
- Receive logs from Promtail
- Index and store logs
- Provide LogQL query interface
- Handle log retention

**Storage**:
- **Type**: BoltDB + Filesystem
- **Location**: `/tmp/loki` in container
- **Volume**: `copilotos_loki_data`
- **Retention**: 7 days (168 hours)

**Index Strategy**:
- Labels: `service`, `container`
- Chunks stored as files
- BoltDB for index

### 5. Promtail

**Role**: Log collection agent

**Responsibilities**:
- Discover Docker containers
- Read container logs via Docker API
- Filter by compose project label
- Add labels (service, container)
- Push logs to Loki

**Service Discovery**:
```yaml
docker_sd_configs:
  - host: unix:///var/run/docker.sock
    filters:
      - name: label
        values: ["com.docker.compose.project=copilotos-bridge"]
```

**Relabeling**:
- Container name → `container` label
- Service name → `service` label

### 6. cAdvisor

**Role**: Container metrics collector

**Responsibilities**:
- Collect CPU, memory, network, disk metrics
- Monitor all containers on host
- Expose metrics for Prometheus
- Provide web UI

**Metrics Exposed**:
- `container_cpu_usage_seconds_total`
- `container_memory_usage_bytes`
- `container_network_receive_bytes_total`
- `container_fs_reads_bytes_total`
- And many more...

**Access**:
- **Prometheus**: Scrapes port 8080
- **Web UI**: http://localhost:8080

---

## Data Flow

### Metrics Flow

```
1. FastAPI app records event
   └─> telemetry.track_request(method, endpoint, status, duration)

2. Metric updated in custom registry
   └─> REQUEST_COUNT.labels(method, endpoint, status).inc()

3. Prometheus scrapes /api/metrics
   └─> GET http://api:8001/api/metrics (every 10s)

4. Prometheus stores in TSDB
   └─> Compressed blocks on disk

5. Grafana queries Prometheus
   └─> PromQL: rate(copilotos_requests_total[5m])

6. Dashboard displays result
   └─> User sees graph/stat
```

### Logs Flow

```
1. Application writes log
   └─> print() or logger.info()

2. Docker captures stdout/stderr
   └─> Stored in /var/lib/docker/containers/<id>/<id>-json.log

3. Promtail reads via Docker API
   └─> Uses Docker service discovery

4. Promtail filters & labels
   └─> Adds service="api", container="copilotos-api"

5. Promtail pushes to Loki
   └─> POST http://loki:3100/loki/api/v1/push

6. Loki indexes & stores
   └─> BoltDB (index) + Filesystem (chunks)

7. Grafana queries Loki
   └─> LogQL: {service="api"} |= "error"

8. Logs displayed in UI
   └─> User sees log entries
```

### Alert Flow (Optional)

```
1. Prometheus evaluates alert rules
   └─> Every evaluation_interval (30s)

2. Alert fires if condition met
   └─> Error rate > 5% for 5 minutes

3. Alertmanager receives alert
   └─> POST http://alertmanager:9093/api/v1/alerts

4. Alertmanager groups & routes
   └─> Based on labels (severity, service)

5. Notification sent
   └─> Slack, email, PagerDuty, etc.

6. User acknowledges
   └─> Via Grafana or Alertmanager UI
```

---

## Network Architecture

### Docker Network

All services communicate via `copilotos-network`:

```yaml
networks:
  copilotos-network:
    external: true
```

**Services on network**:
- `api` (main application)
- `web` (Next.js frontend)
- `mongodb`
- `redis`
- `prometheus`
- `grafana`
- `loki`
- `promtail`
- `cadvisor`

### Service Discovery

**Prometheus** uses static discovery:
```yaml
static_configs:
  - targets: ['api:8001']  # Resolves via Docker DNS
```

**Promtail** uses Docker service discovery:
```yaml
docker_sd_configs:
  - host: unix:///var/run/docker.sock
```

### Port Mappings

| Service | Internal | Host | Public? |
|---------|----------|------|---------|
| Prometheus | 9090 | 9090 | ❌ No |
| Grafana | 3000 | 3001 | ⚠️ Localhost only |
| Loki | 3100 | 3100 | ❌ No |
| cAdvisor | 8080 | 8080 | ❌ No |

**Production**: Only Grafana should be exposed, via reverse proxy with auth.

---

## Storage Architecture

### Volumes

```yaml
volumes:
  prometheus_data:
    name: copilotos_prometheus_data
  grafana_data:
    name: copilotos_grafana_data
  loki_data:
    name: copilotos_loki_data
```

### Disk Usage

After 7 days with moderate load:

| Volume | Size | Growth Rate |
|--------|------|-------------|
| Prometheus | ~1.4 GB | ~200 MB/day |
| Loki | ~700 MB | ~100 MB/day |
| Grafana | ~10 MB | Minimal |
| **Total** | **~2.1 GB** | ~300 MB/day |

### Data Retention

**Prometheus**:
- Configured via `--storage.tsdb.retention.time=7d`
- Old blocks automatically deleted
- Can also set size limit: `--storage.tsdb.retention.size=50GB`

**Loki**:
- Configured in `loki.yml`: `retention_period: 168h`
- Compactor runs periodically to delete old chunks

**Grafana**:
- No automatic cleanup (mostly config, not data)
- Dashboards and settings persist indefinitely

---

## Scaling Considerations

### Vertical Scaling

Increase resources for single instance:

```yaml
prometheus:
  deploy:
    resources:
      limits:
        cpus: '2.0'      # Increase CPU
        memory: 4G       # Increase memory
```

**When to scale up**:
- Scrape latency increasing
- Query timeouts
- Out of memory errors
- High CPU usage (>80%)

### Horizontal Scaling

Run multiple instances (requires additional setup):

**Prometheus**:
- Use federation or Thanos/Cortex
- Each instance scrapes subset of targets
- Deduplicate in Grafana or query layer

**Grafana**:
- Share database (PostgreSQL)
- Put behind load balancer
- Session affinity not required

**Loki**:
- Run multiple ingesters
- Use object storage (S3) for chunks
- Requires microservices mode

### Load Distribution

**Reduce load on Prometheus**:
1. Increase scrape interval (15s → 30s)
2. Use recording rules for expensive queries
3. Reduce cardinality (fewer labels)
4. Sample metrics (not recommended)

**Reduce load on Loki**:
1. Filter logs before ingestion (in Promtail)
2. Reduce log verbosity
3. Aggregate similar logs
4. Increase retention interval between compactions

---

## Security Architecture

### Attack Surface

**Exposed ports** (localhost only):
- Grafana: 3001 (authentication required)
- Prometheus: 9090 (no auth by default)
- cAdvisor: 8080 (no auth)

**Docker socket access**:
- Promtail reads Docker socket (read-only)
- cAdvisor reads Docker socket (requires privileged)

### Security Measures

1. **Network isolation**: All on private Docker network
2. **Port binding**: Only localhost (127.0.0.1)
3. **Authentication**: Grafana requires login
4. **Readonly mounts**: Config files mounted read-only
5. **No root**: Grafana runs as non-root user
6. **Resource limits**: Prevent DoS via resource exhaustion

### Production Hardening

1. **TLS/HTTPS**: Enable in Grafana + reverse proxy
2. **OAuth/SSO**: Integrate with corporate SSO
3. **RBAC**: Configure Grafana roles (admin, editor, viewer)
4. **Audit logging**: Enable in Grafana
5. **Network policies**: Restrict pod-to-pod communication (K8s)
6. **Secrets management**: Use Vault or K8s secrets

---

## Monitoring the Monitoring

### Self-Monitoring

Prometheus monitors itself:
```promql
# Prometheus health
up{job="prometheus"}

# Scrape duration
prometheus_target_scrape_duration_seconds

# TSDB status
prometheus_tsdb_head_series
prometheus_tsdb_storage_blocks_bytes
```

Monitor monitoring stack via:
- cAdvisor (container metrics)
- Prometheus self-metrics
- Grafana logs

### Health Checks

All services have health checks:

```yaml
prometheus:
  healthcheck:
    test: ["CMD", "wget", "-q", "--tries=1", "-O-", "http://localhost:9090/-/healthy"]
    interval: 30s
    timeout: 10s
    retries: 3

grafana:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

Check via:
```bash
docker ps --filter name=copilotos --format "table {{.Names}}\t{{.Status}}"
```

---

## Technology Choices

### Why These Tools?

**Prometheus**:
- ✅ Industry standard for metrics
- ✅ Powerful query language (PromQL)
- ✅ Efficient time-series storage
- ✅ Pull-based (easy to secure)
- ✅ Native Grafana integration

**Grafana**:
- ✅ Best-in-class visualization
- ✅ Supports multiple datasources
- ✅ Extensive plugin ecosystem
- ✅ Active community
- ✅ Free and open source

**Loki**:
- ✅ Designed for Kubernetes/Docker logs
- ✅ Efficient storage (doesn't index full text)
- ✅ Powerful query language (LogQL)
- ✅ Native Grafana integration
- ✅ Lightweight compared to ELK

**cAdvisor**:
- ✅ Built by Google, battle-tested
- ✅ Low overhead
- ✅ Native Docker support
- ✅ Rich container metrics
- ✅ Simple deployment

### Alternatives Considered

- **Metrics**: Datadog, New Relic (paid, SaaS)
- **Logs**: ELK Stack (heavier), Fluentd + Elasticsearch
- **Visualization**: Kibana (ELK-specific), Chronograf
- **Container metrics**: Telegraf, node-exporter

---

## Next Steps

- [Setup guide](./setup.md) for installation
- [Metrics reference](./metrics.md) for all available metrics
- [Dashboards guide](./dashboards.md) for creating visualizations
- [Production guide](./production.md) for deployment best practices
