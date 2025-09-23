## Guardas permanentes (Next.js Chat LLM)

Este checklist debe verificarse antes de cualquier deploy a producción para evitar respuestas de mocks/cache.

### ✅ Service Workers y MSW
- [ ] MSW no está instalado o solo se activa con doble condición (env + flag de usuario)
- [ ] Service Workers se desregistran automáticamente si MSW está deshabilitado
- [ ] No hay `mockServiceWorker.js` residual en public/ para producción
- [ ] Runtime checks validan que no hay indicadores de mock en localStorage

### ✅ FastAPI Backend (apps/api/src/routers/chat.py)
- [ ] Handlers del chat utilizan `JSONResponse` con `NO_STORE_HEADERS`
- [ ] Headers aplicados: `Cache-Control: no-store, no-cache, must-revalidate, max-age=0`
- [ ] Headers aplicados: `Pragma: no-cache`
- [ ] Headers aplicados: `Expires: 0`
- [ ] Sin `response_model` en decoradores cuando se usa JSONResponse

### ✅ Cliente HTTP (apps/web/src/lib/api-client.ts)
- [ ] Axios client incluye headers: `Cache-Control: no-store, no-cache, must-revalidate`
- [ ] Axios client incluye headers: `Pragma: no-cache`
- [ ] Axios client incluye headers: `Expires: 0`
- [ ] Timeout configurado para evitar requests colgados

### ✅ Next.js Frontend
- [ ] Sin Next.js API routes con cache para endpoints LLM
- [ ] No hay `generateStaticParams` o ISR en rutas con I/O de LLM
- [ ] Runtime configuration valida NEXT_PUBLIC_API_URL en producción

### ✅ Estado y Cache Management (apps/web/src/lib/store.ts)
- [ ] `invalidateOnContextChange()` implementado para login/logout
- [ ] `clearAllData()` implementado para reset completo
- [ ] Zustand persistence configurada correctamente
- [ ] Cache keys de localStorage se limpian en cambios de contexto

### ✅ Runtime Guards (apps/web/src/lib/runtime.ts)
- [ ] `assertProdNoMock()` se ejecuta en punto de entrada principal
- [ ] Validación de NEXT_PUBLIC_API_URL requerida en producción
- [ ] Detección y warning de indicadores mock en localStorage
- [ ] Guards activos sin fallback silencioso a mocks

### ✅ Testing y Verificación
- [ ] Headers Cache-Control verificados en respuestas de `/api/chat`
- [ ] Sin diferencias funcionales entre navegador normal e incógnito
- [ ] Responses LLM reales (no mock) en ambiente de pruebas
- [ ] Diagnóstico de headers completado en `logs/network_checks/`

### 🛠️ Script de Pánico (Depuración)

Si sospechas problemas de cache en producción:

```bash
# 1. Verificar headers en backend
curl -D - -X POST "http://localhost:8001/api/chat" \
  -H "Content-Type: application/json" \
  --data '{"message":"test"}' | grep -i cache

# 2. Limpiar todo cache del navegador (Dev Tools)
# - Application > Storage > Clear storage
# - Application > Service Workers > Unregister all
# - Hard reload (Ctrl+Shift+R)

# 3. Verificar variables de entorno
echo $NEXT_PUBLIC_API_URL
echo $NEXT_PUBLIC_ENABLE_MSW
echo $NODE_ENV
```

### 📋 Pre-Deploy Validation

Antes de deploy a producción:
1. ✅ Ejecutar `docker compose restart api web`
2. ✅ Verificar headers con curl en `/api/chat`
3. ✅ Confirmar respuestas reales de LLM (no mock)
4. ✅ Validar runtime guards en navegador
5. ✅ Test en navegador incógnito para verificar consistencia

---

**Última actualización**: $(date)
**Responsable**: Team DevOps / QA

> "Distingue lo que controlas de lo que no (Epicteto)."
> Controlamos headers, flags y SW; reducimos incertidumbre imponiendo no-store, rutas dinámicas y limpieza explícita.
