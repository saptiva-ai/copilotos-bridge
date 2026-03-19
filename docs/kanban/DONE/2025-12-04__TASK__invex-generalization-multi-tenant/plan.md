# Plan de Implementación: Generalización BankAdvisor

> **Fecha de creación:** 2026-01-09
> **Estado:** ✅ COMPLETADO
> **Estimación original:** 4-6 horas
> **Tiempo real:** ~3 horas

---

## 1. Objetivo del plan

Eliminar el acoplamiento a INVEX en BankAdvisor para habilitarlo como producto multi-banco/multi-tenant, manteniendo retrocompatibilidad con deploys existentes de INVEX.

---

## 2. Principios de diseño

### 2.1 Configuration over Hardcoding

```
ANTES: Hardcode → "INVEX" en código
DESPUÉS: Config → perfil de tenant define primary_bank
```

### 2.2 Explicit over Implicit

```
ANTES: Sin banco → asume INVEX silenciosamente
DESPUÉS: Sin banco → pide clarificación o usa benchmark neutral
```

### 2.3 Backward Compatibility

```
ANTES: Deploy INVEX funciona con hardcodes
DESPUÉS: Deploy INVEX funciona igual usando invex.yaml profile
```

---

## 3. Arquitectura propuesta: Bank Context

### 3.1 Modelo de estado

```typescript
interface BankContext {
  // Modo de determinación del banco
  bank_mode: 'explicit' | 'inferred' | 'needs_clarification' | 'system_benchmark';

  // Banco(s) seleccionado(s)
  bank_id: string | null;
  bank_name: string | null;
  banks: string[];

  // Fuente de la determinación
  source: 'user_selection' | 'query_mention' | 'tenant_config' | 'default_neutral';

  // Flag de tenant bloqueado
  tenant_locked: boolean;
}
```

### 3.2 Reglas de determinación

```
┌─────────────────────────────────────────────────────────────┐
│              ÁRBOL DE DECISIÓN: BANK CONTEXT                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [Usuario envía query]                                       │
│         │                                                    │
│         ▼                                                    │
│  ¿Menciona banco explícitamente?                             │
│         │                                                    │
│    ┌────┴────┐                                               │
│   SÍ        NO                                               │
│    │         │                                               │
│    ▼         ▼                                               │
│  bank_mode   ¿Es query comparativa/ranking?                  │
│  =explicit        │                                          │
│    │         ┌────┴────┐                                     │
│    │        SÍ        NO                                     │
│    │         │         │                                     │
│    │         ▼         ▼                                     │
│    │    bank_mode  ¿tenant_locked = true?                    │
│    │    =system_       │                                     │
│    │    benchmark  ┌───┴───┐                                 │
│    │         │    SÍ      NO                                 │
│    │         │     │       │                                 │
│    │         │     ▼       ▼                                 │
│    │         │  bank_mode  bank_mode                         │
│    │         │  =inferred  =needs_                           │
│    │         │  (usar      clarification                     │
│    │         │  primary)   (preguntar)                       │
│    │         │     │       │                                 │
│    └─────────┴─────┴───────┘                                 │
│                    │                                         │
│                    ▼                                         │
│             [Continuar pipeline]                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Fases de implementación

### Fase 1: Frontend - UI Neutral ✅

**Objetivo:** Eliminar hardcodes de INVEX en componentes de UI

**Archivos a modificar:**
- `apps/web/src/components/chat/BankAdvisorHints.tsx`

**Cambios específicos:**

```typescript
// ANTES
export const DEFAULT_BANK_ADVISOR_QUESTIONS = [
  "¿Cómo ha evolucionado la cartera vencida de INVEX...",
  "Compárame la cartera vencida de INVEX contra...",
  ...
];

// DESPUÉS
export const DEFAULT_BANK_ADVISOR_QUESTIONS = [
  "¿Cuál es el ranking de bancos por IMOR?",
  "Muéstrame la evolución del IMOR del sistema bancario",
  "¿Cuáles son los 5 bancos con mejor capitalización?",
  "Compara el ICOR de los principales bancos",
  "¿Cómo ha evolucionado la cartera total del sistema?",
];

// NUEVO: Templates para preguntas específicas de banco
export const BANK_SPECIFIC_QUESTION_TEMPLATES = [
  "¿Cómo ha evolucionado la cartera vencida de {BANCO}...",
  ...
];

