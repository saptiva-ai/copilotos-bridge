# Legacy Scripts

⚠️ **SCRIPTS OBSOLETOS - NO USAR**

Esta carpeta contiene scripts archivados que ya no se deben usar.
Se mantienen solo como referencia histórica.

## Contenido

### `deploy_archive/` (18 scripts)
Scripts de deploy obsoletos reemplazados por `deploy-to-production.sh` (registry strategy):
- `DEPLOY-NOW.sh`
- `deploy-production-v3.sh`, `v2.sh`, `-safe.sh`
- `deploy-registry.sh`
- `deploy-from-registry.sh`
- Y 12 más...

**Usar en su lugar:** `../deploy-to-production.sh`

### `old_deployment/` (6 scripts)
Scripts de deployment antiguos:
- `blue-green-switch.sh` (blue-green ya no se usa)
- `init-blue-green.sh`
- `push-to-registry.sh` (usar `../push-dockerhub.sh`)
- `rollback.sh`
- `build-frontend.sh`

### Otros
- `sanitize.sh` - Script de sanitización obsoleto
- `manual-deploy-prod.sh` - Deploy manual antiguo

## ⚠️ Advertencia

**NO ejecutar estos scripts en producción.**

Si necesitas deploy, usa:
```bash
./scripts/deploy-to-production.sh 0.1.3
```

---
**Ver también:** `../README.md` para organización actual de scripts
