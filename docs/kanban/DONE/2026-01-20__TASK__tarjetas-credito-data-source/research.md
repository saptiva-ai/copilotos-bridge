# Research: Tarjetas de Credito Data Source

**Fecha**: 2026-01-28
**Status**: Completado

---

## Resumen Ejecutivo

Los datos de tarjetas de credito **SI existen** en las fuentes CNBV (`040_TO.csv`) con 73 codigos de concepto especificos. Sin embargo, actualmente el ETL **agrega** estos datos en `cartera_consumo_total` sin separarlos como columna individual.

---

## 1. Fuentes de Datos Encontradas

### Archivo Principal
- **Ruta**: `plugins/bank-advisor-private/data/raw/AnalisisGeneral/sh_datos_csv_40_i/040_TO.csv`
- **Registros**: 11.78 millones
- **Columnas**: `concepto`, `institucion`, `fecha`, `tipo_saldo`, `saldo_se`

### Catalogo de Conceptos
- **Ruta**: `plugins/bank-advisor-private/data/raw/AnalisisGeneral/sh_datos_csv_40_i/catalogo_conceptos_040.xlsx`
- **Total conceptos**: 740
- **Conceptos TDC**: 73

---

## 2. Codigos de Concepto - Tarjetas de Credito

### Balance Sheet (Situacion Financiera)

| Concepto | Descripcion |
|----------|-------------|
| 40100207 | Tarjeta de credito (cartera) |
| 40100246 | Tarjeta de credito |
| 40100285 | Tarjeta de credito |
| 40100324 | Tarjeta de credito |
| 40100363 | Tarjeta de credito |
| 40100402 | Tarjeta de credito |
| 40100063 | Tarjeta de credito |

### Estado de Resultados

| Concepto | Descripcion |
|----------|-------------|
| 40100114 | Tarjeta de Credito |
| 40100137 | Tarjeta de credito |
| 40100149 | Tarjeta de credito |
| 40100150 | Primera anualidad y subsecuentes de tarjeta de credito |
| 40100425 | Tarjeta de Credito |
| 40100447 | Tarjeta de Credito |
| 40100469 | Tarjeta de Credito |
| 40100491 | Tarjeta de Credito |
| 40100513 | Tarjeta de Credito |
| 40100535 | Tarjeta de Credito |

### Indicadores

| Concepto | Descripcion |
|----------|-------------|
| 40200041 | Tarjeta de credito |
| 40200059 | Tarjeta de credito |
| 40200080 | Tarjeta de credito |
| 40200102 | Tarjeta de credito |
| 40200124 | Tarjeta de credito |
| 40200146 | Tarjeta de Credito |
| 40200168 | Tarjeta de Credito |

### Flujos 12 Meses

| Concepto | Descripcion |
|----------|-------------|
| 40200190 | Tarjeta de Credito |
| 40200199 | Tarjeta de credito |

---

## 3. Arquitectura ETL Actual

### Pipeline de Carga
```
040_TO.csv
  → loaders_analisis_general.py (Polars, chunks 1M)
  → bank_src_analisis_general (particionado por año)
  → transforms.py (agrega conceptos)
  → monthly_kpis
```

### Archivos Clave

| Archivo | Funcion |
|---------|---------|
| `etl/core/loaders/loaders_analisis_general.py` | Carga CSV a PostgreSQL |
| `etl/ops/load_catalogo_conceptos.py` | Carga catalogo Excel |
| `etl/core/transforms.py` | Transforma a metricas |
| `migrations/003_schema_extended_unified.sql` | Schema monthly_kpis |

---

## 4. Schema monthly_kpis (Relevante)

```sql
-- Columnas existentes relacionadas con consumo
cartera_consumo_total NUMERIC(20,2),  -- Incluye TDC agregado
pe_consumo NUMERIC(10,4),             -- Perdida esperada consumo
tasa_invex_consumo NUMERIC(10,4),     -- Tasa consumo

-- Columna TDC: NO EXISTE actualmente
-- cartera_tdc NUMERIC(20,2),         -- Propuesta
```

### Logica de Agregacion Actual (transforms.py)

```python
consumo_cols = [
    "consumo_etapa_1",    # Etapa 1 (sin deterioro)
    "consumo_etapa_2",    # Etapa 2 (deterioro significativo)
    "consumo_etapa_3",    # Etapa 3 (deterioro crediticio)
    "consumo_etapa_vr"    # Tasa variable
]
cartera_consumo_total = SUM(consumo_cols)  # TDC incluido aqui
```

---

## 5. Datos Operativos Disponibles

En `hip_info_operativa_consolidada`:

| Columna | Descripcion | Status |
|---------|-------------|--------|
| `contratos_tdc` | Numero de contratos TDC por banco | Disponible |

Mapeado en `analytics_service.py:151`.

---

## 6. Query Parser (Parcial)

En `query_spec_parser.py` ya existe:

```python
CARTERA_TDC = MetricAlias(
    triggers=["tarjeta de credito", "tarjetas de credito", "tdc", "credit cards"],
    # ...pero NO esta mapeado a columna real
)
```

---

## 7. Gap Analysis

| Aspecto | Estado | Accion Requerida |
|---------|--------|------------------|
| Datos raw disponibles | OK | Ninguna |
| Catalogo conceptos | OK | Ninguna |
| ETL carga datos | OK | Ninguna |
| Columna TDC separada | FALTA | Agregar a schema + transforms |
| Query parser mapping | PARCIAL | Completar mapping |
| Indicadores TDC (IMOR) | FALTA | Agregar columnas indicadores |

---

## 8. Auditoria del Sistema (2026-01-28)

### Arquitectura Real Descubierta

