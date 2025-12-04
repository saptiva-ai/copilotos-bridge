# ETL Scheduler Setup - BankAdvisor

**Status:** ✅ Implementado (Semi-automático)
**Fecha:** 2025-11-29

---

## 🎯 Objetivo

Automatizar la ejecución diaria del ETL con:
- ✅ Ejecución programada (cron/systemd)
- ✅ Logging estructurado
- ✅ Tracking de ejecuciones (tabla `etl_runs`)
- ✅ Healthcheck con `last_etl_run`

---

## 📁 Archivos Creados

| Archivo | Descripción |
|---------|-------------|
| `src/bankadvisor/models/etl_run.py` | Modelo SQLAlchemy para tracking |
| `src/bankadvisor/etl_runner.py` | Wrapper con logging + tracking |
| `src/bankadvisor/__main__.py` | CLI entry point |

---

## 🚀 Ejecución Manual (Testing)

### Desde el contenedor Docker

```bash
# Ejecutar ETL manualmente
docker exec -it bank-advisor-mcp python -m bankadvisor.etl_runner

# Ver logs en tiempo real
docker logs -f bank-advisor-mcp
```

### Desde el host (desarrollo local)

```bash
cd plugins/bank-advisor-private
.venv/bin/python -m bankadvisor.etl_runner
```

### Verificar ejecución en /health

```bash
curl http://localhost:8001/health | jq .etl
```

**Output esperado:**
```json
{
  "etl": {
    "last_run_id": 1,
    "last_run_started": "2025-11-29T02:00:01Z",
    "last_run_completed": "2025-11-29T02:03:45Z",
    "last_run_status": "success",
    "last_run_duration_seconds": 224.3,
    "last_run_rows": 1248
  }
}
```

---

## ⏰ Opción 1: Cron (Sistema Host)

**Ventajas:**
- Simple, visible, fácil de debuggear
- No depende del ciclo de vida del contenedor
- Estándar de facto en Linux

**Desventajas:**
- No se ve "desde el código" (configuración externa)

### Setup con Cron

1. **Editar crontab del usuario:**

```bash
crontab -e
```

2. **Agregar línea para ejecutar a las 2:00 AM diariamente:**

```cron
# BankAdvisor ETL - Runs daily at 2:00 AM
0 2 * * * docker exec bank-advisor-mcp python -m bankadvisor.etl_runner --cron >> /var/log/bankadvisor-etl.log 2>&1
```

3. **Verificar crontab:**

```bash
crontab -l | grep bankadvisor
```

4. **Ver logs:**

```bash
tail -f /var/log/bankadvisor-etl.log
```

### Ejemplo de Output en Logs

```
2025-11-29T02:00:01Z etl_runner.main.started triggered_by=cron
2025-11-29T02:00:01Z etl.started run_id=5 triggered_by=cron
2025-11-29T02:00:02Z etl.phase.base.started run_id=5
2025-11-29T02:01:45Z etl.phase.base.completed run_id=5 rows_processed=1248
2025-11-29T02:01:45Z etl.phase.enhanced.started run_id=5
2025-11-29T02:03:44Z etl.phase.enhanced.completed run_id=5 icap_rows=624 tda_rows=312 tasas_rows=1856
2025-11-29T02:03:45Z etl.completed run_id=5 status=success duration_seconds=224.3
```

---

## ⏰ Opción 2: Systemd Timer (Más robusto)

**Ventajas:**
- Mejor manejo de reintentos y dependencias
- Integración con journalctl
- Persistencia entre reboots

**Desventajas:**
- Más complejo de configurar

### Setup con Systemd

1. **Crear servicio: `/etc/systemd/system/bankadvisor-etl.service`**

```ini
[Unit]
Description=BankAdvisor ETL Pipeline
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
User=root
ExecStart=/usr/bin/docker exec bank-advisor-mcp python -m bankadvisor.etl_runner --cron
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

2. **Crear timer: `/etc/systemd/system/bankadvisor-etl.timer`**

```ini
[Unit]
Description=BankAdvisor ETL Daily Schedule
Requires=bankadvisor-etl.service

[Timer]
# Run daily at 2:00 AM
OnCalendar=daily
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

3. **Activar timer:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable bankadvisor-etl.timer
sudo systemctl start bankadvisor-etl.timer
```

4. **Verificar status:**

```bash
# Ver próxima ejecución
sudo systemctl list-timers | grep bankadvisor

# Ver logs de última ejecución
sudo journalctl -u bankadvisor-etl.service -n 100
```

---

## ⏰ Opción 3: APScheduler (Dentro del contenedor)

**⚠️ NO RECOMENDADO para este proyecto** porque:
- Agrega complejidad innecesaria
- Si el proceso FastAPI se cae, se pierde el scheduler
- Dificulta debugging (mezclado con logs de la app)

**Para demo es preferible cron/systemd** porque:
- Es visible y fácil de explicar
- Se puede mostrar el crontab como "evidencia"
- Es más honesto (no pretendemos tener un microservicio completo)

---

## 📊 Monitoreo del ETL

### 1. Consultar historial de ejecuciones

```sql
SELECT
    id,
    started_at,
    completed_at,
    status,
    duration_seconds,
    rows_processed_base,
    error_message
FROM etl_runs
ORDER BY started_at DESC
LIMIT 10;
```

### 2. Ver última ejecución exitosa

```sql
SELECT
    started_at,
    duration_seconds,
    rows_processed_base
FROM etl_runs
WHERE status = 'success'
ORDER BY started_at DESC
LIMIT 1;
```

### 3. Detectar fallos recientes

```sql
SELECT
    id,
    started_at,
    error_message
