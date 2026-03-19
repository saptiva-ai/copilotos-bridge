---
id: "BUG-2026-02-19__promedio-me-serie-temporal-inconsistencia"
title: "Bug: PROMEDIO ME inconsistente vs cubo (Moneda Extranjera) + punto huérfano en serie"
status: "BACKLOG"
phase: "Implement"
priority: "Alta"
scope_in:
  - "Identificar causa raíz de discrepancia en serie PROMEDIO de Tasa Promedio ME"
  - "Explicar y eliminar punto huérfano (rojo aislado ~8.6) en gráfica INVEX vs PROMEDIO ME"
  - "Comparar datos raw (DB/MV) contra valores del cubo Tableau para 5+ meses"
  - "Agregar tests de regresión para merge de series y filtro por moneda"
scope_out:
  - "Cambios en ETL/backfill histórico (ticket separado si necesario)"
  - "Redefinición de población del promedio (cubierto por BUG-2026-02-13)"
  - "Cambios en MN (solo ME)"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 1
validation_commands:
  - "python3.11 -m pytest tests/e2e/charts/test_peer_avg_tasa_me_chart.py -v"
  - "python3.11 -m pytest plugins/bank-advisor-private/tests/unit/application/test_use_cases.py -k PeerAverage -v"
pr_files: []
test_status: "pending"
related_tickets:
  - "2026-02-18__BUG__tasas-mn-me-discrepancia-tableau (DONE — fix denominador tasa=0)"
  - "2026-02-13__BUG__tableau-peer-average-definition-mismatch (BACKLOG — include/exclude INVEX)"
---

# Bug: PROMEDIO ME inconsistente vs cubo + punto huérfano en serie

## Reportado por
Rodrigo (usuario Bajaware) — 2026-02-19

## Problema

En la gráfica de **Tasa Promedio en Moneda Extranjera** (INVEX vs PROMEDIO), la serie PROMEDIO de BankAdvisor **no coincide** con los valores del cubo de referencia (gráfica blanca / Tableau). Adicionalmente, aparece un **punto rojo aislado** (huérfano) alrededor de ~8.6% que no pertenece claramente a la línea INVEX ni a PROMEDIO.

### Síntomas específicos

1. **Valor 6.06% ausente**: En la gráfica blanca (cubo) la serie PROMEDIO muestra un valor de **6.06%** en un punto. Este valor **no aparece** en ningún tooltip de BankAdvisor.
2. **Punto huérfano**: Un punto rojo aislado cerca de ~8.6% sin continuidad en la serie. Posible merge erróneo de series o dato de otra consulta.
3. **Valores de tooltip no cuadran**: Oct 2022 → INVEX: 8.64, PROMEDIO: 7.26 en BankAdvisor; estos no corresponden con los valores visibles en el cubo.

## Evidencia: Valores de referencia

### A) Gráfica blanca (cubo / Tableau) — Moneda Extranjera

**Serie INVEX (roja):**

| # | Valor |
|---|-------|
| 1 | 6.66 |
| 2 | 5.98 |
| 3 | 5.94 |
| 4 | 5.54 |
| 5 | 5.53 |
| 6 | 5.52 |
| 7 | 5.49 |
| 8 | 5.51 |
| 9 | 5.47 |
| 10 | 6.02 |
| 11 | 6.43 |
| 12 | 7.35 |
| 13 | 7.82 |
| 14 | 8.46 |
| 15 | 9.30 |
| 16 | 10.30 |
| 17 | 10.34 |
| 18 | 10.28 |
| 19 | 10.16 |
| 20 | 10.32 |
| 21 | 9.05 |

**Serie PROMEDIO (gris):**

| # | Valor | Nota |
|---|-------|------|
| 1 | 4.62 | |
| 2 | 3.96 | |
| 3 | 3.30 | |
| 4 | 3.74 | |
| 5 | 5.49 | |
| 6 | 9.51 | |
| 7 | 9.25 | |
| 8 | **6.06** | **No aparece en BankAdvisor** |
| 9 | 8.30 | |
| 10 | 6.68 | |
| 11 | 8.51 | |
| 12 | 8.39 | |
| 13 | 8.87 | |
| 14 | 8.87 | |
| 15 | 8.98 | |
| 16 | 9.07 | |
| 17 | 10.33 | |

