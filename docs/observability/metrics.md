# Metrics Reference

Complete reference of all Prometheus metrics exposed by Copilotos Bridge.

---

## Endpoint

All metrics are exposed at: **`/api/metrics`**

Format: Prometheus exposition format

---

## Core HTTP Metrics

### `copilotos_requests_total`

**Type**: Counter
**Description**: Total number of HTTP requests received
**Labels**:
- `method` - HTTP method (GET, POST, PUT, DELETE)
- `endpoint` - Request path (e.g., `/api/chat`, `/api/health`)
- `status_code` - HTTP response status code (200, 404, 500, etc.)

**Example**:
```promql
# Request rate by endpoint
rate(copilotos_requests_total[5m])

# Error rate (4xx + 5xx)
rate(copilotos_requests_total{status_code=~"[45].."}[5m])
```

### `copilotos_request_duration_seconds`

**Type**: Histogram
**Description**: HTTP request duration in seconds
**Labels**:
- `method` - HTTP method
- `endpoint` - Request path
**Buckets**: 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0 seconds

**Example**:
```promql
# P95 latency
histogram_quantile(0.95, rate(copilotos_request_duration_seconds_bucket[5m]))

# P99 latency by endpoint
histogram_quantile(0.99,
  rate(copilotos_request_duration_seconds_bucket{endpoint="/api/chat"}[5m])
)
```

---

## Deep Research Metrics

### `copilotos_research_requests_total`

**Type**: Counter
**Description**: Total deep research requests
**Labels**:
- `intent_type` - Type of research intent
- `classification_method` - Method used to classify intent

**Example**:
```promql
# Research requests by intent
sum by (intent_type) (rate(copilotos_research_requests_total[5m]))
```

### `copilotos_research_duration_seconds`

**Type**: Histogram
**Description**: Deep research operation duration
**Labels**:
- `research_phase` - Phase of research (query, search, synthesis, etc.)
- `success` - Whether operation succeeded (true/false)
**Buckets**: 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0 seconds

**Example**:
```promql
# P95 research duration by phase
histogram_quantile(0.95,
  rate(copilotos_research_duration_seconds_bucket[5m])
) by (research_phase)

# Failed research operations
rate(copilotos_research_duration_seconds_count{success="false"}[5m])
```

### `copilotos_research_quality_score`

**Type**: Gauge
**Description**: Research quality score (0-1)
**Labels**:
- `research_type` - Type of research performed

**Example**:
```promql
# Current quality scores
copilotos_research_quality_score

# Average quality by type
avg by (research_type) (copilotos_research_quality_score)
```

### `copilotos_intent_classification_total`

**Type**: Counter
**Description**: Intent classification results
**Labels**:
- `intent_type` - Classified intent type
- `confidence_level` - Confidence level (high, medium, low)
- `method` - Classification method used

**Example**:
```promql
# Classification rate by confidence
sum by (confidence_level) (rate(copilotos_intent_classification_total[5m]))

# Low confidence classifications (potential issues)
rate(copilotos_intent_classification_total{confidence_level="low"}[5m])
```

---

## Performance Metrics

### `copilotos_active_connections`

**Type**: Gauge
**Description**: Number of currently active HTTP connections

**Example**:
```promql
# Current active connections
copilotos_active_connections

# Peak connections in last hour
max_over_time(copilotos_active_connections[1h])
```

### `copilotos_memory_usage_bytes`

**Type**: Gauge
**Description**: Memory usage in bytes
**Labels**:
- `type` - Memory type (heap, rss, etc.)

**Example**:
```promql
# Current memory usage
copilotos_memory_usage_bytes

# Memory usage trend
rate(copilotos_memory_usage_bytes[5m])
```

### `copilotos_cache_operations_total`

**Type**: Counter
**Description**: Cache operations count
**Labels**:
- `operation` - Operation type (get, set, delete)
- `backend` - Cache backend (redis, memory)
- `hit` - Whether operation was a hit or miss

**Example**:
```promql
# Cache hit rate
sum(rate(copilotos_cache_operations_total{hit="hit"}[5m])) /
sum(rate(copilotos_cache_operations_total[5m]))

# Cache misses by backend
rate(copilotos_cache_operations_total{hit="miss"}[5m]) by (backend)
```