FROM etl_runs
WHERE status = 'failure'
  AND started_at > NOW() - INTERVAL '7 days'
ORDER BY started_at DESC;
```

---

## 🧪 Testing del Sistema

### Test 1: Ejecución manual

```bash
docker exec -it bank-advisor-mcp python -m bankadvisor.etl_runner
```

**Resultado esperado:**
- Logs estructurados en STDOUT
- Registro en tabla `etl_runs` con `status='success'`
- `/health` muestra el nuevo run

### Test 2: Simular fallo

```bash
# Renombrar archivo de datos para forzar error
docker exec -it bank-advisor-mcp mv /app/data/raw/CNBV_Datos.xlsx /app/data/raw/CNBV_Datos.bak

# Ejecutar ETL (debería fallar)
docker exec -it bank-advisor-mcp python -m bankadvisor.etl_runner

# Verificar que se registró el error
curl http://localhost:8001/health | jq .etl.last_run_status
# Output: "failure"

# Restaurar archivo
docker exec -it bank-advisor-mcp mv /app/data/raw/CNBV_Datos.bak /app/data/raw/CNBV_Datos.xlsx
```

### Test 3: Verificar healthcheck

```bash
# Healthcheck debe mostrar ETL info
curl http://localhost:8001/health

# Verificar que retorna 200 OK
echo $?  # Debe ser 0
```

---

## 📝 Logging Estructurado

El ETL runner usa `structlog` para generar logs JSON parseables:

```json
{
  "event": "etl.completed",
  "run_id": 5,
  "status": "success",
  "duration_seconds": 224.3,
  "rows_base": 1248,
  "rows_icap": 624,
  "rows_tda": 312,
  "rows_tasas": 1856,
  "timestamp": "2025-11-29T02:03:45Z"
}
```

**Ventajas:**
- Fácil de parsear con `jq`, `grep`, `awk`
- Compatible con herramientas de observabilidad (Datadog, CloudWatch, etc.)
- Debuggeable en caso de errores

---

## 🎬 Script de Demo para el 3 de Diciembre

### Demostración del ETL Automático

**1. Mostrar el healthcheck:**

```bash
curl http://localhost:8001/health | jq .etl
```

**Decir:**
> "Como pueden ver, el ETL se ejecuta automáticamente todos los días a las 2:00 AM. La última ejecución fue el [fecha] y procesó [X] registros en [Y] segundos."

**2. Mostrar el crontab (opcional):**

```bash
crontab -l | grep bankadvisor
```

**Decir:**
> "El scheduler está configurado con cron, que es el estándar de facto en producción Linux. Simple, confiable, y fácil de monitorear."

**3. Mostrar historial de ejecuciones:**

```sql
SELECT
    id,
    DATE(started_at) as fecha,
    status,
    ROUND(duration_seconds::numeric, 1) as duracion_seg,
    rows_processed_base as filas
FROM etl_runs
ORDER BY started_at DESC
LIMIT 5;
```

**Decir:**
> "Tenemos un historial completo de todas las ejecuciones del ETL, con métricas de duración y filas procesadas. Esto nos permite monitorear la salud del pipeline."

---

## 🚨 Troubleshooting

### Error: "ModuleNotFoundError: No module named 'bankadvisor'"

**Causa:** El contenedor no tiene el código montado o el PYTHONPATH no está configurado.

**Solución:**
```bash
# Verificar que el código esté montado
docker exec bank-advisor-mcp ls -la /app/plugins/bank-advisor-private/src

# Verificar PYTHONPATH
docker exec bank-advisor-mcp env | grep PYTHON
```

### Error: "relation 'etl_runs' does not exist"

**Causa:** La tabla `etl_runs` no se ha creado.

**Solución:**
```bash
# Ejecutar ETL una vez para crear la tabla
docker exec -it bank-advisor-mcp python -m bankadvisor.etl_runner
```

La función `ensure_etl_runs_table_exists()` se encarga de crear la tabla automáticamente.

### Error: Cron no ejecuta el comando

**Causa:** Variables de entorno no disponibles en cron.

**Solución:**
```cron
# Agregar PATH completo
PATH=/usr/local/bin:/usr/bin:/bin
0 2 * * * docker exec bank-advisor-mcp python -m bankadvisor.etl_runner --cron >> /var/log/bankadvisor-etl.log 2>&1
```

---

## ✅ Checklist de Implementación

- [x] Crear modelo `ETLRun` para tracking
- [x] Crear `etl_runner.py` con logging estructurado
- [x] Crear CLI ejecutable con `python -m`
- [x] Modificar `/health` endpoint para mostrar `last_etl_run`
- [ ] Configurar cron en servidor de demo
- [ ] Ejecutar ETL inicial para poblar `etl_runs`
- [ ] Validar healthcheck muestra info correcta
- [ ] Documentar en guion de demo

---

## 📚 Referencias

- [Cron Syntax](https://crontab.guru/)
- [Systemd Timers](https://www.freedesktop.org/software/systemd/man/systemd.timer.html)
- [structlog Documentation](https://www.structlog.org/)

---

**Status Final:** ✅ **LISTO PARA CONFIGURAR EN SERVIDOR DE DEMO**

El ETL ahora es semi-automático: se ejecuta vía cron/systemd, con logging estructurado, tracking de ejecuciones, y visible en el healthcheck.

**Para el demo del 3 de diciembre:**
> "Los datos se actualizan automáticamente una vez al día a las 2:00 AM. El último ETL fue exitoso el [fecha], procesando [X] registros en [Y] segundos. Esto lo pueden ver en el endpoint `/health`."
