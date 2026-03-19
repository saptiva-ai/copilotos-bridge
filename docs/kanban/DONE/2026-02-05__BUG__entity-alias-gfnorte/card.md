---
status: REVIEW
---
# BUG: GFNORTE no reconocido como alias de BANORTE

## Status: DOING → REVIEW (verificado en PROD)

## Descripcion

El sistema no reconoce "GFNORTE" como un alias de Banorte. Cuando el usuario pregunta por GFNORTE, el sistema responde que no tiene datos.

## Feedback Relacionado

| ID | Fecha | Comentario |
|----|-------|------------|
| FDBK-0075 | 2026-02-05 | "No entiende la data" - User asked "Dime el historico del portafolio GFNORTE" |

## Root Cause

El backend (`banking_keywords.py`) ya tenía `gfnorte` para routing, pero el plugin tenía **3 diccionarios de banco independientes** sin GFNORTE:

1. `query_spec_parser.py:BANK_ALIASES` — extracción principal
2. `context_enricher.py:BANK_PATTERNS` — enriquecimiento de contexto
3. `bank_resolver.py:BANK_ALIASES` — resolución de dominio

El query llegaba al plugin pero GFNORTE no se resolvía a BANORTE.

## Fix Implementado (2026-02-08)

### Archivos modificados (4)

| Archivo | Alias agregados |
|---------|----------------|
| `plugins/.../services/query_spec_parser.py` | gfnorte, gfbanorte, grupo financiero banorte, banorte ixe → BANORTE; gfinbursa, grupo financiero inbursa → INBURSA |
| `plugins/.../services/context_enricher.py` | gfnorte, gfbanorte → BANORTE; gfinbursa → INBURSA |
| `plugins/.../domain/services/bank_resolver.py` | GFNORTE, GFBANORTE, GRUPO FINANCIERO BANORTE → BANORTE; GFINBURSA, GRUPO FINANCIERO INBURSA → INBURSA; GFINVEX → INVEX |
| `apps/backend/src/config/banking_keywords.py` | gfbanorte → banorte; gfinbursa, grupo financiero inbursa → inbursa |

### Tests

- Inline validation passed: all alias resolutions verified
- 970/981 plugin tests pass (11 pre-existing failures unrelated)

### Validación E2E en PROD (2026-02-08)

Test: `tests/e2e/regression/test_feedback_replay_2026_02_08.py`
Target: `http://localhost:18000` (SSH tunnel a PROD)

| # | ID | Query | Resultado | Detalle |
|---|-----|-------|-----------|---------|
| 1 | FDBK-0075 | Dime el historico del portafolio GFNORTE | PASSED | GFNORTE → BANORTE resolved (chart + text) |
| 2 | FDBK-0075b | IMOR de GFNORTE en 2025 | PASSED | GFNORTE → BANORTE resolved (chart + text) |
| 3 | FDBK-0075c | cartera de Grupo Financiero Banorte | PASSED | GFNORTE → BANORTE resolved (text) |

**3/3 PASSED** — El backend ya normaliza `gfnorte → banorte` via `ACRONYM_NORMALIZATIONS`
en `banking_keywords.py` (ya estaba en PROD). Los cambios en el plugin agregan
redundancia (defense in depth) para cuando el query llega directamente al plugin.

## Prioridad

Media - 1 reporte de usuario

## Feedback Vinculado

**1 reporte(s)** de usuarios en producción.

| # | Feedback ID | Usuario | Query | Feedback | Fecha |
|---|-------------|---------|-------|----------|-------|
| 1 | FDBK-0075 | `76ac87f9` | Dime el historico del portafolio GFNORTE | No entiende la data | 2026-02-05 |
