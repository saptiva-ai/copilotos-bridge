# BUG: Discrepancia TASA PROMEDIO MN/ME entre Tableau y Sistema

**ID**: 2026-02-18__BUG__tasas-mn-me-discrepancia-tableau
**Estado**: DONE
**Prioridad**: Alta
**Creado**: 2026-02-18

## Problema

Las métricas TASA PROMEDIO MN y TASA PROMEDIO ME del sistema Saptiva/BankAdvisor divergen de los valores mostrados en el tablero Tableau de referencia (Invex_Tablero_V3) para el mismo periodo (Enero 2025).

## Impacto

- Usuarios comparan pantalla Saptiva (azul) vs Tableau (blanca) y detectan inconsistencias
- BANCREA ME: diferencia masiva (2.95% Tableau vs 7.80% Sistema)
- MN: diferencias de 0.04-0.18pp en 5 bancos (BANCREA, VE POR MAS, BANCO BASE, MONEX, SABADELL)
- ME: diferencias de 0.02-4.85pp en 3+ bancos
- Afecta confianza en el sistema

## Bancos Afectados

### MN (Moneda Nacional)
| Banco | Tableau | Sistema | Diff |
|-------|---------|---------|------|
| BANCREA | 13.5266% | 13.56% | +0.04pp |
| VE POR MAS | 13.4341% | 13.48% | +0.04pp |
| BANCO BASE | 13.1707% | 13.35% | +0.18pp |
| SABADELL | 13.0253% | 13.07% | +0.04pp |
| MONEX | 12.6951% | 12.75% | +0.05pp |

### ME (Moneda Extranjera)
| Banco | Tableau | Sistema | Diff |
|-------|---------|---------|------|
| BANCREA | 2.95% | 7.80% | +4.85pp |
| BANCO BASE | 7.47% | 7.66% | +0.19pp |
| INVEX | 9.05% | 9.31% | +0.26pp |
| MONEX | 7.12% | 7.14% | +0.02pp |
| SABADELL | 7.36% | 7.38% | +0.02pp |

## Fuente de Verdad

**Tableau es la fuente de verdad.** Nuestro sistema debe coincidir con los valores de Tableau.

Los valores de las capturas de pantalla (ej: BANCREA MN 13.5266%, BANCREA ME 2.95%) son el **target inmediato** a alcanzar. Si después del fix no se logra coincidencia exacta con algún valor de las capturas, se registra como **hipótesis plausible: las capturas pueden usar un data refresh diferente al CSV disponible en el repo**.

## Causa Raíz (HIPÓTESIS PRINCIPAL — validada numéricamente)

**Manejo distinto de filas con `Average Rate = 0`** en el denominador del promedio ponderado:

- **Tableau**: `if Rate = 0 THEN NULL ELSE Rate/100 END` → NULL excluido del numerador SUM, pero **Total Portfolio se incluye en denominador**
- **Nuestro backfill** (`scripts/data/backfill_tasas.py:162-171`): filtra `Average Rate > 0` → excluye de **AMBOS** numerador y denominador

Resultado: `denominador_Tableau > denominador_nuestro` → `tasa_Tableau < tasa_nuestra`

Caso extremo BANCREA ME: 10 filas tasa=0 con $102M portfolio vs 1 fila tasa=7.8% con $62M. Tableau: 7.8×62/(62+102) = 2.95%. Nuestro: 7.8×62/62 = 7.80%.

**Estado de validación**: Reproducción numérica con el CSV del repo coincide con los 10 valores de referencia de las capturas (error < 0.02pp). Si algún valor no coincide post-fix en PROD, verificar si el CSV en PROD difiere del CSV del repo.

## Siguiente Acción

1. Aplicar fix en `backfill_tasas.py` (adoptar método Tableau)
2. Verificar que los valores post-fix coincidan con las capturas
3. Si hay discrepancias residuales → hipótesis: data refresh diferente
4. Re-ejecutar backfill contra PROD
5. Agregar tests de regresión

## Documentos Relacionados

- [research.md](research.md) - Hallazgos detallados y evidencia
- [repro.md](repro.md) - Pasos de reproducción
- [tableau.md](tableau.md) - Análisis del workbook Tableau
- [data_audit.md](data_audit.md) - Auditoría de datos crudos
- [fix_plan.md](fix_plan.md) - Plan de corrección y tests

## Archivos Clave del Sistema

| Componente | Ruta |
|-----------|------|
| Backfill script | `scripts/data/backfill_tasas.py` |
| Metric normalizer | `plugins/bank-advisor-private/src/bankadvisor/domain/services/metric_normalizer.py` |
| Tableau workbook | `plugins/bank-advisor-private/data/raw/incoming/drive-download-20260212T024209Z-1-001/tableau_extract/Invex_Tablero_V3.twb` |
| Raw CSV | `plugins/bank-advisor-private/data/raw/incoming/drive-download-20260212T024209Z-1-001/CorporateLoan_CNBVDB.csv` |
| E2E tests tasas | `tests/e2e/charts/test_tasa_{mn,me}_dual_prompts.py` |
