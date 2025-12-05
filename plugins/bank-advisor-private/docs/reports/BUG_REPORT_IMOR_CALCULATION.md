# 🐛 Bug Report: IMOR Calculation Incorrect (141% vs 2.35%)

**Fecha:** 2025-12-04
**Severidad:** 🔴 CRITICAL
**Afecta:** Todas las métricas de cartera (IMOR, ICOR, ratios)
**Status:** ✅ ROOT CAUSE IDENTIFIED

---

## 📋 Resumen

El cálculo de IMOR está retornando **valores imposibles** (>100%) debido a un error en cómo el ETL calcula `cartera_total` y `cartera_vencida`.

### Síntoma Observado

```sql
SELECT
    fecha, banco_norm,
    cartera_total,      -- 1,775 millones
    cartera_vencida,    -- 2,511 millones  ← Mayor que total!
    imor                -- 1.414 (141%)    ← IMPOSIBLE
FROM monthly_kpis
WHERE banco_norm = 'INVEX'
  AND fecha = '2025-07-01';
```

**Problema:** cartera_vencida (2,511) > cartera_total (1,775) es matemáticamente imposible.

---

## 🔍 Análisis de Root Cause

### 1. Datos Fuente Correctos (Excel)

**Archivo:** `data/raw/CNBV_Cartera_Bancos_V2.xlsx`
**Institución:** INVEX (código 40059)
**Fecha:** Julio 2025

```
Columna                          | Valor (MDP) | % del Total
─────────────────────────────────┼─────────────┼────────────
Cartera Total Etapa 1            | 45,059.81   | 94.7%
Cartera Total Etapa 2            |  1,393.56   |  2.9%
Cartera Total Etapa 3            |  1,117.70   |  2.3%
Cartera Total Etapa VR           |      0.00   |  0.0%
─────────────────────────────────┼─────────────┼────────────
TOTAL (Etapa todas)              | 47,571.07   | 100.0%
```

**Interpretación IFRS 9:**
- **Etapa 1:** Créditos performing (sin deterioro)
- **Etapa 2:** Créditos con incremento significativo en riesgo
- **Etapa 3:** Créditos con evidencia objetiva de deterioro (credit-impaired)
- **Etapa VR:** Clasificación legacy (vencida riesgosa)

### 2. Cálculo Incorrecto en ETL

**Archivo:** `etl/transforms_polars.py`

#### Error #1: cartera_total (Líneas 215-222)

```python
# CÓDIGO ACTUAL (INCORRECTO)
df = df.with_columns([
    (
        pl.col("cartera_comercial_total") +    # Solo etapa 2
        pl.col("cartera_consumo_total") +      # Solo etapa 2
        pl.col("cartera_vivienda_total")       # Solo etapa 2
    ).alias("cartera_total")
])
```

**Problema:** Solo suma los totales de Etapa 2 por segmento (comercial, consumo, vivienda), ignorando Etapa 1 y Etapa 3.

**Resultado:** cartera_total = 1,775 millones (debería ser 47,571)

#### Error #2: cartera_vencida (Líneas 224-228)

```python
# CÓDIGO ACTUAL (CORRECTO en concepto, pero usa denominador malo)
etapa_3_cols = [c for c in existing_cols if "etapa_3" in c]
df = df.with_columns([
    safe_sum(etapa_3_cols).alias("cartera_vencida")
])
```

**Problema:** El cálculo de cartera_vencida parece correcto (suma Etapa 3), pero como cartera_total solo incluye Etapa 2, el ratio queda mal.

**Resultado:** cartera_vencida = 2,511 millones (probablemente suma segmentos adicionales)

### 3. Cálculo de IMOR (Correcto)

```python
# etl/transforms_polars.py línea 488-499
def calculate_imor(df: pl.LazyFrame) -> pl.LazyFrame:
    return df.with_columns([
        pl.when(pl.col("cartera_total") > 0)
        .then(pl.col("cartera_vencida") / pl.col("cartera_total"))
        .otherwise(None)
        .alias("imor")
    ])
```

**Fórmula:** `IMOR = cartera_vencida / cartera_total`

Esta fórmula es **correcta**, pero produce resultados absurdos porque los inputs están mal:

```
IMOR_actual = 2,511 / 1,775 = 1.414 (141%) ❌

IMOR_correcto = 1,118 / 47,571 = 0.0235 (2.35%) ✅
```

---

## 💡 Solución Propuesta

### Fix #1: Corregir cálculo de cartera_total

**Opción A: Usar columna existente "Cartera de Crédito Total Etapa todas"**

```python
# SOLUCIÓN RECOMENDADA
df = df.with_columns([
    pl.col("cartera_credito_total_etapa_todas").alias("cartera_total")
])
```

**Opción B: Sumar todas las etapas manualmente**

```python
# SOLUCIÓN ALTERNATIVA
df = df.with_columns([
    (
        safe_sum([c for c in existing_cols if "etapa_1" in c and "total" in c.lower()]) +
        safe_sum([c for c in existing_cols if "etapa_2" in c and "total" in c.lower()]) +
        safe_sum([c for c in existing_cols if "etapa_3" in c and "total" in c.lower()])
    ).alias("cartera_total")
])
```

### Fix #2: Verificar cartera_vencida

**Acción:** Confirmar que suma de etapa_3 es correcta o usar columna específica si existe.

```python
# Verificar si existe columna directa
if "cartera_total_etapa_3" in existing_cols:
    df = df.with_columns([
        pl.col("cartera_total_etapa_3").alias("cartera_vencida")
    ])
else:
    # Mantener suma de segmentos etapa_3
    etapa_3_cols = [c for c in existing_cols if "etapa_3" in c]
    df = df.with_columns([
        safe_sum(etapa_3_cols).alias("cartera_vencida")
    ])
```

