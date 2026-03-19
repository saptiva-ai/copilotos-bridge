---
id: "BUG-2026-03-03__corporate-loan-invex-tasa-etl"
title: "ETL load_corporate_loan() no inyecta tasa_mn/tasa_me de INVEX"
status: "DONE"
phase: "Done"
scope_in:
  - "Fix merge CorporateLoan → bank_fact_kpis_mensual para INVEX"
  - "Resolver mismatch institution code 040059 vs 040131 en merge_corporate_rates()"
  - "Corregir documentación incorrecta en etl_runbook.md y source_mapping.md"
scope_out:
  - "Cambios en load_corporate_loan() (el loader funciona correctamente)"
  - "Cambios en frontend o analytics_service"
  - "Fix de otras métricas INVEX (ya resuelto en BUG-2026-03-02)"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 1
validation_commands:
  - "PYTHONPATH=plugins/bank-advisor-private .venv/bin/python3.11 -c 'diagnostic script'"
  - "psql: SELECT banco_norm, tasa_mn, tasa_me FROM bank_fact_kpis_mensual WHERE banco_norm='INVEX' AND fecha='2025-12-01'"
pr_files:
  - "plugins/bank-advisor-private/etl/core/transforms.py"
  - "docs/data/etl_runbook.md"
  - "docs/data/source_mapping.md"
test_status: "passed — diagnostic confirms 106/108 non-null, mean 0.16, no regression on peers"
---

# Summary

- **Objective:** Hacer que el ETL pipeline inyecte correctamente tasa_mn y tasa_me de INVEX desde CorporateLoan_CNBVDB.csv hacia bank_fact_kpis_mensual, y corregir documentación errónea.
- **Contexto:** Se descubrió que el CSV tiene 13,543 registros válidos de INVEX (Jun 2016 – Dic 2025) con tasas reales (MN ~13%, ME ~8%), pero el ETL produce 0/NULL en la DB.
- **Data patch aplicado:** 115 SQL UPDATEs directos a la DB como fix temporal (2026-03-03). Este fix se pierde si se re-ejecuta el ETL.
- **Constraints:** No romper las tasas de los otros 5 bancos dual-source que SÍ funcionan.

# Síntoma Reportado

- INVEX tasa_mn = 0 y tasa_me = 0 en charts de benchmark
- Los otros 5 bancos con tasa (BBVA, SANTANDER, BANORTE, HSBC, CITIBANAMEX) muestran valores correctos
- CorporateLoan_CNBVDB.csv tiene datos reales para INVEX: MN ~12-20%, ME ~5-10%

# Causa Raíz (Confirmada)

2 bugs encadenados:
1. `enrich_with_instituciones()` remapea INVEX 040059→040131 (código de Banco Ahorro Famsa)
2. `merge_corporate_rates()` joinea INVEX con datos de Ahorro Famsa (~39% MN) por colisión de código
3. `merge_corporate_rates_final()` coalesce prefiere NaN/Famsa sobre valores reales de INVEX

# Fix Aplicado

- `merge_corporate_rates()`: filtrar 040131 (Ahorro Famsa) + remap 040059→040131
- `etl_runbook.md`: corregida documentación incorrecta sobre tasa INVEX
- `source_mapping.md`: actualizado gotcha de código de institución INVEX

# Updates

- 2026-03-03 10:00 - Creada. Data patch de 115 UPDATEs aplicado como fix temporal.
- 2026-03-03 10:10 - Research completado. Causa raíz confirmada con diagnósticos.
- 2026-03-03 10:13 - Fix implementado y validado. 106/108 non-null, media 0.16 (correcto). Sin regresión en peers.
