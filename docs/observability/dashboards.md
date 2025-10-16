# Grafana Dashboards Guide

Complete guide to using Grafana dashboards for monitoring Copilotos Bridge.

---

## Accessing Grafana

1. **Start monitoring**: `make obs-up`
2. **Open browser**: http://localhost:3001
3. **Login**:
   - Username: `admin`
   - Password: `admin`
4. **(Optional)** Skip password change for local development

---

## Pre-built Dashboards

### Copilotos Bridge API Dashboard

**Location**: Dashboards → Copilotos Bridge → Copilotos Bridge API

**Panels**:

#### 1. Request Rate (req/s)
- **Type**: Stat panel
- **Metric**: `rate(copilotos_requests_total[1m])`
- **Shows**: Current requests per second
- **Color**: Green = healthy

#### 2. P95 Latency
- **Type**: Stat panel
- **Metric**: `histogram_quantile(0.95, rate(copilotos_request_duration_seconds_bucket[5m]))`
- **Shows**: 95th percentile response time
- **Thresholds**:
  - Green: <0.5s
  - Yellow: 0.5-1.0s
  - Red: >1.0s

#### 3. Error Rate (5xx)
- **Type**: Stat panel
- **Metric**: `rate(copilotos_requests_total{status=~"5.."}[5m]) / rate(copilotos_requests_total[5m])`
- **Shows**: Percentage of 5xx errors
- **Thresholds**:
  - Green: <1%
  - Yellow: 1-5%
  - Red: >5%

#### 4. Total Requests
- **Type**: Stat panel
- **Metric**: `sum(rate(copilotos_requests_total[5m]))`
- **Shows**: Total request volume

#### 5. Response Time Percentiles
- **Type**: Time series graph
- **Metrics**:
  - P50: `histogram_quantile(0.50, rate(copilotos_request_duration_seconds_bucket[5m]))`
  - P95: `histogram_quantile(0.95, rate(copilotos_request_duration_seconds_bucket[5m]))`
  - P99: `histogram_quantile(0.99, rate(copilotos_request_duration_seconds_bucket[5m]))`
- **Shows**: Response time distribution over time

#### 6. HTTP Status Codes
- **Type**: Stacked time series
- **Metrics**:
  - 2xx: `rate(copilotos_requests_total{status=~"2.."}[1m])`
  - 4xx: `rate(copilotos_requests_total{status=~"4.."}[1m])`
  - 5xx: `rate(copilotos_requests_total{status=~"5.."}[1m])`
- **Shows**: Status code distribution over time

---

## Using Dashboards

### Time Range Selection

**Top right corner** - Select time range:
- Last 5 minutes
- Last 15 minutes
- Last 1 hour
- Last 6 hours
- Last 24 hours
- Custom range

**Refresh**: Auto-refresh every 10s, 30s, 1m, or 5m

### Variables

Dashboards can use variables for filtering. The API dashboard doesn't have variables by default, but you can add them.

### Zoom In

Click and drag on any graph to zoom into a specific time range.

### Panel Menu

Click panel title → More options:
- **View** - Full screen
- **Edit** - Modify panel
- **Share** - Get embed link
- **Explore** - Open in Explore view
- **Inspect** - See raw data

---

## Creating Custom Dashboards

### Method 1: Through UI

1. Click **+** (top right) → **Dashboard**
2. Click **Add visualization**
3. Select **Prometheus** datasource
4. Enter query (e.g., `rate(copilotos_requests_total[5m])`)
5. Configure panel settings
6. Click **Apply**
7. Save dashboard

### Method 2: JSON Import

Create JSON file in `infra/monitoring/grafana/dashboards/`:

```json
{
  "title": "My Custom Dashboard",
  "panels": [
    {
      "id": 1,
      "type": "graph",
      "title": "My Panel",
      "targets": [
        {
          "expr": "rate(copilotos_requests_total[5m])",
          "refId": "A"
        }
      ]
    }
  ]
}
```

Restart Grafana: `docker restart copilotos-grafana`

---

## Useful Panel Queries

### Request Metrics

```promql
# Total requests
sum(rate(copilotos_requests_total[5m]))

# Requests by endpoint
sum by (endpoint) (rate(copilotos_requests_total[5m]))

# Requests by status code
sum by (status_code) (rate(copilotos_requests_total[5m]))

# Success rate
sum(rate(copilotos_requests_total{status_code=~"2.."}[5m])) /
sum(rate(copilotos_requests_total[5m]))
```

### Latency Metrics

```promql
# Average latency
rate(copilotos_request_duration_seconds_sum[5m]) /
rate(copilotos_request_duration_seconds_count[5m])

# P50, P95, P99
histogram_quantile(0.50, rate(copilotos_request_duration_seconds_bucket[5m]))
histogram_quantile(0.95, rate(copilotos_request_duration_seconds_bucket[5m]))
histogram_quantile(0.99, rate(copilotos_request_duration_seconds_bucket[5m]))

# Slow requests (>1s)
rate(copilotos_request_duration_seconds_count[5m]) -
rate(copilotos_request_duration_seconds_bucket{le="1.0"}[5m])
```

