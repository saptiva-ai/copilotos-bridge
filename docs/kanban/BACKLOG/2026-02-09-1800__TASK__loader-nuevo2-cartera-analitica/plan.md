# Plan

## Objetivo
- Ingestar `nuevo2.csv` en una nueva tabla `bank_src_*` con un esquema documentado y estable.

## Alcance
### Dentro
- Definir nombres de columna para el archivo sin encabezados
- Loader + transformación + migración

### Fuera
- Escrituras en producción (hasta que se completen las validaciones de la tarea padre)
- Visualización en frontend

## Fases
### Fase 1 (Investigación de esquema)
- [ ] Confirmar definiciones de columna (spec de Bajaware o inferidas + validadas)
- [ ] Identificar claves: código de institución, fecha, geografía, banderas

### Fase 2 (Implementar loader)
- [ ] Crear loader en `plugins/bank-advisor-private/etl/core/loaders/`
- [ ] Agregar migración para tabla destino `bank_src_*`
- [ ] Agregar pruebas unitarias para parseo + tipado + sanidad de conteo de filas

### Fase 3 (Integrar + Validar)
- [ ] Agregar a specs de promoción (si es necesario)
- [ ] Dry-run del ETL contra `data/raw/current/`

## Comandos de validación
- `cd plugins/bank-advisor-private && .venv/bin/pytest -q -k nuevo2`

## Criterios de éxito
- El loader parsea el archivo de forma determinista (mismo esquema en cada ejecución)
- Esquema de tabla destino revisado e indexado para patrones de consulta
- Pruebas unitarias cubren casos borde de delimitador/entrecomillado/parseo de fechas
