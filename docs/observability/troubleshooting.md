# Troubleshooting Guide

Common issues and solutions for the observability stack.

---

## Services Won't Start

### Issue: `make obs-up` fails with "port already in use"

**Error**:
```
Error: bind: address already in use (port 3001/9090/8080)
```

**Solution**:

1. **Check what's using the port**:
   ```bash
   lsof -i :3001  # Check Grafana port
   lsof -i :9090  # Check Prometheus port
   lsof -i :8080  # Check cAdvisor port
   ```

2. **Stop conflicting service** or **change ports**:

   Edit `infra/docker-compose.resources.yml`:
   ```yaml
   grafana:
     ports:
       - "3002:3000"  # Change host port to 3002
   ```

3. **Restart**:
   ```bash
   make obs-restart
   ```

### Issue: Services crash immediately after starting

**Symptoms**:
```bash
make obs-status
# Shows "Exited (1)" or "Restarting"
```

**Solution**:

1. **Check logs**:
   ```bash
   docker logs copilotos-prometheus
   docker logs copilotos-grafana
   docker logs copilotos-loki
   ```

2. **Common causes**:
   - **Invalid configuration**: Check YAML syntax
   - **Permission denied**: Check volume permissions
   - **Out of memory**: Check `docker stats`

3. **Verify configuration**:
   ```bash
   # Test Prometheus config
   docker run --rm -v $(pwd)/infra/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml \
     prom/prometheus:v2.48.0 \
     promtool check config /etc/prometheus/prometheus.yml
   ```

4. **Restart with clean state**:
   ```bash
   make obs-clean  # WARNING: Deletes all data
   make obs-up
   ```

---

## Prometheus Issues

### Issue: Prometheus not scraping API metrics

**Symptoms**:
- Target shows as "DOWN" at http://localhost:9090/targets
- No `copilotos_*` metrics appear

**Solution**:

1. **Check API is exposing metrics**:
   ```bash
   curl http://localhost:8001/api/metrics
   # Should return Prometheus format metrics
   ```

   If fails:
   ```bash
   # Check API is running
   curl http://localhost:8001/api/health

   # Check API container
   docker ps | grep api
   docker logs copilotos-api
   ```

2. **Check network connectivity**:
   ```bash
   # From Prometheus container
   docker exec copilotos-prometheus wget -O- http://api:8001/api/metrics
   ```

   If fails, check Docker network:
   ```bash
   docker network inspect copilotos-network
   # Both prometheus and api containers should be listed
   ```

3. **Verify scrape configuration**:
   ```bash
   cat infra/monitoring/prometheus.yml
   # Ensure:
   # - targets: ['api:8001']
   # - metrics_path: '/api/metrics'  # NOT '/metrics'
   ```

4. **Check Prometheus logs**:
   ```bash
   docker logs copilotos-prometheus 2>&1 | grep -i error
   ```

### Issue: Prometheus running out of disk space

**Symptoms**:
- Prometheus crashes
- Logs show "out of space" errors

**Solution**:

1. **Check current disk usage**:
   ```bash
   docker exec copilotos-prometheus du -sh /prometheus
   ```

2. **Reduce retention period**:

   Edit `infra/docker-compose.resources.yml`:
   ```yaml
   prometheus:
     command:
       - '--storage.tsdb.retention.time=3d'  # Change from 7d to 3d
   ```

3. **Increase disk space** or **clean old data**:
   ```bash
   # Clean old data (WARNING: deletes metrics)
   docker exec copilotos-prometheus rm -rf /prometheus/*
   docker restart copilotos-prometheus
   ```

---

## Grafana Issues

### Issue: Grafana shows "No data" in dashboard

**Symptoms**:
- Panels show "No data"
- Queries return empty results

**Solution**:

1. **Check time range**:
   - Top right corner → Extend to "Last 24 hours"
   - Ensure current time is included

2. **Test datasource**:
   - Configuration → Data Sources → Prometheus
   - Click "Save & Test"
   - Should show green checkmark

3. **Test query in Explore**:
   - Explore (compass icon)
   - Select Prometheus datasource
   - Try simple query: `copilotos_requests_total`
   - If empty, Prometheus isn't scraping (see above)

4. **Check Prometheus is reachable**:
   ```bash
   docker exec copilotos-grafana wget -O- http://prometheus:9090/api/v1/query?query=up
   ```

### Issue: Can't login to Grafana

**Symptoms**:
- "Invalid username or password"

