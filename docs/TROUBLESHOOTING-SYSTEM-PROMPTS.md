# System Prompts Troubleshooting

## 🚨 PROBLEMA CRÍTICO: Modelos no se identifican correctamente

### Síntomas

Los modelos de SAPTIVA responden como si fueran otros asistentes (e.g., Qwen) y no conocen:
- Qué es Saptiva
- Su identidad como CopilotOS
- El contexto del sistema

**Ejemplos:**

```
Usuario: "¿Qué es Saptiva?"
Modelo: "Okay, the user is asking... I'm not immediately familiar with 'Saptiva'..."

Usuario: "Eres CopilotOS?"
Modelo: "¡Hola! Parece que hay un pequeño malentendido. Soy Qwen..."
```

### Causa Raíz

**Feature flag `ENABLE_MODEL_SYSTEM_PROMPT` deshabilitada o ausente en producción.**

Cuando esta variable no está configurada o está en `false`, el sistema usa "modo legacy" que **NO incluye el system prompt** de `registry.yaml`.

### Ubicación del Código

**Archivo:** `apps/api/src/services/saptiva_client.py`
**Línea:** 500

```python
# Feature flag: si está deshabilitado, usar comportamiento legacy
if not settings.enable_model_system_prompt:
    logger.info(
        "Model system prompt feature disabled, using legacy behavior",
        model=model,
        channel=channel
    )
    # ❌ Comportamiento legacy: mensajes simples sin system prompt estructurado
    legacy_messages = [{"role": "user", "content": user_prompt}]
    # ...
```

### Solución

#### 1. Verificar Variable en Producción

```bash
# SSH al servidor
ssh jf@34.42.214.246

# Verificar si existe
cd /home/jf/copilotos-bridge
grep ENABLE_MODEL_SYSTEM_PROMPT envs/.env
```

#### 2. Agregar Variables si No Existen

```bash
# Agregar al final del .env
echo -e '\n# System Prompt Configuration' >> envs/.env
echo 'ENABLE_MODEL_SYSTEM_PROMPT=true' >> envs/.env
echo 'PROMPT_REGISTRY_PATH=prompts/registry.yaml' >> envs/.env
```

**⚠️ IMPORTANTE:** El path correcto es `prompts/registry.yaml` (relativo a `/app` en el container), NO `apps/api/prompts/registry.yaml`

#### 3. Recrear API Container (NO solo restart)

```bash
# ❌ INCORRECTO: restart NO carga nuevas variables
docker compose -f infra/docker-compose.yml --env-file envs/.env restart api

# ✅ CORRECTO: down/up recrea el container con nuevas variables
docker compose -f infra/docker-compose.yml --env-file envs/.env down api
docker compose -f infra/docker-compose.yml --env-file envs/.env up -d api

# Verificar que levantó correctamente
docker logs copilotos-api --tail 20
curl http://localhost:8001/api/health
```

**⚠️ CRÍTICO:** `docker restart` NO carga cambios en `.env`. SIEMPRE usar `down` + `up` para cambios de configuración.

#### 4. Verificar en Container

```bash
# Verificar que la variable llegó al container
docker exec copilotos-api env | grep ENABLE_MODEL_SYSTEM_PROMPT
# Debe mostrar: ENABLE_MODEL_SYSTEM_PROMPT=true
```

### Verificación Final

Hacer un test en el chat:

```
Usuario: "¿Qué es Saptiva?"
Esperado: El modelo debe identificarse como CopilotOS y explicar Saptiva correctamente
```

```
Usuario: "¿Quién eres?"
Esperado: "Soy CopilotOS, asistente de Saptiva..."
```

### Configuración en Archivos

**Local Development (`envs/.env`)**
```bash
# System Prompts por Modelo (líneas 48-50)
ENABLE_MODEL_SYSTEM_PROMPT=true
PROMPT_REGISTRY_PATH=prompts/registry.yaml
```

