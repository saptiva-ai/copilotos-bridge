# 📊 Observability Stack

Comprehensive monitoring and observability for Copilotos Bridge using Prometheus, Grafana, Loki, and cAdvisor.

## 🚀 Quick Start

```bash
# Start the monitoring stack
make obs-up

# Access the dashboards
# Grafana:    http://localhost:3001 (admin/admin)
# Prometheus: http://localhost:9090
# cAdvisor:   http://localhost:8080

# View logs
make obs-logs

# Stop the stack
make obs-down
```

## 📦 Components

### Prometheus (Port 9090)
- **Purpose**: Metrics collection and storage
- **Retention**: 7 days
- **Scrape Interval**: 10 seconds (API), 15 seconds (others)
- **Configuration**: `prometheus.yml`

**Metrics Scraped**:
- FastAPI application metrics (`/api/metrics`)
- Container metrics (cAdvisor)
- Prometheus self-metrics

### Grafana (Port 3001)
- **Purpose**: Metrics visualization and dashboards
- **Default Credentials**: `admin` / `admin`
- **Datasources**: Prometheus (metrics), Loki (logs)
- **Pre-configured Dashboard**: Copilotos Bridge API

**Dashboard Panels**:
- Request Rate (req/s)
- P95 Latency
- Error Rate (5xx)
- Total Requests
- Response Time Percentiles (P50, P95, P99)
- HTTP Status Codes (2xx, 4xx, 5xx)

### Loki (Port 3100)
- **Purpose**: Log aggregation and querying
- **Retention**: 7 days (168 hours)
- **Configuration**: `loki.yml`

### Promtail
- **Purpose**: Log collection from Docker containers
- **Source**: Docker socket (`/var/run/docker.sock`)
- **Filter**: Only containers with `com.docker.compose.project=copilotos-bridge`
- **Configuration**: `promtail.yml`

**Labels Added**:
- `container`: Container name
- `service`: Compose service name

### cAdvisor (Port 8080)
- **Purpose**: Container-level metrics (CPU, memory, network, disk)
- **Privileged**: Yes (required for host metrics)

## 📈 Available Metrics

The FastAPI application exposes comprehensive Prometheus metrics at `/api/metrics`:

### Request Metrics
- `copilotos_requests_total` - Total HTTP requests by method, endpoint, status
- `copilotos_request_duration_seconds` - Request duration histogram

### Deep Research Metrics
- `copilotos_research_requests_total` - Research requests by intent type
- `copilotos_research_duration_seconds` - Research operation duration
- `copilotos_research_quality_score` - Research quality scores
- `copilotos_intent_classification_total` - Intent classifications

### Performance Metrics
- `copilotos_active_connections` - Active connections gauge
- `copilotos_memory_usage_bytes` - Memory usage by type
- `copilotos_cache_operations_total` - Cache operations (hit/miss)

### Business Metrics
- `copilotos_active_user_sessions` - Active user sessions
- `copilotos_rate_limit_hits_total` - Rate limit violations
- `copilotos_external_api_calls_total` - External API calls
- `copilotos_external_api_duration_seconds` - External API latency

### Error Tracking
- `copilotos_errors_total` - Application errors by type, endpoint, severity

### Document Ingestion
- `copilotos_pdf_ingest_seconds` - PDF ingestion phase duration
- `copilotos_pdf_ingest_errors_total` - PDF ingestion errors by code

### Tool Usage
- `copilotos_tool_invocations_total` - Tool invocations by key
- `copilotos_tool_toggle_total` - Tool enable/disable events
- `copilotos_tool_call_blocked_total` - Blocked tool attempts
- `copilotos_planner_tool_suggested_total` - Planner suggestions

## 🔧 Configuration

### Resource Limits

All monitoring services have resource limits configured in `docker-compose.resources.yml`:

| Service | CPU Limit | Memory Limit |
|---------|-----------|--------------|
| Prometheus | 0.5 cores | 512 MB |
| Grafana | 0.5 cores | 256 MB |
| Loki | 0.5 cores | 256 MB |
| Promtail | 0.25 cores | 128 MB |
| cAdvisor | 0.5 cores | 256 MB |

### Disk Usage

- **Prometheus Data**: `~100-200 MB/day` (7 days = ~1.4 GB)
- **Loki Data**: `~50-100 MB/day` (7 days = ~700 MB)
- **Grafana Data**: `~10 MB` (dashboards and config)

