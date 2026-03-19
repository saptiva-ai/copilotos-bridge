# ISSUE-004: Generalización BankAdvisor - Eliminación Acoplamiento INVEX

> **Fuente:** Solicitud de producto para habilitar BankAdvisor como solución multi-banco/multi-tenant.
> **Fecha de creación:** 2026-01-09
> **Estado:** ✅ COMPLETADO (implementación core)
> **Prioridad:** Alta
> **Tipo:** Feature + Bug Fix + Technical Debt

---

## Resumen ejecutivo

BankAdvisor fue desarrollado inicialmente como producto específico para INVEX. A medida que se expande a nuevos clientes bancarios, se identificaron **acoplamientos hardcodeados** que impiden su uso neutral:

1. **UI con sesgo:** Preguntas sugeridas mencionan "INVEX" explícitamente
2. **Backend con default INVEX:** El sistema asume INVEX cuando el usuario no especifica banco
3. **Pronombres posesivos → INVEX:** "mi IMOR", "mi cartera" se interpretan automáticamente como "IMOR de INVEX"
4. **Bug relacionado:** "SISTEMA < INVEX" para métricas como ICAP (confusión promedio vs suma)

### Impacto de negocio

| Aspecto | Problema | Impacto |
|---------|----------|---------|
| **Ventas** | No se puede hacer demo a otros bancos sin ver "INVEX" | Bloquea pipeline comercial |
| **Producto** | Parece herramienta interna de INVEX, no producto SaaS | Percepción de producto inmaduro |
| **Confianza** | Usuario pregunta por BBVA y sistema responde con datos INVEX | Pérdida de credibilidad |
| **Soporte** | Cada nuevo cliente requiere fork o parches manuales | Costo operativo insostenible |

---

## Evidencias del problema

### Evidencia 1: UI - Preguntas sugeridas hardcodeadas

**Archivo:** `apps/web/src/components/chat/BankAdvisorHints.tsx`

**Código problemático (ANTES):**
```typescript
export const DEFAULT_BANK_ADVISOR_QUESTIONS = [
  "¿Cómo ha evolucionado la cartera vencida de INVEX en los últimos 12 meses?",
  "Compárame la cartera vencida de INVEX contra el promedio del sistema bancario.",
  "¿Cuál es la tendencia del IMOR de INVEX en 2024?",
  "Muéstrame las principales métricas de riesgo de crédito para INVEX.",
  "¿Qué tan concentrada está la cartera comercial de INVEX en 2024?",
];
```

**Comportamiento observado:**
- El usuario nuevo ve "INVEX" como única opción sugerida
- No hay forma de cambiar el banco desde la UI inicial
- Crea percepción de producto "propiedad de INVEX"

**Screenshot mental:**
```
┌─────────────────────────────────────────────┐
│ 💡 Preguntas sugeridas                      │
├─────────────────────────────────────────────┤
│ [¿Cómo ha evolucionado la cartera de INVEX?]│
│ [Compárame INVEX contra el sistema]         │
│ [IMOR de INVEX en 2024]                     │  ← Todo dice "INVEX"
│ [Métricas de riesgo de INVEX]               │
│ [Cartera comercial de INVEX]                │
└─────────────────────────────────────────────┘
```

---

### Evidencia 2: Backend - Aliases posesivos → INVEX

**Archivo:** `plugins/bank-advisor-private/src/bankadvisor/services/query_spec_parser.py`

**Código problemático (ANTES):**
```python
BANK_ALIASES: Dict[str, str] = {
    "invex": "INVEX",
    "banco invex": "INVEX",
    # INVEX inference: "mi", "del banco", "nuestro" imply INVEX
    "mi banco": "INVEX",      # ← PROBLEMA
    "del banco": "INVEX",     # ← PROBLEMA
    "nuestro banco": "INVEX", # ← PROBLEMA
    "nuestro": "INVEX",       # ← PROBLEMA
    "sistema": "SISTEMA",
    ...
}
```

**Y también patrón regex:**
```python
# Special case: "mi" + metric pattern implies INVEX
mi_pattern = r'\bmi\s+(imor|icor|icap|cartera|pdm|...)'
if re.search(mi_pattern, query_lower):
    found_banks.append("INVEX")  # ← PROBLEMA
```

**Casos de test que fallan (comportamiento actual):**

| Query del usuario | Banco detectado | Esperado |
|-------------------|-----------------|----------|
| "mi IMOR" | INVEX | ❓ Clarificación |
| "mi cartera" | INVEX | ❓ Clarificación |
| "nuestro ICAP" | INVEX | ❓ Clarificación |
| "del banco" | INVEX | ❓ Clarificación |

---

### Evidencia 3: Runtime Config - Default a INVEX

**Archivo:** `plugins/bank-advisor-private/src/bankadvisor/runtime_config.py`

