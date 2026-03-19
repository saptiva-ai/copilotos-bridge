# BUG: metric-namespace-mismatch-tda-tasa-etapas

**Prioridad:** P0
**Fecha:** 2026-03-09
**Status:** BACKLOG

---

## Resumen

## Resumen

Namespace mismatch entre query_spec_parser → evolucion_banco_handler → evolution use case causa que métricas específicas (TDA, tasa de interés efectiva, distribución de etapas) se ruteen a CARTERA_TOTAL por defecto.

**Detectado en**: Triage 2026-03-09 (4/4 thumbs-down, conv `54e74d33`)
**FDBKs**: FDBK-0199, FDBK-0200, FDBK-0201, FDBK-0202
**Relacionado**: `multi-bank-comparison-routing-failures` (DOING, problemas 1 y 2)

## Root Cause

Triple gap en la cadena de metric resolution:

| Capa | Archivo | Status |
|------|---------|--------|
| Parser | query_spec_parser.py:284 `"tda" → "TDA"` | ✅ OK |
| Handler | evolucion_banco_handler.py:_METRIC_MAP | ❌ Sin entrada TDA |
| Use case | evolution.py:_HIP_TO_COLUMN | ❌ Sin mapping `"tda" → "tda_cartera_total"` |

La columna BD `tda_cartera_total` existe pero no hay puente desde el parser.

## Métricas afectadas

- **TDA**: parser reconoce → handler no → use case no → fallback a cartera_total (MDP en vez de %)
- **Tasa interés efectiva**: parser mapea a TASA_SISTEMA → handler no lo conecta con tasa_mn/tasa_me
- **Distribución de etapas**: no existe en ningún metric map → empty result

## Fix requerido

1. **evolucion_banco_handler.py:_METRIC_MAP**: Agregar entradas para TDA y variantes
2. **evolution.py:_HIP_TO_COLUMN**: Agregar `"tda" → "tda_cartera_total"`
3. **Audit completo**: Comparar TODAS las métricas de query_spec_parser.METRIC_MAP vs _METRIC_MAP del handler para detectar gaps adicionales
4. Evaluar si distribución de etapas requiere handler nuevo o extensión del existente

## Archivos a modificar

- `plugins/bank-advisor-private/src/bankadvisor/handlers/evolucion_banco_handler.py` (_METRIC_MAP ~L129-213)
- `plugins/bank-advisor-private/src/bankadvisor/application/use_cases/evolution.py` (_HIP_TO_COLUMN ~L55-65)
- `plugins/bank-advisor-private/src/bankadvisor/services/query_spec_parser.py` (referencia)

## Criterios de Aceptación

- [ ] "TDA de cartera total" multi-banco devuelve porcentajes TDA (no MDP)
- [ ] "Tasa de interés efectiva" multi-banco devuelve tasas correctas
- [ ] Audit de métricas parser vs handler: 0 gaps sin documentar
- [ ] E2E replay de FDBK-0199 a FDBK-0202 pasa

## Referencias

- Triage: `docs/reports/feedback_triage/2026-03-09.md`
- Deep investigation: `docs/kanban/DOING/2026-03-06__BUG__multi-bank-comparison-routing-failures/card.md`

---

## Criterios de Aceptación

- [ ] TODO

---

## Referencias

- N/A