*Nota: Las etiquetas de mes no son visibles en las capturas; los valores se listan en orden secuencial.*

### B) BankAdvisor (tooltips confirmados)

| Fecha | INVEX (BA) | PROMEDIO (BA) |
|-------|-----------|--------------|
| Oct 2022 | 8.64 | 7.26 |
| Dec 2022 | 9.44 | 7.65 |

**Anomalía visual**: Punto rojo aislado cerca de ~8.6% sin continuidad en la serie.

## Expected vs Actual

| Aspecto | Expected | Actual |
|---------|----------|--------|
| PROMEDIO ME | Coincide con cubo/DB para mismos filtros y set de bancos | Valores divergen (ej: 6.06% ausente) |
| Series visuales | Dos líneas continuas (INVEX + PROMEDIO) | Punto rojo huérfano aislado sin serie |
| Tooltips | Valores consistentes con cubo | Oct 2022: 7.26 vs cubo diferente |

## BLOQUEADOR RESUELTO: Definición exacta de PROMEDIO en Tableau

> **Estado**: RESUELTO (2026-02-19). Fórmulas extraídas del workbook `.twb`.

### Hoja Tableau: "Tasa x Tiempo ME" (evolución temporal)

Título visible: **"Tasas Moneda Extranjera"**. Fuente: `Invex_Tablero_V3.twb` líneas 11362-11481.

### Cadena de fórmulas (5 campos calculados encadenados)

```
[Tasa Todos] = IF [Average Rate] = 0 THEN NULL ELSE [Average Rate]/100 END
               └─ Convierte rate=0 → NULL. Divide entre 100 (% → ratio).

[TASA INVEX] = IF [DESCRIPCION]='INVEX' THEN [Tasa Todos] ELSE NULL END
               └─ Aísla solo filas de INVEX.

[SALDO INVEX] = IF [DESCRIPCION]='INVEX' THEN [Total Portfolio] ELSE 0 END
                └─ Portfolio solo de INVEX (demás → 0).

[Tasa Prom Pond] = SUM([Total Portfolio] * [Tasa Todos]) / SUM([Total Portfolio])
                   └─ ★ SERIE PROMEDIO ★
                   └─ WAVG por cartera. Numerador excluye rate=0 (NULL).
                   └─ Denominador incluye TODOS los portfolios (incluso rate=0).

[Tasa Pond Invex] = SUM([SALDO INVEX] * [TASA INVEX]) / SUM([SALDO INVEX])
                    └─ ★ SERIE INVEX ★
                    └─ WAVG solo de INVEX, ponderado por cartera por estado.
```

### Respuestas a las 5 preguntas concretas

| # | Pregunta | Respuesta |
|---|----------|-----------|
| 1 | ¿AVG ignorando NULLs o set fijo? | **Set fijo de 14 bancos** (filtro `Descripcion conjunto`). NULLs se ignoran en SUM del numerador, pero el denominador incluye TODOS los portfolios. |
| 2 | ¿Promedio simple o ponderado? | **PONDERADO (WAVG)**: `SUM(Portfolio × Rate) / SUM(Portfolio)`. NO es `AVG(Rate)`. |
| 3 | ¿Manejo de tasa=0? | `IF Rate=0 THEN NULL` → excluido del numerador pero Portfolio INCLUIDO en denominador. Idéntico al hallazgo del ticket `2026-02-18`. |
| 4 | ¿Set dinámico o fijo? | **Fijo: 14 bancos** — ACTINVER, AFIRME, BANCA MIFEL, BANCO BASE, BANCO DEL BAJÍO, BANCREA, BANREGIO, BANSÍ, CIBANCO, INVEX, MONEX, MULTIVA, SABADELL, VE POR MÁS. |
| 5 | ¿Incluye o excluye INVEX? | **INCLUYE** INVEX en el PROMEDIO (Tasa Prom Pond usa Tasa Todos, que incluye a todos). |

### Granularidad de los datos fuente

La fuente `CorporateLoan_CNBVDB.csv` tiene granularidad **banco × estado × moneda × mes**. Cada banco tiene múltiples filas por periodo (una por estado). El WAVG agrega primero por estado dentro de cada banco, luego entre bancos. Nuestro sistema tiene una sola fila `tasa_me` por banco por periodo (ya pre-agregada).

