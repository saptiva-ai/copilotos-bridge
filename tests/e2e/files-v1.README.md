# Files V1 E2E Tests

Tests end-to-end automatizados para el sistema unificado de files V1.

## Tests Incluidos

### ✅ API Tests (`files-v1.spec.ts`)

1. **Happy Path: Upload 2 PDFs**
   - Sube dos PDFs correctamente
   - Verifica respuesta 201 Created
   - Confirma status READY
   - Valida estructura de respuesta (`file_id`, `status`, `bytes`, `mimetype`)

2. **Happy Path: Multiple Files in Single Request**
   - Sube múltiples archivos en una sola petición
   - Verifica que cada archivo recibe su propio `file_id`

3. **MIME Invalid: Reject .exe (415)**
   - Intenta subir archivo `.exe`
   - Espera rechazo con 415 Unsupported Media Type
   - Verifica mensaje de error apropiado

4. **File Too Large: Reject >10MB (413)**
   - Intenta subir PDF de 11MB
   - Espera rechazo con 413 Request Entity Too Large
   - Verifica error code `UPLOAD_TOO_LARGE`

5. **Rate Limit: Block 6th Upload (429)**
   - Realiza 6 uploads consecutivos
   - Primeros 5 deben pasar (201)
   - 6º debe ser bloqueado (429)
   - Verifica error code `RATE_LIMITED`

6. **Idempotency**
   - Sube archivo con `Idempotency-Key`
   - Re-sube con mismo key
   - Verifica que devuelve mismo `file_id`

7. **Deprecated Redirect**
   - POST a `/api/documents/upload`
   - Verifica redirect 307 a `/api/files/upload`

8. **Metrics Verification**
   - GET `/api/metrics`
   - Verifica presencia de métricas:
     - `copilotos_pdf_ingest_seconds`
     - `copilotos_pdf_ingest_errors_total`
     - `copilotos_tool_invocations_total`

## Fixtures

Las fixtures se generan automáticamente con `generate_fixtures.py`:

| Archivo | Tamaño | Propósito |
|---------|--------|-----------|
| `small.pdf` | ~600 bytes | Upload básico |
| `document.pdf` | ~1 KB | Upload con contenido |
| `large.pdf` | 11 MB | Test de límite de tamaño |
| `fake.exe` | ~2 KB | Test de MIME validation |

### Generar Fixtures

```bash
# Desde la raíz del proyecto
python tests/fixtures/files/generate_fixtures.py
```

Las fixtures se crean en `tests/fixtures/files/`.

## Ejecutar Tests

### Prerequisitos

1. **Servicios en ejecución**
   ```bash
   docker-compose up -d
   # o
   make dev
   ```

2. **Playwright instalado**
   ```bash
   npm install
   npx playwright install chromium
   ```

3. **Variables de entorno** (opcional)
   ```bash
   export API_BASE_URL=http://localhost:8001
   export BASE_URL=http://localhost:3000
   ```

### Ejecutar Solo Tests de Files

```bash
# Con npm/pnpm
npx playwright test files-v1

# Con make (si está configurado)
make test-e2e-files
```

### Ejecutar Todos los Tests E2E

```bash
npx playwright test
```

### Modos de Ejecución

```bash
# Modo headless (CI)
npx playwright test files-v1

# Modo headed (debug)
npx playwright test files-v1 --headed

# Con UI interactiva
npx playwright test files-v1 --ui

# Solo un test específico
npx playwright test files-v1 -g "happy path"

# Con mayor verbosidad
npx playwright test files-v1 --reporter=list

# Generar reporte HTML
npx playwright test files-v1 --reporter=html
```

### Debug

```bash
# Pausar en primer fallo
npx playwright test files-v1 --debug

# Pausar en un test específico
npx playwright test files-v1 -g "rate limit" --debug

# Ver trace de ejecución
npx playwright show-report
```

## Configuración

Los tests usan la configuración global de `playwright.config.ts`:

```typescript
{
  baseURL: process.env.API_BASE_URL || 'http://localhost:8001',
  timeout: 30000,
  retries: process.env.CI ? 3 : 1,
  reporter: ['html', 'junit', 'json', 'github'],
}
```

### Variables de Entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `API_BASE_URL` | `http://localhost:8001` | URL del backend API |
| `BASE_URL` | `http://localhost:3000` | URL del frontend |
| `CI` | - | Si está en CI (afecta retries) |

## Integración CI/CD

### GitHub Actions

```yaml
name: Files V1 E2E Tests

on:
  pull_request:
    paths:
      - 'apps/api/src/routers/files.py'
      - 'apps/api/src/services/file_ingest.py'
      - 'tests/e2e/files-v1.spec.ts'

jobs:
  e2e-files:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup services
        run: docker-compose up -d

      - name: Install dependencies
        run: npm ci

      - name: Install Playwright
        run: npx playwright install --with-deps chromium

      - name: Generate test fixtures
        run: python tests/fixtures/files/generate_fixtures.py

      - name: Run Files E2E tests
        run: npx playwright test files-v1
        env:
          API_BASE_URL: http://localhost:8001

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: playwright-report/
```

## Troubleshooting

### Error: Fixtures not found

```bash
# Generar fixtures
python tests/fixtures/files/generate_fixtures.py

# Verificar que existen
ls -lh tests/fixtures/files/
```

### Error: API not available

```bash
# Verificar servicios
docker-compose ps

# Ver logs del API
docker-compose logs -f copilotos-api

# Verificar health endpoint
curl http://localhost:8001/api/health
```

### Error: Authentication failed

```bash
# El test usa demo_admin por default
# Verificar que el usuario existe en la DB

# O regenerar auth
rm -rf playwright/.auth/
npx playwright test auth.setup
```

### Rate limit ya alcanzado

```bash
# Limpiar rate limit key de Redis
docker-compose exec redis redis-cli DEL "rate_limit:upload:demo_admin"

# O esperar 60 segundos
```

### Tests flaky

Los tests de rate limiting pueden ser flaky debido a timing. Si falla:

1. Verifica que no hay otros tests corriendo en paralelo
2. Asegúrate que Redis está limpio
3. Aumenta el timeout si es necesario

## Estructura de Respuestas

### Upload Exitoso (201)

```json
{
  "files": [
    {
      "file_id": "abc123...",
      "doc_id": "abc123...",
      "status": "READY",
      "mimetype": "application/pdf",
      "bytes": 12345,
      "pages": 1,
      "name": "document.pdf",
      "filename": "document.pdf"
    }
  ]
}
```

### Error Codes

| Code | HTTP | Descripción |
|------|------|-------------|
| `UPLOAD_TOO_LARGE` | 413 | Archivo >10MB |
| `UNSUPPORTED_MIME` | 415 | MIME type no soportado |
| `RATE_LIMITED` | 429 | >5 uploads/min |
| `EXTRACTION_FAILED` | 500 | Error en procesamiento |

## Próximos Pasos

Una vez que estos tests pasen:

1. ✅ **Backend V1 validado**
2. ⏳ **Frontend integration**: Integrar botón de upload y toggle
3. ⏳ **E2E UI Tests**: Tests con Playwright UI (upload via browser)
4. ⏳ **Canary deployment**: 5% usuarios en postprod
5. ⏳ **Full rollout**: 100% si métricas OK

## Referencias

- **Spec completa**: `VALIDATION_REPORT_V1.md`
- **Script validación**: `scripts/validation/validate_files_v1.sh`
- **Backend router**: `apps/api/src/routers/files.py`
- **Servicio ingestion**: `apps/api/src/services/file_ingest.py`
- **Config Playwright**: `playwright.config.ts`