**Código problemático (ANTES):**
```python
@property
def primary_bank(self) -> str:
    """Get the primary bank (default for queries without bank)."""
    return os.environ.get("PRIMARY_BANK") or self._get("banks", "primary", default="INVEX")
    #                                                                               ^^^^^^^

@property
def apply_bank_default(self) -> bool:
    """Whether to auto-add primary bank when metric+date but no bank."""
    return self._get("defaults", "apply_bank_default", default=True)
    #                                                           ^^^^
```

**Comportamiento:**
1. Usuario pregunta: "Dame el IMOR de los últimos 3 meses"
2. Sistema detecta: métrica=IMOR, fecha=3 meses, banco=None
3. `apply_bank_default=True` → agrega `primary_bank="INVEX"`
4. Respuesta habla de INVEX sin que el usuario lo pidiera

---

### Evidencia 4: Bug relacionado - SISTEMA < INVEX (BUG-10)

**Archivo:** `plugins/bank-advisor-private/config/synonyms.yaml`

**Documentación existente:**
```yaml
icap_total:
  # BUG-10: SISTEMA uses simple average (mean) for ICAP, not sum
  sistema_aggregation: "mean"
  sistema_note: "Para SISTEMA, el ICAP representa el promedio simple de todos los bancos"

tda_cartera_total:
  # BUG-10: SISTEMA uses weighted average for TDA
  sistema_aggregation: "weighted_avg"
```

**Problema observado:**
- Usuario pregunta: "ICAP de INVEX vs Sistema"
- Respuesta: INVEX=15.72%, SISTEMA=14.89%
- Usuario confundido: "¿Cómo puede INVEX ser mayor que el sistema completo?"

**Causa raíz:**
- SISTEMA para ratios (ICAP, IMOR, ICOR) es **promedio**, no suma
- Para métricas absolutas (cartera_total), SISTEMA sí es suma
- Falta indicar esto claramente al usuario

---

## Criterios de aceptación (DoD)

| # | Criterio | Verificación | Estado |
|---|----------|--------------|--------|
| **AC-1** | No hay texto "INVEX" en UI salvo selección explícita del usuario | Smoke check + visual | ✅ |
| **AC-2** | Query sin banco explícito NO asume INVEX silenciosamente | Test unitario | ✅ |
| **AC-3** | Menú inicial muestra preguntas neutrales (ranking, sistema, comparativas) | Visual | ✅ |
| **AC-4** | INVEX no está preseleccionado en ningún componente | Code review | ✅ |
| **AC-5** | Para métricas con SISTEMA, se indica si es promedio/suma | Metadata check | ✅ |
| **AC-6** | Smoke check anti-hardcode pasa en CI | Script | ✅ |
| **AC-7** | Retrocompatibilidad: deploys INVEX existentes siguen funcionando | Config profile | ✅ |

---

## Archivos afectados

### Archivos modificados

| Archivo | Líneas | Cambio |
|---------|--------|--------|
| `apps/web/src/components/chat/BankAdvisorHints.tsx` | 107-134 | Preguntas neutrales + `getBankSpecificQuestions()` |
| `plugins/.../runtime_config.py` | 150-159 | `apply_bank_default` default False |
| `plugins/.../query_spec_parser.py` | 49-56, 1068-1077 | Eliminados aliases posesivos |
| `plugins/.../config/profiles/invex.yaml` | 68-86 | Bloque `tenant.locked` |
| `plugins/.../config/profiles/template.yaml` | 81-105 | Template multi-tenant |
| `plugins/.../src/main.py` | 1171-1204 | `sistema_note` en metadata |

### Archivos nuevos

| Archivo | Propósito |
|---------|-----------|
| `tests/unit/clarification/test_bank_context.py` | Tests unitarios de detección banco |
| `scripts/smoke_check_invex_hardcode.sh` | Smoke check CI anti-regresión |
| `docs/bugfixes/bankadvisor-generalization.md` | Documentación técnica del fix |
| `docs/kanban/BACKLOG/ISSUE-004_.../` | Esta documentación kanban |

---

## Historial de cambios

| Fecha | Acción | Autor |
|-------|--------|-------|
| 2026-01-09 | Issue creado, investigación completada | Claude |
| 2026-01-09 | Plan aprobado, implementación iniciada | Claude |
| 2026-01-09 | Implementación completada, smoke check pasa | Claude |
| 2026-01-09 | Documentación kanban creada | Claude |

---

## Referencias

- `docs/bugfixes/bankadvisor-generalization.md` - Documentación técnica detallada
- `docs/kanban/BACKLOG/ISSUE-003_user-reported-bugs/issue.md` - BUG-10 original (SISTEMA < INVEX)
- `plugins/bank-advisor-private/config/synonyms.yaml` - Configuración de métricas
