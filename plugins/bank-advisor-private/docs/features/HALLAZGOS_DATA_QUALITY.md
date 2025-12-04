# Hallazgos Críticos: Calidad de Datos BankAdvisor

**Fecha**: 2025-12-03
**Score General**: 73.9/100
**Estado**: ❌ 6 problemas críticos identificados

---

## 📊 Resumen Ejecutivo

Se ejecutó validación completa de integridad de datos sobre 7 métricas × 7 bancos = 49 validaciones.

**Distribución de Calidad**:
- ✅ **Buena (≥80)**: 24/49 (49%)
- 🟡 **Aceptable (60-79)**: 13/49 (27%)
- 🟠 **Warning (40-59)**: 6/49 (12%)
- 🔴 **Crítica (<40)**: 6/49 (12%)

---

## 🔴 Problemas Críticos (P0) - Requieren Acción Inmediata

### 1. ICOR: Valores Negativos Fuera de Rango ✅ RESUELTO

**Status**: ✅ **FIXED** (2025-12-03)

**Solución Aplicada**:
- Modificado `calculate_icor()` en `etl/transforms_polars.py` para usar `.abs()` en reservas
- Formula corregida: `|reservas_etapa_todas| / cartera_vencida`
- ETL re-ejecutado: INVEX ahora muestra ICOR = 108.65% (antes: -1.09%)
- **Todos los valores ahora positivos y dentro del rango esperado**

**Commit**: c3bdb203 - fix(etl): Fix ICOR negative values using absolute value

---

### 2. ICOR: Valores Negativos Fuera de Rango (HISTÓRICO - RESUELTO)

**Score**: 0/100 para todos los bancos (INVEX, SISTEMA, SANTANDER, BANORTE, HSBC, CITIBANAMEX)

**Problema**:
```
Expected Range: 0 - 500 %
Actual Range: -2.21 to -0.31 (103/103 valores negativos)
Latest Value (INVEX): -1.09%
```

**Causa Raíz**:
- ICOR (Índice de Cobertura) está almacenado como **valor negativo** en la DB
- Validación esperaba 0-500% (cobertura típica 100-200%)
- **TODOS** los 103 valores históricos están negativos para todos los bancos

**Implicaciones**:
- Visualizaciones muestran valores negativos (incorrectos)
- Usuario ve "ICOR de INVEX: -1.09%" → **no tiene sentido**
- Comparaciones inválidas

**Acción Requerida**:
1. **Investigar fuente de datos**: ¿Por qué ICOR es negativo en ETL?
   ```python
   # Verificar transformación en etl/polars_transform.py
   # ¿Se está invirtiendo el signo incorrectamente?
   ```

2. **Opción A** (si datos son correctos negativos):
   - Actualizar rango esperado a `-500 to 0`
   - Cambiar visualización para mostrar valor absoluto
   - Actualizar documentación: "ICOR negativo indica..."

3. **Opción B** (más probable - error de transformación):
   - Corregir ETL para invertir signo: `icor_abs = abs(icor)`
   - Re-ejecutar ETL histórico
   - Validar que valores queden en 0-500%

**Prioridad**: 🔴 **CRÍTICA** - Datos inválidos en producción

---

### 2. ICAP: 100% Valores en Zero

**Score**: 70/100 para 6/7 bancos (solo penalty por zeros)

**Problema**:
```
Expected Range: 0 - 30 %
Actual Range: 0.00 - 0.00 (100% de 103 valores = 0)
Latest Value: 0.00%
```

**Bancos afectados**: INVEX, SISTEMA, SANTANDER, BANORTE, HSBC, CITIBANAMEX

**Causa Raíz**:
- Columna `icap_total` existe pero **todos los valores son 0.00**
- Script de validación previo reportó "89.2% cobertura" pero valores son zeros, no NULLs
- ETL no está cargando datos de ICAP correctamente

**Implicaciones**:
- Queries como "ICAP de INVEX" retornan línea plana en 0
- Usuario no puede analizar capitalización
- Visualización inútil

**Acción Requerida**:
1. **Verificar fuente de datos CNBV**:
   ```sql
   -- ¿CNBV reporta ICAP como columna separada?
   SELECT DISTINCT column_name FROM cnbv_raw_data WHERE column_name LIKE '%cap%';
   ```

2. **Revisar transformación ETL**:
   ```python
   # En etl/polars_transform.py
   # Buscar cálculo de icap_total
   # ¿Fórmula correcta? ¿Columna fuente correcta?
   ```

