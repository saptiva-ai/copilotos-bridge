# ✅ Resumen de Pruebas - Sistema de Prompts por Modelo

## 🎯 Estado Final: FUNCIONANDO CORRECTAMENTE

### 📊 Resultados de Pruebas con Usuario Demo

#### 1. Prueba de Modelos Diferentes

**Saptiva Turbo** (Optimizado para brevedad):
- ✅ Temperature: 0.25 (configurado)
- ✅ Max tokens: 1200 (chat)
- ✅ System hash: `f962b2adf7b10997`
- ✅ Respuesta: Ultra-concisa, formato bullet points
- ✅ Addendum visible: "Fuente: Saptiva..." y "Próximos pasos..."

**Saptiva Cortex** (Razonamiento profundo):
- ✅ Temperature: 0.7 (configurado)
- ✅ Max tokens: 1200 (chat)
- ✅ System hash: `250b67f0a07a528b`
- ✅ Respuesta: Muestra razonamiento interno (Chain-of-thought)
- ✅ Comportamiento diferenciado vs Turbo

**Saptiva Ops** (Operaciones y datos):
- ✅ Temperature: 0.3 (configurado)
- ✅ Max tokens: 1200 (chat)
- ✅ System hash: `edb2968e88149d5f`
- ✅ Respuesta: Tabla estructurada con métricas
- ✅ Formato orientado a datos/analytics

#### 2. Prueba de Canales (max_tokens)

| Canal | Max Tokens Esperado | Max Tokens Real | Estado |
|-------|---------------------|-----------------|--------|
| chat  | 1200 | 1200 | ✅ |
| report| 3500 | 3500 | ✅ |
| title | 64   | 64   | ✅ (cortó respuesta correctamente) |

#### 3. Telemetría

```json
{
  "request_id": "c57137a1-6076-4434-91a0-59733b8c279b",
  "system_hash": "f962b2adf7b10997",    // ✅ SHA256 truncado
  "prompt_version": "v1",                // ✅ Versión del registro
  "model": "Saptiva Turbo",
  "channel": "chat",
  "has_tools": false
}
```

## 🔧 Problema Encontrado y Solución

### Problema: Docker Cache
**Síntoma**: El contenedor no tomaba los cambios en el código ni las nuevas variables de entorno.

**Causas**:
1. Docker usa cache de layers en builds
2. `docker restart` no recarga env vars
3. La ruta del registry estaba incorrecta (apps/api/prompts vs prompts/)

**Solución Implementada**:
```bash
# 1. Corregir variable de entorno
PROMPT_REGISTRY_PATH=prompts/registry.yaml  # (antes: apps/api/prompts/registry.yaml)

# 2. Rebuild sin cache + recrear contenedor
docker compose build --no-cache api
docker compose down api
docker compose up -d api
```

## 📚 Documentación Agregada

### Makefile
- ✅ Sección prominente en `make help` sobre Docker cache
- ✅ Comandos `rebuild-api` y `rebuild-all` mejorados
- ✅ Ahora hacen `build --no-cache` + `down` + `up` automáticamente

### README.md
- ✅ Nueva sección "⚠️ Common Issue: Code Changes Not Reflected?"
- ✅ Explicación clara de por qué ocurre
- ✅ Soluciones paso a paso
- ✅ Comandos de verificación

## 🚀 Comandos para Desarrollo Futuro

```bash
# Cuando cambies código en la API:
make rebuild-api

# Cuando cambies variables de entorno:
make rebuild-all

# Verificar que el código está sincronizado:
make debug-file-sync

# Verificar que las env vars se cargaron:
docker exec copilotos-api env | grep PROMPT_REGISTRY_PATH
```

## 📋 Checklist de Verificación

- [x] Registry YAML cargando correctamente
- [x] System prompts diferenciados por modelo
- [x] Max tokens por canal funcionando
- [x] Telemetría con system_hash
- [x] Placeholder substitution ({CopilotOS}, {Saptiva}, {TOOLS})
- [x] Addendum visible en respuestas
- [x] Feature flag funcional (ENABLE_MODEL_SYSTEM_PROMPT=true)
- [x] Backward compatibility (getattr fallbacks)
- [x] Documentación actualizada (Makefile + README)
- [x] Tests exitosos con usuario demo

## 💡 Insights Técnicos

### Docker Cache & Container Lifecycle
- `docker restart`: Mantiene mismo contenedor (viejo código + env vars)
- `docker compose up`: Usa imágenes cacheadas si existen
- `docker compose down + up`: Recrea contenedores con nueva imagen
- `--no-cache`: Fuerza rebuild completo ignorando layers cacheadas

### Orden Correcto para Actualizaciones
1. Modificar código/config
2. `docker compose build --no-cache <service>`
3. `docker compose down <service>`
4. `docker compose up -d <service>`

**NUNCA** usar solo `docker restart` para cambios de código o env vars.
