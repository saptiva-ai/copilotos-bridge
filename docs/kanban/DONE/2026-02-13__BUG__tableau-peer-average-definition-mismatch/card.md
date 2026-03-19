---
id: "BUG-2026-02-13__tableau-peer-average-definition-mismatch"
title: "Tableau vs peer-average mismatch (include/exclude INVEX)"
status: "BACKLOG"
phase: "Research"
scope_in:
  - "Alinear la definicion de promedio para grafica target vs promedio"
  - "Documentar formula actual vs formula de Tableau con evidencia numerica"
  - "Definir estrategia de compatibilidad (flag o cambio por defecto)"
scope_out:
  - "Cambios de ETL o backfill historico"
  - "Cambios de metrica fuera de cartera_total"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 1
validation_commands:
  - "python3.11 -m pytest -q plugins/bank-advisor-private/tests/unit/application/test_use_cases.py -k PeerAverageUseCase"
  - "python3.11 -m pytest -q plugins/bank-advisor-private/src/bankadvisor/tests/unit/test_query_spec_parser_financial_metrics.py -k peer_average"
  - "cd apps/backend && PYTEST_ADDOPTS='--no-cov' python3.11 -m pytest -q tests/unit/test_delta_context_injection.py -k peer_average"
pr_files: []
test_status: "research-only"
---

# Summary
- Objective: cerrar la discrepancia entre la grafica actual y la referencia de Tableau para "INVEX vs promedio".
- Constraint: mantener trazabilidad numerica por mes y explicitar la poblacion del promedio.

# Problema
Usuarios de Bajaware reportan que, para prompts tipo:

```
Crea una grafica donde se compare la cartera total de INVEX contra la cartera promedio de los bancos:
MONEX, BANCREA, SABADELL, BANCA MIFEL, MULTIVA, AFIRME, BANSI, VE POR MAS Y BANCO BASE.
De enero 2021 hasta el dato mas reciente que tengas.
```

la linea de INVEX coincide, pero la linea de promedio no coincide con la imagen de Tableau (Image #1).

# Causa raiz
La discrepancia no viene de calidad de datos; viene de la definicion del promedio:

- Implementacion actual: promedio de peers **sin INVEX**.
  - `plugins/bank-advisor-private/src/bankadvisor/application/use_cases/peer_average.py:37`
  - `plugins/bank-advisor-private/src/bankadvisor/repositories/kpi_repository.py:234`
- Referencia Tableau/Image #1: promedio del grupo **incluyendo INVEX**.

# Evidencia numerica (oct-2021)
Comparacion exacta para `fecha = 2021-10-01`, metrica `cartera_total`:

| Valor | MDP | Redondeado |
|---|---:|---:|
| INVEX | 20,552.54 | 20,553 |
| Promedio 9 peers (sin INVEX) | 37,636.29 | 37,636 |
| Promedio grupo (9 peers + INVEX) | 35,927.92 | 35,928 |

En la imagen, los labels visibles son aprox:
- rojo: `20,553` (INVEX)
- negro: `35,928` (promedio)

`35,928` coincide con el promedio **incluyendo** INVEX, no con peers-only.

# Verificacion de origen de datos (descartes)
Validaciones en BD para el universo de 10 bancos y `cartera_total`:

- Cobertura completa: `2021-01-01` a `2025-11-01` (59 meses).
- `n_peers_usados = 9` en todos los meses.
- Sin duplicados por `(banco, fecha)`.
- Sin desvio MONEX/BMONEX para este corte.

Conclusión: el gap es de formula, no de completitud de datos.

# Solucion propuesta
Definir explicitamente la poblacion del benchmark:

1. Opcion A (alinear Tableau): incluir target en `AVG`.
2. Opcion B (mantener actual): peers-only, pero etiquetar como "Promedio pares (sin INVEX)".
3. Opcion C (recomendada): soportar ambos modos con flag:
   - `average_population = peers_only | peers_plus_target`
   - default configurable por tenant (Bajaware en modo Tableau).

# Criterios de aceptacion
- [ ] La serie de octubre 2021 coincide con la definicion elegida (documentada).
- [ ] El payload de respuesta incluye metadata explicita de poblacion del promedio.
- [ ] E2E para prompt de cartera total valida labels esperados segun modo.
- [ ] Documentacion para negocio aclara formula aplicada en cada modo.

# Updates
- 2026-02-13 13:25 - Ticket creado con evidencia SQL y comparacion numerica contra Image #1.