La auditoria revelo que el sistema es mas complejo de lo inicialmente documentado:

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA WAREHOUSE (39.4M registros)         │
├─────────────────────────────────────────────────────────────┤
│  hip_analisis_general (11.78M) ← 040_TO.csv [DATOS TDC]    │
│  hip_cartera_comercial (4.96M)                              │
│  hip_banca_multiple (12.5M)                                 │
│  hip_reporte_r04a (5M+)                                     │
│  hip_reporte_r12a (4.3M)                                    │
└─────────────────────────────────────────────────────────────┘
           ↓ (migrations 030-049)
┌─────────────────────────────────────────────────────────────┐
│              MATERIALIZED VIEWS (8 existentes)              │
├─────────────────────────────────────────────────────────────┤
│  bank_mv_ranking_cartera_mensual                            │
│  bank_mv_evolucion_cartera                                  │
│  bank_mv_cartera_por_actividad                              │
│  bank_mv_cartera_por_tamano                                 │
│  bank_mv_vivienda_por_producto                              │
│  bank_mv_vivienda_por_perfil                                │
│  bank_mv_cartera_por_estado                                 │
│  bank_mv_metricas_financieras                               │
└─────────────────────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────────────────┐
│              FACT TABLES (3NF Normalizado)                  │
├─────────────────────────────────────────────────────────────┤
│  bank_fact_kpis_mensual (antes monthly_kpis)                │
│  bank_fact_cartera_segmentada                               │
│  bank_fact_cartera_comercial                                │
│  bank_fact_cartera_vivienda                                 │
└─────────────────────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────────────────┐
│              COMPATIBILITY VIEWS                            │
├─────────────────────────────────────────────────────────────┤
│  monthly_kpis → VIEW de bank_fact_kpis_mensual              │
└─────────────────────────────────────────────────────────────┘
```

### Hallazgos Clave

1. **`monthly_kpis` es un VIEW**, no una tabla. La tabla real es `bank_fact_kpis_mensual`
2. **51 migrations** documentan toda la evolucion del schema
3. **8 materialized views** ya existen para analytics pre-agregados
4. Los datos TDC estan en `hip_analisis_general` (11.78M registros)
5. El ETL usa Polars con pipeline de 1486 lineas en transforms.py

### Gaps Identificados

| Gap | Riesgo | Descripcion |
|-----|--------|-------------|
| Hip data fuera de migrations | Alto | 39.4M registros cargados sin validacion formal |
| MV refresh no automatico | Medio | Funciones manuales, sin scheduler |
| Excepciones silenciosas | Medio | `except Exception: pass` en transforms.py |
| SQLAlchemy desactualizado | Bajo | Solo 4 modelos vs 50+ tablas |

---

## 9. Critica de Opcion A Original

La Opcion A (Extender ETL) tiene problemas significativos:

| Problema | Impacto |
|----------|---------|
| Tabla incorrecta | `monthly_kpis` es VIEW, no tabla |
| Sin migration path | No contemplo los 51 migrations existentes |
| Ignora patrones | Ya hay 8 MVs, el patron es crear MV no modificar fact |
| Fuente diferente | TDC esta en `hip_analisis_general`, no en fuentes de kpis |
| Invasivo | Modificar transforms.py (1486 lineas) es riesgoso |

---

## 10. Opciones de Implementacion Revisadas

### Opcion A: Extender ETL ~~(Recomendado)~~ (DESCARTADA)

**Esfuerzo**: Alto (2-3 dias)
**Riesgo**: Alto - puede romper ETL existente
**Problemas**: Ver seccion 9

### Opcion B: Materialized View (RECOMENDADA)

**Esfuerzo**: Bajo (4-6 horas)
**Riesgo**: Bajo - es aditivo, no modifica nada existente

1. Crear migration 052 con `bank_mv_cartera_tdc`
2. Agregar funcion de refresh
3. Actualizar analytics_service.py
4. Completar query_spec_parser.py

**Ventajas**:
- Sigue patron existente (8 MVs similares)
- Datos historicos ya disponibles (11.78M registros)
- No modifica ETL core
- Refresh concurrente sin bloqueos

### Opcion C: Usar Contratos como Proxy (LIMITADA)

**Esfuerzo**: Bajo (horas)
**Limitacion**: Solo conteo de contratos, no montos

---

## 11. Conceptos Recomendados para MV

### Cartera TDC (Balance Sheet)

| Concepto | Descripcion | Uso en MV |
|----------|-------------|-----------|
| 40100207 | Tarjeta de credito (cartera total) | cartera_tdc |
| 40100246 | Tarjeta de credito etapa 1 | cartera_tdc_etapa1 |
| 40100285 | Tarjeta de credito etapa 2 | cartera_tdc_etapa2 |
| 40100324 | Tarjeta de credito etapa 3 | cartera_tdc_vencida |

### Indicadores TDC

| Concepto | Descripcion | Uso en MV |
|----------|-------------|-----------|
| 40200041 | IMOR Tarjeta de credito | imor_tdc |
| 40200102 | Cobertura Tarjeta de credito | icor_tdc |

---

## 12. Siguiente Paso

Crear `plan.md` con implementacion de Opcion B:
1. Migration 052: crear `bank_mv_cartera_tdc`
2. Service: actualizar analytics_service.py
3. Parser: completar query_spec_parser.py
4. Tests: validar queries de usuario
5. Refresh: agregar al ETL runner

---

## Referencias

- Catalogo: `catalogo_conceptos_040.xlsx`
- Schema real: `migrations/024_rename_monthly_kpis.sql` (bank_fact_kpis_mensual)
- MVs existentes: `migrations/030-049`
- Transforms: `etl/core/transforms.py` (no modificar)
- Parser: `src/bankadvisor/services/query_spec_parser.py`
- Analytics: `src/bankadvisor/services/analytics_service.py`
