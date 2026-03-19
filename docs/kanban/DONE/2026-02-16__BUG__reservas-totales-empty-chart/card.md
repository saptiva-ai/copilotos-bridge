---
id: "BUG-2026-02-16__reservas-totales-empty-chart"
title: "Reservas Totales devuelve chart_status=empty para promedio multi-banco"
status: "DONE"
phase: "Research"
scope_in:
  - "Diagnosticar por qué RESERVAS_ETAPA_TODAS devuelve empty para 10 bancos en ene 2023–ene 2024"
  - "Verificar si la métrica existe en bank_fact_kpis_mensual para el rango y bancos solicitados"
  - "Determinar si el handler soporta 'promedio' (no delta) para reservas_etapa_todas"
  - "Corregir el pipeline para que el prompt E2E devuelva chart con datos"
scope_out:
  - "Cambios de ETL o backfill histórico"
  - "Métricas de PE (pe_total, pe_sg) — ya resueltas en tickets anteriores"
  - "Cambios en chart_formatter coloring (ya funciona para cartera)"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 0
validation_commands:
  - "python3.11 tests/e2e/charts/test_reservas_totales_bar_chart.py"
pr_files: []
test_status: "failing"
---

# Summary
- Objective: hacer que el prompt de "promedio de Reservas Totales" para 10 bancos devuelva una gráfica de barras con datos reales.
- Constraint: no alterar el comportamiento de métricas de cartera ya validadas (cartera_total, cartera_comercial, sin_gob).

# Problema
El prompt:

```
Toma como periodo inicial enero 2023 y como periodo actual enero 2024.
Presenta una gráfica de barras donde se vea el promedio de las Reservas
Totales para los meses seleccionados entre los bancos: MONEX, INVEX,
BANCREA, SABADELL, BANCA MIFEL, MULTIVA, AFIRME, BANSI, VE POR MÁS
Y BANCO BASE. Marca a INVEX de color rojo.
Así como una tabla con: Banco | PROM Reservas Totales
```

Devuelve:
- `chart_status=empty`, 0 traces
- `title='RESERVAS_ETAPA_TODAS'` (métrica detectada correctamente)
- LLM responde: "No encontré datos de Reservas Totales para los bancos solicitados"

# Evidencia del test E2E

| Validador | Resultado |
|-----------|-----------|
| V3_METRIC_DETECTION | PASS — detectó `RESERVAS_ETAPA_TODAS` |
| V1_CHART_EXISTS | FAIL — `chart_status=empty` |
| V4_BANK_COVERAGE | FAIL — 0/10 bancos |
| V7_TABLE_DATA | FAIL — sin table_data |
| Otros 7 validadores | FAIL — cascada del empty |

Score: 3/13 passed.

# Hipótesis de causa raíz

1. **Lag de datos IFRS9**: Las métricas de reservas tienen ~5-6 meses de rezago regulatorio. Periodo ajustado a ene 2023–ene 2024 para mitigar.
2. **Handler no soporta "promedio"**: El `EvolucionBancoHandler` puede estar ruteando a `execute_delta()` (variación) en vez de un cálculo de promedio simple.
3. **SQL vacío**: La query a `bank_fact_kpis_mensual` para `reservas_etapa_todas` con estos 10 bancos y rango puede no devolver filas (¿alias resolution? ¿filtro de fechas?).

# Investigación necesaria

- [ ] Query directa a DB: `SELECT banco_norm, fecha, reservas_etapa_todas FROM bank_fact_kpis_mensual WHERE fecha BETWEEN '2023-01-01' AND '2024-01-01' AND banco_norm IN ('INVEX', 'MONEX', ...)` — verificar si hay filas.
- [ ] Trazar el code path desde `QueryRouter` → handler → SQL para este prompt específico.
- [ ] Verificar si el handler tiene whitelist de métricas para "promedio" vs "delta".
- [ ] Si el dato no existe para ene 2024, probar con periodo ene 2022–ene 2023.

# Criterios de aceptación
- [ ] `test_reservas_totales_bar_chart.py` pasa ≥11/13 validadores.
- [ ] La gráfica muestra barras horizontales con datos de reservas para ≥7/10 bancos.
- [ ] INVEX aparece en rojo, resto en gris.
- [ ] Tabla markdown presente en la respuesta con columnas Banco + PROM Reservas.

# Updates
- 2026-02-16 — Ticket creado. Test E2E escrito y ejecutado: 3/13 (metric detection OK, chart empty).