export function getBankSpecificQuestions(bankName: string): string[] {
  return BANK_SPECIFIC_QUESTION_TEMPLATES.map(t => t.replace("{BANCO}", bankName));
}
```

**Criterio de éxito:**
- [ ] DEFAULT_BANK_ADVISOR_QUESTIONS no contiene "INVEX"
- [ ] Función getBankSpecificQuestions() disponible para uso futuro

---

### Fase 2: Backend - Lógica Neutral ✅

**Objetivo:** Eliminar inferencia automática de INVEX

#### 2.1 Eliminar aliases posesivos

**Archivo:** `plugins/bank-advisor-private/src/bankadvisor/services/query_spec_parser.py`

```python
# ANTES
BANK_ALIASES: Dict[str, str] = {
    "invex": "INVEX",
    "banco invex": "INVEX",
    "mi banco": "INVEX",      # ← ELIMINAR
    "del banco": "INVEX",     # ← ELIMINAR
    "nuestro banco": "INVEX", # ← ELIMINAR
    "nuestro": "INVEX",       # ← ELIMINAR
    "sistema": "SISTEMA",
    ...
}

# DESPUÉS
BANK_ALIASES: Dict[str, str] = {
    "invex": "INVEX",
    "banco invex": "INVEX",
    # NOTE: Possessive pronouns removed (BUG-07 fix)
    "sistema": "SISTEMA",
    ...
}
```

#### 2.2 Eliminar regex "mi" + métrica

**Archivo:** `plugins/bank-advisor-private/src/bankadvisor/services/query_spec_parser.py`

```python
# ANTES
def _extract_banks_heuristic(self, user_query: str) -> List[Optional[str]]:
    ...
    mi_pattern = r'\bmi\s+(imor|icor|...)'
    if re.search(mi_pattern, query_lower):
        found_banks.append("INVEX")  # ← ELIMINAR BLOQUE
    ...

# DESPUÉS
def _extract_banks_heuristic(self, user_query: str) -> List[Optional[str]]:
    ...
    # NOTE: Possessive "mi" pattern REMOVED (BUG-07 fix)
    # Previously: "mi IMOR" -> INVEX. Now triggers clarification.
    ...
```

#### 2.3 Cambiar default de apply_bank_default

**Archivo:** `plugins/bank-advisor-private/src/bankadvisor/runtime_config.py`

```python
# ANTES
@property
def apply_bank_default(self) -> bool:
    return self._get("defaults", "apply_bank_default", default=True)

# DESPUÉS
@property
def apply_bank_default(self) -> bool:
    """Whether to auto-add primary bank when metric+date but no bank.

    NOTE: Changed default to False for multi-tenant support (BUG-07 fix).
    """
    return self._get("defaults", "apply_bank_default", default=False)
```

**Criterio de éxito:**
- [ ] BANK_ALIASES no tiene "mi banco", "del banco", "nuestro"
- [ ] Regex "mi" + métrica eliminado
- [ ] apply_bank_default default es False

---

### Fase 3: Configuración de Perfiles ✅

**Objetivo:** Mantener retrocompatibilidad con deploys INVEX existentes

#### 3.1 Actualizar invex.yaml

**Archivo:** `plugins/bank-advisor-private/config/profiles/invex.yaml`

```yaml
# AGREGAR al final:
tenant:
  # When true, this deployment is locked to a single bank
  locked: true
  display_notice: "Mostrando datos de INVEX (cambiar banco)"
```

#### 3.2 Actualizar template.yaml

**Archivo:** `plugins/bank-advisor-private/config/profiles/template.yaml`

```yaml
defaults:
  # Set to false for multi-tenant (triggers clarification)
  apply_bank_default: false

tenant:
  locked: false
  # display_notice: "Mostrando datos de <BANK> (cambiar banco)"
```

**Criterio de éxito:**
- [ ] invex.yaml tiene tenant.locked = true
- [ ] template.yaml tiene apply_bank_default = false

---

### Fase 4: Bug SISTEMA ✅

**Objetivo:** Agregar nota explicativa cuando SISTEMA representa promedio

#### 4.1 Agregar sistema_note a metadata

**Archivo:** `plugins/bank-advisor-private/src/main.py`

```python
# En _try_hu3_nlp_pipeline(), antes de agregar metadata:

# BUG-10 FIX: Add SISTEMA aggregation note if applicable
sistema_note = None
if entities.banks and "SISTEMA" in [b.upper() for b in entities.banks]:
    sistema_note = config.get_sistema_note(entities.metric_id)
    if sistema_note:
        logger.info("hu3_nlp.sistema_note_added", metric=entities.metric_id)

# ... después de crear metadata:
if sistema_note:
    data["metadata"]["sistema_note"] = sistema_note
```

**Criterio de éxito:**
- [ ] Cuando query incluye SISTEMA, metadata tiene sistema_note si aplica

---

### Fase 5: Pruebas y Validación ✅

**Objetivo:** Verificar que los cambios funcionan y no hay regresiones

#### 5.1 Tests unitarios

**Archivo nuevo:** `tests/unit/clarification/test_bank_context.py`

```python
class TestBankDetection:
    def test_explicit_bank_detection(self):
        """Bancos explícitos se detectan correctamente"""

    def test_no_bank_triggers_clarification(self):
        """Query sin banco NO asume INVEX"""

    def test_possessive_pronouns_no_longer_default_invex(self):
        """'mi', 'nuestro' ya no infieren INVEX"""