**Solution**:

1. **Use default credentials**:
   - Username: `admin`
   - Password: `admin`

2. **Reset admin password**:
   ```bash
   docker exec -it copilotos-grafana grafana-cli admin reset-admin-password newpassword
   ```

3. **Check Grafana logs**:
   ```bash
   docker logs copilotos-grafana 2>&1 | tail -50
   ```

### Issue: Dashboard is read-only, can't edit

**Reason**: Dashboard is provisioned from JSON file

**Solution**:

**Option 1**: Edit JSON file directly
```bash
# Edit the source file
vim infra/monitoring/grafana/dashboards/copilotos-api.json

# Restart Grafana
docker restart copilotos-grafana
```

**Option 2**: Save a copy
1. Click "Save As" (top right)
2. Give new name
3. Edit the copy (not provisioned)

---

## Loki Issues

### Issue: No logs appearing in Grafana

**Symptoms**:
- Explore → Loki → `{service="api"}` returns no results

**Solution**:

1. **Check Promtail is running**:
   ```bash
   docker ps | grep promtail
   docker logs copilotos-promtail
   ```

2. **Check Promtail can access Docker socket**:
   ```bash
   docker exec copilotos-promtail ls -l /var/run/docker.sock
   # Should show socket file
   ```

3. **Verify container labels**:
   ```bash
   docker inspect copilotos-api | grep com.docker.compose.project
   # Should show: "com.docker.compose.project": "copilotos"
   ```

4. **Check Loki is receiving logs**:
   ```bash
   # Loki metrics endpoint
   curl http://localhost:3100/metrics | grep loki_ingester_streams_created_total
   # Should show non-zero value
   ```

5. **Test Promtail → Loki connection**:
   ```bash
   docker exec copilotos-promtail wget -O- http://loki:3100/ready
   # Should return "ready"
   ```

### Issue: Logs are delayed or missing

**Symptoms**:
- Old logs appear but not recent ones
- 5-10 minute delay

**Solution**:

1. **Check Promtail scrape interval**:
   ```bash
   cat infra/monitoring/promtail.yml | grep refresh_interval
   # Should be 5s (default)
   ```

2. **Restart Promtail**:
   ```bash
   docker restart copilotos-promtail
   ```

3. **Check for errors**:
   ```bash
   docker logs copilotos-promtail 2>&1 | grep -i error
   ```

---

## cAdvisor Issues

### Issue: cAdvisor won't start or crashes

**Error**:
```
failed to start container: failed to create containerd task: OCI runtime create failed
```

**Solution**:

**On some Linux systems**, cAdvisor needs `/dev/kmsg`:

Edit `infra/docker-compose.resources.yml`:
```yaml
cadvisor:
  # Comment out if causing issues:
  # devices:
  #   - /dev/kmsg:/dev/kmsg
```

Or add `privileged: true`:
```yaml
cadvisor:
  privileged: true
```

### Issue: cAdvisor shows no container metrics

**Solution**:

1. **Check cAdvisor web UI**: http://localhost:8080
   - Should list all containers

2. **Verify Docker socket mount**:
   ```bash
   docker inspect copilotos-cadvisor | grep /var/run/docker.sock
   ```

3. **Check cAdvisor logs**:
   ```bash
   docker logs copilotos-cadvisor
   ```

---

## Network Issues

### Issue: Services can't communicate

**Symptoms**:
- Prometheus can't scrape API
- Grafana can't connect to Prometheus
- Promtail can't reach Loki

**Solution**:

1. **Check Docker network exists**:
   ```bash
   docker network ls | grep copilotos
   ```

2. **Verify all services are on the same network**:
   ```bash
   docker network inspect copilotos-network
   # Should list: api, prometheus, grafana, loki, promtail, cadvisor
   ```

3. **Recreate network if needed**:
   ```bash
   make stop
   docker network rm copilotos-network
   docker network create copilotos-network
   make dev
   make obs-up
   ```

4. **Test connectivity between containers**:
   ```bash
   # From prometheus to api
   docker exec copilotos-prometheus ping api

   # From grafana to prometheus
   docker exec copilotos-grafana wget -O- http://prometheus:9090/api/v1/status/config
   ```

---

## Performance Issues

### Issue: High memory usage

**Symptoms**:
- Docker stats shows high memory
- System becomes slow
- OOMKilled errors

**Solution**:

1. **Check current resource usage**:
   ```bash
   docker stats --no-stream | grep copilotos
   ```