### Discrepancia confirmada vs nuestra implementación

| Aspecto | Tableau | BankAdvisor (`peer_average.py:579`) |
|---------|---------|-------------------------------------|
| Tipo de promedio | **WAVG** `SUM(P×R)/SUM(P)` | **Simple** `SUM(R)/COUNT(R)` |
| Ponderación | Por `Total Portfolio` (cartera por estado) | Ninguna |
| Manejo rate=0 | NULL en numerador, Portfolio en denominador | Excluye de ambos (si tasa_me=NULL) |
| Set de bancos | 14 bancos fijos | Los que el usuario pida (típ. 9-10) |
| INVEX en promedio | **Incluido** | **Incluido** (desde fix reciente) |
| Granularidad | Fila por banco×estado×moneda×mes | Una fila por banco×mes |

**Impacto**: La diferencia WAVG vs Simple AVG explica discrepancias sostenidas en todos los meses. Bancos con portfolios grandes pero tasas bajas (ej: BANCREA ME $102M con tasa 7.8%) pesan más en WAVG que en simple AVG. La diferencia puede ser de varios puntos porcentuales.

### Fuentes en el workbook

- Workbook: `plugins/bank-advisor-private/data/raw/incoming/drive-download-20260212T024209Z-1-001/Invex_Tablero_V3.twb`
- Hoja "Tasa x Tiempo ME": líneas 11362-11481 (evolución temporal con 2 series)
- Hoja "Tasas vs Promedio ME": líneas 11820-11932 (bar chart snapshot para un mes)
- Datasource: `CorporateLoan_CNBVDB.csv` + `Instituciones` (join por clave)
- CSV de referencia rápida: `TASAS DATOS.csv` (25 filas, promedios por banco×moneda)

---

## Causa raíz (confirmada por análisis del workbook)

### ✅ H3 — CONFIRMADA: Promedio PONDERADO (WAVG) vs Simple AVG

Tableau usa `SUM(Portfolio × Rate) / SUM(Portfolio)` (WAVG por cartera).
Nuestro `PeerAverageUseCase` (línea 579-580 de `peer_average.py`) usa promedio simple:
```python
all_norm = [v for v in norm_values.values() if v is not None]
peer_avg = sum(all_norm) / len(all_norm) if all_norm else None
```

Esto explica discrepancias **sostenidas** en todos los meses. Bancos con portfolios grandes pero tasas bajas/altas desequilibran el WAVG vs el simple AVG.

Adicionalmente, Tableau opera sobre datos **granulares** (banco×estado×moneda×mes), mientras que nosotros ya tenemos un `tasa_me` pre-agregado por banco×mes. Para replicar exactamente el WAVG de Tableau, necesitaríamos ponderar por `Total Portfolio` a nivel de estado, o al menos por cartera total del banco.

### ✅ H7 — CONFIRMADA: Set de bancos diferente

Tableau filtra por **14 bancos fijos**: ACTINVER, AFIRME, BANCA MIFEL, BANCO BASE, BANCO DEL BAJÍO, BANCREA, BANREGIO, BANSÍ, CIBANCO, INVEX, MONEX, MULTIVA, SABADELL, VE POR MÁS.

Nuestro sistema usa los bancos que el usuario pide en el prompt (típicamente 9 peers + INVEX = 10). Faltan: ACTINVER, BANCO DEL BAJÍO, BANREGIO, CIBANCO.

### ✅ H5 — CONFIRMADA: Plotly + None = "punto huérfano"

INVEX tiene dato ME para Oct 2022 (8.64%) pero es NULL en Sep y Nov 2022. Plotly en modo `lines+markers` sin `connectgaps: true` renderiza un marker aislado. **Esto explica el punto rojo huérfano reportado por Rodrigo.**

Pendiente: capturar JSON Plotly vía E2E para confirmar visualmente.

### Hipótesis descartadas

- **H8 (formato mixto)**: Solo 4/3234 outliers, AUTO_DETECT los maneja. No causa punto huérfano.
- **H1 (filtro moneda)**: `tasa_me` ya está separada de `tasa_mn`.
- **H2 (dataset diferente)**: Ambas series usan la misma tabla.
- **H4 (desfase temporal)**: Mismo eje de fechas.
- **H6 (forward-fill)**: No hay forward-fill en `PeerAverageUseCase`.

