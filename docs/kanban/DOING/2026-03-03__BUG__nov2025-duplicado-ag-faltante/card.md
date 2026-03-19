---
id: "BUG-2026-03-03__nov2025-duplicado-ag-faltante"
title: "Datos Nov 2025 duplicados de Oct + AG (040_TO.csv) faltante en entrega"
status: "DOING"
phase: "Validate"
scope_in:
  - "Documentar hallazgo: Nov 2025 = Oct 2025 en CNBV_Cartera_Bancos_V2.xlsx"
  - "Documentar hallazgo: 040_TO.csv (Analisis General) no incluido en entrega 20260302"
  - "Comunicar a Bajaware y solicitar correcciones"
  - "EDA completo entrega 20260304: comparacion byte-a-byte, analisis 20 archivos"
  - "Cargar CNBV corregido al ETL"
  - "Analisis BM como sustituto de AG: verificacion cruzada 10 metricas"
  - "Analisis ICAP en Tableau: formula trivial ICAP_Total/100 desde ICAP_Bancos.xlsx"
scope_out:
  - "Adapter BM→AG para 56 bancos AG-only (tarea separada BACKLOG)"
  - "Generar datos sintéticos de Nov"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
plan_phase: 0
validation_commands:
  - "psql $DATABASE_URL -c \"SELECT banco_norm, fecha, ROUND(cartera_total::numeric/1e6) FROM bank_fact_kpis_mensual WHERE fecha >= '2025-11-01' AND banco_norm = 'INVEX' ORDER BY fecha\""
pr_files: []
test_status: "N/A — data quality issue, not code"
---

# Summary

- **Objective:** Documentar y comunicar a Bajaware dos problemas de calidad de datos en la entrega `drive-download-20260302T184043Z-1-001`.
- **Impacto original:** (A) Nov 2025 = Oct 2025. (B) Sin AG, Dic 2025 solo tiene datos de 6 bancos.
- **Estado actual:** (A) RESUELTO por re-entrega. (B) MITIGADO — BM suple 9/10 metricas; ICAP viene de ICAP_Bancos.xlsx (tiene Dic 2025). **Listo para cargar.**

# Updates

- 2026-03-03 - Creada. Hallazgos verificados contra BD y Excel fuente.
- 2026-03-04 - EDA completo de re-entrega `drive-download-20260304T143340Z-1-001`:
  - Problema A (CNBV Nov=Oct): **CORREGIDO** — 35/35 cols diferentes, md5 cambio
  - Problema B (040_TO.csv faltante): **SIGUE PENDIENTE** — no incluido
  - Comparacion byte-a-byte: solo 1 de 16 archivos ETL cambio (CNBV +800 bytes)
  - "Nueva carpeta" CSVs Nov=Oct: sin cambios (no lo tocaron)
  - CASTIGOS1.xlsx: duplicado exacto de CASTIGOS.xlsx
  - Archivos Tableau: datos internos de Feb 2025, irrelevantes
  - Mensaje actualizado para Bajaware en research.md
- 2026-03-04 - **HALLAZGO CRITICO**: BM (`sh_datos_40.csv`) contiene mismos datos que AG:
  - 7/7 metricas de cartera: match **exacto** (bit-for-bit) vs AG
  - IMOR/IMORA: ~igual (BM en decimal, AG en porcentaje; delta <0.5%)
  - ICAP: **NO existe en BM** (concepto 4021750 ausente)
  - BM tiene datos hasta Dic 2025 para 58 entidades (incluido INVEX)
  - BM ya no requiere `040_TO.csv` para 9/10 metricas del KPI pipeline
  - Opciones: (1) adapter BM→AG, (2) esperar entrega AG, (3) hibrida
- 2026-03-04 - **PLAN DE CARGA creado** (`plan.md`):
  - 10 fases: backup → copy → dry-run promote → promote → dry-run ETL → dry-run transform → carga UPSERT → IMOR comercial → refresh MVs → validacion
  - Riesgo critico mitigado: `use_upsert=True` para NO truncar bancos AG-only
  - Rollback: tabla backup `bank_fact_kpis_mensual_bak_20260304`
  - Phase cambiada a Plan, listo para ejecutar
