# Maintenance Scripts

Scripts para mantenimiento del sistema, diagnósticos y troubleshooting.

## Scripts Disponibles

### Diagnósticos
- **`quick-diagnostic.sh`** - Diagnóstico rápido completo del sistema
  ```bash
  ./scripts/maintenance/quick-diagnostic.sh
  ```
- **`dev-troubleshoot.sh`** - Solución automatizada de problemas comunes
  ```bash
  ./scripts/maintenance/dev-troubleshoot.sh [cache|ports|permissions|all]
  ```
- **`diagnose-nginx-413.sh`** - Diagnóstico específico de error 413

### Health Checks
- **`health-check.sh`** - Verificación básica de salud de servicios
- **`prod-health-check.sh`** - Health check específico para producción

### Limpieza & Optimización
- **`docker-cleanup.sh`** - Limpieza de Docker (imágenes, volúmenes, contenedores)
- **`cleanup-server.sh`** - Limpieza general del servidor
- **`cleanup-duplicate-drafts.py`** - Limpiar drafts duplicados (DB)
- **`analyze-chunk-optimization.py`** - Análisis de optimización de chunks

### Fixes Específicos
- **`fix-nginx-413.sh`** - Fix para error 413 (payload too large)
- **`audit-production-state.sh`** - Auditar estado de producción

### Monitoreo
- **`monitor-backups.sh`** - Monitoreo de sistema de backups

### Otros
- **`clear-server-cache.sh`** - Limpiar cache del servidor
- **`repro_second_image.sh`** - Reproducir issue de segunda imagen

## Uso Común

```bash
# Troubleshooting rápido
./scripts/maintenance/dev-troubleshoot.sh cache

# Diagnóstico completo
./scripts/maintenance/quick-diagnostic.sh

# Limpieza de Docker
./scripts/maintenance/docker-cleanup.sh

# Health check
./scripts/maintenance/health-check.sh
```

## Opciones de dev-troubleshoot.sh

```bash
./scripts/maintenance/dev-troubleshoot.sh cache        # Limpiar caches
./scripts/maintenance/dev-troubleshoot.sh ports        # Fix port conflicts
./scripts/maintenance/dev-troubleshoot.sh permissions  # Fix permisos
./scripts/maintenance/dev-troubleshoot.sh all          # Ejecutar todos los fixes
```

---
**Ver también:** `../README.md` para más información