**Total**: ~2.1 GB for 7 days of retention

## 📖 Usage Examples

### Viewing Metrics in Grafana

1. Open Grafana: http://localhost:3001
2. Login with `admin` / `admin`
3. Navigate to "Dashboards" → "Copilotos Bridge" → "Copilotos Bridge API"

### Querying Logs in Grafana

1. Go to "Explore" in Grafana
2. Select "Loki" datasource
3. Example queries:
   ```logql
   {service="api"} |= "error"
   {service="api"} |= "research"
   {container="copilotos-api"} |= "POST" |= "/api/chat"
   ```

### Raw Prometheus Queries

Visit http://localhost:9090 and try:

```promql
# Request rate per endpoint
rate(copilotos_requests_total[5m])

# P95 latency
histogram_quantile(0.95, rate(copilotos_request_duration_seconds_bucket[5m]))

# Error rate
rate(copilotos_errors_total[5m])

# Active connections
copilotos_active_connections

# Cache hit rate
rate(copilotos_cache_operations_total{hit="hit"}[5m]) /
rate(copilotos_cache_operations_total[5m])
```

## 🎯 Alerting (Future Enhancement)

To add alerts, create `prometheus.yml` alert rules:

```yaml
groups:
  - name: copilotos_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(copilotos_errors_total[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(copilotos_request_duration_seconds_bucket[5m])) > 0.8
        for: 5m
        annotations:
          summary: "P95 latency above 800ms"
```

Then configure Alertmanager for notifications (Slack, email, PagerDuty, etc.).

## 🧹 Maintenance

### Clean Old Data

```bash
# Remove all monitoring data (WARNING: irreversible)
make obs-clean
```

### Restart Services

```bash
# Restart all monitoring services
make obs-restart

# Or individually
docker restart copilotos-prometheus
docker restart copilotos-grafana
```

### Backup Grafana Dashboards

```bash
# Dashboards are in version control
cp infra/monitoring/grafana/dashboards/*.json ~/grafana-backup/
```

## 🐛 Troubleshooting

### Prometheus Not Scraping API Metrics

1. Check API is healthy: `curl http://localhost:8001/api/health`
2. Check metrics endpoint: `curl http://localhost:8001/api/metrics`
3. Check Prometheus targets: http://localhost:9090/targets
4. Look for scrape errors in Prometheus logs: `make obs-logs`

### Grafana Can't Connect to Prometheus

1. Verify Prometheus is running: `docker ps | grep prometheus`
2. Check datasource config: `cat infra/monitoring/grafana/provisioning/datasources/datasources.yml`
3. Test connection from Grafana container:
   ```bash
   docker exec copilotos-grafana wget -O- http://prometheus:9090/api/v1/status/config
   ```

### Promtail Not Collecting Logs

1. Check Docker socket is mounted: `docker inspect copilotos-promtail | grep docker.sock`
2. Verify container labels: `docker inspect copilotos-api | grep com.docker.compose`
3. Check Promtail config: `cat infra/monitoring/promtail.yml`
4. View Promtail logs: `docker logs copilotos-promtail`

### High Memory Usage

If monitoring consumes too much memory:

1. Reduce retention period in `loki.yml` and `prometheus.yml`
2. Increase scrape interval in `prometheus.yml`
3. Adjust resource limits in `docker-compose.resources.yml`

## 📚 Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Loki Documentation](https://grafana.com/docs/loki/)
- [cAdvisor GitHub](https://github.com/google/cadvisor)
- [PromQL Cheat Sheet](https://promlabs.com/promql-cheat-sheet/)
- [LogQL Cheat Sheet](https://grafana.com/docs/loki/latest/logql/)

## 🔐 Security Notes

- **Change Grafana password**: Default `admin/admin` should be changed in production
- **Restrict access**: Monitoring ports should not be exposed to the internet
- **Use reverse proxy**: Put Grafana behind nginx/traefik with authentication
- **Enable HTTPS**: Use SSL certificates for production deployments

## 🎉 Summary

This observability stack provides:

✅ **Real-time metrics** - Request rates, latency, errors
✅ **Centralized logs** - All container logs in one place
✅ **Container insights** - CPU, memory, network, disk usage
✅ **Pre-built dashboards** - Visualize API performance
✅ **7-day retention** - Week of historical data
✅ **Production-ready** - Resource limits and health checks

**Total overhead**: ~1.5 GB RAM, ~2 GB disk for 7 days of data