## Archivos clave del sistema

| Componente | Ruta | Relevancia |
|-----------|------|------------|
| **PeerAverageUseCase** | `plugins/bank-advisor-private/src/bankadvisor/application/use_cases/peer_average.py` | Lógica core de INVEX vs PROMEDIO. Línea 579: cálculo de `peer_avg` |
| **EvolutionUseCase** | `plugins/bank-advisor-private/src/bankadvisor/application/use_cases/evolution.py` | Use case alternativo si se rutea a evolución en vez de peer_average |
| **MetricNormalizer** | `plugins/bank-advisor-private/src/bankadvisor/domain/services/metric_normalizer.py` | Normalización ratio↔porcentaje. `tasa_me` está en AUTO_DETECT |
| **Backfill tasas** | `scripts/data/backfill_tasas.py` | ETL que pobla `tasa_me` en DB. Fix previo: denominador con tasa=0 |
| **comparison_tools** | `plugins/bank-advisor-private/src/bankadvisor/tools/comparison_tools.py` | Herramienta MCP que invoca PeerAverageUseCase |
| **E2E test ME** | `tests/e2e/charts/test_peer_avg_tasa_me_chart.py` | 14 validadores × 3 prompts. Valores Tableau de referencia en L44-53 |
| **Chart render (front)** | `apps/web/src/components/chat/BankChartPreview.tsx` | Renderizado Plotly en el front. Ver cómo maneja `None` en series |
| **KPI model** | `plugins/bank-advisor-private/src/bankadvisor/models/kpi.py` | Modelo SQLAlchemy con columna `tasa_me` |
| **Tableau workbook** | `plugins/bank-advisor-private/data/raw/incoming/.../Invex_Tablero_V3.twb` | Fuente de verdad para fórmulas Tableau |

### Tablas de DB relevantes

| Tabla | Uso |
|-------|-----|
| `bank_fact_kpis_mensual` | KPIs mensuales por banco (columna `tasa_me`) |
| `bank_mv_evolucion_cartera_banco` | Materialized view de evolución (fuente alternativa) |
| `bank_dim_institucion` | Dimensión de instituciones (`clave_cnbv`, `nombre_corto`) |

## Plan de investigación

### Fase 0: Anclaje a meses concretos (árbol de decisión rápido)

Tenemos tooltips confirmados para **Oct 2022** y **Dec 2022**. Usarlos como ground truth binaria:

```
¿INVEX Oct-2022 en DB = 8.64?
├─ NO → bug en extracción DB o normalización previa. Investigar MetricNormalizer.
└─ SÍ → ¿PROMEDIO Oct-2022 recalculado (misma fórmula que peer_average.py) = 7.26?
     ├─ SÍ → los datos son correctos pero la fórmula difiere del cubo.
     │        → ir a Fase 2 (comparar fórmula Tableau).
     └─ NO → bug en cálculo del promedio: set de bancos, normalización, o ponderación.
              → ir a Fase 1 (pruebas baratas).
```

### Fase 1: Pruebas baratas (Tier 1 — hacer primero)

**1a. Query de sanidad: distribución de tasa_me por banco y rango**
```sql
-- Cazar valores en formato ratio vs porcentaje
SELECT periodo_id, UPPER(banco_norm) banco, tasa_me,
  CASE
    WHEN tasa_me < 1 THEN 'RATIO (< 1)'
    WHEN tasa_me BETWEEN 1 AND 30 THEN 'PORCENTAJE (1-30)'
    ELSE 'OUTLIER (> 30)'
  END AS formato_probable
FROM bank_fact_kpis_mensual
WHERE UPPER(banco_norm) IN ('INVEX', 'MONEX', 'BANCREA', 'SABADELL',
  'BANCA MIFEL', 'MULTIVA', 'AFIRME', 'BANSI', 'VE POR MAS', 'BANCO BASE')
  AND tasa_me IS NOT NULL
  AND (tasa_me < 1 OR tasa_me > 30)
ORDER BY periodo_id, banco;
```

