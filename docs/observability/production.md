# Production Deployment Guide

Best practices for deploying the observability stack in production.

---

## Production Checklist

### Security

- [ ] Change Grafana admin password
- [ ] Set up reverse proxy with authentication
- [ ] Enable HTTPS/TLS
- [ ] Restrict network access to monitoring ports
- [ ] Configure firewall rules
- [ ] Enable audit logging
- [ ] Set up SSO/OAuth (optional)

### Reliability

- [ ] Configure persistent storage
- [ ] Set up backup strategy
- [ ] Configure appropriate retention periods
- [ ] Set resource limits
- [ ] Enable health checks
- [ ] Configure restart policies
- [ ] Test disaster recovery

### Monitoring

- [ ] Configure alerting rules
- [ ] Set up notification channels
- [ ] Define SLOs and SLIs
- [ ] Create runbooks for alerts
- [ ] Set up on-call rotation
- [ ] Configure escalation policies

### Performance

- [ ] Tune scrape intervals
- [ ] Configure recording rules
- [ ] Set up remote storage (optional)
- [ ] Optimize query performance
- [ ] Enable query caching
- [ ] Monitor monitoring stack itself

---

## Security

### Change Default Passwords

**Grafana**:

```bash
# Method 1: Via environment variable
# Edit docker-compose.resources.yml
grafana:
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=your_secure_password_here
```

```bash
# Method 2: Via CLI
docker exec -it copilotos-grafana \
  grafana-cli admin reset-admin-password 'your_secure_password'
```

### Reverse Proxy Setup

**nginx example**:

```nginx
server {
    listen 443 ssl;
    server_name grafana.example.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    location / {
        proxy_pass http://localhost:3001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Basic auth (optional)
        auth_basic "Restricted";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }
}
```

### Restrict Port Access

**Don't expose monitoring ports to public internet**:

Edit `infra/docker-compose.resources.yml`:

```yaml
grafana:
  ports:
    - "127.0.0.1:3001:3000"  # Only localhost can access

prometheus:
  # Remove ports section entirely for internal-only access
  # Access via reverse proxy only
```

### Enable OAuth/SSO

**Grafana with GitHub OAuth**:

```yaml
grafana:
  environment:
    - GF_AUTH_GITHUB_ENABLED=true
    - GF_AUTH_GITHUB_CLIENT_ID=${GITHUB_CLIENT_ID}
    - GF_AUTH_GITHUB_CLIENT_SECRET=${GITHUB_CLIENT_SECRET}
    - GF_AUTH_GITHUB_ALLOWED_ORGANIZATIONS=your-org
```

---

## Persistent Storage

### Volume Backup Strategy

**1. Regular backups**:

```bash
#!/bin/bash
# backup-monitoring.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/monitoring"

# Backup Prometheus data
docker run --rm \
  -v copilotos_prometheus_data:/data \
  -v $BACKUP_DIR:/backup \
  alpine tar czf /backup/prometheus-$DATE.tar.gz /data

# Backup Grafana dashboards
docker run --rm \
  -v copilotos_grafana_data:/data \
  -v $BACKUP_DIR:/backup \
  alpine tar czf /backup/grafana-$DATE.tar.gz /data

# Keep only last 7 days
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
```

**2. Schedule with cron**:

```cron
# Backup every day at 3 AM
0 3 * * * /opt/scripts/backup-monitoring.sh
```

### Remote Storage (Optional)

For long-term metric storage, configure Prometheus remote write:

```yaml
# prometheus.yml
remote_write:
  - url: "https://prometheus-remote-storage.example.com/api/v1/write"
    basic_auth:
      username: user
      password: pass
```

Options:
- **Thanos** - Open source long-term storage
- **Cortex** - Multi-tenant Prometheus
- **VictoriaMetrics** - Fast, cost-effective storage
- **Grafana Cloud** - Managed service

---

## Retention Policy

### Balancing Storage and History

**Considerations**:
- Disk space available
- Query performance (more data = slower queries)
- Compliance requirements
- Typical analysis patterns

**Recommended retention**:
- **Development**: 3-7 days
- **Staging**: 7-14 days
- **Production**: 15-30 days
- **Long-term storage**: Use remote write

### Configure Retention

**Prometheus**:

