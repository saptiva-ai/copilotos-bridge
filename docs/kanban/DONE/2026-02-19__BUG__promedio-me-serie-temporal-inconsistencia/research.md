# Research: PROMEDIO ME inconsistencia vs Tableau

## Fecha de investigación: 2026-02-19

---

## 1. Hallazgos de Base de Datos (Fase 0 + Fase 1)

### 1.1 Anclaje Oct/Dec 2022 — VERIFICADO

**Oct 2022 (periodo_id=202210)**: 6 bancos con datos ME

| Banco | tasa_me (ratio) | tasa_me (%) |
|-------|----------------|-------------|
| BANCO BASE | 0.0550 | 5.50 |
| INVEX | 0.0864 | **8.64** |
| MIFEL | 0.1601 | 16.01 |
| MONEX | 0.0564 | 5.64 |
| SABADELL | 0.0441 | 4.41 |
| VE POR MAS | 0.0339 | 3.39 |

- **INVEX = 8.64%** ✅ coincide con tooltip BankAdvisor
- **PROMEDIO simple**: (5.50+8.64+16.01+5.64+4.41+3.39)/6 = **7.265 ≈ 7.26%** ✅ coincide con tooltip

**Dec 2022 (periodo_id=202212)**: 6 bancos con datos ME

| Banco | tasa_me (%) |
|-------|-------------|
| BANCO BASE | 5.93 |
| INVEX | 9.44 |
| MIFEL | 16.85 |
| MONEX | 5.61 |
| SABADELL | 4.74 |
| VE POR MAS | 3.31 |

- **INVEX = 9.44%** ✅ coincide con tooltip
- **PROMEDIO simple**: 7.646 ≈ **7.65%** ✅ coincide con tooltip

**Decisión del árbol**: Los datos son correctos. La fórmula de BankAdvisor produce exactamente los tooltips observados. La discrepancia es contra **Tableau**, que usa WAVG (no simple AVG).

### 1.2 Formato de datos tasa_me (H8)

De 3,234 valores no-NULL en `bank_fact_kpis_mensual`:
- **3,230** son ratios (< 1): formato correcto
- **4** son porcentaje (≥ 1): COVALTO(202309), KEB HANA(202309, 202504), VE POR MAS(202310)

`MetricNormalizer.AUTO_DETECT` maneja estos 4 correctamente (≥1 → mantiene como %).

**H8 DESCARTADA** como causa del punto huérfano.

### 1.3 Cobertura de bancos (H7)

| Banco | Meses con datos ME | Rango |
|-------|-------------------|-------|
| BANCO BASE | ~66 | 201906-202501 |
| INVEX | ~66 | 201906-202501 |
| MIFEL | ~66 | 201906-202501 |
| MONEX | ~66 | 201906-202501 |
| SABADELL | ~66 | 201906-202501 |
| VE POR MAS | ~66 | 201906-202501 |
| BANCREA | ~45 | 201906-202501 (gaps) |
| AFIRME | ~40 | 202001-202501 |
| BANSI | **33** | **201910-202206** (discontinuado) |
| MULTIVA | **4** | **202403-202511** (reciente) |
| BANCA MIFEL | — | No existe. Se resuelve como "MIFEL" |
| BANCO DEL BAJÍO | — | **NO existe en DB** |

**Hallazgo clave**: "BANCA MIFEL" se resuelve a "MIFEL" en la DB. "BANCO DEL BAJÍO" no tiene datos ME en absoluto.

### 1.4 INVEX Orphan Point (H5) — CONFIRMADO

**El "punto huérfano" reportado por Rodrigo es real y tiene explicación en los datos.**

Reconstrucción de serie completa INVEX ME (Sep-Nov 2022):

| Periodo | INVEX tasa_me | Bancos con datos |
|---------|--------------|-----------------|
| 202209 | **NULL** | 5 (sin INVEX) |
| **202210** | **0.0864 (8.64%)** | **6 (con INVEX)** |
| 202211 | **NULL** | 5 (sin INVEX) |

INVEX tiene dato para Oct 2022 pero es NULL para Sep y Nov 2022. En Plotly con `mode: "lines+markers"` y sin `connectgaps: true`, esto produce un **marker aislado** (punto sin línea conectora) — el "punto huérfano" rojo reportado.

### 1.5 WAVG vs Simple AVG (H3) — CONFIRMADO

Prueba con Oct 2022 usando `cartera_total` como proxy de peso:

| Método | Resultado Oct 2022 |
|--------|-------------------|
| Simple AVG | **7.26%** (coincide con tooltip BA) |
| WAVG con cartera_total | **5.95%** |
| Diferencia | **1.31pp** |

El WAVG difiere significativamente porque `cartera_total` es portfolio total (MN+ME), no ME-específico. El peso correcto sería el portfolio ME por banco, pero **esta columna no existe en `bank_fact_kpis_mensual`**.

