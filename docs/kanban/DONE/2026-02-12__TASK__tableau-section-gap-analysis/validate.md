# Validate: Fase 0 + Fase 1

**Fecha:** 2026-02-12
**Status:** PASS

---

## Fase 0: cartera_total en visualizations.yaml

### Cambio
- Archivo: `plugins/bank-advisor-private/config/visualizations.yaml`
- Agregada entry #10 `cartera_total` con `dual_mode`, `line`, `Millones MXN`

### Verificacion
- [x] Entry presente en YAML
- [x] Modo `dual_mode` (misma logica que ICOR/ICAP)
- [ ] Smoke test: query "cartera total de INVEX" (pendiente restart backend)

---

## Fase 1: Backfill 13 columnas desde CNBV XLSX

### Script
- **Extendido**: `scripts/data/backfill_cartera_total.py`
- **Nuevo (temporal)**: `scripts/data/eda_xlsx_cols_35_39.py`

### Ejecucion
- Comando: `DATABASE_URL=... uv run scripts/data/backfill_cartera_total.py`
- Resultado: **1,784 filas** actualizadas, **1,524 ICOR** computados
- 17 bancos: INVEX, AFIRME, BANREGIO, MONEX, MIFEL, BANCO BASE, BANCREA, BANSI, MULTIVA, SABADELL, VE POR MAS, INTERCAM BANCO, INMOBILIARIO MEXICANO, JP MORGAN, COVALTO, UALA, AUTOFIN
- Rango temporal: Ene 2017 — Nov 2025 (107 meses por banco)

### Columnas pobladas

| Columna | Tipo | Ejemplo INVEX 202401 | Status |
|---------|------|---------------------|--------|
| cartera_total | currency | 36,410,974,308 | OK (ya existia, revalidado) |
| cartera_consumo_total | currency | 21,478,009,970 | OK (ya existia, revalidado) |
| cartera_vivienda_total | currency | 62,355,725 | OK (ya existia, revalidado) |
| empresarial_total | currency | 13,415,742,253 | NEW |
| entidades_financieras_total | currency | 1,454,866,360 | NEW |
| entidades_gubernamentales_total | currency | 0 | NEW (INVEX no tiene) |
| cartera_comercial_sin_gob | currency | 14,870,608,613 | NEW |
| reservas_etapa_todas | currency | -1,683,594,868 | NEW (negativo, convencion contable) |
| ct_etapa_1 | ratio | 0.9628 | NEW |
| ct_etapa_2 | ratio | 0.0158 | NEW |
| ct_etapa_3 | ratio | 0.0213 | NEW |
| pe_total | ratio | 0.0462 | NEW |
| icor | ratio | 2.1701 | COMPUTED (ABS(reservas)/cartera_vencida) |

### Cross-checks

1. **Integridad de segmentos**: `emp + efin = cc_sin_gob` PASS
2. **Ratios suman ~1**: `e1 + e2 + e3 = 0.9999` PASS (VR = 0.0001)
3. **PE formula**: `-reservas / ct = 0.0462` PASS
4. **ICOR formula**: `|reservas| / cv = 2.1701` PASS
5. **CT del XLSX vs col 26**: 36,410.974308 MDP == col 26 (Cartera Total Etapa todas) PASS

### Cobertura post-backfill (INVEX)

| Columna | Pre | Post | Delta |
|---------|-----|------|-------|
| empresarial_total | 0% | 35.7% | +107 filas |
| reservas_etapa_todas | 0% | 35.7% | +107 filas |
| ct_etapa_1 | 15% | 35.7% | +61 filas |
| pe_total | 15% | 35.7% | +61 filas |
| icor | 35% | 35.3% | +0 (ya tenia, revalidado) |

### Notas tecnicas

1. **SCALE_FACTOR**: XLSX en MDP, BD en pesos. Multiplicar por 1,000,000 para currency. Ratios NO se escalan.
2. **Reservas negativas**: XLSX almacena reservas como negativos. PE usa `(-reservas/ct)` para obtener ratio positivo. ICOR usa `ABS(reservas)/cv`.
3. **psycopg3 vs psycopg2**: `IN %s` con tupla no funciona en psycopg3. Usar `= ANY(%s)` con lista.
4. **Idempotencia**: WHERE clause usa `OR columna IS NULL` — re-ejecutar no sobreescribe datos existentes.

---

## Pendiente

- [ ] Restart backend: `docker compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml --env-file envs/.env restart backend`
- [ ] Smoke test chat: "cartera total de INVEX" → debe generar grafica dual_mode
- [ ] Eliminar script temporal `scripts/data/eda_xlsx_cols_35_39.py` (o mantener para referencia)