```yaml
prometheus:
  command:
    - '--storage.tsdb.retention.time=30d'
    - '--storage.tsdb.retention.size=50GB'  # Whichever comes first
```

**Loki**:

```yaml
# loki.yml
limits_config:
  retention_period: 720h  # 30 days
```

---

## Alerting

### Alert Manager Setup

**1. Add Alertmanager to compose**:

```yaml
# docker-compose.resources.yml
alertmanager:
  image: prom/alertmanager:v0.26.0
  container_name: copilotos-alertmanager
  restart: unless-stopped
  volumes:
    - ./monitoring/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
    - alertmanager_data:/alertmanager
  ports:
    - "9093:9093"
  networks:
    - copilotos-network
  profiles:
    - monitoring
```

**2. Configure Prometheus to use it**:

```yaml
# prometheus.yml
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - 'alertmanager:9093'

rule_files:
  - '/etc/prometheus/alerts/*.yml'
```

**3. Create alert rules**:

```yaml
# monitoring/alerts/copilotos.yml
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
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} (threshold: 5%)"

      # High latency
      - alert: HighLatency
        expr: |
          histogram_quantile(0.95,
            rate(copilotos_request_duration_seconds_bucket[5m])
          ) > 1.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High P95 latency"
          description: "P95 latency is {{ $value }}s (threshold: 1s)"

      # Service down
      - alert: ServiceDown
        expr: up{job="copilotos-api"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service is down"
          description: "Copilotos API has been down for more than 1 minute"

      # Research failures
      - alert: ResearchFailuresHigh
        expr: |
          rate(copilotos_research_duration_seconds_count{success="false"}[5m]) > 0.1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High research failure rate"
          description: "Research operations failing at {{ $value }} req/s"

      # External API issues
      - alert: ExternalAPIDown
        expr: |
          sum(rate(copilotos_external_api_calls_total{status="success"}[5m])) by (service) /
          sum(rate(copilotos_external_api_calls_total[5m])) by (service) < 0.9
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "External API {{ $labels.service }} availability low"
          description: "Availability is {{ $value | humanizePercentage }} (threshold: 90%)"

      # High memory usage
      - alert: HighMemoryUsage
        expr: copilotos_memory_usage_bytes{type="rss"} > 500000000  # 500MB
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value | humanize }}B"
```

**4. Configure notifications**:

```yaml
# monitoring/alertmanager.yml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'
    - match:
        severity: warning
      receiver: 'slack'

receivers:
  - name: 'default'
    email_configs:
      - to: 'team@example.com'
        from: 'alerts@example.com'
        smarthost: 'smtp.example.com:587'
        auth_username: 'alerts@example.com'
        auth_password: '${SMTP_PASSWORD}'

  - name: 'slack'
    slack_configs:
      - api_url: '${SLACK_WEBHOOK_URL}'
        channel: '#alerts'
        title: 'Copilotos Alert'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}\n{{ end }}'

  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: '${PAGERDUTY_SERVICE_KEY}'
```

---

## Resource Tuning

### Production Resource Limits

```yaml
# docker-compose.resources.yml
services:
  prometheus:
    deploy:
      resources:
        limits:
          cpus: '2.0'      # Increase for production
          memory: 2G       # 2GB for larger datasets
        reservations:
          cpus: '0.5'
          memory: 512M

  grafana:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 128M

  loki:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G       # 1GB for log storage
        reservations:
          cpus: '0.25'
          memory: 256M
```

### Scrape Interval Optimization

**Balance freshness vs. load**:

```yaml
# prometheus.yml
global:
  scrape_interval: 30s      # Production: 30s-60s
  evaluation_interval: 30s

scrape_configs:
  - job_name: 'copilotos-api'
    scrape_interval: 15s    # Critical services: 15s
    static_configs:
      - targets: ['api:8001']

  - job_name: 'cadvisor'
    scrape_interval: 60s    # Container metrics: 60s
    static_configs:
      - targets: ['cadvisor:8080']
```

### Recording Rules

Pre-compute expensive queries:

