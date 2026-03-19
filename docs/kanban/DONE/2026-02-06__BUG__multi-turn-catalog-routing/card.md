# BUG: Multi-turn Catalog Routing

**Created**: 2026-02-06
**Priority**: P1 (4 feedback reports in single day)
**Source**: Feedback triage 2026-02-06
**Notion**: https://www.notion.so/3015a0e4ae2181089e7db134f621aeb

## Problem

Follow-up catalog queries in multi-turn conversations bypass the catalog fast path.

**Pattern**: User asks "cual es la clave de INVEX?" (routed correctly via catalog fast path), then follows up with "y la de BBVA?" or "cual es la de Scotiabank?" — these elliptical follow-ups are NOT recognized as catalog queries by `QueryRouter` and fall through to the LLM path instead.

## Impact

- 4 negative feedback reports on 2026-02-06
- Users expect instant, accurate catalog lookups for follow-up queries
- LLM path may hallucinate bank codes instead of using the authoritative catalog

## Root Cause (hypothesis)

`QueryRouter.classify()` checks for catalog keywords ("clave", "codigo") but elliptical queries like "y la de X?" lack these keywords. The router needs to consider conversation context or detect the elliptical reference pattern.

## Related

- Catalog fast path: `apps/backend/src/services/query_router.py`
- Catalog handler: `apps/backend/src/services/bank_analytics_client.py:handle_catalog_query()`
- Previous fix: `bank-code-confusion` (DONE) and `bank-code-hallucination` (DONE)

## Feedback IDs

- FDBK-0075, FDBK-0076, FDBK-0077, FDBK-0078

## Feedback Vinculado

**4 reporte(s)** de usuarios en producción.

| # | Feedback ID | Usuario | Query | Feedback | Fecha |
|---|-------------|---------|-------|----------|-------|
| 1 | FDBK-0078 | `cb6c6879` | cual es la de monex ? | la clave de MONEX no es la correcta | 2026-02-06 |
| 2 | FDBK-0079 | `cb6c6879` | a que banco pertenece la siguiente clave: 0000040067 | menciona que la clave no es de ningún banco y antes me dijo que supuestamente... | 2026-02-06 |
| 3 | FDBK-0085 | `cb6c6879` | cual es la de ssntander ? | no me respondió correctamente, la clave es incorrecta | 2026-02-06 |
| 4 | FDBK-0086 | `cb6c6879` | cual es la de santander ? | clave incorrecta y me proporciona el menú guía fuera de contexto | 2026-02-06 |

<details>
<summary>Detalle completo de feedbacks</summary>

### FDBK-0078
- **User**: `cb6c6879-e598-439a-881d-c92c93b6cd2b`
- **Conversation**: `e6d0aed2-cfac-42dd-953f-ad71eae6c7b8`
- **Message**: `070ae1b5-96b6-4f15-8ac5-3a5baefe5ef8`
- **Rating**: 👎
- **Query**: "cual es la de monex ?"
- **Feedback**: "la clave de MONEX no es la correcta"
- **Fecha**: 2026-02-06T15:15:45.167Z

### FDBK-0079
- **User**: `cb6c6879-e598-439a-881d-c92c93b6cd2b`
- **Conversation**: `e6d0aed2-cfac-42dd-953f-ad71eae6c7b8`
- **Message**: `4dab0d21-5124-40f6-92f7-fbbc8d5cbce7`
- **Rating**: 👎
- **Query**: "a que banco pertenece la siguiente clave: 0000040067"
- **Feedback**: "menciona que la clave no es de ningún banco y antes me dijo que supuestamente era de MONEX"
- **Fecha**: 2026-02-06T15:16:37.487Z

### FDBK-0085
- **User**: `cb6c6879-e598-439a-881d-c92c93b6cd2b`
- **Conversation**: `e6d0aed2-cfac-42dd-953f-ad71eae6c7b8`
- **Message**: `7c86132f-1d09-418f-a370-1a7f609de63e`
- **Rating**: 👎
- **Query**: "cual es la de ssntander ?"
- **Feedback**: "no me respondió correctamente, la clave es incorrecta"
- **Fecha**: 2026-02-06T15:24:05.409Z

### FDBK-0086
- **User**: `cb6c6879-e598-439a-881d-c92c93b6cd2b`
- **Conversation**: `e6d0aed2-cfac-42dd-953f-ad71eae6c7b8`
- **Message**: `145ca1d9-7c16-49c6-b1a5-fbc647fff71c`
- **Rating**: 👎
- **Query**: "cual es la de santander ?"
- **Feedback**: "clave incorrecta y me proporciona el menú guía fuera de contexto"
- **Fecha**: 2026-02-06T15:24:45.896Z

</details>
