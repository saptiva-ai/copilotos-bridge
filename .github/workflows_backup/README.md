# Workflows Backup

Este directorio contiene workflows de CI/CD que están temporalmente deshabilitados para simplificar el pipeline.

## Estado Actual

**Workflow Activo:**
- `.github/workflows/ci-cd.yml` - Pipeline básico de tests (backend + frontend)

**Workflows Deshabilitados:**
Los siguientes workflows están en backup y pueden reactivarse según necesidad:

### `bankadvisor-ci.yml`
- **Propósito**: Tests específicos del plugin bank-advisor
- **Razón**: Consolidado en ci-cd.yml principal
- **Reactivar si**: Necesitas tests aislados para bank-advisor

### `ci-cd-optimized.yml`
- **Propósito**: Versión optimizada con cacheo avanzado
- **Razón**: Preferimos simplicidad sobre optimización prematura
- **Reactivar si**: Tiempos de CI son problema crítico

### `epic-validation.yml`
- **Propósito**: Validación de estructura de épicas y documentos
- **Razón**: Validación movida a pre-commit hooks
- **Reactivar si**: Necesitas validación automática de docs

### `mcp-ci.yml`
- **Propósito**: Tests de MCP (Model Context Protocol) servers
- **Razón**: MCP servers aún no en producción
- **Reactivar si**: Integración de MCP servers está activa

### `happy-path-tests.yml`
- **Propósito**: Suite de 40 test cases end-to-end
- **Razón**: Requiere infraestructura completa (Weaviate, MongoDB, Redis)
- **Reactivar si**:
  - Infraestructura de tests está disponible en CI
  - Tests happy-path son críticos para merge
  - Necesitas validación automática de NL2SQL pipeline

## Cómo Reactivar un Workflow

1. Copiar el archivo de vuelta:
   ```bash
   cp .github/workflows_backup/WORKFLOW.yml .github/workflows/
   ```

2. Verificar que las secrets necesarias están configuradas

3. Hacer commit y push

## Deployment

Actualmente el deployment es **manual**. Para deployar:

```bash
# Opción 1: TAR deployment
./scripts/deploy.sh tar --force

# Opción 2: Registry deployment (si credenciales están configuradas)
./scripts/deploy.sh registry --force
```

## Futuro

Cuando la infraestructura de CI/CD esté más madura:
- Reactivar `happy-path-tests.yml` para validación automática
- Considerar `ci-cd-optimized.yml` si tiempos de CI son > 10min
- Integrar MCP tests cuando estén en producción

## Notas

- Fecha de backup: 2026-01-07
- Responsable: Claude Code
- Revisión sugerida: Q1 2026
