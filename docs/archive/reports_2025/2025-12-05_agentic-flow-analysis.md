# Análisis del Flujo Agéntico - Worst Practices, Best Practices, Gaps y Mejoras

**Fecha:** 2025-12-05  
**Alcance:** `.claude/` - Sistema de agentes, comandos, skills, hooks y reglas

---

## Resumen Ejecutivo

El sistema agéntico está bien estructurado con separación clara de responsabilidades, pero presenta **confusiones críticas** sobre la invocación de agentes, **gaps en validación y observabilidad**, y **oportunidades de mejora** en consistencia y mantenibilidad.

**Score General:** 7.5/10
- ✅ Arquitectura sólida (Strategic/Tactical/Operational)
- ⚠️ Confusión sobre custom agents vs built-in agents
- ⚠️ Falta de validación y observabilidad
- ✅ Hooks bien implementados
- ⚠️ Gaps en documentación y debugging

---

## 1. Worst Practices 🔴

### 1.1 ✅ RESUELTO: Custom Agents como Subagents (Actualizado)

**Estado:** **RESUELTO** - Se ha actualizado la documentación para usar Task() determinísticamente.

**Solución Implementada:**
- Los custom agents (.claude/agents/*.md) **SÍ son subagents válidos**
- Se invocan usando `Task(subagent_type="agent-name", prompt="Feature description: $ARGUMENTS")`
- Patrón determinista establecido en todos los comandos
- Documentación creada en `.claude/docs/TASK_USAGE.md`

**Cambios Realizados:**
- ✅ Actualizado `/do` para usar Task() con subagent_type
- ✅ Actualizado `/plan` y `/prd` con patrón determinista
- ✅ Actualizado `/dev-loop` para usar Task() correctamente
- ✅ Creado `.claude/docs/TASK_USAGE.md` con guía completa
- ✅ Actualizado `software-developer.md` para usar Task() correctamente

**Patrón Determinista:**
```python
Task(
    subagent_type="software-developer",
    prompt=f"Feature description: $ARGUMENTS"
)
```

### 1.2 Falta de Validación de Consistencia

**Problema:** No hay mecanismo para validar que:
- Los agentes referenciados en `delegation-matrix.md` existan en `.claude/agents/`
- Los skills referenciados en agentes existan en `.claude/skills/`
- Los comandos en `do.md` coincidan con los archivos en `.claude/commands/`

**Evidencia:**
- `delegation-matrix.md` lista 9 agentes, pero no valida que existan
- `do.md` tiene routing logic pero no valida que los comandos existan
- Si un agente se mueve a `agents_parking/`, el routing puede seguir apuntando a él

**Impacto:**
- Errores silenciosos cuando se intenta usar agentes que no existen
- Difícil mantener consistencia manualmente

**Recomendación:**
- Crear script de validación: `.claude/scripts/validate-consistency.sh`
- Ejecutar en pre-commit hook

### 1.3 Hooks que Oculten Errores

**Problema:** `post_edit.sh` tiene múltiples `|| echo` que ocultan errores reales.

**Evidencia:**
```bash
# Líneas 62, 68, 79, 88
"$isort_cmd" "${py_files[@]}" 2>/dev/null || echo "post_edit: isort failed; skipping" >&2
"$black_cmd" "${py_files[@]}" 2>/dev/null || echo "post_edit: black failed; skipping" >&2
```

**Impacto:**
- Errores de formato se ignoran silenciosamente
- El código puede quedar mal formateado sin que nadie se dé cuenta

**Recomendación:**
- Al menos loguear errores a un archivo de log
- Opcionalmente, fallar si el formateo es crítico

### 1.4 Falta de Observabilidad

**Problema:** No hay forma de saber:
- Qué agentes se invocan más frecuentemente
- Cuánto tiempo toma cada agente
- Qué agentes fallan más
- Qué comandos se usan más

**Impacto:**
- No se puede optimizar el sistema basado en datos
- Difícil identificar agentes problemáticos
- No hay métricas para justificar mejoras

**Recomendación:**
- Agregar logging estructurado en hooks
- Crear dashboard simple de métricas (opcional)

### 1.5 Documentación Incompleta sobre Task()

**Problema:** No está claro cuándo usar `Task()` vs ejecutar directamente.

**Evidencia:**
- `dev-loop.md` menciona usar Task() para built-in agents
- Pero no hay ejemplos claros de cuándo NO usarlo
- No hay documentación sobre los built-in agents disponibles

**Recomendación:**
- Crear `.claude/docs/TASK_USAGE.md` con ejemplos claros
- Documentar built-in agents disponibles

---

## 2. Best Practices ✅

### 2.1 Separación Clara de Responsabilidades

**Evidencia:**
- Strategic (sonnet) → prd-architect, plan-architect
- Tactical (sonnet) → software-developer, code-reviewer
- Operational (haiku) → test-runner, dev-validator, infra-doctor

**Beneficio:**
- Fácil entender qué agente usar para cada tarea
- Modelos apropiados para cada nivel de complejidad

### 2.2 Uso Apropiado de Modelos

**Evidencia:**
- Sonnet para análisis complejo (code, planning, review)
- Haiku para tareas simples (validation, diagnostics, mapping)

**Beneficio:**
- Optimización de costos
- Velocidad apropiada para cada tarea

### 2.3 Circuit Breakers Bien Definidos

**Evidencia:**
- `software-developer.md` tiene circuit breakers claros:
  - Per-CA retries: 3
  - Total retries: 10
  - Session time: 30 min
  - Token budget: 50k

**Beneficio:**
- Previene loops infinitos
- Control de costos
- Escalación apropiada

### 2.4 TDD Discipline Bien Documentada

**Evidencia:**
- `software-developer.md` tiene sección completa de TDD
- RED → GREEN → REFACTOR claramente definido
- Auto-corrección con dev-validator

**Beneficio:**
- Calidad de código consistente
- Tests como documentación viva

### 2.5 Hooks Bien Estructurados

**Evidencia:**
- `session_start.sh`: Inicializa entorno
- `preflight.sh`: Valida infraestructura
- `post_edit.sh`: Formatea código automáticamente

**Beneficio:**
- Automatización de tareas repetitivas
- Consistencia en el entorno

### 2.6 Exit Codes Estandarizados

**Evidencia:**
- `exit-codes.md` define claramente:
  - 0: Success
  - 1: Tests failed
  - 2: Infra/preflight failure

**Beneficio:**
- Comportamiento predecible
- Fácil debugging

### 2.7 Parking de Agentes No Usados

**Evidencia:**
- `agents_parking/` contiene agentes deprecados
- `README.md` explica el proceso

**Beneficio:**
- Historial preservado
- No confusión con agentes activos

### 2.8 Deprecation de Comandos

**Evidencia:**
- `commands_deprecated/` contiene comandos antiguos
- `README.md` explica migración

**Beneficio:**
- Transición suave
- Documentación de cambios

---

## 3. Gaps (Faltantes) ⚠️

### 3.1 Falta de Mecanismo de Rollback

**Problema:** Si un agente falla y modifica archivos, no hay forma de revertir.

**Impacto:**
- Cambios parciales pueden dejar el código en estado inconsistente
- Difícil recuperarse de errores

**Recomendación:**
- Git commit antes de cambios grandes
- O crear checkpoint system

### 3.2 No Hay Logging/Auditoría

**Problema:** No se registra qué agentes se invocan, cuándo, con qué parámetros.

**Impacto:**
- Imposible debuggear problemas
- No hay historial de decisiones

**Recomendación:**
- Agregar logging estructurado en hooks
- Guardar en `.claude/logs/` (gitignored)

### 3.3 Falta de Retry a Nivel de Orquestación

**Problema:** Si un agente falla, no hay retry automático a nivel de `/do` o `/dev-loop`.

**Evidencia:**
- `software-developer` tiene retry interno
- Pero si `test-runner` falla, no hay retry en `dev-loop`

**Recomendación:**
- Agregar retry logic en comandos de orquestación
- Con exponential backoff

### 3.4 No Hay Validación de que Agentes Sigan sus Reglas

**Problema:** No hay forma de verificar que un agente realmente siga las instrucciones de su archivo .md.

**Impacto:**
- Agentes pueden desviarse de sus responsabilidades
- Difícil mantener disciplina

**Recomendación:**
- Crear checklist de validación post-ejecución
- O reviews periódicas de outputs

### 3.5 Falta Documentación de Debugging

**Problema:** Si algo falla, no está claro cómo debuggearlo.

**Preguntas sin respuesta:**
- ¿Cómo saber qué agente se invocó?
- ¿Cómo ver logs de un agente específico?
- ¿Cómo reproducir un error?

**Recomendación:**
- Crear `.claude/docs/DEBUGGING.md`
- Incluir troubleshooting guide

### 3.6 No Hay Tests para Hooks

**Problema:** Los hooks son críticos pero no están testeados.

**Impacto:**
- Cambios en hooks pueden romper el sistema
- Difícil refactorizar con confianza

**Recomendación:**
- Crear tests para hooks en `.claude/tests/`
- Ejecutar en CI

### 3.7 Falta Guía de Creación de Nuevos Agentes

**Problema:** No está claro cómo crear un nuevo agente.

**Preguntas sin respuesta:**
- ¿Qué template usar?
- ¿Qué modelo elegir?
- ¿Cómo integrarlo en routing?

**Recomendación:**
- Crear `.claude/docs/CREATING_AGENTS.md`
- Incluir template y checklist

### 3.8 No Hay Validación de Skills Referenciados

**Problema:** Si un agente referencia un skill que no existe, falla silenciosamente.

**Evidencia:**
- `software-developer.md` lista skills: `[code, test, explore]`
- Pero no valida que existan en `.claude/skills/`

**Recomendación:**
- Validar skills en script de consistencia
- O hacer skills opcionales con fallback

---

## 4. Puntos de Mejora 🚀

### 4.1 Mejorar Consistencia entre Archivos

**Problema:** Información duplicada en múltiples archivos.

**Evidencia:**
- `delegation-matrix.md`, `do.md`, `workflow.md` tienen routing logic similar
- Cambios requieren actualizar múltiples lugares

**Mejora:**
- Centralizar routing en un solo lugar
- Otros archivos referencian la fuente de verdad

### 4.2 Agregar Validación Pre-commit

**Mejora:**
- Script que valida:
  - Agentes referenciados existen
  - Skills referenciados existen
  - Comandos referenciados existen
  - No hay referencias a agentes en parking

### 4.3 Mejorar Manejo de Errores en Hooks

**Mejora:**
- `post_edit.sh` debería:
  - Loguear errores a archivo
  - Opcionalmente fallar si es crítico
  - Reportar estadísticas de formateo

### 4.4 Agregar Métricas Básicas

**Mejora:**
- Logging simple de:
  - Agente invocado
  - Tiempo de ejecución
  - Resultado (success/failure)
- Guardar en `.claude/logs/metrics.jsonl`

### 4.5 Documentar Built-in Agents

**Mejora:**
- Crear `.claude/docs/BUILTIN_AGENTS.md`
- Listar todos los built-in agents disponibles
- Ejemplos de uso con Task()

### 4.6 Mejorar Documentación de Task()

**Mejora:**
- Crear `.claude/docs/TASK_USAGE.md` con:
  - Cuándo usar Task() vs ejecutar directamente
  - Ejemplos de cada caso
  - Troubleshooting común

### 4.7 Agregar Health Check de Sistema Agéntico

**Mejora:**
- Comando `/agent-health` que valida:
  - Todos los agentes tienen formato correcto
  - Todos los skills existen
  - Routing está consistente
  - Hooks son ejecutables

### 4.8 Mejorar Manejo de Versiones

**Mejora:**
- Versionar agentes (v1, v2, etc.)
- Documentar breaking changes
- Migración guide entre versiones

### 4.9 Agregar Tests de Integración

**Mejora:**
- Tests que validan:
  - `/do` routing funciona
  - Agentes producen outputs esperados
  - Hooks se ejecutan correctamente

### 4.10 Mejorar Feedback Loop

**Mejora:**
- Agregar mecanismo para:
  - Reportar problemas con agentes
  - Sugerir mejoras
  - Track issues por agente

---

## 5. Priorización de Mejoras

### Alta Prioridad (Crítico)

1. **Aclarar Custom Agents vs Built-in Agents** (1.1)
   - Impacto: Alto (confusión actual)
   - Esfuerzo: Bajo (documentación)

2. **Validación de Consistencia** (1.2, 3.8)
   - Impacto: Alto (previene errores)
   - Esfuerzo: Medio (script)

3. **Documentación de Debugging** (3.5)
   - Impacto: Alto (productividad)
   - Esfuerzo: Bajo (documentación)

### Media Prioridad (Importante)

4. **Observabilidad Básica** (1.4, 4.4)
   - Impacto: Medio (optimización)
   - Esfuerzo: Medio (logging)

5. **Mejorar Manejo de Errores en Hooks** (1.3, 4.3)
   - Impacto: Medio (calidad)
   - Esfuerzo: Bajo (mejoras)

6. **Documentar Built-in Agents** (4.5)
   - Impacto: Medio (usabilidad)
   - Esfuerzo: Bajo (documentación)

### Baja Prioridad (Nice to Have)

7. **Métricas Avanzadas** (4.4)
   - Impacto: Bajo (nice to have)
   - Esfuerzo: Alto (dashboard)

8. **Tests de Integración** (4.9)
   - Impacto: Bajo (calidad)
   - Esfuerzo: Alto (infraestructura)

---

## 6. Recomendaciones Inmediatas

### Acción 1: Aclarar Documentación (1 día)

Crear `.claude/docs/AGENT_ARCHITECTURE.md` que explique claramente:
- Custom agents son prompts/instrucciones
- Built-in agents se invocan con Task()
- Cuándo usar cada uno

### Acción 2: Script de Validación (2 días)

Crear `.claude/scripts/validate-consistency.sh` que valide:
- Agentes referenciados existen
- Skills referenciados existen
- Comandos referenciados existen

### Acción 3: Mejorar Hooks (1 día)

Mejorar `post_edit.sh` para:
- Loguear errores a `.claude/logs/post_edit.log`
- Reportar estadísticas
- Opcionalmente fallar en errores críticos

### Acción 4: Documentación de Debugging (1 día)

Crear `.claude/docs/DEBUGGING.md` con:
- Cómo debuggear agentes
- Dónde encontrar logs
- Troubleshooting común

---

## 7. Métricas Sugeridas

Para medir el éxito de las mejoras:

1. **Tiempo promedio de ejecución por agente**
2. **Tasa de éxito por agente** (success/failure)
3. **Frecuencia de uso por agente**
4. **Tiempo de debugging** (antes vs después)
5. **Errores de consistencia detectados** (con script)

---

## 8. Conclusión

El sistema agéntico tiene una **base sólida** con buena arquitectura y separación de responsabilidades. Sin embargo, hay **confusiones críticas** sobre la invocación de agentes y **gaps importantes** en validación, observabilidad y documentación.

**Prioridades inmediatas:**
1. Aclarar documentación sobre custom vs built-in agents
2. Agregar validación de consistencia
3. Mejorar documentación de debugging
4. Mejorar manejo de errores en hooks

Con estas mejoras, el sistema será más robusto, mantenible y fácil de usar.

---

**Próximos Pasos:**
- [ ] Revisar y aprobar este análisis
- [ ] Priorizar acciones inmediatas
- [ ] Asignar tareas de implementación
- [ ] Crear issues/tickets para tracking

