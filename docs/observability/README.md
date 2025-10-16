# 📊 Observability Stack - Copilotos Bridge

**Status**: ✅ Production Ready
**Version**: 1.0
**Last Updated**: 2025-10-14

---

## Overview

Comprehensive observability solution for Copilotos Bridge using industry-standard tools:

- **Prometheus** - Metrics collection and time-series storage
- **Grafana** - Visualization and dashboarding
- **Loki** - Log aggregation and querying
- **Promtail** - Automated log collection
- **cAdvisor** - Container resource monitoring

## Quick Start

```bash
# Start main application
make dev

# Start monitoring stack
make obs-up

# Access dashboards
# Grafana:    http://localhost:3001 (admin/admin)
# Prometheus: http://localhost:9090
# cAdvisor:   http://localhost:8080

# Stop monitoring
make obs-down
```

## Key Features

✅ **Zero Code Changes** - API already exposes Prometheus metrics
✅ **Pre-configured Dashboards** - See API performance immediately
✅ **Centralized Logs** - All container logs in one place
✅ **Low Overhead** - ~1.5 GB RAM, ~2 GB disk (7 days)
✅ **Production Ready** - Resource limits, health checks
✅ **Simple Commands** - Single Make targets to control everything

## Architecture

```
┌─────────────┐
│   Grafana   │ ← Visualization (port 3001)
│  (Queries)  │
└─────┬───────┘
      │
      ├──→ ┌──────────────┐
      │    │  Prometheus  │ ← Metrics (port 9090)
      │    │  (Scrapes)   │
      │    └──────┬───────┘
      │           │
      │           └──→ /api/metrics (FastAPI app)
      │           └──→ cAdvisor (container metrics)
      │
      └──→ ┌──────────────┐
           │     Loki     │ ← Logs (port 3100)
           │   (Stores)   │
           └──────▲───────┘
                  │
           ┌──────┴───────┐
           │   Promtail   │ ← Collects logs
           │   (Reads)    │
           └──────▲───────┘
                  │
           Docker Socket (/var/run/docker.sock)
```

## Components

| Component | Port | Purpose | Retention |
|-----------|------|---------|-----------|
| Prometheus | 9090 | Metrics storage | 7 days |
| Grafana | 3001 | Dashboards | N/A |
| Loki | 3100 | Log storage | 7 days |
| Promtail | - | Log collection | N/A |
| cAdvisor | 8080 | Container metrics | N/A |

## Resource Usage

**Total Overhead**:
- **RAM**: ~1.5 GB
- **Disk**: ~2 GB (7 days of data)
- **CPU**: <10% combined

All services have resource limits configured in `docker-compose.resources.yml`.

## Available Metrics

The FastAPI application exposes **24 metric families** at `/api/metrics`:

### Core Metrics
- `copilotos_requests_total` - HTTP requests by method, endpoint, status
- `copilotos_request_duration_seconds` - Request latency histogram
- `copilotos_errors_total` - Application errors by type and severity
- `copilotos_active_connections` - Active connection count

### Business Metrics
- `copilotos_research_requests_total` - Deep Research operations
- `copilotos_intent_classification_total` - Intent classifications
- `copilotos_external_api_calls_total` - External API usage
- `copilotos_tool_invocations_total` - Tool usage tracking

### Performance Metrics
- `copilotos_cache_operations_total` - Cache hit/miss rates
- `copilotos_memory_usage_bytes` - Memory usage by type
- `copilotos_active_user_sessions` - Active sessions

### Document Metrics
- `copilotos_pdf_ingest_seconds` - PDF ingestion duration
- `copilotos_pdf_ingest_errors_total` - Ingestion errors

[→ See complete metrics reference](./metrics.md)

## Pre-built Dashboards

### Copilotos Bridge API Dashboard

**Panels**:
1. Request Rate (req/s)
2. P95 Latency
3. Error Rate (5xx)
4. Total Requests
5. Response Time Percentiles (P50, P95, P99)
6. HTTP Status Codes (2xx, 4xx, 5xx)

[→ Dashboard guide](./dashboards.md)

## Documentation

- **[Setup Guide](./setup.md)** - Installation and configuration
- **[Architecture](./architecture.md)** - System design and data flow
- **[Metrics Reference](./metrics.md)** - All available metrics
- **[Dashboards](./dashboards.md)** - Using Grafana dashboards
- **[Troubleshooting](./troubleshooting.md)** - Common issues and solutions
- **[Production Guide](./production.md)** - Production deployment best practices

## Commands

```bash
# Start/stop
make obs-up         # Start monitoring stack
make obs-down       # Stop monitoring stack

# Management
make obs-restart    # Restart all services
make obs-status     # Check service status
make obs-logs       # View monitoring logs

# Data management
make obs-clean      # Delete all monitoring data (WARNING)
```

## Quick Examples

### View Request Rate

**Grafana**:
1. Open http://localhost:3001
2. Go to "Copilotos Bridge API" dashboard
3. See "Request Rate" panel

**Prometheus Query**:
```promql
rate(copilotos_requests_total[5m])
```

### Query Logs

**Grafana Explore**:
```logql
# All API errors
{service="api"} |= "error"

# Research operations
{service="api"} |= "research"

# POST requests
{container="copilotos-api"} |= "POST"
```

### Check Container Resources

Open http://localhost:8080 to see cAdvisor's real-time container metrics.

## Security Notes

⚠️ **Important for Production**:

1. **Change default password**: Grafana defaults to `admin/admin`
2. **Don't expose ports**: Keep 3001, 9090, 8080 internal
3. **Use reverse proxy**: Put Grafana behind nginx/traefik with auth
4. **Enable HTTPS**: Use SSL certificates

[→ Production security guide](./production.md#security)

## Troubleshooting

### Prometheus Not Scraping

```bash
# Check API metrics endpoint
curl http://localhost:8001/api/metrics

# Check Prometheus targets
open http://localhost:9090/targets
```

### Grafana Shows No Data

1. Check time range (top right corner)
2. Test datasource: Configuration → Data Sources → Prometheus → Test
3. Verify Prometheus is running: `docker ps | grep prometheus`

[→ Full troubleshooting guide](./troubleshooting.md)

## Support

- **Issues**: Check [troubleshooting guide](./troubleshooting.md)
- **Metrics**: See [metrics reference](./metrics.md)
- **Configuration**: See [setup guide](./setup.md)

## Next Steps

1. **Start monitoring**: `make obs-up`
2. **Open Grafana**: http://localhost:3001 (admin/admin)
3. **View dashboard**: Dashboards → Copilotos Bridge API
4. **Explore logs**: Use Grafana Explore with Loki datasource
5. **Customize**: Add your own dashboards and alerts

---

**Status**: ✅ Ready for production use
**Overhead**: Minimal (~1.5 GB RAM, ~2 GB disk)
**Configuration**: Complete, no additional setup required
