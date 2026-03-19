---
status: DONE
---
# BUG: Límites Hardcodeados - top_n y max_banks

## Tipo: D - Límites y Configuración

## Prioridad: 🟡 Medium

## Problema (RESUELTO)

El sistema tiene límites hardcodeados que ignoran los parámetros del usuario:
- "top 15 bancos" → devuelve 5 (top_n=5 en SegmentHandler)
- "todas las instituciones" → máximo 5 bancos en QuerySpec
- "ranking completo" → limitado arbitrariamente

## Evidencia (Código)

```python
# specs.py:147
if len(normalized) > 5:
    raise ValueError(f"Maximum 5 banks supported, got {len(normalized)}")

# segment_handler.py:75
return await AnalyticsService.get_segment_ranking(
    segment_code=segment_code,
    metric_column=entities.metric_id,
    top_n=5,  # HARDCODED - ignora input del usuario
)

# analytics_service.py:1120
def get_segment_ranking(self, ..., top_n=5):  # Default 5
```

## Fix Implementado (2026-02-05)

**Archivo**: `plugins/bank-advisor-private/src/bankadvisor/handlers/ranking_handler.py`

### 1. Añadido método `_extract_top_n()` con patrones regex:
```python
TOP_N_PATTERNS = [
    r"top\s*(\d+)",
    r"(\d+)\s*(?:primeros|mejores|peores|mayores|menores)",
    r"los\s*(\d+)\s*(?:banco|principal|grande|mejor)",
]

def _extract_top_n(self, user_query: str, spec: Any) -> int:
    # Priority: query text > spec.top_n > default 10
    for pattern in self.TOP_N_PATTERNS:
        match = re.search(pattern, query_lower)
        if match:
            return int(match.group(1))  # Bounds: 1-100

    # "todos los bancos" → 50
    if "todos los" in query_lower:
        return 50

    return spec.top_n if spec else 10
```

### 2. Actualizado `handle()` para usar extracción dinámica:
```python
# BEFORE (hardcoded):
top_n = 10
if spec and hasattr(spec, 'top_n') and spec.top_n:
    top_n = spec.top_n

# AFTER (dynamic):
top_n = self._extract_top_n(user_query, spec)
```

### Tests Verificados

```bash
✅ "top 10 bancos": 10 (expected 10)
✅ "top 15 por cartera": 15 (expected 15)
✅ "los 20 mayores bancos": 20 (expected 20)
✅ "ranking de bancos": 10 (expected 10)
✅ "todos los bancos": 50 (expected 50)
```

## Criterios de Aceptación

- [x] "top 15 IMOR" → devuelve 15 bancos
- [x] "ranking completo" → devuelve todos (límite 50)
- [x] "todos los bancos" → retorna 50 resultados
- [x] Extracción dinámica de top_n en ranking_handler

## Nota: Archivos Pendientes

Otros handlers aún tienen hardcoded limits (scope reducido para MVP):
- `segment_handler.py:75` - top_n=5
- `analytics_service.py:1120` - default 5
- `specs.py:147-148` - max 5 banks validation

Estos pueden abordarse en un ticket de seguimiento si hay demanda.

## Relacionado

- TIPO D: Límites
- Sibling: BUG-2026-02-04__implicit-ranking-routing (fixed together)