3. **Opciones**:
   - **Si CNBV no tiene ICAP**: Eliminar métrica o calcular a partir de otras columnas
   - **Si está en otro campo**: Mapear campo correcto en ETL
   - **Si cálculo está mal**: Corregir fórmula

**Prioridad**: 🔴 **CRÍTICA** - Métrica nueva anunciada pero sin datos

---

## 🟠 Problemas Importantes (P1)

### 3. BBVA: Sin Datos para Ninguna Métrica ✅ RESUELTO

**Status**: ✅ **FIXED** (2025-12-03)

**Problema Original**:
- BBVA tenía solo 75 registros hasta 2023-04-01 (hace 2 años)
- Todas las métricas con valores 0 o NULL

**Causa Raíz Identificada**:
- El catálogo `Instituciones.xlsx` usa "BBVA MÉXICO" (con acento)
- El mapping `BANK_NAME_MAPPING` solo tenía "BBVA MEXICO" (sin acento)
- La búsqueda `if pattern in name` fallaba: "BBVA MEXICO" ∉ "BBVA MÉXICO"
- Resultado: "BBVA MÉXICO" no se normalizaba a "BBVA"

**Solución Aplicada**:
1. Agregado "BBVA MÉXICO" (con acento) al `BANK_NAME_MAPPING` en `etl/transforms_polars.py:33`
2. Re-ejecutado ETL: cargó 28 meses adicionales (mayo 2023 a julio 2025)
3. **Resultado**: 103 registros totales (antes: 75), datos hasta 2025-07-01

**Validación**:
```
Date range: 2017-01-01 to 2025-07-01
Total records: 103
Recent values:
- Cartera Total: ~252M MXN
- IMOR: 0.30%
- ICOR: 0.81%
```

**File Modified**: `etl/transforms_polars.py:33`

**Prioridad**: 🟠 **ALTA** - Banco importante sin datos → ✅ RESUELTO

---

### 4. TDA: 91.3% Valores en Zero ✅ DOCUMENTADO

**Status**: ✅ **DOCUMENTED** (2025-12-03) - Comportamiento esperado

**Análisis Realizado**:
TDA (Tasa de Descuentos Anuales) es una **métrica anual reportada solo en enero**, no mensual.

**Datos Validados**:
```
Coverage: 9/103 valores non-zero por banco (8.7%)
Frecuencia: 1 valor por año (enero, excepto 2022 que es febrero)
Expected Range: 0 - 100 %
Actual Data: 91.3% de valores = 0.00
Non-zero Range: 0 - 6.91%
Latest Value: 0.00%
```

**Fechas con Datos Non-Zero**:
- 2017-01-01: INVEX = 4.25%, HSBC = 6.91%, SISTEMA = 4.11%
- 2018-01-01: INVEX = 5.52%, HSBC = 5.50%, SISTEMA = 3.96%
- 2019-01-01: INVEX = 4.47%, HSBC = 4.29%, SISTEMA = 3.89%
- 2020-01-01: INVEX = 3.44%, HSBC = 4.52%, SISTEMA = 4.10%
- 2021-01-01: INVEX = 3.80%, HSBC = 5.35%, SISTEMA = 4.50%
- 2022-02-01: INVEX = 2.95%, HSBC = 6.00%, SISTEMA = 3.41%
- 2023-01-01: INVEX = 3.01%, HSBC = 5.48%, SISTEMA = 3.03%
- 2024-01-01: INVEX = 4.82%, HSBC = 4.54%, SISTEMA = 2.88%
- 2025-01-01: INVEX = 2.31%, HSBC = 2.34%, SISTEMA = 1.49%

**Conclusión**:
- ✅ **TDA es métrica anual válida**, reportada cada enero
- ✅ **El 91.3% de zeros es correcto** (11 meses sin datos + 1 mes con datos)
- ✅ **No requiere corrección** - comportamiento esperado

**Recomendación para UI**:
- Mostrar TDA como "Métrica Anual" con tooltip: "Reportada en enero de cada año"
- Visualizaciones deben usar agregación anual, no mensual
- Filtros de fecha deben sugerir comparación año a año

**Prioridad**: ✅ **RESUELTO** - No es problema, es comportamiento esperado de métrica anual

---

### 5. Cartera Total BBVA: 100% Zeros ✅ RESUELTO

**Status**: ✅ **FIXED** (2025-12-03) - Resuelto con fix de normalización BBVA

