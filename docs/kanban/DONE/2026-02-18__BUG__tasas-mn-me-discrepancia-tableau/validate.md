# Validación: Discrepancia TASA PROMEDIO MN/ME

## Fecha: 2026-02-18

## Resumen

Fix aplicado en dos fases:
1. **Fase 1** (denominador asimétrico): Adoptar método Tableau donde rate=0 infla denominador
2. **Fase 2** (NULL vs 0.0): Cuando ALL rates=0, producir NULL en vez de 0.0

## Verificación Ene 2025 — Paridad Tableau ✅

| Banco | MN DB | MN Target | ME DB | ME Target |
|-------|-------|-----------|-------|-----------|
| BANCREA | 13.5266% | 13.5266% | 2.9481% | 2.95% |
| BANCO BASE | 13.1707% | 13.1707% | 7.4674% | 7.47% |
| INVEX | 15.0100% | — | 9.0477% | 9.05% |
| MONEX | 12.6951% | 12.6951% | 7.1170% | 7.12% |
| SABADELL | 13.0253% | 13.0253% | 7.3642% | 7.36% |
| VE POR MAS | 13.4341% | 13.4341% | 7.6300% | — |

Todos los valores con target coinciden (tolerancia ME ±0.02pp por redondeo de display).

## Verificación NULL→0 — BANCREA ME ✅

| Periodo | Antes (bug) | Despues (fix) |
|---------|-------------|---------------|
| 202201-202412 | 0.000000 | NULL |
| 202501 | 0.029481 | 0.029481 (sin cambio) |
| 202502+ | valores reales | sin cambio |

- **36 periodos** corregidos de `0.0` → `NULL` para BANCREA ME
- **48 grupos totales** con all-zero rates ahora producen NULL
- **0 zeros espurios** restantes (excl. SISTEMA)

## Verificación Pipeline ✅

- `_build_timeline_chart()` preserva `None` → gaps en Plotly
- `evolution.py` filtra `IS NOT NULL` → NULLs no aparecen como data points
- El bar chart (`_build_comparison_chart()`) convierte `None→0` (aceptable para barras)

## Tests de Regresión ✅

```
17/17 passed — test_backfill_tasas_tableau_parity.py
```

Tests nuevos:
- `test_all_zero_rates_gives_null` — ALL rates=0 → None
- `test_bancrea_me_jul2024_all_zero` — caso real BANCREA
- `test_single_positive_rate_among_zeros` — 1 positivo entre zeros → valor válido

## PROD Execution Log

1. Dry-run: 7,558 pairs, 48 NULL groups
2. Execute: 7,558 rows updated + 18 TE rows
3. Manual NULL fix: 5 additional zeros → NULL (psycopg edge case)
4. MV refresh: `bank_mv_comparativa_bancos`, `bank_mv_resumen_sistema`
5. Final verification: 0 zeros remaining, all parity values match

## Bugs Separados Identificados (fuera de scope)

| Archivo | Linea | Issue |
|---------|-------|-------|
| `chart_formatter.py` | 1092 | `.fillna(0)` en stacked bar pivot |
| `region_service.py` | 230-235,261 | `COALESCE(...,0)` + `.fillna(0)` |
| `analytics_service.py` | 2343-2348 | `COALESCE(...,0)` en SQL regional |

Estos afectan charts regionales/IFRS, no tasa MN/ME.
