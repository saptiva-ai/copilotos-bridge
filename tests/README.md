# Test Suite - OctaviOS Chat Bank Advisor

## Resumen Ejecutivo

Este directorio contiene **~350+ casos de prueba** organizados en tres categorías principales:
- **E2E (End-to-End)**: Tests de integración completa contra el backend
- **Unit**: Tests unitarios para servicios específicos
- **Integration**: Tests de infraestructura (Python scripts)

## Estructura de Directorios

```
tests/
├── e2e/                          # Tests End-to-End (~300 casos)
│   ├── regression/               # Regresión y Happy Path
│   ├── conversation/             # Contexto multi-turno
│   ├── clarification/            # Desambiguación NLU
│   ├── security/                 # Seguridad y pentesting
│   ├── charts/                   # Persistencia de gráficos
│   └── run_all.py               # Runner maestro
├── unit/                         # Tests Unitarios
│   ├── clarification/           # Parser y clarificación
│   └── services/                # Servicios backend
├── integration/                  # Python scripts de infraestructura
├── fixtures/                     # Datos de prueba
│   └── happy_path/              # Casos del Happy Path Suite
├── runner/                       # Runner paralelo por suites
└── utils/                        # Helpers compartidos
    └── helpers.py               # Auth, SSE parsing, chat
```

---

## Inventario de Tests por Archivo

### E2E - Regression (`e2e/regression/`)

| Archivo | Casos | Propósito | Fecha Creación | Commit |
|---------|-------|-----------|----------------|--------|
| `test_happy_path_suite.py` | **47** | Suite principal: RAG, NL2SQL, Comparisons, BA-001/BA-002 | 2025-01 | `f86c6977` |
| `test_bug_regression_suite.py` | **20** | Validación de bugs específicos (BUG-01 a BUG-11, BA-001/BA-002) | 2025-01 | `e1b4d454` |
| `test_ranking_detection.py` | **45** | BUG-014: Rankings sin falsos negativos | 2025-01 | `9c1f86d6` |
| `test_prd_epic_coverage_frontend.py` | ? | Cobertura de épicas PRD | 2024-12 | `dc3eec19` |

### E2E - Conversation (`e2e/conversation/`)

| Archivo | Casos | Propósito | Fecha Creación |
|---------|-------|-----------|----------------|
| `test_multi_turn_context.py` | **16 escenarios** (~80 turns) | Contexto multi-turno, anáfora, corrección | 2025-01 |
| `test_cartera_vivienda_suite.py` | **25 escenarios** | Bugs hipotecario/vivienda, sticky context | 2026-01 |
| `test_multi_bank_comparison.py` | ? | Comparaciones entre múltiples bancos | 2024-12 |

### E2E - Clarification (`e2e/clarification/`)

| Archivo | Casos | Propósito | Fecha Creación |
|---------|-------|-----------|----------------|
| `test_clarification_scenarios.py` | **16** | Queries ambiguas y edge cases | 2025-01 |
| `test_clarification_edge_cases.py` | **76** | Edge cases: typos, unicode, emojis, inyección | 2024-12 |

### E2E - Security (`e2e/security/`)

| Archivo | Casos | Propósito | Fecha Creación |
|---------|-------|-----------|----------------|
| `test_auth_token_manipulation.py` | **20** | Manipulación JWT: signatures, payloads, algoritmos | 2025-01 |
| `test_security_advanced.py` | **50+** | Prompt injection, SSRF, NoSQL, XSS, path traversal | 2025-01 |

### Unit Tests (`unit/`)

| Archivo | Casos | Propósito |
|---------|-------|-----------|
| `clarification/test_clarifications.py` | **4** | HU3: thresholds y payload structure |
| `clarification/test_query_spec_parser.py` | ? | Parser de query specs |
| `clarification/test_bank_context.py` | ? | Contexto de banco multi-tenant |
| `services/test_text_sanitizer.py` | **21** | BUG-06 (SQL stripping), BUG-11 (markdown) |

---

## Análisis Crítico

### Redundancias Resueltas (2026-01-15)

| Problema | Estado | Acción Tomada |
|----------|--------|---------------|
| **Estructura anidada** `tests/e2e/tests/e2e/` | ✅ RESUELTO | Carpeta eliminada, `test_metrics_suite.py` movido a `e2e/metrics/` |
| **Código duplicado `get_auth_token`** | ✅ RESUELTO | 6 archivos migrados a usar `utils/helpers.py` |
| **Nomenclatura inconsistente** | ✅ RESUELTO | 4 archivos renombrados (ver tabla abajo) |
| **Casos BA-001/BA-002 duplicados** | ⚠️ PENDIENTE | Mantener en Happy Path, considerar eliminar de bug_regression |

### Nomenclatura - Cambios Aplicados (2026-01-15)

| Anterior | Nuevo | Razón |
|----------|-------|-------|
| `test_known_bugs.py` | `test_bug_regression_suite.py` | Más descriptivo del propósito |
| `test_clarifications_stress.py` | `test_clarification_edge_cases.py` | "Stress" implica carga, no edge cases |
| `test_hipotecario_bugs.py` | `test_cartera_vivienda_suite.py` | Nombre técnico consistente |
| `test_ranking_false_negative.py` | `test_ranking_detection.py` | Más genérico, el bug ID va en docstring |