```yaml
# monitoring/rules/recordings.yml
groups:
  - name: copilotos_recordings
    interval: 15s
    rules:
      # Request rate by endpoint
      - record: copilotos:requests:rate5m
        expr: sum by (endpoint) (rate(copilotos_requests_total[5m]))

      # Error rate
      - record: copilotos:error_rate:rate5m
        expr: |
          sum(rate(copilotos_requests_total{status_code=~"5.."}[5m])) /
          sum(rate(copilotos_requests_total[5m]))

      # P95 latency
      - record: copilotos:latency:p95
        expr: |
          histogram_quantile(0.95,
            rate(copilotos_request_duration_seconds_bucket[5m])
          )
```

Use in dashboards:
```promql
# Instead of complex histogram_quantile
copilotos:latency:p95
```

---

## High Availability (Optional)

### Prometheus HA

Run multiple Prometheus instances:

```yaml
prometheus-1:
  image: prom/prometheus:v2.48.0
  # ... config

prometheus-2:
  image: prom/prometheus:v2.48.0
  # ... same config
```

Use Thanos or Cortex for deduplication.

### Grafana HA

Use external database:

```yaml
grafana:
  environment:
    - GF_DATABASE_TYPE=postgres
    - GF_DATABASE_HOST=postgres:5432
    - GF_DATABASE_NAME=grafana
    - GF_DATABASE_USER=grafana
    - GF_DATABASE_PASSWORD=${DB_PASSWORD}
```

Run multiple Grafana instances behind load balancer.

---

## Monitoring the Monitoring

Monitor your observability stack itself:

```promql
# Prometheus health
up{job="prometheus"}

# Prometheus storage
prometheus_tsdb_storage_blocks_bytes
prometheus_tsdb_head_series

# Grafana health
grafana_api_response_status_total

# Loki ingestion
loki_ingester_streams_created_total
rate(loki_request_duration_seconds_count[5m])
```

---

## Disaster Recovery

### Backup Strategy

1. **Automated daily backups** (see Persistent Storage section)
2. **Off-site storage** (S3, cloud storage)
3. **Retention**: Keep 30 days of backups
4. **Test restores** monthly

### Recovery Procedure

**1. Restore Prometheus data**:

```bash
# Stop Prometheus
docker stop copilotos-prometheus

# Restore from backup
docker run --rm \
  -v copilotos_prometheus_data:/data \
  -v /backups/monitoring:/backup \
  alpine sh -c "rm -rf /data/* && tar xzf /backup/prometheus-20250114.tar.gz -C /"

# Start Prometheus
docker start copilotos-prometheus
```

**2. Restore Grafana**:

```bash
docker stop copilotos-grafana

docker run --rm \
  -v copilotos_grafana_data:/data \
  -v /backups/monitoring:/backup \
  alpine sh -c "rm -rf /data/* && tar xzf /backup/grafana-20250114.tar.gz -C /"

docker start copilotos-grafana
```

### RTO/RPO Targets

- **RTO** (Recovery Time Objective): < 1 hour
- **RPO** (Recovery Point Objective): < 24 hours

---

## Cost Optimization

### Storage Costs

**Reduce retention**:
- Production: 15-30 days
- Non-production: 7 days

**Compress old data**:
```yaml
prometheus:
  command:
    - '--storage.tsdb.min-block-duration=2h'
    - '--storage.tsdb.max-block-duration=2h'
```

**Use cheaper storage tiers** for backups (S3 Glacier, etc.)

### Compute Costs

**Reduce scrape frequency**:
- Non-critical metrics: 60s interval
- Use recording rules for expensive queries

**Right-size resources**:
- Start with limits, monitor actual usage
- Adjust based on P95 utilization

---

## Compliance and Audit

### Audit Logging

Enable audit logs in Grafana:

```yaml
grafana:
  environment:
    - GF_LOG_LEVEL=info
    - GF_LOG_FILTERS=alerting.notifier:debug
```

### Data Retention Policies

Configure to meet compliance requirements:
- GDPR: Document data retention
- HIPAA: Encrypt at rest and in transit
- SOC 2: Audit access logs

### Access Control

**Grafana RBAC**:
- Admin: Full access
- Editor: Edit dashboards
- Viewer: Read-only

Configure in Grafana UI: Configuration → Users

---

## Next Steps

- [Review metrics](./metrics.md) to understand what's monitored
- [Setup dashboards](./dashboards.md) for visualization
- [Troubleshooting guide](./troubleshooting.md) for common issues
- [Architecture overview](./architecture.md) for system design
