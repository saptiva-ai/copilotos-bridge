# Research

## Questions
- El promedio del benchmark debe incluir o excluir INVEX?
- El gap visual viene de formula o de origen/calidad de datos?
- La imagen de referencia corresponde a `cartera_total` o a otra metrica?

## Findings

### F1) Parser/intent correctos para prompt de cartera total
- `metric = CARTERA_TOTAL`
- `peer_average_mode = True`
- `target_bank = INVEX`
- peers detectados: `MONEX, BANCREA, SABADELL, MIFEL, MULTIVA, AFIRME, BANSI, VE POR MAS, BANCO BASE`

### F2) Formula actual en codigo
- Se excluye target de peers en request DTO:
  - `plugins/bank-advisor-private/src/bankadvisor/application/use_cases/peer_average.py:37`
- El SQL calcula:
  - `target_value` para INVEX
  - `peer_average = AVG(CASE WHEN banco IN peers THEN metric END)` (sin INVEX)
  - `plugins/bank-advisor-private/src/bankadvisor/repositories/kpi_repository.py:234`

### F3) Calidad/cobertura de datos (descartes)
- Universo de 10 bancos con `cartera_total`:
  - cobertura completa `2021-01-01` a `2025-11-01`
  - 59 filas por banco
  - sin duplicados `(banco, fecha)`
  - `n_peers_usados = 9` todos los meses
- No se observo desviacion por alias MONEX/BMONEX en este corte.

### F4) Match numerico con Image #1
Caso octubre 2021:

- INVEX: `20,552.54` -> `20,553` (label rojo)
- AVG peers-only (sin INVEX): `37,636.29` -> `37,636`
- AVG incluyendo INVEX: `35,927.92` -> `35,928` (label negro)

El valor negro observado en la imagen coincide con promedio incluyendo INVEX.

### F5) Eje X y labels
- Datos reales inician en enero 2021.
- Que el primer tick visible sea agosto 2021 es consistente con auto-ticks/auto-labeling del chart.
- No explica el gap de promedio.

## References
- `plugins/bank-advisor-private/src/bankadvisor/application/use_cases/peer_average.py`
- `plugins/bank-advisor-private/src/bankadvisor/repositories/kpi_repository.py`
- `plugins/bank-advisor-private/src/main.py`
- `docs/kanban/BACKLOG/2026-02-13__BUG__tableau-peer-average-definition-mismatch/card.md`
