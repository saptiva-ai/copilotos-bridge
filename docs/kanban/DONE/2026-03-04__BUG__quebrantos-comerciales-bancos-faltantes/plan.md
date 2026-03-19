# Plan: Cargar quebrantos comerciales faltantes

## Fuente

`Castigos Comerciales.xlsx` (56KB, Sheet 1, 2209 rows)
- Columnas: `Institucion1`, `Fecha`, `CASTIGOS ACMULUADOS COMERCIAL`, (null)
- Formatos fecha mixtos: `YYYY/M/DD` y `YYYY-MM-DD 00:00:00`
- Valores: acumulados anuales en MDP (se resetean en Enero)
- Rango: 2022-01 a 2025-12 (48 meses), ~48 bancos

## Logica de conversion

```
delta_mensual_mdp = acum[year, month] - acum[year, month-1]
delta_mensual_mdp (Enero) = acum[year, 1]  (prev = 0, inicio de año)
delta_mensual_pesos = delta_mensual_mdp * 1_000_000
```

## Fase 0: Backup

```sql
CREATE TABLE bank_fact_kpis_mensual_qc_bak_20260304
AS SELECT banco_norm, fecha, quebrantos_comerciales
FROM bank_fact_kpis_mensual
WHERE quebrantos_comerciales IS NOT NULL;
```

## Fase 1: Dry-run — Leer Excel y generar deltas

Script Python que:
1. Lee `Castigos Comerciales.xlsx`
2. Mapea codigos institucion → banco_norm usando `bank_dim_institucion`
3. Calcula deltas mensuales (acum[m] - acum[m-1])
4. Filtra solo los 10 peer banks: INVEX, MONEX, BANCREA, SABADELL, MIFEL, MULTIVA, AFIRME, BANSI, VE POR MAS, BANCO BASE
5. **NO** escribe en BD — solo imprime:
   - Total rows a insertar/actualizar
   - Valores para bancos de validacion (INVEX, MULTIVA) para verificar vs BD existente
   - Deltas negativos detectados (para decision: omitir o cargar)
   - Cross-check: Excel delta vs BD existente (debe ser 100% match)

## Fase 2: Dry-run — Simular UPSERT

```sql
-- Para cada (banco_norm, fecha, delta_pesos):
-- SOLO actualizar quebrantos_comerciales, NO tocar otras columnas
UPDATE bank_fact_kpis_mensual
SET quebrantos_comerciales = :delta_pesos
WHERE banco_norm = :banco AND fecha = :fecha
  AND (quebrantos_comerciales IS NULL OR quebrantos_comerciales = 0);
```

Dry-run: ejecutar SELECT para contar cuantas rows matchean el WHERE sin ejecutar UPDATE.

**Protecciones:**
- Solo actualiza rows donde `quebrantos_comerciales IS NULL OR = 0` (no sobreescribe datos existentes)
- Solo toca columna `quebrantos_comerciales` (no afecta cartera, imor, icap, etc.)
- Verifica que `banco_norm` + `fecha` existen en la tabla antes de UPDATE
- Rows que no existen en la tabla se ignoran (no INSERT, solo UPDATE)

## Fase 3: Ejecutar UPSERT

Ejecutar los UPDATEs reales con las protecciones de Fase 2.

## Fase 4: Validacion post-carga

```sql
-- 1. Contar rows actualizadas por banco
SELECT banco_norm, COUNT(*) as total,
       SUM(CASE WHEN quebrantos_comerciales > 0 THEN 1 ELSE 0 END) as nonzero
FROM bank_fact_kpis_mensual
WHERE banco_norm IN ('MONEX','MIFEL','AFIRME','BANCO BASE',
                     'INVEX','MULTIVA','VE POR MAS','BANCREA','BANSI','SABADELL')
AND quebrantos_comerciales IS NOT NULL
GROUP BY banco_norm ORDER BY banco_norm;

-- 2. Verificar T1 totals vs Excel
SELECT EXTRACT(YEAR FROM fecha) as yr,
       SUM(quebrantos_comerciales)/1e6 as total_mdp
FROM bank_fact_kpis_mensual
WHERE banco_norm IN ('INVEX','MONEX','BANCREA','SABADELL','MIFEL',
                     'MULTIVA','AFIRME','BANSI','VE POR MAS','BANCO BASE')
AND EXTRACT(MONTH FROM fecha) IN (1,2,3)
AND fecha >= '2023-01-01'
GROUP BY yr ORDER BY yr;
-- Esperado: 2023=192.87, 2024=1383.47, 2025=18.87

-- 3. Verificar que otras metricas NO cambiaron
SELECT banco_norm, fecha, cartera_total, imor, icap_total
FROM bank_fact_kpis_mensual
WHERE banco_norm = 'MONEX' AND fecha IN ('2024-01-01','2024-06-01')
-- Estos valores deben ser identicos pre y post carga
```

## Fase 5: Refresh MVs

```sql
REFRESH MATERIALIZED VIEW CONCURRENTLY bank_mv_kpis_latest;
-- + las demas MVs que incluyan quebrantos
```

## Rollback

```sql
-- Restaurar desde backup
UPDATE bank_fact_kpis_mensual kpi
SET quebrantos_comerciales = bak.quebrantos_comerciales
FROM bank_fact_kpis_mensual_qc_bak_20260304 bak
WHERE kpi.banco_norm = bak.banco_norm AND kpi.fecha = bak.fecha;

-- Limpiar nuevos valores (rows que eran NULL antes)
UPDATE bank_fact_kpis_mensual kpi
SET quebrantos_comerciales = NULL
WHERE NOT EXISTS (
    SELECT 1 FROM bank_fact_kpis_mensual_qc_bak_20260304 bak
    WHERE bak.banco_norm = kpi.banco_norm AND bak.fecha = kpi.fecha
)
AND kpi.quebrantos_comerciales IS NOT NULL;
```

## Decisiones pendientes

1. **Deltas negativos**: INVEX 2024-10 = -115.86 MDP, MULTIVA 2024-10 = -1167 MDP.
   - Opcion A: Omitir (solo cargar positivos, como hace la BD actual)
   - Opcion B: Cargar todos (refleja realidad contable)
   - **Recomendacion**: Opcion A para consistencia con datos existentes
2. **Bancos fuera del grupo peer**: El Excel tiene ~48 bancos. Cargar solo los 10 peers o todos?
   - **Recomendacion**: Cargar todos para completitud del dataset
