# TASK: stale-chart-detector-bar-chart-false-positives

**Prioridad:** P2
**Fecha:** 2026-03-09
**Status:** BACKLOG

---

## Resumen

## Resumen

El detector de stale charts interpreta montos monetarios (eje X de gráficas de barras horizontales) como años faltantes, generando falsos positivos S0.

**Detectado en**: Triage 2026-03-09 — 8/16 stale charts son falsos positivos
**Ejemplo**: x_range=[2089062083692.68, 10109265225.0] reportado como "Missing years {2025}" cuando son pesos MDP en eje X.

## Fix requerido

Agregar heurística al stale-chart detector para distinguir:
- Eje X temporal (años/fechas) → validar cobertura de años
- Eje X monetario/numérico (bar charts) → skip validación de años

Posible: verificar si x_range values > 3000 (no puede ser un año) o usar chart_type metadata.

## Criterios de Aceptación

- [ ] Bar charts horizontales con eje X monetario no generan STALE false positive
- [ ] Charts temporales siguen detectando años faltantes correctamente

## Referencias

- Triage: `docs/reports/feedback_triage/2026-03-09.md` (SC-2, SC-3, SC-6, SC-7, SC-10, SC-11, SC-14, SC-15)

---

## Criterios de Aceptación

- [ ] TODO

---

## Referencias

- N/A
