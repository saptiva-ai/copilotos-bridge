---
id: "BUG-2026-03-02__invex-unit-normalization-etl"
title: "INVEX unit normalization mismatch in bank_fact_kpis_mensual"
status: "DOING"
phase: "Implement"
scope_in:
  - "Normalizar unidades AG (pesos → miles de pesos, % → decimal)"
  - "Fix fecha type mismatch en merge legacy↔AG"
  - "Remap INVEX ICAP/TDA institution code 040059 → 040131"
  - "Investigar tasa_mn/tasa_me = 0 para INVEX"
scope_out:
  - "Blank pages PDF (tarea separada)"
  - "LLM interpretation por gráfica (tarea separada)"
  - "Cambios en el frontend o analytics_service"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 2
validation_commands:
  - "cd plugins/bank-advisor-private && .venv/bin/python3.11 -m etl.etl_unified --upsert"
  - "psql: SELECT banco_norm, cartera_total, icap_total FROM bank_fact_kpis_mensual WHERE banco_norm IN ('INVEX','AFIRME','MONEX') AND fecha='2025-09-01'"
pr_files:
  - "plugins/bank-advisor-private/etl/core/loaders_unified.py"
  - "plugins/bank-advisor-private/etl/core/transforms.py"
  - "plugins/bank-advisor-private/etl/core/transforms_pipeline.py"
test_status: "pendiente — requiere re-run ETL + spot check BD"
---

# Summary

- **Objective:** Corregir las gráficas benchmark de INVEX que muestran valores "cerca de 0" comparados con peers (MONEX, AFIRME, etc.), haciendo que INVEX parezca insignificante cuando en realidad es un banco de tamaño similar.
- **Impacto:** Afecta a los 6 "legacy banks" (INVEX, BBVA, BANORTE, SANTANDER, HSBC, CITIBANAMEX) — no es solo INVEX.
- **Constraints:** No modificar datos de bancos que ya están correctos (AG-only banks).

# Síntoma Reportado

Las gráficas benchmark de INVEX mostraban valores "cerca de 0" comparados con los peers (MONEX, AFIRME, etc.), haciendo que INVEX pareciera insignificante cuando en realidad es un banco de tamaño similar.

Ejemplo Sept 2025 (antes del fix):
- INVEX cartera_total: 49,754,432 (miles de pesos)
- AFIRME cartera_total: 67,937,006,546 (pesos)
- Ratio: 1365× diferencia (debería ser ~1.4×)

# Updates

- 2026-03-02 14:00 - Creada. Causa raíz identificada: dual-pipeline unit mismatch + fecha type mismatch en merge.
- 2026-03-02 14:00 - 3 archivos modificados (no commiteados): loaders_unified.py, transforms.py, transforms_pipeline.py.
- 2026-03-02 14:00 - Investigación tasa_mn/tasa_me: INVEX tiene Average Rate = 0 en CorporateLoan CSV desde 2017. Última tasa válida: dic 2016.
- 2026-03-02 21:31 - Upsert BD completado: 5,238 rows (18 bancos). Validación IMOR derivado ✓ para INVEX, AFIRME, BBVA, BANORTE.