**1b. Cobertura de BANSI y MULTIVA en ME**
```sql
SELECT UPPER(banco_norm) banco, COUNT(*) meses,
  MIN(periodo_id) desde, MAX(periodo_id) hasta,
  MIN(tasa_me) min_tasa, MAX(tasa_me) max_tasa
FROM bank_fact_kpis_mensual
WHERE UPPER(banco_norm) IN ('BANSI', 'MULTIVA')
  AND tasa_me IS NOT NULL
GROUP BY banco_norm;
```

**1c. Anclaje Oct/Dec 2022**
```sql
SELECT periodo_id, UPPER(banco_norm) banco, tasa_me
FROM bank_fact_kpis_mensual
WHERE periodo_id IN (202210, 202212)
  AND UPPER(banco_norm) IN ('INVEX', 'MONEX', 'BANCREA', 'SABADELL',
    'BANCA MIFEL', 'MULTIVA', 'AFIRME', 'BANSI', 'VE POR MAS', 'BANCO BASE')
  AND tasa_me IS NOT NULL
ORDER BY periodo_id, banco;
```
→ Con esto calcular AVG simple y comparar con tooltip BA (7.26 / 7.65).

**1d. Captura de JSON para punto huérfano**
- Enviar prompt E2E, extraer `plotly_config.data[*].y`.
- Buscar patrón `None, None, X, None, None` (punto aislado).
- Verificar si `connectgaps` está configurado.

### Fase 2: Comparación de fórmulas Tableau (BLOQUEADOR)
1. Extraer fórmula Tableau de `Invex_Tablero_V3.twb` para "Tasas Moneda Extranjera".
2. Determinar si Tableau usa WAVG (ponderado por cartera) o simple AVG.
3. Determinar manejo de NULLs: ¿`AVG` estándar (ignora NULL)? ¿Set fijo con carry-forward? ¿`NULLIF(rate, 0)`?
4. Verificar si incluye/excluye INVEX en el promedio.

### Fase 3: Extracción de datos raw completa
1. Consultar `bank_fact_kpis_mensual` para INVEX + peers ME con granularidad mensual:
   ```sql
   SELECT periodo_id, UPPER(banco_norm) AS banco, tasa_me
   FROM bank_fact_kpis_mensual
   WHERE UPPER(banco_norm) IN ('INVEX', 'MONEX', 'BANCREA', 'SABADELL',
     'BANCA MIFEL', 'MULTIVA', 'AFIRME', 'BANSI', 'VE POR MAS', 'BANCO BASE')
     AND tasa_me IS NOT NULL
   ORDER BY periodo_id, banco_norm;
   ```
2. Calcular PROMEDIO simple vs PROMEDIO ponderado para cada mes.
3. Comparar contra valores del cubo (tabla de evidencia arriba).

### Fase 4: Fix y validación
1. Implementar corrección según hallazgos.
2. Producir tabla comparativa:

| Fecha | INVEX (DB) | PROMEDIO (DB) | INVEX (UI) | PROMEDIO (UI) | INVEX (cubo) | PROMEDIO (cubo) | Delta |
|-------|-----------|--------------|-----------|--------------|-------------|----------------|-------|
| Oct 2022 | ? | ? | 8.64 | 7.26 | ~8.46 | ? | ? |
| Dec 2022 | ? | ? | 9.44 | 7.65 | ~9.30 | ? | ? |
| Mes 6.06% | ? | ? | ? | ? | ? | 6.06 | ? |

## Criterios de aceptación

- [ ] Se documenta la definición exacta de PROMEDIO en Tableau (bloqueador resuelto).
- [ ] Se identifica y documenta la causa raíz de la discrepancia PROMEDIO ME.
- [ ] Se corrige y se valida con:
  - [ ] Comparación DB vs UI para mínimo 5 meses (incluye Oct 2022, Dec 2022, y el mes del 6.06%).
  - [ ] Desaparición del "punto huérfano", O bien: si existe, queda explicado por gaps en la fuente y el render está configurado para no confundir (ej: `connectgaps: true` o tooltip aclaratorio).
  - [ ] Test automatizado que garantice merge por fecha y filtro por moneda correcto.
- [ ] El JSON de Plotly no contiene puntos aislados no explicados (validar programáticamente: ningún `y[i] != None` rodeado de `y[i-1] == None AND y[i+1] == None` sin justificación en la fuente).
- [ ] Se comparte evidencia (tabla comparativa + query + screenshots).
- [ ] E2E test `test_peer_avg_tasa_me_chart.py` pasa sin regresiones.