---

## 🧪 Validación del Fix

### Test Case: INVEX Julio 2025

**Input (Excel):**
```
Cartera Total Etapa 1: 45,059.81
Cartera Total Etapa 2:  1,393.56
Cartera Total Etapa 3:  1,117.70
──────────────────────────────────
Total:                 47,571.07
```

**Expected Output (monthly_kpis):**
```sql
cartera_total   = 47,571.07  ✅
cartera_vencida =  1,117.70  ✅
imor            =  0.0235    ✅ (2.35%)
```

### Validación con Otros Bancos

| Banco | Cartera Total (Esperado) | IMOR (Esperado) | Status |
|-------|--------------------------|-----------------|--------|
| BBVA  | ~1,200,000 MDP | 1.5% - 2.5% | Revisar |
| SANTANDER | ~900,000 MDP | 1.5% - 2.5% | Revisar |
| BANORTE | ~800,000 MDP | 1.5% - 2.5% | Revisar |
| SISTEMA | ~3,500,000 MDP | 2.0% - 3.0% | Revisar |

**Rango normal IMOR en México:** 1.5% - 3.5%

---

## 📊 Impacto

### Métricas Afectadas

- ❌ **IMOR** (Índice de Morosidad): Valores >100% imposibles
- ❌ **ICOR** (Índice de Cobertura): Ratio incorrecto por usar cartera_vencida mal
- ❌ **Ratios de Etapa** (ct_etapa_1, ct_etapa_2, ct_etapa_3): Denominador incorrecto
- ❌ **Pérdida Esperada**: Cálculos derivados incorrectos
- ❌ **Cartera Total**: Subestimada por factor ~27x

### Queries Afectadas

Todas las queries que usan:
- `cartera_total`
- `cartera_vencida`
- `imor`
- `icor`
- Ratios de calidad de cartera

### Usuarios Afectados

- ✅ **Sistema sigue funcionando** (no crashes)
- ❌ **Datos analíticos incorrectos** (decisiones de negocio erróneas)
- ❌ **Dashboards mostrando valores imposibles**

---

## 🚀 Plan de Acción

### Prioridad Alta (Inmediato)

1. **Fix el ETL (transforms_polars.py)**
   - [ ] Implementar Fix #1 para cartera_total
   - [ ] Verificar Fix #2 para cartera_vencida
   - [ ] Agregar test unitario con datos de INVEX

2. **Re-ejecutar ETL en producción**
   ```bash
   docker exec bank-advisor python -m etl.etl_unified
   ```

3. **Validar resultados**
   ```sql
   SELECT
       banco_norm,
       AVG(imor) as imor_promedio,
       MAX(imor) as imor_max
   FROM monthly_kpis
   GROUP BY banco_norm
   HAVING MAX(imor) > 0.10;  -- Debe estar vacío (ningún banco >10%)
   ```

### Prioridad Media (Seguimiento)

4. **Agregar validaciones en ETL**
   - [ ] Assert: cartera_vencida <= cartera_total
   - [ ] Assert: 0 <= IMOR <= 0.15 (15% es máximo razonable)
   - [ ] Warning si IMOR > 0.05 (5% es alto pero posible)

5. **Documentar estructura IFRS 9**
   - [ ] Explicar Etapa 1/2/3 en README
   - [ ] Documentar fórmulas de calidad de cartera

### Prioridad Baja (Mejoras)

6. **Refactorizar cálculos de cartera**
   - [ ] Crear función `calculate_cartera_total()` explícita
   - [ ] Separar lógica de segmentos vs. etapas
   - [ ] Agregar logging de valores intermedios

---

## 🔗 Referencias

- **Archivo ETL:** `etl/transforms_polars.py` líneas 215-228
- **Función IMOR:** `etl/transforms_polars.py` líneas 488-499
- **Datos fuente:** `data/raw/CNBV_Cartera_Bancos_V2.xlsx`
- **IFRS 9 Etapas:** https://www.ifrs.org/issued-standards/list-of-standards/ifrs-9-financial-instruments/
- **CNBV Normativa:** Circular Única de Bancos (CUB)

---

## 📝 Evidencia

### Query de Diagnóstico

```sql
-- Mostrar el problema
SELECT
    fecha,
    banco_norm,
    cartera_total,
    cartera_vencida,
    ROUND(cartera_vencida::numeric, 2) as cv_redondeado,
    ROUND((cartera_vencida / NULLIF(cartera_total, 0))::numeric, 4) as imor_calc,
    imor,
    CASE
        WHEN cartera_vencida > cartera_total THEN '❌ IMPOSIBLE'
        WHEN imor > 0.15 THEN '⚠️ MUY ALTO'
        WHEN imor > 0.05 THEN '⚠️ ALTO'
        ELSE '✅ OK'
    END as status
FROM monthly_kpis
WHERE fecha >= '2025-01-01'
ORDER BY imor DESC NULLS LAST
LIMIT 20;
```

### Datos Fuente (Excel)

```python
# Script para extraer datos de Excel
import pandas as pd

df = pd.read_excel("data/raw/CNBV_Cartera_Bancos_V2.xlsx")
invex = df[df['Institucion'] == 40059].tail(1)

print(f"Etapa 1: {invex['Cartera Total Etapa 1'].values[0]:,.2f}")
print(f"Etapa 2: {invex['Cartera Total Etapa 2'].values[0]:,.2f}")
print(f"Etapa 3: {invex['Cartera Total Etapa 3'].values[0]:,.2f}")
print(f"Total:   {invex['Cartera de Crédito Total Etapa todas'].values[0]:,.2f}")
```

---

**Reportado por:** Claude Code
**Fecha:** 2025-12-04 23:59 UTC
**Próxima acción:** Implementar fix y validar