**Producción (`envs/.env` en servidor)**
```bash
# ⚠️ CRÍTICO: Debe existir esta variable
ENABLE_MODEL_SYSTEM_PROMPT=true
```

### Configuración por Defecto

**Archivo:** `apps/api/src/core/config.py`
**Líneas:** 241-248

```python
prompt_registry_path: str = Field(
    default="apps/api/prompts/registry.yaml",
    description="Ruta al archivo YAML de registro de prompts"
)
enable_model_system_prompt: bool = Field(
    default=True,  # ✅ Default es True
    description="Feature flag: habilitar system prompts por modelo"
)
```

**Nota:** Aunque el default es `True`, si la variable de entorno no existe en el `.env`, puede que Pydantic no la cargue correctamente en algunos casos.

### Debugging

#### Ver si el Registry se Cargó

```bash
# Logs del API al iniciar
docker logs copilotos-api 2>&1 | grep -i 'registry\|prompt'
```

#### Ver Payload Enviado a SAPTIVA

Buscar en logs:
```bash
docker logs copilotos-api 2>&1 | grep -i 'legacy_mode\|system.*prompt'
```

Si ves `"legacy_mode": True`, la flag está deshabilitada.

### Prevención

1. **Agregar a Checklist de Deploy:**
   - Verificar `ENABLE_MODEL_SYSTEM_PROMPT=true` en `.env` de producción

2. **Health Check Extendido:**
   - Agregar endpoint que verifique si el prompt registry está cargado

3. **Monitoreo:**
   - Alertar si se detecta `legacy_mode: true` en logs de producción

### Archivos Relacionados

| Archivo | Propósito |
|---------|-----------|
| `apps/api/prompts/registry.yaml` | Definición de system prompts por modelo |
| `apps/api/src/core/config.py:245` | Definición del setting |
| `apps/api/src/core/prompt_registry.py` | Carga del YAML |
| `apps/api/src/services/saptiva_client.py:500` | Feature flag check |

### Historial de Cambios

**2025-10-06 - Fix Completo:**
- **Problema detectado:** Modelos no se identificaban en producción
- **Causa raíz 1:** Variable `ENABLE_MODEL_SYSTEM_PROMPT` ausente en `.env` de producción
- **Causa raíz 2:** Variable `PROMPT_REGISTRY_PATH` tenía path incorrecto
- **Fix aplicado:**
  1. Agregada `ENABLE_MODEL_SYSTEM_PROMPT=true` a `.env`
  2. Agregada `PROMPT_REGISTRY_PATH=prompts/registry.yaml` a `.env`
  3. Container recreado con `down/up` (NO solo `restart`)
- **Nota importante:** `docker restart` NO carga nuevas variables de entorno
- **Comando correcto:** `docker compose down api && docker compose up -d api`
- **Commit:** 2e0907b (docs), pendiente (fix config)

---

## Otras Configuraciones Importantes

### Ruta del Registry

```bash
# Si el registry.yaml está en ubicación no estándar
PROMPT_REGISTRY_PATH=/ruta/custom/registry.yaml
```

### Modelos Configurados

Verificar que los modelos en `registry.yaml` coincidan con los nombres usados en la app:

```yaml
models:
  "Saptiva Turbo":     # ✅ Debe coincidir exactamente
  "Saptiva Cortex":    # ✅ Case-sensitive
  "Saptiva Ops":       # ✅ Espacios importantes
```

### Parámetros por Modelo

Cada modelo tiene parámetros específicos en `registry.yaml`:

```yaml
params:
  temperature: 0.25      # Turbo: más determinista
  temperature: 0.35      # Cortex: balance
  temperature: 0.2       # Ops: muy determinista
```

---

## Contacto

Si el problema persiste después de seguir estos pasos, verificar:
1. Logs completos del API
2. Variables de entorno cargadas en el container
3. Permisos de lectura en `prompts/registry.yaml`
4. Versión del código en producción vs. local
