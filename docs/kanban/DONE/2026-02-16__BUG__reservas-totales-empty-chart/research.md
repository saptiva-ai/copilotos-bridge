# Research — Reservas Totales Empty Chart

## Status: Complete

## Diagnóstico

### Flujo del prompt

```
Prompt: "...promedio de las Reservas Totales para los meses seleccionados entre los bancos..."
   │
   ├─ EVOLUTION_KEYWORDS.matches()? → NO (0 keywords match)
   │   Keywords: crecimiento, evolución, variación, tendencia, histórico, etc.
   │   Prompt no contiene ninguna de estas palabras.
   │
   ├─ FINANCIAL_KEYWORDS.matches()? → NO (0 keywords match)
   │   Keywords: roa, roe, icap, imor, captación, activo total, etc.
   │   "reservas" no está en este diccionario.
   │
   ├─ Otros handlers? → NO match
   │   Ningún handler tiene "reservas" en su keyword list.
   │
   └─ FALLBACK → NL2SQL path
       │
       ├─ QuerySpecParser: "reservas totales" → "RESERVAS" → "reservas_etapa_todas" ✓
       │   (query_spec_parser.py:216, analytics_service.py:189)
       │
       └─ NL2SQL genera query pero devuelve chart_status=empty
           Title muestra: "RESERVAS_ETAPA_TODAS" (métrica detectada correctamente)
```

### Causa raíz confirmada

**Ningún handler tiene "reservas" en su keyword map.**

- `EvolucionBancoHandler._METRIC_MAP`: cartera comercial, cartera total, captación, PE — **no reservas**
- `MetricasFinancierasHandler.FINANCIAL_KEYWORDS`: ROA, ROE, ICAP, IMOR — **no reservas**
- `EVOLUTION_KEYWORDS`: crecimiento, evolución, variación — el prompt dice "promedio", no "evolución"

El prompt cae al **NL2SQL fallback**, que identifica la métrica (`RESERVAS_ETAPA_TODAS`) pero no logra construir un chart con datos.

### Datos en la fuente

- `CNBV_Cartera_Bancos_V2.xlsx` tiene `Reservas Etapa todas` para 135 instituciones, 2017-01 a 2025-11.
- Los 10 bancos del prompt están todos en la fuente.
- ETL carga a columna `reservas_etapa_todas` en `bank_fact_kpis_mensual`.
- **Los datos crudos existen** — el problema es de routing, no de data.

### Opciones de solución

**Opción A (mínima)**: Agregar `"reservas"` y variantes al `_METRIC_MAP` del `EvolucionBancoHandler`:
```python
_METRIC_MAP = {
    ...existing...
    "reservas totales": "reservas_etapa_todas",
    "reservas": "reservas_etapa_todas",
    "provisiones": "reservas_etapa_todas",
    "reservas preventivas": "reservas_etapa_todas",
}
```
Y agregar `"promedio"` a `EVOLUTION_KEYWORDS` o al menos asegurar que el handler sea alcanzado via `_parse_period_comparison()`.

**Opción B (más robusta)**: Agregar un handler dedicado para reservas/provisiones, similar a cómo `metricas_financieras_handler` maneja ROA/ROE.

**Opción C (recomendada)**: Opción A + agregar `"promedio"` como keyword de evolución. Esto permite que el prompt "promedio de Reservas Totales entre bancos" sea interceptado por `EvolucionBancoHandler`, que ya sabe manejar multi-bank via `_handle_multi_bank()`.

### Problema secundario: "promedio" no es "delta"

El prompt pide **promedio**, no **variación**. El handler actual tiene:
- `_handle_multi_bank()` → `EvolutionUseCase.execute()` (time series)
- `_handle_period_delta()` → `EvolutionUseCase.execute_delta()` (variación %)

El prompt tiene "periodo inicial ... periodo actual" que matchea `_PERIODO_LABEL` regex → entra a `_handle_period_delta()`. Pero delta calcula **variación porcentual**, no promedio.

**Se necesita un tercer path**: promedio simple entre dos fechas. O reinterpretar el prompt como delta (que al menos devolvería datos).

### Archivos a modificar

1. `plugins/bank-advisor-private/src/bankadvisor/handlers/evolucion_banco_handler.py`
   - Agregar "reservas" variantes a `_METRIC_MAP`
   - Agregar "promedio" a `EVOLUTION_KEYWORDS` (o nuevo handler path)
2. Posiblemente `plugins/bank-advisor-private/src/bankadvisor/application/use_cases/evolution.py`
   - Agregar `execute_average()` si no existe path de promedio
