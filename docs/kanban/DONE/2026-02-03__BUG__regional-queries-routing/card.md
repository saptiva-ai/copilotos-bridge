---
status: DONE
---
# BUG: Queries Regionales - Routing y Datos No Utilizados

## Tipo: A/C - Routing + Datos Existentes No Usados

## Prioridad: 🔴 Critical

## Estado: RESUELTO ✅

## Problema

Las queries regionales fallan aunque los datos SÍ existen:
- "cartera comercial por estado" → "No tengo datos" (FALSO)
- "distribución por región" → Error técnico
- "cartera en CDMX" → No encuentra datos

Los datos EXISTEN en `bank_mv_cartera_por_estado` (verificado Oct 2025).

## Causa Raíz Identificada

**Handler Chain Conflict**: `ResumenSistemaHandler` (posición 4) matcheaba queries con "concentración" antes de que `CarteraRegionHandler` (posición 9) pudiera procesarlas.

Query: "concentración por estado"
- ResumenSistemaHandler.matches("concentración") → TRUE ❌
- CarteraRegionHandler nunca ve la query

## Solución Implementada (2026-02-05)

### 1. Regional Exclusions en ResumenSistemaHandler

```python
# plugins/bank-advisor-private/src/bankadvisor/handlers/resumen_sistema_handler.py

REGIONAL_EXCLUSIONS = {
    "por estado", "por estados", "por región", "por region", "por regiones",
    "por entidad", "por entidades", "entidad federativa", "entidades federativas",
    "geográfica", "geografica", "geográfico", "geografico",
    "norte", "sur", "centro", "occidente", "sureste", "noroeste", "noreste",
}

def matches(self, user_query: str, ...) -> bool:
    query_lower = user_query.lower()
    
    # FIX: Yield to CarteraRegionHandler if regional qualifier present
    if any(exclusion in query_lower for exclusion in REGIONAL_EXCLUSIONS):
        logger.debug("handler.resumen_sistema.yield_to_regional", ...)
        return False
    
    return any(keyword in query_lower for keyword in SISTEMA_KEYWORDS)
```

### 2. Unit Tests (32 tests)

```
plugins/bank-advisor-private/tests/unit/handlers/test_resumen_sistema_handler.py
- 13 test cases for regional exclusions (should NOT match)
- 10 test cases for system keywords (should match)
- Edge cases: case insensitivity, mixed keywords
- Keyword set validation
```

### 3. E2E Regression Tests (8 tests)

```
tests/e2e/regression/test_bug_2026_02_03_regional_queries_routing.py
- 5 regional queries → CarteraRegionHandler
- 3 system queries → ResumenSistemaHandler (no regression)
```

## Archivos Modificados

1. `plugins/bank-advisor-private/src/bankadvisor/handlers/resumen_sistema_handler.py`
   - Added `REGIONAL_EXCLUSIONS` set (lines 64-86)
   - Updated `matches()` to check exclusions first (lines 98-119)

2. `plugins/bank-advisor-private/tests/unit/handlers/test_resumen_sistema_handler.py` (NEW)

3. `tests/e2e/regression/test_bug_2026_02_03_regional_queries_routing.py` (NEW)

## Verificación

```bash
# Unit tests: 32/32 passed
cd plugins/bank-advisor-private && .venv/bin/pytest tests/unit/handlers/test_resumen_sistema_handler.py -v

# E2E tests: 8/8 passed  
python tests/e2e/regression/test_bug_2026_02_03_regional_queries_routing.py

# Regression (no breakage): 5/5 passed
python tests/e2e/regression/test_bug_2026_02_04_bank_code_hallucination.py
python tests/e2e/regression/test_bug_2026_02_04_temporal_context_bleeding.py
```

## Criterios de Aceptación

- [x] "cartera por entidad federativa" → datos de MV
- [x] "distribución geográfica INVEX" → chart con regiones
- [x] "concentración por estado" → regional data (not time series)
- [x] System queries still work (no regression)

## Relacionado

- TIPO A: Desincronización (para coherencia texto/datos) - Separate ticket

## Feedback Vinculado

**4 reporte(s)** de usuarios en producción.

| # | Feedback ID | Usuario | Query | Feedback | Fecha |
|---|-------------|---------|-------|----------|-------|
| 1 | FDBK-0022 | `7f5aa3b9` | cual es la distribucion por estado de la cartera comercia... | no me entrego el resultado | 2026-02-03 |
| 2 | FDBK-0023 | `7f5aa3b9` | cual es la concentracion por estado de la cartera comerci... | se rompio | 2026-02-03 |
| 3 | FDBK-0024 | `7f5aa3b9` | CARTERA_COMERCIAL de INVEX de 2025 puedes mostrar un comp... | Ya no presenta el detalle por estado | 2026-02-03 |
| 4 | FDBK-0025 | `7f5aa3b9` | puedes darme el detalle de la cartera comercial de invex ... | No tomo en cuenta los estados precargados | 2026-02-03 |

<details>
<summary>Detalle completo de feedbacks</summary>

### FDBK-0022
- **User**: `7f5aa3b9-8f98-459e-abc2-0148b23486f9`
- **Conversation**: `06dbbe9d-64f8-452a-a656-c1ee531d2ecd`
- **Message**: `dcf2be1c-20df-467c-bd0a-113f739b0f37`
- **Rating**: 👎
- **Query**: "cual es la distribucion por estado de la cartera comercial de invex?"
- **Feedback**: "no me entrego el resultado"
- **Fecha**: 2026-02-03T17:54:58.298Z

### FDBK-0023
- **User**: `7f5aa3b9-8f98-459e-abc2-0148b23486f9`
- **Conversation**: `06dbbe9d-64f8-452a-a656-c1ee531d2ecd`
- **Message**: `54e37640-39cc-4e80-ade9-9a908025dd3c`
- **Rating**: 👎
- **Query**: "cual es la concentracion por estado de la cartera comercial de invex"
- **Feedback**: "se rompio"
- **Fecha**: 2026-02-03T17:55:20.004Z

### FDBK-0024
- **User**: `7f5aa3b9-8f98-459e-abc2-0148b23486f9`
- **Conversation**: `06dbbe9d-64f8-452a-a656-c1ee531d2ecd`
- **Message**: `85d1061d-b7d3-4b66-ab1e-74b82461b356`
- **Rating**: 👎
- **Query**: "CARTERA_COMERCIAL de INVEX de 2025 puedes mostrar un comparativo por region? (Cartera Comercial)"
- **Feedback**: "Ya no presenta el detalle por estado"
- **Fecha**: 2026-02-03T17:56:53.272Z

### FDBK-0025
- **User**: `7f5aa3b9-8f98-459e-abc2-0148b23486f9`
- **Conversation**: `06dbbe9d-64f8-452a-a656-c1ee531d2ecd`
- **Message**: `5ee79c81-4eaf-4227-9407-b62b743b53d8`
- **Rating**: 👎
- **Query**: "puedes darme el detalle de la cartera comercial de invex por entidad federativa"
- **Feedback**: "No tomo en cuenta los estados precargados"
- **Fecha**: 2026-02-03T17:58:33.182Z

</details>
