---
id: "BUG-2026-02-16__imor-variation-scatter-instead-of-bar"
title: "IMOR variation prompt devuelve scatter chart en vez de bar chart de variacion"
status: "BACKLOG"
phase: "Research"
scope_in:
  - "Diagnosticar por que el prompt de variacion IMOR multi-banco produce scatter (time series) en vez de bar chart horizontal"
  - "Determinar si EvolucionBancoHandler debe aceptar IMOR para el path de delta, o si se necesita un handler nuevo"
  - "Implementar soporte de variacion bar chart para IMOR entre dos periodos"
  - "Validar que no haya regresion en queries IMOR existentes (single-bank time series, ranking, comparative)"
scope_out:
  - "Cambios en el formato de scatter chart existente para IMOR single-bank"
  - "Cambios en MetricasFinancierasHandler para queries que ya funcionan"
  - "Soporte de promedios (AVG) para IMOR — solo variacion delta"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 0
validation_commands:
  - "python3.11 tests/e2e/charts/test_variacion_imor_bar_chart.py"
  - "python3.11 -m pytest plugins/bank-advisor-private/tests/unit/test_evolucion_handler.py -x"
pr_files: []
test_status: "failing"
---

# Summary
- Objective: hacer que el prompt de "variacion de IMOR" para 10 bancos entre dos periodos devuelva una grafica de barras horizontal con variacion porcentual, colores (INVEX rojo), y table_data de 4 columnas.
- Constraint: no alterar el comportamiento de queries IMOR existentes (single-bank time series via MetricasFinancierasHandler, comparative ratios, rankings).

# Problema
El prompt:

```
Toma como periodo inicial enero 2024 y como periodo actual enero 2025.
Compara el IMOR entre el periodo inicial y el periodo final entre los
bancos: MONEX, INVEX, BANCREA, SABADELL, BANCA MIFEL, MULTIVA, AFIRME,
BANSI, VE POR MAS Y BANCO BASE.
Presenta el dato del periodo inicial, el dato del periodo final y la
variacion entre el periodo inicial.
Donde la variacion es = (periodo actual / periodo inicial -1)
Haz una grafica de barras donde se vea la variacion graficada y marca
a INVEX de color rojo. Asi como una tabla con:
Banco | IMOR 2024 | IMOR 2025 | % Variacion
```

Devuelve:
- **scatter chart** (10 traces, time series) en vez de **horizontal bar chart** (variacion)
- Sin colores highlight (INVEX no marcado en rojo)
- Sin `table_data` (4 columnas esperadas)
- Sin variacion porcentual calculada
- Titulo: "Comparacion de IMOR: INVEX, AFIRME, ..." (correcto en metrica, incorrecto en tipo de chart)

# Evidencia del test E2E

| Validador | Resultado | Detalle |
|-----------|-----------|---------|
| V1 Chart exists (bar h) | FAIL | scatter en vez de bar |
| V2 Period parsing | FAIL | titulo sin 2024/2025 |
| V3 Metric detection | PASS | "IMOR" detectado correctamente |
| V4 Bank coverage | PASS | 10/10 bancos presentes |
| V5 INVEX highlight | FAIL | sin marker.color |
| V6 Neutral colors | FAIL | sin marker.color |
| V7 Zeroline | FAIL | xaxis.zeroline=None |
| V8 Table data 4 cols | FAIL | table_data ausente |
| V9 No fabrication | PASS | sin marcadores de fabricacion |
| V10 Variation values | FAIL | x_vals son fechas, no porcentajes |
| V11 Text labels | FAIL | trace.text vacio |
| V12 Table bank coverage | FAIL | table_data ausente |
| V13 No text contradiction | PASS | sin contradiccion |
| V14 Text/chart coherence | PASS | skip (no es bar chart) |
| V15 Markdown table | PASS | 10 filas, 10/10 bancos |

**Score: 6/15 passed**

# Causa raiz

```
Prompt: "Compara el IMOR ... variacion ... grafica de barras"
   |
   +-- EvolucionBancoHandler.matches()? --> NO
   |   _METRIC_EXCLUSIONS = {"imor", "morosidad", "mora", ...}
   |   "imor" esta en la exclusion list --> handler rechaza la query
   |
   +-- MetricasFinancierasHandler.matches()? --> SI
   |   FINANCIAL_KEYWORDS = {"imor": FinancialMetric.IMOR, ...}
   |   Pero este handler produce TIME SERIES (scatter), no delta bar chart
   |
   +-- Resultado: scatter chart con 10 traces de IMOR a lo largo del tiempo
       en vez de bar chart horizontal con variacion % entre ene-2024 y ene-2025
```

El `EvolucionBancoHandler` tiene el path `_handle_period_delta()` que calcula variacion porcentual y genera bar charts horizontales, pero IMOR esta bloqueado en `_METRIC_EXCLUSIONS` porque originalmente ese handler solo manejaba **crecimiento de cartera**, no ratios financieros.

# Hipotesis de solucion

**Opcion A**: Remover "imor" de `_METRIC_EXCLUSIONS` y agregar IMOR a `_METRIC_MAP` del `EvolucionBancoHandler`. Riesgo: queries como "IMOR de INVEX" (single-bank, sin periodo comparativo) podrian dejar de llegar a `MetricasFinancierasHandler`.

**Opcion B**: Condicionar la exclusion: solo excluir IMOR cuando NO hay patron de comparacion de periodos. Si hay `_parse_period_comparison()` match + multi-banco, permitir IMOR en el handler.

**Opcion C**: Crear un handler dedicado `VariacionRatioHandler` que maneje variacion % de ratios (IMOR, ICOR, ICAP) entre periodos. Mas limpio pero mas codigo.

**Recomendacion**: Opcion B — exclusion condicional. Minimo cambio, maximo impacto.

# Acceptance criteria
1. El test E2E `test_variacion_imor_bar_chart.py` pasa >= 11/15 validators
2. Sin regresion en tests unitarios existentes de EvolucionBancoHandler (80/80)
3. Queries "IMOR de INVEX" (single-bank) siguen produciendo time series scatter
4. Queries "ranking de IMOR" siguen funcionando via ranking handler