---

## Error Tracking

### `copilotos_errors_total`

**Type**: Counter
**Description**: Total application errors
**Labels**:
- `error_type` - Error class name
- `endpoint` - Endpoint where error occurred
- `severity` - Error severity (error, warning, critical)

**Example**:
```promql
# Error rate by type
sum by (error_type) (rate(copilotos_errors_total[5m]))

# Critical errors
rate(copilotos_errors_total{severity="critical"}[5m])

# Errors by endpoint
topk(5,
  sum by (endpoint) (rate(copilotos_errors_total[5m]))
)
```

---

## Business Metrics

### `copilotos_active_user_sessions`

**Type**: Gauge
**Description**: Number of active user sessions

**Example**:
```promql
# Current active sessions
copilotos_active_user_sessions

# Peak sessions today
max_over_time(copilotos_active_user_sessions[24h])
```

### `copilotos_rate_limit_hits_total`

**Type**: Counter
**Description**: Rate limit violations
**Labels**:
- `endpoint` - Rate-limited endpoint
- `user_id` - User who hit rate limit

**Example**:
```promql
# Rate limit violations
sum(rate(copilotos_rate_limit_hits_total[5m])) by (endpoint)

# Users hitting rate limits
count by (user_id) (copilotos_rate_limit_hits_total)
```

### `copilotos_external_api_calls_total`

**Type**: Counter
**Description**: External API calls
**Labels**:
- `service` - External service name
- `endpoint` - API endpoint called
- `status` - Call status (success, error)

**Example**:
```promql
# External API call rate
sum by (service) (rate(copilotos_external_api_calls_total[5m]))

# Failed external calls
rate(copilotos_external_api_calls_total{status="error"}[5m])
```

### `copilotos_external_api_duration_seconds`

**Type**: Histogram
**Description**: External API call duration
**Labels**:
- `service` - External service name
- `endpoint` - API endpoint called
**Buckets**: 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0 seconds

**Example**:
```promql
# P95 external API latency
histogram_quantile(0.95,
  rate(copilotos_external_api_duration_seconds_bucket[5m])
) by (service)

# Slow external calls (>5s)
rate(copilotos_external_api_duration_seconds_count{le="5"}[5m])
```

---

## Document Ingestion Metrics

### `copilotos_pdf_ingest_seconds`

**Type**: Histogram
**Description**: PDF ingestion phase duration
**Labels**:
- `phase` - Ingestion phase (extract, parse, chunk, embed, index)
**Buckets**: 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 13.0, 21.0 seconds

**Example**:
```promql
# P95 ingestion time by phase
histogram_quantile(0.95,
  rate(copilotos_pdf_ingest_seconds_bucket[5m])
) by (phase)

# Slowest ingestion phase
max by (phase) (
  histogram_quantile(0.95,
    rate(copilotos_pdf_ingest_seconds_bucket[5m])
  )
)
```

### `copilotos_pdf_ingest_errors_total`

**Type**: Counter
**Description**: PDF ingestion errors
**Labels**:
- `code` - Error code (parse_failed, too_large, invalid_format, etc.)

**Example**:
```promql
# Ingestion error rate
sum by (code) (rate(copilotos_pdf_ingest_errors_total[5m]))

# Most common ingestion errors
topk(3, sum by (code) (copilotos_pdf_ingest_errors_total))
```

---

## Tool Usage Metrics

### `copilotos_tool_invocations_total`

**Type**: Counter
**Description**: Tool invocations by tool key
**Labels**:
- `tool` - Tool identifier

**Example**:
```promql
# Tool usage rate
sum by (tool) (rate(copilotos_tool_invocations_total[5m]))

# Most used tools
topk(5, sum by (tool) (copilotos_tool_invocations_total))
```

### `copilotos_tool_toggle_total`

**Type**: Counter
**Description**: Tool enable/disable events
**Labels**:
- `tool` - Tool identifier
- `state` - New state (enabled, disabled)

**Example**:
```promql
# Tool toggles
sum by (tool, state) (copilotos_tool_toggle_total)

# Recently disabled tools
increase(copilotos_tool_toggle_total{state="disabled"}[1h])
```