### Cobertura Actual por Categoría

```
 Regresión/Smoke    ████████████████████ 112 casos (32%)
 Conversación       ████████████████      57 casos (16%)
 Clarificación      ████████████████████  92 casos (26%)
 Seguridad          ██████████████        70 casos (20%)
 Unitarios          ██████                25 casos (7%)
```

### Gaps de Cobertura Identificados

1. **Tests de rendimiento/carga** - No hay tests de throughput para el chat
2. **Tests de concurrencia** - Múltiples usuarios simultáneos no probados
3. **Tests de timeout/resilencia** - Solo parcialmente cubiertos en integration/
4. **Tests de RAG con documentos grandes** - No hay validación de límites
5. **Tests de rate limiting** - No verificados en security/

---

## Puntos de Mejora Técnica

### 1. Centralización de Helpers (Alta Prioridad)

```python
# Actual: Cada test tiene su propia implementación
def parse_sse_response(response):  # Duplicado en 8+ archivos
    ...

# Propuesto: Usar utils/helpers.py consistentemente
from utils.helpers import parse_sse_response, get_auth_token, send_chat_message
```

### 2. Fixtures Compartidos (Media Prioridad)

```python
# Crear tests/conftest.py con fixtures pytest
@pytest.fixture
def auth_token():
    return get_auth_token()

@pytest.fixture
def chat_session(auth_token):
    return ChatSession(token=auth_token)
```

### 3. Parametrización de Tests (Media Prioridad)

```python
# Actual: Clases de datos manuales
TEST_CASES = [TestCase(...), TestCase(...), ...]

# Propuesto: pytest.mark.parametrize
@pytest.mark.parametrize("query,expected_type,keywords", [
    ("IMOR de INVEX", "chart", ["IMOR", "INVEX"]),
    ("¿Qué es ICAP?", "rag", ["ICAP", "Capitalización"]),
])
def test_query_routing(query, expected_type, keywords):
    ...
```

### 4. Timeouts y Retries (Baja Prioridad)

```python
# Propuesto: Decorador de retry para tests flaky
@retry(max_attempts=3, delay=1.0)
def test_chat_response():
    ...
```

---

## Cómo Ejecutar

### Runner paralelo por suites
```bash
python -m tests.runner
python -m tests.runner --suite e2e_regression --suite integration
python -m tests.runner --list
```

### Suite Completa E2E
```bash
python tests/e2e/run_all.py
```

### Test Específico
```bash
# Happy Path
python tests/e2e/regression/test_happy_path_suite.py

# Con filtros
python tests/e2e/regression/test_happy_path_suite.py --category NL2SQL --max 10

# Verbose
python tests/e2e/regression/test_happy_path_suite.py --verbose
```

### Tests Unitarios
```bash
pytest tests/unit/ -v
```

### Suite Integration
```bash
python tests/integration/run_all.py
```

### Variables de Entorno
```bash
export TEST_BACKEND_URL=http://localhost:8000
export TEST_AUTH_USER=demo
export TEST_AUTH_PASS=Demo1234
export TEST_MODEL="Saptiva Turbo"
```

---

## Acciones Recomendadas (Roadmap)

### Completado (2026-01-15)
- [x] **Eliminar** `tests/e2e/tests/e2e/` - estructura redundante
- [x] **Migrar** todos los tests a usar `utils/helpers.py`
- [x] **Renombrar** archivos según propuesta de nomenclatura

### Corto Plazo (Próximo Sprint)
- [ ] Crear `tests/conftest.py` con fixtures compartidos
- [ ] **Unificar** tests BA-001/BA-002 en un solo lugar (eliminar duplicados)
- [ ] Agregar tests de rate limiting en security/

### Medio Plazo
- [ ] Implementar tests de carga básicos
- [ ] Agregar cobertura de concurrencia
- [ ] Documentar cada suite con su propio README

---

## Historial de Cambios

| Fecha | Commit | Descripción |
|-------|--------|-------------|
| 2026-01-15 | - | **BA-001**: Fix detección abstención ("no encuentro" presente) |
| 2026-01-15 | - | **BA-002**: Fix INVEX default bias (100% tests passing) |
| 2026-01-15 | - | **BUG-014**: Ranking detection 52.9% → 82.4% (+30%) |
| 2026-01-14 | `6967eb0e` | 100% Happy Path Suite (47/47) |
| 2026-01-14 | `718bccc6` | Consolidación y optimización E2E |
| 2026-01-14 | `0dbcb3c4` | Fix assertions de regresión |
| 2025-01-12 | `da1cf107` | Tests hipotecario bugs |
| 2024-12 | `beb0669b` | Sistema de clarificación HU3 |

---

## Contacto

Para preguntas sobre los tests, consultar:
- `docs/context/PATTERNS.md` - Patrones de testing
- `.claude/rules/` - Reglas de desarrollo