---

## 2. Análisis de la Pipeline de Datos

### 2.1 Backfill tasas (capa intra-banco)

`scripts/data/backfill_tasas.py` procesa `CorporateLoan_CNBVDB.csv`:
- Granularidad fuente: banco × estado × moneda × mes
- Computa WAVG intra-banco: `SUM(Portfolio × Rate) / SUM(Portfolio)` por banco×moneda×mes
- Almacena resultado como `tasa_me` (ratio, ej: 0.0864 para 8.64%)
- **NO persiste** el `SUM(Portfolio)` por banco×moneda×mes → no hay peso ME disponible

### 2.2 Peer Average (capa inter-banco)

`peer_average.py:579` computa PROMEDIO:
```python
all_norm = [v for v in norm_values.values() if v is not None]
peer_avg = sum(all_norm) / len(all_norm)  # Simple AVG
```

Debería ser WAVG como Tableau: `SUM(cartera_me × tasa_me) / SUM(cartera_me)`

### 2.3 Columnas disponibles para ponderar

| Columna | Tabla | Disponible | Es ME-específica |
|---------|-------|-----------|-----------------|
| `cartera_total` | bank_fact_kpis_mensual | ✅ | ❌ (MN+ME+todo) |
| `cartera_comercial_total` | bank_fact_kpis_mensual | ✅ | ❌ |
| `Total Portfolio` | CorporateLoan_CNBVDB.csv | ✅ (en CSV) | ✅ (filtrable) |
| `cartera_me` | — | ❌ NO EXISTE | — |

### 2.4 Opciones para obtener peso ME

1. **Proxy con `cartera_total`**: Disponible ya, sin schema change. Impreciso (pondera por total, no ME).
2. **Agregar columna `cartera_me`**: Modificar backfill para también guardar `SUM(Total Portfolio) WHERE Currency='ME'` por banco×mes. Requiere schema change + re-backfill.
3. **Calcular WAVG en backfill**: Agregar una fila "PROMEDIO" pre-computada al backfill que haga el WAVG inter-banco directamente desde el CSV granular.

---

## 3. Hipótesis — Estado Final

| # | Hipótesis | Estado | Impacto |
|---|-----------|--------|---------|
| H3 | WAVG vs Simple AVG | ✅ **CONFIRMADA** | **PRINCIPAL** — diferencia sostenida en todos los meses |
| H5 | Plotly + None = punto huérfano | ✅ **CONFIRMADA** | Punto rojo aislado Oct 2022 (INVEX NULL en Sep/Nov) |
| H7 | Set de bancos diferente | ✅ **CONFIRMADA** | 14 en Tableau vs 6-9 con datos |
| H8 | Formato mixto (ratio vs %) | ❌ **DESCARTADA** | Solo 4/3234 outliers, AUTO_DETECT los maneja |
| H1 | Filtro moneda erróneo | ❌ **DESCARTADA** | `tasa_me` ya es ME-específica |
| H2 | Dataset diferente | ❌ **DESCARTADA** | Ambas series usan misma tabla |
| H4 | Desfase temporal | ❌ **DESCARTADA** | Mismo eje de fechas |
| H6 | Forward-fill | ❌ **DESCARTADA** | No hay forward-fill |

---

## 4. Causa Raíz Definitiva

### Discrepancia PROMEDIO: H3 (WAVG vs Simple AVG)
- Tableau: `SUM(Portfolio_ME × Rate) / SUM(Portfolio_ME)` con 14 bancos fijos
- BankAdvisor: `SUM(Rate) / COUNT(Rate)` con ~6-9 bancos dinámicos
- La diferencia es **estructural** y afecta todos los meses

### Punto huérfano: H5 (INVEX NULL en meses adyacentes)
- INVEX tiene dato ME solo para Oct 2022 (y otros meses), pero gaps en Sep/Nov 2022
- Plotly renderiza un marker aislado cuando un punto tiene dato pero sus vecinos son NULL
- **No es un bug de código**, es un reflejo fiel de los datos

---

## 5. Preguntas Abiertas para Plan

1. **¿Usar `cartera_total` como proxy o agregar `cartera_me` al schema?**
   - Proxy: rápido pero impreciso (portfolio total vs ME)
   - Schema change: preciso pero requiere migration + re-backfill

2. **¿Cómo manejar el punto huérfano de INVEX?**
   - Opción A: `connectgaps: true` en Plotly (conecta líneas sobre gaps)
   - Opción B: Dejar como está + documentar (los datos son correctos)
   - Opción C: Interpolar/forward-fill en el backend

3. **¿Replicar el set de 14 bancos de Tableau o mantener dinámico?**
   - Afecta tanto el denominador WAVG como la cobertura visual
   - Relacionado con ticket BUG-2026-02-13 (include/exclude INVEX)
