# Testing Scripts

Scripts de testing, validación y verificación del sistema.

**Nota Importante:** Algunos scripts de testing de uso muy frecuente se mantienen en `scripts/` (root):
- `../test-runner.sh` - Runner principal consolidado de todos los tests
- `../test_audit_flow.sh` - Tests de flujo completo de auditoría
- `../test_password_reset.sh` - Tests de password reset
- `../test_bank_query_*.py` - Tests de detección bancaria

Estos scripts usan **rutas relativas** y **variables de entorno** (`TEST_PDF`, `API_URL`) para configuración.

## Scripts Disponibles

### Tests de Integración
- **`test-auth-and-chat.py`** - Tests de autenticación + chat
  ```bash
  python scripts/testing/test-auth-and-chat.py
  ```
- **`test-mongodb.py`** - Tests de conexión MongoDB
- **`test-all-models.py`** - Tests de todos los modelos Saptiva
- **`test_integration.py`** - Suite completa de integración

### Tests de RAG & Búsqueda
- **`test-rag-ingestion.py`** - Tests de ingesta RAG
- **`test-semantic-search.py`** - Tests de búsqueda semántica
- **`test-resource-lifecycle.py`** - Tests de ciclo de vida de recursos

### Tests de Sistema
- **`test-auth-logging.py`** - Tests de logging de autenticación
- **`test-backup-system.sh`** - Tests del sistema de backups
- **`test-credential-rotation.sh`** - Tests de rotación de credentials
- **`test_mcp_tools.sh`** - Tests de herramientas MCP ([Guía](README_MCP_TESTING.md))

### Validaciones
- **`validate-config.sh`** - Validar configuración
- **`validate-env-server.sh`** - Validar environment en servidor
- **`validate-mvp.sh`** - Validar funcionalidad MVP
- **`validate-production-readiness.sh`** - Validar antes de producción
- **`validate-setup.sh`** - Validar setup inicial
- **`validate_saptiva_api.py`** - Validar API de Saptiva

### Verificaciones
- **`verify-deployment.sh`** - Verificar deployment exitoso
- **`verify-deps.sh`** - Verificar dependencias
- **`verify.sh`** - Verificación general
- **`verify_pdf_extraction.py`** - Verificar extracción de PDFs

### Tests de Datos
- **`reproduce_golden_case.py`** - Reproducir caso golden de tests

## Uso Común

### Testing Completo
```bash
# Tests de integración
python scripts/testing/test-auth-and-chat.py

# Validar antes de deploy
./scripts/testing/validate-production-readiness.sh

# Verificar deployment
./scripts/testing/verify-deployment.sh
```

### Validaciones Pre-Producción
```bash
# 1. Validar setup
./scripts/testing/validate-setup.sh

# 2. Validar MVP
./scripts/testing/validate-mvp.sh

# 3. Validar producción
./scripts/testing/validate-production-readiness.sh

# 4. Verificar deployment
./scripts/testing/verify-deployment.sh
```

### Tests Específicos
```bash
# RAG
python scripts/testing/test-rag-ingestion.py
python scripts/testing/test-semantic-search.py

# MongoDB
python scripts/testing/test-mongodb.py

# Saptiva API
python scripts/testing/validate_saptiva_api.py
```

## Convenciones

- `test-*.py` - Tests de Python (ejecutar con Python)
- `test_*.py` - Tests de Python (unittest/pytest)
- `validate-*.sh` - Validaciones de shell
- `verify-*.sh` - Verificaciones de shell

---
**Ver también:** `../README.md` para más información
