# Plan de Testing - Plugin-First Architecture Migration

## Objetivo
Validar que la migración a arquitectura Plugin-First funciona correctamente antes de merge a `main`.

---

## 1. Tests de Infraestructura (Smoke Tests)

### 1.1 Verificar que todos los servicios inician
```bash
# Limpiar y reiniciar
make stop
make clean
make dev

# Verificar health de todos los servicios
make health
```

**Expected:**
- Backend: 🟢 Healthy (http://localhost:8000)
- File Manager: 🟢 Healthy (http://localhost:8001)
- Frontend: 🟢 Healthy (http://localhost:3000)
- MongoDB: 🟢 Connected
- Redis: 🟢 Connected

### 1.2 Verificar endpoints de health individuales
```bash
# Backend
curl -s http://localhost:8000/api/health | jq

# File Manager
curl -s http://localhost:8001/health | jq

# Capital414 Auditor
curl -s http://localhost:8002/health | jq
```

---

## 2. Tests del Plugin file-manager

### 2.1 Test de Upload
```bash
# Crear archivo de prueba
echo "Test PDF content" > /tmp/test.txt

# Upload via curl
curl -X POST http://localhost:8001/upload \
  -F "file=@/tmp/test.txt" \
  -F "user_id=test_user" \
  -F "session_id=test_session" | jq

# Guardar minio_key del response para siguientes tests
```

**Expected Response:**
```json
{
  "file_id": "...",
  "filename": "test.txt",
  "size": 17,
  "mime_type": "text/plain",
  "minio_key": "test_user/test_session/xxx.txt",
  "sha256": "...",
  "extracted_text": "Test PDF content"
}
```

### 2.2 Test de Download
```bash
# Usar minio_key del paso anterior
curl -s http://localhost:8001/download/{minio_key}
```

### 2.3 Test de Metadata
```bash
curl -s "http://localhost:8001/metadata/{minio_key}?include_text=true" | jq
```

### 2.4 Test de Extracción de Texto
```bash
curl -X POST "http://localhost:8001/extract/{minio_key}?force=false" | jq
```

---

## 3. Tests de Integración Backend → file-manager

### 3.1 Test via API de Chat con archivo
```bash
# 1. Login para obtener token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"Demo1234"}' | jq -r '.access_token')

# 2. Crear chat session
SESSION=$(curl -s -X POST http://localhost:8000/api/chat/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Session"}' | jq -r '.id')

# 3. Upload archivo via backend (debería delegarse a file-manager)
curl -X POST "http://localhost:8000/api/files/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/test.pdf" \
  -F "session_id=$SESSION" | jq
```

---

## 4. Tests del Plugin Capital414

### 4.1 Test directo con file_path (legacy)
```bash
# Copiar PDF de prueba al contenedor
docker cp /path/to/test.pdf octavios-capital414-auditor:/tmp/test.pdf

# Llamar al tool via MCP (requiere cliente MCP o curl al endpoint)
curl -X POST http://localhost:8002/mcp/tools/audit_document_full \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/tmp/test.pdf",
    "policy_id": "auto"
  }' | jq
```

### 4.2 Test con minio_key (nuevo flujo)
```bash
# 1. Primero subir archivo al file-manager
UPLOAD_RESPONSE=$(curl -s -X POST http://localhost:8001/upload \
  -F "file=@/path/to/test.pdf" \
  -F "user_id=audit_test" \
  -F "session_id=session1")

MINIO_KEY=$(echo $UPLOAD_RESPONSE | jq -r '.minio_key')

# 2. Llamar audit con minio_key
curl -X POST http://localhost:8002/mcp/tools/audit_document_full \
  -H "Content-Type: application/json" \
  -d "{
    \"minio_key\": \"$MINIO_KEY\",
    \"policy_id\": \"auto\"
  }" | jq
```

**Expected Response:**
```json
{
  "job_id": "...",
  "status": "completed",
  "total_findings": 5,
  "findings_by_severity": {"low": 2, "medium": 2, "high": 1},
  "executive_summary_markdown": "..."
}
```

---

## 5. Tests E2E (Frontend)

### 5.1 Test manual de flujo completo
1. Abrir http://localhost:3000
2. Login con demo/Demo1234
3. Crear nuevo chat
4. Subir un PDF
5. Escribir "Auditar archivo: test.pdf"
6. Verificar que el audit se ejecuta y muestra resultados

### 5.2 Test con Playwright (opcional)
```bash
make test T=e2e
```

---

## 6. Tests de Resiliencia

### 6.1 Test de reinicio de file-manager
```bash
# Reiniciar solo file-manager
docker compose -f infra/docker-compose.yml restart file-manager

# Verificar que backend sigue funcionando (debería reconectar)
curl -s http://localhost:8000/api/health | jq

# Esperar reconexión y probar upload
sleep 10
curl -X POST http://localhost:8001/upload -F "file=@/tmp/test.txt" -F "user_id=test" | jq
```

### 6.2 Test de file-manager caído
```bash
# Detener file-manager
docker compose -f infra/docker-compose.yml stop file-manager

# Verificar que backend reporta error graceful
curl -s http://localhost:8000/api/health | jq

# El backend debería seguir respondiendo pero con degradación
```

---

## 7. Tests de Performance (Opcional)

### 7.1 Benchmark de upload
```bash
# Instalar hey (HTTP load generator)
# brew install hey

# Test de carga al file-manager
hey -n 100 -c 10 -m POST \
  -F "file=@/tmp/test.txt" \
  -F "user_id=bench" \
  http://localhost:8001/upload
```

---

## 8. Checklist de Validación

### Infraestructura
- [ ] `make dev` inicia todos los servicios sin errores
- [ ] `make health` muestra todos los servicios healthy
- [ ] Backend escucha en puerto 8000
- [ ] File-manager escucha en puerto 8001
- [ ] Capital414 escucha en puerto 8002

### file-manager Plugin
- [ ] POST /upload funciona y retorna metadata
- [ ] GET /download/{key} retorna el archivo
- [ ] GET /metadata/{key} retorna info correcta
- [ ] POST /extract/{key} extrae texto
- [ ] Texto extraído se cachea en Redis

### Capital414 Plugin
- [ ] audit_document_full con file_path funciona (legacy)
- [ ] audit_document_full con minio_key funciona (nuevo)
- [ ] Archivos temporales se limpian después del audit
- [ ] Los 8 auditors se ejecutan correctamente

### Integración
- [ ] Backend puede consumir file-manager via FileManagerClient
- [ ] Capital414 puede descargar archivos de file-manager
- [ ] Flujo completo de chat + upload + audit funciona

### Logs
- [ ] No hay errores críticos en `make logs`
- [ ] Los logs muestran comunicación entre servicios
- [ ] Cleanup de archivos temporales se registra

---

## 9. Comandos de Debugging

```bash
# Ver logs de todos los servicios
make logs

# Ver logs específicos
make logs S=api
make logs S=file-manager
make logs S=capital414-auditor

# Shell en contenedor
make shell S=api
make shell S=file-manager

# Verificar conexión Redis
docker compose -f infra/docker-compose.yml exec redis redis-cli ping

# Verificar buckets MinIO
docker compose -f infra/docker-compose.yml exec minio mc ls local/documents
```

---

## 10. Rollback Plan

Si los tests fallan:

```bash
# 1. Detener servicios
make stop

# 2. Revertir al branch main
git checkout main

# 3. Reiniciar
make dev
```

---

## Resultado Esperado

Todos los checks del checklist deben estar marcados antes de hacer merge del branch `refactor/extract-capital414-plugin` a `main`.