2. **Identify culprit**:
   ```bash
   docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}" | grep copilotos | sort -k2 -hr
   ```

3. **Adjust resource limits**:

   Edit `infra/docker-compose.resources.yml`:
   ```yaml
   prometheus:
     deploy:
       resources:
         limits:
           memory: 256M  # Reduce from 512M
   ```

4. **Reduce retention/data**:
   - Reduce Prometheus retention (see above)
   - Reduce Loki retention
   - Clear old data: `make obs-clean`

### Issue: Slow dashboard loading

**Symptoms**:
- Grafana takes 10+ seconds to load
- Queries timeout

**Solution**:

1. **Reduce time range**:
   - Use "Last 1 hour" instead of "Last 24 hours"

2. **Optimize queries**:
   - Add `rate()` or `increase()` to counter queries
   - Use shorter intervals: `[5m]` instead of `[1h]`

3. **Reduce panel count**:
   - Split dashboard into multiple smaller dashboards

4. **Check Prometheus performance**:
   ```bash
   curl http://localhost:9090/metrics | grep prometheus_tsdb
   ```

---

## Data Issues

### Issue: Metrics disappeared

**Symptoms**:
- Historical data is missing
- Gaps in graphs

**Possible causes**:
- Prometheus restarted and lost data (not persisted)
- Volume was deleted
- Retention period expired

**Solution**:

1. **Check Prometheus volume**:
   ```bash
   docker volume ls | grep prometheus
   docker volume inspect copilotos_prometheus_data
   ```

2. **Verify retention**:
   ```bash
   docker exec copilotos-prometheus \
     wget -O- http://localhost:9090/api/v1/status/runtimeinfo | jq '.data.storageRetention'
   ```

3. **Check if volume is properly mounted**:
   ```bash
   docker inspect copilotos-prometheus | grep -A5 Mounts
   ```

### Issue: Duplicate metrics

**Symptoms**:
- Same metric appears multiple times
- Confusing results in Grafana

**Cause**: Multiple Prometheus instances scraping the same target

**Solution**:

1. **Check running Prometheus instances**:
   ```bash
   docker ps | grep prometheus
   ```

2. **Stop duplicates**:
   ```bash
   docker stop <duplicate_container_id>
   ```

---

## Configuration Issues

### Issue: Changes to config files not applied

**Symptoms**:
- Edited `prometheus.yml` but changes don't appear
- Dashboard updates not visible

**Solution**:

1. **Restart the affected service**:
   ```bash
   # For Prometheus config changes
   docker restart copilotos-prometheus

   # For Grafana dashboards
   docker restart copilotos-grafana

   # Or restart all
   make obs-restart
   ```

2. **Verify config was mounted**:
   ```bash
   docker exec copilotos-prometheus cat /etc/prometheus/prometheus.yml
   # Should show your changes
   ```

3. **Check for syntax errors**:
   ```bash
   # For Prometheus
   docker run --rm -v $(pwd)/infra/monitoring/prometheus.yml:/config.yml \
     prom/prometheus:v2.48.0 \
     promtool check config /config.yml
   ```

---

## Getting Help

If issues persist:

1. **Check logs**:
   ```bash
   make obs-logs
   # Or individual service:
   docker logs copilotos-prometheus
   ```

2. **Check resource usage**:
   ```bash
   docker stats --no-stream | grep copilotos
   ```

3. **Verify all services are healthy**:
   ```bash
   make obs-status
   ```

4. **Review configuration**:
   - [Setup guide](./setup.md)
   - [Metrics reference](./metrics.md)
   - [Production guide](./production.md)

5. **Full restart**:
   ```bash
   make obs-down
   make obs-clean  # WARNING: Deletes all data
   make obs-up
   ```

---

## Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `address already in use` | Port conflict | Change port or stop conflicting service |
| `no such host` | Network issue | Check Docker network |
| `permission denied` | Volume permissions | Check file/folder ownership |
| `out of memory` | Resource limit | Increase memory limit or reduce retention |
| `context deadline exceeded` | Timeout | Increase timeout or optimize query |
| `target down` | Service not reachable | Check service is running and network |
| `invalid configuration` | Syntax error | Validate YAML syntax |
| `no data points` | No metrics scraped | Check Prometheus targets |

---

## Next Steps

- [Review metrics](./metrics.md) to understand what's available
- [Check production guide](./production.md) for deployment best practices
- [Return to main guide](./README.md) for overview