### Research Metrics

```promql
# Research throughput
sum(rate(copilotos_research_requests_total[5m]))

# Research by intent
sum by (intent_type) (rate(copilotos_research_requests_total[5m]))

# Failed research
rate(copilotos_research_duration_seconds_count{success="false"}[5m])

# Quality scores
avg(copilotos_research_quality_score)
avg by (research_type) (copilotos_research_quality_score)
```

### System Metrics

```promql
# Active connections
copilotos_active_connections

# Memory usage
copilotos_memory_usage_bytes

# Cache hit rate
sum(rate(copilotos_cache_operations_total{hit="hit"}[5m])) /
sum(rate(copilotos_cache_operations_total[5m]))
```

---

## Explore View

For ad-hoc queries and log exploration.

### Using Explore

1. Click **Explore** (compass icon, left sidebar)
2. Select datasource:
   - **Prometheus** for metrics
   - **Loki** for logs

### Metrics (Prometheus)

**Example queries**:
```promql
# See all metrics
{__name__=~"copilotos_.*"}

# Specific metric
copilotos_requests_total

# With filters
copilotos_requests_total{endpoint="/api/chat",status_code="200"}

# Rate over time
rate(copilotos_requests_total[5m])
```

### Logs (Loki)

**Example queries**:
```logql
# All API logs
{service="api"}

# Error logs only
{service="api"} |= "error"

# Research logs
{service="api"} |= "research"

# POST requests
{container="copilotos-api"} |= "POST"

# Exclude health checks
{service="api"} != "/health"

# Regex filter
{service="api"} |~ "error|exception|fail"

# Rate of errors
rate({service="api"} |= "error" [5m])
```

**LogQL operators**:
- `|=` - Contains
- `!=` - Does not contain
- `|~` - Regex match
- `!~` - Regex not match
- `| json` - Parse JSON
- `| logfmt` - Parse logfmt

---

## Dashboard Best Practices

### Layout

- **Top row**: High-level KPIs (request rate, latency, errors)
- **Middle rows**: Detailed metrics by dimension
- **Bottom rows**: System metrics (memory, connections)

### Panel Design

- **Use appropriate visualization**:
  - Stat panels for single values
  - Time series for trends
  - Bar charts for comparisons
  - Heatmaps for distributions

- **Set meaningful thresholds**:
  - Green: Everything is fine
  - Yellow: Warning, investigate
  - Red: Critical, action required

- **Add units**: seconds, bytes, percent, etc.

### Performance

- **Avoid expensive queries**: Use recording rules for complex calculations
- **Limit time range**: Don't query 30 days by default
- **Use rate()**: For counters, always use `rate()` or `increase()`

### Annotations

Add events to dashboards:
- Deployments
- Configuration changes
- Incidents
- Scaling events

---

## Sharing Dashboards

### Snapshot

1. Click **Share** (top right)
2. Select **Snapshot** tab
3. Choose expiration
4. Click **Publish to snapshot**
5. Copy URL

### Export JSON

1. Dashboard settings (gear icon)
2. **JSON Model** tab
3. Copy JSON
4. Save to file

### Embed Panel

1. Click panel title → **Share**
2. **Link** tab
3. Copy URL
4. Or use **Embed** for iframe code

---

## Alerting (Grafana 10+)

### Create Alert Rule

1. Open dashboard panel
2. Click panel title → **More** → **New alert rule**
3. Define query and conditions
4. Set evaluation interval
5. Configure notification channel
6. Save

### Example Alert

**High Error Rate**:
- **Query**: `rate(copilotos_requests_total{status_code=~"5.."}[5m]) / rate(copilotos_requests_total[5m]) > 0.05`
- **Condition**: Above 0.05 (5%) for 5 minutes
- **Notification**: Slack, Email, PagerDuty

---

## Troubleshooting

### Dashboard Shows "No Data"

1. **Check time range** - Extend to last 24h
2. **Check datasource** - Configuration → Data Sources → Test
3. **Check query** - Use Explore to test query directly
4. **Check Prometheus** - Visit http://localhost:9090

### Panel Not Updating

1. **Check refresh** - Set auto-refresh (top right)
2. **Check time range** - Use relative time (e.g., "Last 5m")
3. **Manually refresh** - Click refresh button

### Slow Dashboard

1. **Reduce query complexity** - Simplify PromQL expressions
2. **Limit time range** - Don't query months of data
3. **Use recording rules** - Pre-compute expensive queries in Prometheus
4. **Reduce panel count** - Split into multiple dashboards

### Can't Edit Dashboard

**Reason**: Dashboard is provisioned (read-only)

**Solution**:
1. Click **Save As** (top right)
2. Give new name
3. Save to different folder
4. Edit the copy

Or edit JSON file in `infra/monitoring/grafana/dashboards/` and restart Grafana.

---

## Next Steps

- [View metrics reference](./metrics.md) for all available metrics
- [Setup alerts](./production.md#alerting) for production monitoring
- [Explore logs](./README.md#query-logs) with Loki
- [Troubleshooting guide](./troubleshooting.md) for common issues