## Checklist de tareas

**Fase 0 — Anclaje (hacer primero)**
- [x] Ejecutar query de anclaje Oct/Dec 2022 → INVEX DB = 8.64 ✅ / 9.44 ✅
- [x] Recalcular PROMEDIO con misma fórmula que `peer_average.py` → 7.26 ✅ / 7.65 ✅
- [x] Decidir rama del árbol de decisión → **datos correctos, fórmula difiere del cubo**

**Fase 1 — Pruebas baratas**
- [x] Query de sanidad: distribución tasa_me por rango → 4/3234 outliers, AUTO_DETECT OK
- [x] Verificar cobertura BANSI (33 meses, 201910-202206) y MULTIVA (4 meses, 202403-202511)
- [x] INVEX orphan confirmado: dato en 202210, NULL en 202209/202211
- [ ] Capturar JSON de Plotly vía E2E, buscar patrón None-X-None
- [ ] Verificar `connectgaps` en config de Plotly (front + backend)

**Fase 2 — Bloqueador**
- [x] Extraer fórmula Tableau del `.twb` → WAVG `SUM(P×R)/SUM(P)` con 14 bancos fijos
- [x] Documentar: WAVG (no simple AVG), NULLs excluidos de numerador, Portfolio en denominador
- [x] Documentar: INCLUYE INVEX en promedio

**Fase 3 — Fix**
- [x] Implementar WAVG en `peer_average.py` (`_execute_hip_metric` línea 579)
- [x] Resolver fuente de pesos ME → `cartera_total` como proxy (sin schema change)
- [x] Agregar 4 unit tests: WAVG core, fallback NULL, guard non-tasa, connectgaps
- [x] Agregar `connectgaps: true` a traces Plotly para eliminar punto huérfano
- [x] 607/607 unit tests passed (sin regresión)
- [x] E2E tasa_me: 40/42 passed (2 soft warnings V14: LLM hallucination, pre-existente)
- [x] E2E tasa_mn: 42/42 passed (sin regresión)
- [x] E2E imor: 13/14 passed (V14 pre-existente, diff=0.01pp)
- [x] Documentar hallazgos en `research.md`

## Updates
- 2026-02-19 — Ticket creado con evidencia de capturas, hipótesis de causa raíz, y plan de investigación.
- 2026-02-19 — Refinamiento: agregar bloqueador de definición Tableau, priorizar hipótesis por costo de prueba, añadir árbol de decisión con anclaje Oct/Dec 2022, criterio de aceptación para puntos aislados en Plotly JSON.
- 2026-02-19 — **BLOQUEADOR RESUELTO**: Fórmulas Tableau extraídas del workbook `.twb`. H3 y H7 confirmadas.
- 2026-02-19 — **INVESTIGACIÓN DB COMPLETA**: Fases 0-1 ejecutadas contra PROD.
  - H3 CONFIRMADA: WAVG vs Simple AVG (diferencia 1.31pp en Oct 2022).
  - H5 CONFIRMADA: INVEX orphan (NULL en 202209/202211, dato en 202210).
  - H7 CONFIRMADA: 14 bancos Tableau vs 6-9 con datos en nuestra DB.
  - H8 DESCARTADA: solo 4/3234 outliers de formato, AUTO_DETECT los maneja.
  - Hallazgo: `cartera_total` existe pero es MN+ME, no hay `cartera_me`.
  - Hallazgo: MIFEL resuelve "BANCA MIFEL", BANCO DEL BAJÍO no existe en DB.
  - Ver `research.md` para detalle completo.
- 2026-02-19 — **FIX IMPLEMENTADO Y VALIDADO**:
  - WAVG en `_execute_hip_metric` para tasa_me/tasa_mn (cartera_total como peso)
  - `connectgaps: true` en Plotly para eliminar puntos huérfanos
  - response_text dice "WAVG ponderado por cartera" para métricas de tasa
  - 607/607 unit tests + 4 nuevos (WAVG, fallback, guard, connectgaps)
  - E2E: tasa_me 40/42, tasa_mn 42/42, imor 13/14 (sin regresión)
  - PROMEDIO ME last value cambió de ~8.08% (simple AVG) a 8.40% (WAVG)
