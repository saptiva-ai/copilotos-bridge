---
status: DONE
---
# BUG: Datos de quebrantos obsoletos (2020)

## Status: DOING

## Descripcion

El sistema reporta que TODOS los bancos tienen 0 MDP en quebrantos comerciales, usando datos de diciembre 2020. El usuario afirma que si existen datos de quebrantos. Los datos estan desactualizados por 5+ anos o la metrica no esta mapeada correctamente.

## Feedback Relacionado

| ID | Fecha | Comentario |
|----|-------|------------|
| FDBK-0008 | 2026-01-27 | "si hay datos de quebrantos" - User asked "que bancos tienen quebrantos?" |

## Root Cause

- La metrica `QUEBRANTOS_COMERCIALES` solo tiene datos hasta 2020-12-01
- Todos los valores son 0 MDP para todos los bancos
- Posibles causas:
  1. Los datos no se han actualizado en la DB desde 2020
  2. La metrica esta mal mapeada en el ETL
  3. Los quebrantos se reportan bajo otro nombre de metrica despues de 2020

## Investigacion Requerida

1. Verificar si existen datos de quebrantos mas recientes en la DB raw
2. Revisar si el ETL/pipeline incluye quebrantos en sus transformaciones
3. Confirmar con CNBV si la metrica cambio de nombre post-2020

## Prioridad

Baja - 1 reporte de usuario, datos historicos

## Feedback Vinculado

**1 reporte(s)** de usuarios en producción.

| # | Feedback ID | Usuario | Query | Feedback | Fecha |
|---|-------------|---------|-------|----------|-------|
| 1 | FDBK-0008 | `7f5aa3b9` | que bancos tienen quebrantos? | si hay datos de quebrantos | 2026-01-27 |

<details>
<summary>Detalle completo de feedbacks</summary>

### FDBK-0008
- **User**: `7f5aa3b9-8f98-459e-abc2-0148b23486f9`
- **Conversation**: `07aeed9b-73ac-4691-be1c-d6dc04740824`
- **Message**: `cb4bf2d0-7f62-47af-ad2e-78c706f5cd1a`
- **Rating**: 👎
- **Query**: "que bancos tienen quebrantos?"
- **Feedback**: "si hay datos de quebrantos"
- **Fecha**: 2026-01-27T18:33:33.173Z

</details>