class TestInvexHardcodeRemoval:
    def test_default_questions_no_invex_hardcode(self):
        """DEFAULT_BANK_ADVISOR_QUESTIONS no tiene INVEX"""

    def test_bank_aliases_no_possessive_invex_mapping(self):
        """BANK_ALIASES no mapea posesivos a INVEX"""

class TestSistemaNote:
    def test_icap_has_sistema_note(self):
        """ICAP tiene nota de SISTEMA (es promedio)"""
```

#### 5.2 Smoke check script

**Archivo nuevo:** `scripts/smoke_check_invex_hardcode.sh`

```bash
#!/bin/bash
# Falla si encuentra hardcodes problemáticos

# Check 1: DEFAULT_BANK_ADVISOR_QUESTIONS
# Check 2: BANK_ALIASES con posesivos
# Check 3: apply_bank_default default True
# Check 4: System prompts con INVEX
```

**Criterio de éxito:**
- [ ] Test unitarios pasan
- [ ] Smoke check pasa (exit 0)

---

## 5. Resultados de implementación

### 5.1 Archivos modificados (6)

| Archivo | Estado | Cambio principal |
|---------|--------|------------------|
| `BankAdvisorHints.tsx` | ✅ | Preguntas neutrales |
| `runtime_config.py` | ✅ | default False |
| `query_spec_parser.py` | ✅ | Sin aliases posesivos |
| `invex.yaml` | ✅ | tenant.locked |
| `template.yaml` | ✅ | Multi-tenant ready |
| `main.py` | ✅ | sistema_note |

### 5.2 Archivos nuevos (3)

| Archivo | Estado | Propósito |
|---------|--------|-----------|
| `test_bank_context.py` | ✅ | Tests unitarios |
| `smoke_check_invex_hardcode.sh` | ✅ | Smoke check CI |
| `bankadvisor-generalization.md` | ✅ | Documentación |

### 5.3 Smoke check final

```
======================================
INVEX Hardcode Smoke Check
======================================

[1/4] Checking BankAdvisorHints.tsx...
   ✅ PASS: DEFAULT_BANK_ADVISOR_QUESTIONS is bank-neutral
[2/4] Checking QuerySpecParser BANK_ALIASES...
   ✅ PASS: No possessive -> INVEX mappings in BANK_ALIASES
[3/4] Checking runtime_config.py defaults...
   ✅ PASS: apply_bank_default defaults to False
[4/4] Checking registry.yaml prompts...
   ✅ PASS: System prompts are bank-neutral

======================================
RESULT: ✅ PASSED (No INVEX hardcodes in critical paths)
```

---

## 6. Trabajo futuro (no incluido)

### 6.1 Frontend: BankSelector component

**Descripción:** Dropdown con búsqueda para selección explícita de banco

```typescript
// Propuesto para futuro
<BankSelector
  value={selectedBank}
  onChange={setSelectedBank}
  options={bankList}
  placeholder="Selecciona un banco..."
/>
```

**Razón de exclusión:** Requiere cambios en estado de conversación y API

### 6.2 Backend: Clarification flow completo

**Descripción:** Cuando bank_mode = needs_clarification, responder con opciones

```python
# Propuesto para futuro
if bank_mode == "needs_clarification":
    return {
        "type": "clarification",
        "message": "¿De qué banco te gustaría ver los datos?",
        "options": get_top_banks(10)
    }
```

**Razón de exclusión:** Requiere cambios en UX de clarificación

### 6.3 Tests E2E

**Descripción:** Tests de integración con Docker que validen flujo completo

**Razón de exclusión:** Requiere infraestructura de CI completa

---

## 7. Lecciones aprendidas

### 7.1 Lo que funcionó bien

- **Búsqueda exhaustiva inicial:** Encontrar TODOS los hardcodes antes de empezar evitó sorpresas
- **Retrocompatibilidad por perfil:** Usar invex.yaml con tenant.locked preserva comportamiento existente
- **Smoke check automatizado:** Script bash simple pero efectivo para CI

### 7.2 Lo que podría mejorar

- **Tests E2E desde el inicio:** Hubiera sido útil tener tests E2E antes de los cambios
- **Documentación de SISTEMA:** Ya existía la nota en synonyms.yaml pero no se usaba

### 7.3 Recomendaciones para futuros cambios similares

1. **Siempre buscar exhaustivamente** antes de empezar
2. **Crear smoke check primero** que falle con el estado actual
3. **Preservar comportamiento existente** vía configuración, no código
4. **Documentar en kanban** para trazabilidad

---

## 8. Referencias

- `docs/bugfixes/bankadvisor-generalization.md` - Documentación técnica
- `docs/kanban/BACKLOG/ISSUE-004_.../research.md` - Investigación detallada
- `docs/kanban/BACKLOG/ISSUE-003_.../issue.md` - BUG-10 original
