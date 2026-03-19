# TASK: PERF-REPORT: Cache Redis para generación de reportes benchmark

**Prioridad:** P2
**Fecha:** 2026-02-27
**Status:** DONE

---

## Resumen

# Cache Redis para Reportes Benchmark

## Contexto
La generación de reportes benchmark (PPTX + PDF) tarda ~75s para 24 gráficas.
La data bancaria cambia **una vez al mes** (ETL mensual), por lo que el 99% de las
generaciones repiten exactamente los mismos resultados.

## Mediciones Actuales (baseline)
- **Total E2E**: ~75s (24 charts, formato "both")
- NL2SQL + DB Query: ~31s (42%) — ~1.3s/chart
- Chrome/Kaleido Render: ~34s (45%) — ~1.4s/chart
- PPTX Assembly: ~1s (1%)
- PDF Assembly: ~2s (3%)
- PPTX: 3.1 MB | PDF: 2.8 MB | Avg PNG: 172 KB

## Estrategia Propuesta (2 capas de cache)

### Capa 1: Cache de archivos finales (PPTX/PDF)
- **Key**: `benchmark:file:{hash(sorted_preset_ids)}:{format}:{etl_run_id}`
- Si alguien ya generó la misma combinación de presets+formato, servir directo de Redis
- TTL: 30 días o invalidar en nuevo ETL
- **Target**: segunda generación en ~1s

### Capa 2: Cache de PNGs individuales
- **Key**: `benchmark:png:{preset_id}:{etl_run_id}`
- Si el archivo final no está en cache pero los PNGs sí, solo armar PPTX/PDF (~3-5s)
- Cubre el caso de personalización (subconjunto de presets diferente)
- **Target**: generación personalizada en ~5s

### Invalidación
- Discriminador: `etl_run_id` del último ETL run exitoso
- Al correr ETL nuevo, las keys antiguas expiran naturalmente (TTL) o se invalidan activamente
- Endpoint `/health` ya expone `etl.last_run_id`

## Mejoras Opcionales (fase 2)
- Paralelizar queries con `asyncio.gather` (4 workers → ~30s primera vez)
- Bajar scale de 2 a 1 para renders más rápidos
- Bypass NL2SQL con SQL directo para presets fijos

## Archivos Relevantes
- `plugins/bank-advisor-private/src/bankadvisor/services/report_generator.py`
- `plugins/bank-advisor-private/src/bankadvisor/services/chart_exporter.py`
- `plugins/bank-advisor-private/src/bankadvisor/tools/report_tools.py`
- `apps/backend/src/routers/reports_benchmark.py`

## Criterios de Aceptación
- [ ] Primera generación: ~75s (sin cambio)
- [ ] Segunda generación (mismos presets): <2s
- [ ] Generación con presets custom (PNGs cacheados): <5s
- [ ] Cache se invalida correctamente al correr nuevo ETL
- [ ] Tests unitarios para lógica de cache

---

## Criterios de Aceptación

- [ ] TODO

---

## Referencias

- N/A
