---
id: "FEAT-2026-02-16__cvc-cc-sin-castigos-metric"
title: "CVC/CC: agregar metrica Cartera Vencida Comercial sin castigos + prompt onboarding"
status: "DONE"
phase: "Implement"
scope_in:
  - "Desplegar migracion 059 (columna cvc_cc + recrea MVs)"
  - "Actualizar loader para computar CVC/CC = E3_SG / (E1_SG + E2_SG + E3_SG) sin castigos"
  - "Re-ejecutar carga con ambas formulas (imor_comercial + cvc_cc)"
  - "Reescribir 2 prompts onboarding en help-onboarding-content.ts"
  - "Validar 10/10 match con Tableau para 01/2025"
scope_out:
  - "Cambios en IMORA (hip_imor_comercial) — ya corregido en BUG-2026-02-16__imor-comercial-etapa3-data-gap"
  - "Routing/handler/comparison_tools — YA IMPLEMENTADO en develop (sin commit)"
  - "Microdata CNBV (no necesaria — formula resuelta con xlsx)"
  - "Modificar la vista Cartera Vencida de Tableau"
next_action: "Actualizar prompts onboarding (Phase 4) + E2E validation (Phase 5)"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 1
validation_commands:
  - "python3.11 -m pytest -q plugins/bank-advisor-private/tests/unit/domain/test_cvc_cc_computation.py"
  - "python3.11 tests/e2e/charts/test_cvc_cc_snapshot_bar_chart.py"
  - "python3.11 tests/e2e/charts/test_peer_avg_cvc_cc_chart.py"
pr_files: []
test_status: "ready-to-implement"
related_tickets:
  - "BUG-2026-02-16__imor-comercial-etapa3-data-gap"
---

# Summary

- **Objetivo**: alinear la vista "Cartera Vencida" del chatbot con el dashboard Tableau de Bajaware.
- Tableau usa la formula **CVC/CC = E3_SG / (E1_SG + E2_SG + E3_SG)** — SIN castigos.
- Nuestro `hip_imor_comercial` almacena **IMORA = (E3_SG + Castigos) / (E1+E2+E3)** — CON castigos.
- Para 8/10 bancos los valores son identicos (castigos=0), pero **BANCA MIFEL** (1.23% vs 1.25%) y **VE POR MAS** (3.51% vs 3.52%) muestran diferencia visible.
- **10/10 bancos coinciden** cuando se usa la formula CVC/CC sin castigos.

# Vistas Tableau de referencia

## Vista 1: Ranking CVC/CC (barras horizontales, un solo periodo)

**Archivo**: `Screenshot-2026-02-16-231027.png`

- Titulo: "CATERA VENCIDA — Cartera Vencida Comercial / Cartera Comercial — 01/2025"
- Grafica: barras horizontales ordenadas de mayor a menor
- INVEX resaltado en rojo, resto en gris neutro
- Linea de promedio vertical (Promedio = 2.94%)
- Tabla lateral izquierda con valor absoluto por banco
- **Un solo periodo** (01/2025), NO es comparacion entre dos periodos

Valores de referencia (01/2025, ordenados mayor a menor):

| Banco | CVC/CC |
|-------|:------:|
| BANSI | 5.67% |
| AFIRME | 4.43% |
| MULTIVA | 4.33% |
| VE POR MAS | 3.51% |
| BANCO BASE | 2.87% |
| SABADELL | 2.58% |
| INVEX | 2.36% |
| MONEX | 1.58% |
| BANCA MIFEL | 1.23% |
| BANCREA | 0.80% |
| **Promedio** | **2.94%** |

## Vista 2: INVEX vs Promedio de pares (time series)

**Archivo**: `Screenshot-2026-02-16-232204.png`

- Titulo: "CATERA VENCIDA — Cartera Vencida Comercial / Cartera Comercial"
- Periodo: **10/2022 → 03/2025**
- Linea gris (arriba): Promedio CVC/CC de 9 pares (~2.55% en 10/2022 → ~2.95% en 03/2025)
- Linea roja (abajo): INVEX CVC/CC (~0.42% en 10/2022 → ~2.38% en 03/2025)
- Doble label en cada punto: ratio (%) + monto cartera vencida ($MDP)
- Dual Y-axis: INVEX (izq 0-5%) y Promedio (der 0-3.5%)
- INVEX tuvo salto fuerte de 0.65% → 1.97% en 10/2023

# Formulas (del TWB de Tableau)

## CVC/CC (vista "CATERA VENCIDA", TWB linea 1447)

```
E1_SG = Act.Empresarial E1 + Ent.Financieras E1   (Sin Gobierno)
E2_SG = Act.Empresarial E2 + Ent.Financieras E2   (Sin Gobierno)
E3_SG = Act.Empresarial E3 + Ent.Financieras E3   (Sin Gobierno)

CVC/CC = E3_SG / (E1_SG + E2_SG + E3_SG)         <-- SIN castigos
```

Fuente TWB: `Invex_Tablero_V3.twb` linea 1447-1448, campo `Cartera Vencida_`

```xml
<column caption='Cartera Vencida_' datatype='real' name='[Calculation_4114741983628898323]'>
  <calculation formula='[Comercial Etapa 3 (copia)...]/([Comercial Etapa 1 (copia)...]+[Comercial Etapa 2 (copia)...]+[Comercial Etapa 3 (copia)...])' />
</column>
```