**Problema Original**:
- BBVA tenía 75 registros de cartera_total pero todos eran 0.00

**Solución**:
- Mismo fix que punto #3: agregado "BBVA MÉXICO" al mapping
- Después del ETL: cartera_total ahora tiene valores reales (~252M MXN)
- Otros bancos tienen valores válidos (INVEX: 1,775 MDP, SISTEMA: 3.1M MDP)

**Relacionado con**: Problema #3 (BBVA sin datos)

**Acción**: Misma que #3

---

## 🟡 Warnings (P2)

### 6. TASA_MN: Posible Problema de Unidades

**Score**: 92.6/100 (aceptable pero revisar)

**Observación**:
```
Expected Range: 0 - 50 %
Actual Range: 0 - 20.60%
Mean: 10.16%
Latest (INVEX): 18.38%
```

**Estado**: ✅ Dentro de rango, pero en testing manual vimos:
- "TASA_MN de INVEX" retornó 1838.14 (valor * 100?)

**Requiere Verificación**:
1. ¿DB almacena en % (18.38) o basis points (1838)?
2. ¿Transformación inconsistente entre ETL y query engine?

**Acción**: Verificar consulta directa:
```sql
SELECT fecha, tasa_mn FROM monthly_kpis WHERE banco_norm='INVEX' ORDER BY fecha DESC LIMIT 5;
```

---

## ✅ Métricas con Calidad Excelente

### IMOR (Índice de Morosidad)
- **Score**: 98.6/100 promedio
- **Cobertura**: 100% para 6/7 bancos
- **Rango**: 7.12 - 215.22% (dentro de esperado)
- **Última actualización**: 2025-07-01

### Cartera Total
- **Score**: 95.7/100 promedio
- **Cobertura**: 100% para 6/7 bancos
- **Datos válidos y actualizados**

### TASA_MN y TASA_ME
- **Score**: 92.6/100 promedio
- **Cobertura**: 100% para 6/7 bancos
- **Solo ~1-3% zeros (aceptable)**

---

## 📋 Plan de Acción Priorizado

### Esta Semana (P0)

1. **ICOR Negativo** (4h)
   - [ ] Investigar transformación ETL
   - [ ] Corregir signo o rango esperado
   - [ ] Validar datos corregidos
   - [ ] Re-ejecutar ETL si necesario

2. **ICAP Zeros** (4h)
   - [ ] Verificar fuente CNBV
   - [ ] Corregir mapeo/cálculo en ETL
   - [ ] Validar datos reales
   - [ ] Si no disponible: Eliminar métrica o marcar como "no soportada"

3. **Data Quality Warnings en API** (2h)
   - [ ] Implementar warnings en response metadata
   - [ ] Agregar `data_quality_score` por banco/métrica
   - [ ] Mostrar mensaje cuando score < 60

### Próxima Semana (P1)

4. **BBVA Sin Datos** (3h)
   - [ ] Diagnosticar ETL logs
   - [ ] Corregir mapeo de nombres
   - [ ] Re-sincronizar desde abril 2023

5. **TDA Investigación** (2h)
   - [ ] Documentar si métrica es histórica
   - [ ] Agregar nota en UI
   - [ ] Considerar remover si obsoleta

### Mejoras Futuras (P2)

6. **TASA Normalización** (1h)
7. **Automated Data Quality Alerts** (3h)
8. **ETL Monitoring Dashboard** (4h)

---

## 🎯 Métricas de Éxito

**Objetivo**: Score General ≥ 90/100

**Targets por Métrica**:
| Métrica | Actual | Target |
|---------|--------|--------|
| IMOR | 98.6 ✅ | 95 |
| ICOR | **7.1** 🔴 | 95 |
| ICAP | **67.1** 🟠 | 90 |
| TDA | 69.4 🟠 | 85 |
| TASA_MN | 92.6 ✅ | 90 |
| TASA_ME | 85.7 ✅ | 85 |
| Cartera | 95.7 ✅ | 95 |

**Bloqueadores para Producción**:
- 🔴 ICOR con valores negativos (usuario reportará como bug)
- 🔴 ICAP con zeros (métrica anunciada pero no funciona)

**Recomendación**: **No promover a producción** hasta resolver P0s.

---

## 📞 Contactos y Seguimiento

**Responsable Data Quality**: [TBD]
**ETL Owner**: [TBD]
**Fecha Revisión**: 2025-12-03
**Próxima Validación**: 2025-12-10 (después de fixes)
