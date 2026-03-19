---
status: DONE
---
# BUG: Implicit Ranking Routing

## Tipo: Bug - Query Routing

## Prioridad: 🟡 Medium

## Problema

Query "¿Cuáles son los bancos más grandes por cartera?" no genera chart.

## Root Cause (FOUND)

El `IMPLICIT_RANKING` list solo tenía versiones con acentos ("más grandes") pero los usuarios frecuentemente escriben sin acentos ("mas grandes"). El handler no matcheaba queries sin acentos.

## Fix Implementado (2026-02-05)

**Archivo**: `plugins/bank-advisor-private/src/bankadvisor/handlers/ranking_handler.py`

Añadidas versiones sin acento a `IMPLICIT_RANKING`:
```python
IMPLICIT_RANKING = [
    # With accents
    "más grande", "más grandes", "más pequeño", "más pequeños",
    # Without accents (user input often lacks accents)
    "mas grande", "mas grandes", "mas pequeno", "mas pequenos",
    # Other ranking indicators
    "mayores", "menores", "mejores", "peores",
    "top ", "top\d",
    "primeros", "últimos", "ultimos",
]
```

## Tests Verificados

```bash
✅ implicit without accent: True (expected True)
✅ implicit with accent: True (expected True)
✅ top-N pattern: True (expected True)
✅ explicit ranking: True (expected True)
✅ simple metric query: False (expected False)
```

## Criterios de Aceptación

- [x] Query "¿Cuáles son los bancos más grandes por cartera?" genera chart con bancos
- [x] Query sin acentos también funciona
- [x] Pass rate se mantiene >= 97.5%

## Relacionado

- Parent: BUG-2026-02-03__ranking-data-extraction-failures (DONE - 97.5%)
- Sibling: BUG-2026-02-03__hardcoded-limits-top-n (fixed together)