## IMORA (vista "IMORA (dat)", TWB linea 1510)

```
IMORA = (E3_SG + CASTIGOS_ACUMULADOS_COMERCIAL) / (E1_SG + E2_SG + E3_SG)  <-- CON castigos
```

Ya implementada en `hip_imor_comercial` (ticket BUG-2026-02-16__imor-comercial-etapa3-data-gap).

## Diferencia entre ambas

| Aspecto | CVC/CC | IMORA |
|---------|--------|-------|
| Numerador | E3_SG | E3_SG + Castigos |
| Denominador | E1_SG + E2_SG + E3_SG | E1_SG + E2_SG + E3_SG |
| Castigos | NO incluidos | Sumados al numerador |
| Vista Tableau | "CATERA VENCIDA" (Cart_Venc) | "IMORA (dat)" |

# Estado del backend (auditado 2026-02-17)

| Componente | Estado | Archivo |
|---|---|---|
| ORM (cvc_cc column) | LISTO | `models/kpi.py:47` |
| Migracion SQL | ESCRITA, SIN DESPLEGAR | `migrations/059_add_cvc_cc.sql` |
| Routing hip_cvc_cc → cvc_cc | LISTO | `evolution.py:586`, `template_sql_generator.py:56` |
| Handler snapshot (barras) | LISTO | `evolucion_banco_handler.py:577` → `execute_hip_snapshot()` |
| Handler peer_average (lineas) | LISTO | `peer_average.py:357` |
| MetricNormalizer (x100 para %) | LISTO | `metric_normalizer.py:53` |
| comparison_tools (LLM enum) | LISTO | `comparison_tools.py:234` |
| Keywords handler | LISTO | `evolucion_banco_handler.py:155-164` (9 patrones) |
| **Datos en BD** | LISTO (4,099 filas, 201701-202511) | 10/10 match Tableau 01/2025 |
| **Prompts onboarding** | FALTA | `help-onboarding-content.ts:268-284` |

# Prompts de onboarding (corregidos)

## Preset 1: Ranking CVC/CC (barras horizontales snapshot)

**ID**: `cartera-vencida-comercial-ranking`
**Icon**: `bar-h`
**Routing esperado**: keywords "cartera vencida comercial" → `hip_cvc_cc` → `_handle_hip_snapshot()` (un solo periodo, sin `_parse_period_comparison`)

```
Muestra la razon de cartera vencida comercial entre la cartera comercial
para enero 2025 para los bancos:
MONEX, INVEX, BANCREA, SABADELL, BANCA MIFEL, MULTIVA, AFIRME, BANSI,
VE POR MAS Y BANCO BASE.
Haz una grafica de barras horizontales ordenadas de mayor a menor y marca
a INVEX de color rojo.
Incluye una tabla con: Banco | CVC/CC 01/2025
```

## Preset 2: INVEX vs Promedio (time series)

**ID**: `cartera-vencida-comercial-invex-promedio`
**Icon**: `trend`
**Routing esperado**: keywords "cartera vencida comercial" + "INVEX contra promedio" → peer_average handler con `hip_cvc_cc`

```
Crea una grafica donde se compare razon de cartera vencida comercial entre
la cartera comercial de INVEX contra el promedio de los bancos:
MONEX, BANCREA, SABADELL, BANCA MIFEL, MULTIVA, AFIRME, BANSI,
VE POR MAS Y BANCO BASE.
De octubre 2022 hasta el dato mas reciente que tengas.
```

# Fuentes de datos

| Fuente | Archivo | Uso |
|--------|---------|-----|
| Cartera por etapa | `CNBV_Cartera_Bancos_V2.xlsx` | E1_SG, E2_SG, E3_SG |
| Castigos acumulados | `Castigos Comerciales.xlsx` | Solo para IMORA (no para CVC/CC) |
| Mapeo de codigos | `Instituciones.xlsx` | Codigo -> nombre banco |

# Criterios de aceptacion

- [x] Columna `cvc_cc` existe en `bank_fact_kpis_mensual` (migracion 059 desplegada)
- [x] Loader computa CVC/CC sin castigos: E3_SG / (E1+E2+E3)
- [x] Datos cargados: 4,099 filas, periodos 201701-202511
- [x] 10/10 bancos match Tableau para 01/2025 (±0.01pp)
- [x] Promedio = 2.94%
- [ ] Prompt ranking reescrito (snapshot un solo periodo, barras horizontales)
- [ ] Prompt INVEX vs promedio reescrito (time series desde 10/2022)
- [ ] E2E snapshot test pasa: `test_cvc_cc_snapshot_bar_chart.py`
- [ ] E2E peer avg test pasa: `test_peer_avg_cvc_cc_chart.py`

# Updates

- 2026-02-16 - Ticket creado con investigacion completa. Formula CVC/CC confirmada del TWB. 10/10 match verificado.
- 2026-02-17 - Auditoria de backend: routing/handler/ORM ya implementados en develop. Analisis de 2 screenshots de Tableau: Vista 1 (ranking barras) y Vista 2 (INVEX vs promedio time series). Prompts corregidos para calzar con las vistas de Tableau.
- 2026-02-17 - Verificacion PROD: migracion 059 ya desplegada, 3 MVs con cvc_cc, datos cargados (4,099 filas, 201701-202511). 10/10 match Tableau confirmado en BD. Solo faltan: prompts onboarding + E2E tests.
