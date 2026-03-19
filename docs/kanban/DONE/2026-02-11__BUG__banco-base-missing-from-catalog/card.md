---
status: BACKLOG
---
# BUG: BANCO BASE no encontrado en catálogo CNBV

**Prioridad:** P2
**Fecha:** 2026-02-11
**Origen:** Triage 2026-02-11 (FDBK-0118, FDBK-0121, FDBK-0122)

---

## Resumen

Cuando el usuario incluye "BANCO BASE" en una lista de bancos, el sistema responde "No tenemos datos de BANCO BASE en nuestra base de datos CNBV". Sin embargo, Banco Base es una institución real (Banco Base, S.A., Institución de Banca Múltiple). Requiere investigación para determinar su clave CNBV y agregarlo al catálogo.

## Evidencia (prod 2026-02-11)

**Conversación**: `85338a1e`

| Feedback | Query | Respuesta del sistema |
|----------|-------|-----------------------|
| FDBK-0118 | "cartera total de INVEX vs MONEX, BANCREA, SABADELL, BANCA MIFEL, MULTIVA, AFIRME, BANSÍ, VE POR MÁS, BANCO BASE" | "No tenemos datos de BANCO BASE... Sugerencia: ¿Quisiste decir BANCO AZTECA?" |
| FDBK-0121 | Misma lista de bancos, cartera enero 2024 vs 2025 | Mismo mensaje de no encontrado |
| FDBK-0122 | Gráfica INVEX vs promedio del grupo (incluye BANCO BASE) | Mismo mensaje de no encontrado |

### Síntoma

`BANCO BASE` no tiene entrada en `bank_dim_institucion`. El lookup MCP tool (`lookup_bank_code`, `lookup_institution_code`) no lo encuentra. El sistema sugiere "BANCO AZTECA" como alternativa, lo cual es incorrecto.

## Investigación requerida

1. **Verificar clave CNBV**: Buscar "Banco Base" en el catálogo oficial de la CNBV para obtener su clave de 10 dígitos (formato `00000400XX`)
2. **Verificar datos en Neon**: Confirmar si la base de datos ya tiene registros de Banco Base bajo otro nombre o clave
3. **Alias**: Verificar si "BANCO BASE" o "BASE" necesitan alias en `banking_keywords.py` → `normalize_acronyms()`
4. **Insertar en catálogo**: Agregar la entrada a `bank_dim_institucion` con nombre_corto y clave_cnbv

## Criterios de Aceptación

- [ ] Clave CNBV de Banco Base identificada
- [ ] Entrada agregada a `bank_dim_institucion` (o confirmación de que ya existe bajo otro nombre)
- [ ] Query "cartera de Banco Base" retorna datos reales
- [ ] Test de regresión: lookup "BANCO BASE" → código correcto
- [ ] Validar en prod

---

## Referencias

- Triage: `docs/reports/feedback_triage/2026-02-11.md`
- Ticket similar: `2026-02-09__BUG__ixe-040032-missing-from-bank-dimension-lookup-tabl`
- Catálogo CNBV: tabla `bank_dim_institucion` en Neon