### `copilotos_tool_call_blocked_total`

**Type**: Counter
**Description**: Blocked tool invocation attempts
**Labels**:
- `tool` - Tool identifier
- `reason` - Block reason (disabled, rate_limit, permission, etc.)

**Example**:
```promql
# Blocked tool calls
sum by (tool, reason) (rate(copilotos_tool_call_blocked_total[5m]))

# Most blocked tool
topk(1, sum by (tool) (copilotos_tool_call_blocked_total))
```

### `copilotos_planner_tool_suggested_total`

**Type**: Counter
**Description**: Planner tool suggestion events
**Labels**:
- `tool` - Suggested tool

**Example**:
```promql
# Tool suggestions
sum by (tool) (rate(copilotos_planner_tool_suggested_total[5m]))

# Suggestion vs actual usage ratio
sum by (tool) (rate(copilotos_planner_tool_suggested_total[5m])) /
sum by (tool) (rate(copilotos_tool_invocations_total[5m]))
```

---

## Useful Queries

### Service Health

```promql
# Overall request rate
sum(rate(copilotos_requests_total[5m]))

# Success rate
sum(rate(copilotos_requests_total{status_code=~"2.."}[5m])) /
sum(rate(copilotos_requests_total[5m]))

# Error budget (99.9% target)
1 - (
  sum(rate(copilotos_requests_total{status_code=~"[45].."}[5m])) /
  sum(rate(copilotos_requests_total[5m]))
)
```

### Performance

```promql
# P50, P95, P99 latency
histogram_quantile(0.50, rate(copilotos_request_duration_seconds_bucket[5m]))
histogram_quantile(0.95, rate(copilotos_request_duration_seconds_bucket[5m]))
histogram_quantile(0.99, rate(copilotos_request_duration_seconds_bucket[5m]))

# Requests exceeding SLO (>1s)
rate(copilotos_request_duration_seconds_count[5m]) -
rate(copilotos_request_duration_seconds_bucket{le="1.0"}[5m])
```

### Research Operations

```promql
# Research throughput
sum(rate(copilotos_research_requests_total[5m]))

# Average quality score
avg(copilotos_research_quality_score)

# Failed research rate
sum(rate(copilotos_research_duration_seconds_count{success="false"}[5m])) /
sum(rate(copilotos_research_duration_seconds_count[5m]))
```

### External Dependencies

```promql
# External API availability
sum(rate(copilotos_external_api_calls_total{status="success"}[5m])) by (service) /
sum(rate(copilotos_external_api_calls_total[5m])) by (service)

# Slowest external service
max by (service) (
  histogram_quantile(0.95,
    rate(copilotos_external_api_duration_seconds_bucket[5m])
  )
)
```

---

## Alerting Rules

Suggested alert rules for production:

```yaml
groups:
  - name: copilotos_alerts
    interval: 30s
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: |
          sum(rate(copilotos_requests_total{status_code=~"5.."}[5m])) /
          sum(rate(copilotos_requests_total[5m])) > 0.05
        for: 5m
        annotations:
          summary: "Error rate above 5% for 5 minutes"

      # High latency
      - alert: HighLatency
        expr: |
          histogram_quantile(0.95,
            rate(copilotos_request_duration_seconds_bucket[5m])
          ) > 1.0
        for: 5m
        annotations:
          summary: "P95 latency above 1 second"

      # Research failures
      - alert: ResearchFailures
        expr: |
          rate(copilotos_research_duration_seconds_count{success="false"}[5m]) > 0.1
        for: 10m
        annotations:
          summary: "Research operations failing frequently"

      # External API down
      - alert: ExternalAPIDown
        expr: |
          sum(rate(copilotos_external_api_calls_total{status="success"}[5m])) by (service) /
          sum(rate(copilotos_external_api_calls_total[5m])) by (service) < 0.9
        for: 5m
        annotations:
          summary: "External API {{ $labels.service }} availability below 90%"
```

---

## Next Steps

- [Setup dashboards](./dashboards.md) to visualize these metrics
- [Configure alerts](./production.md#alerting) for production
- [Troubleshoot](./troubleshooting.md) metric collection issues
