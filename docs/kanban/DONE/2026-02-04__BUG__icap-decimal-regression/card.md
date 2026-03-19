---
status: DONE
---
# BUG: ICAP Decimal Shift - Regresión Post-Fix

**Prioridad:** P0 - Critical (Regression)
**Fecha:** 2026-02-04
**Reportado por:** cb6c6879-e598
**Status:** DOING

---

## Resumen

El bug de "decimal shift" en valores de ICAP ha regresado. El sistema muestra ICAP de 2005.94% cuando debería ser ~20.05%. Este bug fue "resuelto" en `2026-01-30__BUG__icap-decimal-shift` pero hay reportes nuevos del 2026-02-04.

**Impacto:** Datos de ICAP completamente incorrectos, pérdida de confianza del usuario

---

## Caso Reportado

### Feedback del Usuario
**Fecha:** 2026-02-04 09:40 (CDMX)
**Conv:** f75ee002-0082-46e8-913a-32e58d17327b
**Message ID:** e1c3db60-265a-4b30-ac75-b24d6ce26608

**Query:** `cuanto ha crecido o disminuido el ICAP de BBVA en 2025 ?`

**Respuesta del Sistema:**
```
El ICAP_TOTAL de BBVA ha crecido 4.5% en el periodo analizado de 2025.
El valor actual del ICAP_TOTAL de BBVA es 2005.94%
```

**Feedback:** "el valor actual del icap de bbva no puede ser de 2005.94% como respondió"

### Valor Correcto
```sql
SELECT fecha, banco_norm, icap_total
FROM bank_fact_kpis_mensual
WHERE banco_norm = 'BBVA' AND fecha >= '2025-01-01'
ORDER BY fecha DESC LIMIT 1;

-- Resultado esperado: ~19.97% o ~20.05% (NO 2005.94%)
```

---

## Análisis Técnico

### Evidencia del Error

Del contexto del feedback:
```json
{
  "data_returned": {
    "type": "error",
    "metric_name": "CUANTO HA CRECIDO O DISMINUIDO EL ICAP DE BBVA EN 2025 ?",
    "chart_status": "error",
    "metadata": {
      "time_range_note": "Datos disponibles desde 2017. Año 2005 no tiene datos."
    }
  }
}
```

**Problemas identificados:**
1. El `metric_name` es el query completo, no "ICAP" - indica routing incorrecto
2. El `chart_status: 'error'` indica que el chart pipeline falló
3. El sistema interpretó "2005" como año, no como el valor corrupto
4. El LLM generó el valor 2005.94% sin consultar la DB

### Historial del Fix Original

El ticket `2026-01-30__BUG__icap-decimal-shift` documentó:
- Causa: Multiplicación incorrecta en `skip_multiply` list
- Fix: Agregar ICAP a lista de métricas que no se multiplican
- Status: DONE

### Posibles Causas de la Regresión

1. **Routing incorrecto** - La query no llegó al handler correcto
2. **Cache corrupto** - Datos viejos pre-fix siendo retornados
3. **Path alternativo** - La query siguió un pipeline diferente que no tiene el fix
4. **LLM hallucination** - El sistema no ejecutó SQL y el LLM inventó el valor

---

## Archivos a Investigar

1. **Fix original:**
   - `plugins/bank-advisor-private/src/bankadvisor/handlers/icap_handler.py`
   - `plugins/bank-advisor-private/src/bankadvisor/tools/portfolio_tools.py`

2. **Routing:**
   - `apps/backend/src/services/bank_analytics_client.py`
   - `plugins/bank-advisor-private/src/main.py`

3. **Decimal handling:**
   - Buscar `skip_multiply` o `decimal_shift` en el codebase

---

## Verificación Requerida

```sql
-- 1. Verificar valor correcto en DB (ejecutar en servidor de producción)
SELECT fecha, banco_norm, icap_total
FROM bank_fact_kpis_mensual
WHERE banco_norm = 'BBVA' AND fecha >= '2025-01-01'
ORDER BY fecha DESC LIMIT 3;
```

```
-- 2. Probar query en el sistema
-- Query: "cual es el ICAP de BBVA"
-- Esperado: ~19.97% o ~20.05%
-- NO esperado: 2005.94% o 1997.00%
```

---

## Criterios de Aceptación

- [ ] Query "ICAP de BBVA" devuelve valor entre 10% y 30%
- [ ] No hay valores > 100% para ICAP
- [ ] El chart se genera correctamente (no error)
- [ ] La métrica se identifica como "ICAP", no como el query completo

---

## Referencias

- Ticket original (DONE, regresión): `2026-01-30__BUG__icap-decimal-shift`
- Feedback anteriores resueltos (2026-01-29):
  - 29ccb7e3: "2005.94% no es real, recorre el punto decimal"
  - 4e396081: "mueve el punto en el valor del ICAP"
  - d8858b3f: "mueve el punto mostrando datos erroneos"

## Feedback Vinculado

**1 reporte(s)** de usuarios en producción.

| # | Feedback ID | Usuario | Query | Feedback | Fecha |
|---|-------------|---------|-------|----------|-------|
| 1 | FDBK-0038 | `cb6c6879` | cuanto ha crecido o disminuido el ICAP de BBVA en 2025 ? | el valor actual del icap de bbva no puede ser de 2005.94% como respondió | 2026-02-04 |

<details>
<summary>Detalle completo de feedbacks</summary>

### FDBK-0038
- **User**: `cb6c6879-e598-439a-881d-c92c93b6cd2b`
- **Conversation**: `f75ee002-0082-46e8-913a-32e58d17327b`
- **Message**: `e1c3db60-265a-4b30-ac75-b24d6ce26608`
- **Rating**: 👎
- **Query**: "cuanto ha crecido o disminuido el ICAP de BBVA en 2025 ?"
- **Feedback**: "el valor actual del icap de bbva no puede ser de 2005.94% como respondió"
- **Fecha**: 2026-02-04T15:40:55.134Z

</details>
