# TASK: Test Suite Expansion - Robustez y Seguridad

**Status**: BACKLOG
**Priority**: HIGH
**Created**: 2026-01-08
**Type**: Quality Assurance / Security

## Objetivo

Ampliar la cobertura de tests del sistema para detectar vulnerabilidades de seguridad, validar la robustez del parser NL2SQL, y asegurar la consistencia de datos en conversaciones multi-turno.

## Justificación

El análisis del directorio `tests/` reveló gaps críticos:

| Área | Estado Anterior | Estado Actual |
|------|-----------------|---------------|
| Seguridad avanzada | 6 casos básicos | 65 vectores de ataque |
| Autenticación | Sin cobertura | 20 casos de manipulación JWT |
| Conversaciones multi-turn | 2 turnos máx | 10 escenarios de 5-7 turnos |
| Unit tests parser | 2 funciones | 33 tests comprehensivos |
| Unicode/emoji | Sin cobertura | 23 casos de stress |
| Validación de datos | Sin cobertura | 10 validadores |

## Archivos Creados

### 1. Security Tests Avanzados
**Archivo**: `tests/e2e/security/test_security_advanced.py`
**Casos**: 45

Cubre vectores de ataque:
- Prompt injection avanzado (8 casos)
- SSRF - Server-Side Request Forgery (5 casos)
- NoSQL injection (4 casos)
- Log injection (3 casos)
- ReDoS - Regex Denial of Service (3 casos)
- Unicode exploits (8 casos)
- Header injection (3 casos)
- Path traversal (4 casos)
- SQL injection (5 casos)
- XSS (5 casos)

```bash
# Ejecutar
python tests/e2e/security/test_security_advanced.py
```

### 2. Auth Token Manipulation
**Archivo**: `tests/e2e/security/test_auth_token_manipulation.py`
**Casos**: 20

Valida rechazo de:
- Tokens vacíos/faltantes (4 casos)
- Tokens malformados (4 casos)
- Firmas manipuladas (3 casos)
- Payloads alterados (3 casos)
- Ataques de algoritmo (2 casos)
- Valores especiales (4 casos)

```bash
# Ejecutar
python tests/e2e/security/test_auth_token_manipulation.py
```

### 3. Multi-Turn Context Tests
**Archivo**: `tests/e2e/conversation/test_multi_turn_context.py`
**Escenarios**: 10 (5-7 turnos cada uno)

Escenarios cubiertos:
- `CONV-001`: Cadena larga con acumulación de contexto
- `CONV-002`: Cambio de tema y retorno
- `CONV-003`: Corrección de entidades
- `CONV-004`: Referencias anafóricas
- `CONV-005`: Contexto conflictivo
- `CONV-006`: Manejo de negaciones
- `CONV-007`: Multi-métrica
- `CONV-008`: Evolución temporal
- `CONV-009`: Flujo de clarificación
- `CONV-010`: Stress test 7 turnos

```bash
# Ejecutar
python tests/e2e/conversation/test_multi_turn_context.py
```

### 4. Data Consistency Validation
**Archivo**: `tests/e2e/metrics/test_data_consistency.py`
**Validadores**: 6

Validaciones:
- Rangos de valores por métrica
- Orden temporal de datos
- Detección de all-null traces
- Longitud consistente X/Y
- Nombres de bancos válidos
- Sin fechas duplicadas

```bash
# Ejecutar
python tests/e2e/metrics/test_data_consistency.py
```

### 5. Unit Tests - QuerySpecParser
**Archivo**: `tests/unit/clarification/test_query_spec_parser.py`
**Tests**: 33

Clases de test:
- `TestBankExtraction`: 15 tests de extracción de bancos
- `TestMetricExtraction`: 12 tests de extracción de métricas
- `TestTemporalParsing`: 10 tests de parsing temporal
- `TestConfidenceScoring`: 4 tests de scoring
- `TestTypoHandling`: 4 tests de tolerancia a typos
- `TestComparisonTypes`: 6 tests de tipos de comparación
- `TestClarificationService`: 4 tests de servicio
- `TestEdgeCases`: 8 tests de edge cases

```bash
# Ejecutar (requiere pytest)
pytest tests/unit/clarification/test_query_spec_parser.py -v
```

### 6. Unicode/Emoji Stress Tests
**Archivo**: `tests/e2e/clarification/test_clarifications_stress.py` (ampliado)
**Casos nuevos**: 23

Categorías añadidas:
- Emoji (6 casos): Chart, bank, money emojis
- Advanced Unicode (8 casos): RTL, BOM, homoglyphs, zero-width
- Mathematical (5 casos): Operadores, delta, summation
- Currency (4 casos): Símbolos de moneda

```bash
# Ejecutar
python tests/e2e/clarification/test_clarifications_stress.py --category Emoji
python tests/e2e/clarification/test_clarifications_stress.py --category AdvancedUnicode
```

---

## Implementación

### Fase 1: Configuración (Inmediato)
- [ ] Verificar dependencias (`pytest`, `httpx`, `requests`)
- [ ] Confirmar backend corriendo en `localhost:8000`
- [ ] Confirmar bank-advisor en `localhost:8002`

### Fase 2: Ejecución Inicial
- [ ] Ejecutar suite de seguridad completa
- [ ] Documentar fallos como baseline
- [ ] Priorizar vulnerabilidades críticas

### Fase 3: Integración CI/CD
- [ ] Agregar tests de seguridad a pipeline
- [ ] Configurar thresholds de pass rate
- [ ] Alertas para regresiones

### Fase 4: Mejoras Continuas
- [ ] Agregar nuevos vectores de ataque según OWASP
- [ ] Expandir escenarios de conversación
- [ ] Añadir más validaciones de datos

---

## Métricas de Éxito

| Métrica | Target |
|---------|--------|
| Pass rate seguridad | > 95% |
| Pass rate auth | 100% |
| Pass rate context | > 80% |
| Pass rate data consistency | > 90% |
| Cobertura unit tests | > 80% |

---

## Comandos de Ejecución

```bash
# Suite completa de seguridad
python tests/e2e/security/test_security_advanced.py && \
python tests/e2e/security/test_auth_token_manipulation.py

# Suite de conversación
python tests/e2e/conversation/test_multi_turn_context.py

# Suite de métricas
python tests/e2e/metrics/test_data_consistency.py

# Stress tests con nuevos casos
python tests/e2e/clarification/test_clarifications_stress.py

# Unit tests (requiere pytest)
pytest tests/unit/clarification/ -v

# TODO: Ejecutar suite completa
make test-all  # (pendiente de crear target en Makefile)
```

---

## Dependencias

```txt
pytest>=7.0.0
pytest-asyncio>=0.21.0
httpx>=0.24.0
requests>=2.28.0
```

---

## Archivos Relacionados

- Tests originales: `tests/e2e/security/test_security_prompt_injection.py`
- Happy path: `tests/e2e/test_happy_path_suite.py`
- Fixtures: `tests/fixtures/`
- Parser source: `plugins/bank-advisor-private/src/bankadvisor/services/query_spec_parser.py`

---

## Notas

- Los tests de seguridad deben ejecutarse en ambiente controlado
- Los unit tests requieren acceso al código del plugin `bank-advisor-private`
- Algunos tests pueden fallar inicialmente - esto es esperado y ayuda a identificar áreas de mejora