- 2026-03-04 - **ICAP en Tableau**: formula trivial `[ICAP Total]/100` desde `ICAP_Bancos.xlsx`:
  - No hay calculo complejo — CNBV entrega ICAP pre-calculado
  - twbx empaquetado: hasta Nov 2024 (viejo)
  - Entrega actual: hasta **Dic 2025**, 98 bancos, 14,333 filas
  - INVEX ICAP Dic 2025: 16.38% (CCB=CCF=16.38%)
  - Confirma: ICAP **NO depende de AG** — tiene fuente independiente
- 2026-03-04 - **CONCLUSION: 10/10 metricas cubiertas sin AG**:
  - 7 carteras → BM (match exacto) o CNBV Excel (7 bancos)
  - IMOR/IMORA → BM (~equivalente) o CNBV Excel
  - ICAP → ICAP_Bancos.xlsx (independiente, hasta Dic 2025)
  - ETL Unificado Paso 5 funciona sin AG (runbook § "Ejecución sin AG")
  - **Listo para cargar**: copiar entrega a incoming, promote, ejecutar ETL
- 2026-03-04 - **EJECUCION COMPLETADA** (approach modificado):
  - Fases 0-4 ejecutadas segun plan (backup, copy, promote, dry-runs)
  - **Fase 5 revelo problema critico**: legacy ETL produce valores ~1000x menores (MDP vs pesos)
  - **Cambio de strategy**: UPDATE quirurgico directo con datos BM (ya en escala pesos)
  - Resultado: 33 rows actualizados, 17 bancos, Nov+Dic 2025
  - Fix adicional: 5,238 periodo_id NULLs corregidos
  - 5/5 MVs refrescadas (1 requirio refresh sin CONCURRENTLY)
  - **Validacion final OK**:
    - INVEX Nov: cartera=52.31B, vencida=1.317B, consumo=35.99B, imor=0.0252, icap=15.74
    - INVEX Dic: cartera=51.91B, vencida=1.375B, consumo=36.02B, imor=0.0265, icap=16.38
    - 49 bancos, 11,920 rows (sin perdida de datos)
    - 0 ICAP < 1, Nov ≠ Oct confirmado
  - Backup disponible: `bank_fact_kpis_mensual_bak_20260304`
- 2026-03-04 - **TASAS MN/ME Dic 2025 cargadas** (CorporateLoan):
  - Antes: solo 6 bancos con tasa_mn/tasa_me en Dic 2025
  - Despues: 35 bancos con tasa_mn, 30 con tasa_me
  - Portfolio weights (portfolio_mn/me) tambien cargados para 35 bancos
  - INVEX Dic: tasa_mn=12.86%, tasa_me=8.26%, portfolio_mn=$11.4B
  - Cache PROD invalidado (ETL_COMPLETE), MVs refrescadas
  - Verificado: no era cache — respuesta vieja en historial de conversacion

# Ejecucion Real

## Completado (2026-03-04)

1. **Fase 0**: Backup → `bank_fact_kpis_mensual_bak_20260304` (11,920 rows)
2. **Fase 1**: Copiar entrega a `data/raw/incoming/`
3. **Fase 2-3**: Promote symlinks + BM symlink manual
4. **Fase 4**: Dry-run loaders — 8/8 OK
5. **Fase 5**: Dry-run transform — **HALLAZGO**: escala MDP ~1000x menor que DB
6. **UPDATE quirurgico**: Leer BM `sh_datos_40.csv`, filtrar saldo=130 + conceptos KPI, UPDATE directo por (banco, fecha)
7. **Fix periodo_id**: 5,238 NULLs → calculados desde fecha
8. **Refresh MVs**: 5/5 refrescadas
9. **Validacion**: Todos los criterios cumplidos

## Posterior (requiere codigo — tarea BACKLOG)

- Adapter BM→AG: leer `sh_datos_40.csv`, filtrar saldo=130, renombrar campos a formato AG
- Permitiria actualizar los 56 bancos AG-only a Nov/Dic 2025
- Estimado: ~medio dia desarrollo + tests
