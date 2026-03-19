---
id: "BUG-2026-03-04__quebrantos-comerciales-bancos-faltantes"
title: "Quebrantos comerciales: 4 bancos sin datos historicos + meses faltantes"
status: "DONE"
phase: "Validate"
scope_in:
  - "Cargar quebrantos_comerciales historicos para MONEX, MIFEL, AFIRME, BANCO BASE + meses faltantes"
  - "Fuente correcta: CASTIGOS.xlsx (LIB_CASTIGOS_COMERC, flujo mensual bruto)"
  - "Dry-run completo antes de UPSERT"
  - "Validacion cruzada post-carga vs CASTIGOS.xlsx"
scope_out:
  - "Cambiar el loader ETL permanente (tarea separada)"
  - "Cargar datos pre-2022 (Excel solo tiene 2022-2025)"
artifacts:
  card: card.md
  plan: plan.md
pr_files: []
test_status: "N/A"
---

# Summary

- **Problema:** `quebrantos_comerciales` en `bank_fact_kpis_mensual` tiene datos incompletos.
- **4 bancos sin historico:** MONEX, MIFEL, AFIRME, BANCO BASE (solo 1 row: Nov 2025 del update quirurgico).
- **Meses faltantes:** Incluso bancos cargados (VE POR MAS, MULTIVA, BANCREA) tienen ~50% de meses sin datos.
- **Impacto:** Charts de "INVEX vs PROMEDIO" para quebrantos muestran totales incorrectos (ej. T1 2023: $66M vs real $193M).

# Root Cause

El ETL `load_castigos()` carga desde `CASTIGOS.xlsx` pero no lograba insertar todos los bancos.
`CASTIGOS.xlsx` contiene 46 bancos × 48 meses, columna `LIB_CASTIGOS_COMERC` (flujo mensual bruto en MDP).

# Leccion aprendida: dos fuentes, dos semanticas

Existen **dos archivos** de castigos comerciales con semanticas distintas:

| Archivo | Columna | Semantica | Valores |
|---------|---------|-----------|---------|
| `CASTIGOS.xlsx` | `LIB_CASTIGOS_COMERC` | Flujo mensual bruto (liberaciones) | Siempre >= 0 |
| `Castigos Comerciales.xlsx` | `CASTIGOS ACUMULADOS COMERCIAL` | Acumulado anual | Se resetea en Enero |

**Error cometido**: Se intento cargar inicialmente desde `Castigos Comerciales.xlsx` (acumulados),
calculando deltas mensuales. Esto produjo valores correctos para algunos meses pero incorrectos
para otros — los deltas negativos (reversiones contables) reducian los totales.

**Ejemplo T1 2025** (grupo peer):
- `CASTIGOS.xlsx` (correcto): **51.06 MDP** (MIFEL 37.33, AFIRME 9.16)
- `Castigos Comerciales.xlsx` deltas positivos: 30.70 MDP
- `Castigos Comerciales.xlsx` deltas netos: 18.87 MDP

La BD debe usar `CASTIGOS.xlsx` porque es la fuente del ETL `load_castigos()`.

# Evidence

## Impacto en T1 por grupo peer (10 bancos)

| T1 | BD antes | CASTIGOS.xlsx | BD despues |
|----|----------|---------------|------------|
| 2023 | 65.78 MDP | 187.09 MDP | **192.87 MDP** |
| 2024 | 1,366.51 MDP | 1,363.98 MDP | **1,383.47 MDP** |
| 2025 | 3.55 MDP | 51.06 MDP | **53.02 MDP** |

Nota: BD despues > CASTIGOS.xlsx para T1 2023/2024 porque incluye datos pre-existentes
de bancos que ya estaban parcialmente cargados (BANCREA, VE POR MAS, etc.).

# Resultado

## UPSERT ejecutado (2026-03-04)

**Fuente**: `CASTIGOS.xlsx` columna `LIB_CASTIGOS_COMERC` (flujo mensual, MDP × 1e6 → pesos)

- **1652 rows actualizadas** (NULL/0 → valor de CASTIGOS.xlsx)
- **410 rows skipped** (ya tenian datos correctos, 363 match exacto)
- **54 rows sin fila en BD** (skipped, solo UPDATE no INSERT)
- Proteccion: solo actualiza `quebrantos_comerciales` donde es NULL o 0
- Backup: `bank_fact_kpis_mensual_qc_bak_20260304`
- 12/12 MVs refreshadas

## Canary check

MONEX cartera_total, imor, icap_total: sin cambios. Solo quebrantos_comerciales actualizada.
