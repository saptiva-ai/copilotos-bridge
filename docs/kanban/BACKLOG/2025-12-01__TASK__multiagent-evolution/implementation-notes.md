# Implementation Notes - Multiagent Evolution

> Fase 0 completada. Este documento contiene la arquitectura REAL del repo, no propuesta teórica.

---

## 1. Arquitectura REAL del Repo

### 1.1 Diagrama de Componentes Reales

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              BANKADVISOR PLUGIN (ACTUAL)                            │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                           ENTRY POINT                                        │   │
│  │  src/main.py → FastMCP Server + gRPC (optional)                             │   │
│  │  Ports: 8002 (HTTP/MCP), 50051 (gRPC)                                       │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                             │
│              ┌────────────────────────┼────────────────────────┐                   │
│              ▼                        ▼                        ▼                   │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐        │
│  │    QUERY ROUTER     │  │    FSM MACHINE      │  │   DIRECT HANDLERS   │        │
│  │                     │  │  (python-statemachine)│ │                     │        │
│  │ pipelines/          │  │  fsm/machine.py     │  │ handlers/__init__.py│        │
│  │ query_router.py     │  │                     │  │ (14 handlers)       │        │
│  └──────────┬──────────┘  └──────────┬──────────┘  └──────────┬──────────┘        │
│             │                        │                        │                    │
│             ▼                        ▼                        ▼                    │
│  ┌──────────────────────────────────────────────────────────────────────────┐     │
│  │                         PIPELINE STAGES                                   │     │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐          │     │
│  │  │ InputValidation │  │ IntentDetection │  │ TimeRangeResolver│          │     │
│  │  │ (9 patterns SQL)│  │ (NlpIntentSvc)  │  │ (date parsing)   │          │     │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘          │     │
│  └──────────────────────────────────────────────────────────────────────────┘     │
│                                       │                                             │
│              ┌────────────────────────┼────────────────────────┐                   │
│              ▼                        ▼                        ▼                   │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐        │
│  │   SQL VALIDATOR     │  │   WEAVIATE ONTOLOGY │  │   SQL EXECUTION     │        │
│  │                     │  │                     │  │                     │        │
│  │ services/           │  │ services/           │  │ services/           │        │
│  │ sql_validator.py    │  │ weaviate_ontology   │  │ sql_execution_      │        │
│  │                     │  │ _service.py         │  │ service.py          │        │
│  │ - 24 keywords       │  │                     │  │                     │        │
│  │ - 19 tables         │  │ - Ontology_Term_V2  │  │ - asyncpg pool      │        │
│  │ - 6 patterns        │  │ - MiniLM-L12-v2     │  │ - 30s timeout       │        │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘        │
│                                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────┐     │
│  │                          DATA LAYER                                       │     │
│  │                                                                           │     │
│  │  PostgreSQL                           Weaviate 1.32.2                     │     │
│  │  ┌─────────────┐ ┌─────────────┐     ┌─────────────────────┐             │     │
│  │  │ 3NF Facts   │ │ 10 MVs      │     │ Ontology_Term_V2    │             │     │
│  │  │ - kpis_mens │ │ - evolucion │     │ (embeddings client- │             │     │
│  │  │ - cartera   │ │ - ranking   │     │  side, no vectorizer│             │     │
│  │  │ - metricas  │ │ - comparati │     │  module en server)  │             │     │
│  │  └─────────────┘ └─────────────┘     └─────────────────────┘             │     │
│  └──────────────────────────────────────────────────────────────────────────┘     │
│                                                                                     │
│  ❌ NO EXISTE: Rate Limiting, Redis integration, Q&A Cache, Sandbox Executor       │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Lista de Archivos Clave

| Componente | Path Real | Clase/Función | Responsabilidad |
|------------|-----------|---------------|-----------------|
| **FSM Machine** | `fsm/machine.py` | `QueryStateMachine`, `QueryModel` | Orquestación de estados |
| **Validation Agent** | `fsm/agents/__init__.py` | `ValidationAgent` | Wrapper de InputValidationStage |
| **Analysis Agent** | `fsm/agents/analysis_agent.py` | `AnalysisAgent` | Genera análisis LLM (NO autónomo) |
| **Query Router** | `pipelines/query_router.py` | `QueryRouter` | Chain of Responsibility |
| **Input Validation** | `pipelines/stages/input_validation.py` | `InputValidationStage` | SQL injection + dates |
| **SQL Validator** | `services/sql_validator.py` | `SqlValidator` | 4 capas de defensa |
| **Weaviate Service** | `services/weaviate_ontology_service.py` | `WeaviateOntologyService` | Búsqueda semántica |
| **SQL Execution** | `services/sql_execution_service.py` | `SqlExecutionService` | Pool + timeouts |
| **Handlers** | `handlers/__init__.py` | `get_specific_handlers()` | 14 handlers registrados |
| **Knowledge Handler** | `handlers/knowledge_handler.py` | `KnowledgeHandler` | Glossary via Weaviate |
| **Runtime Config** | `runtime_config.py` | `RuntimeConfig` | Singleton YAML loader |
| **DB Setup** | `db.py` | `get_async_session()` | SQLAlchemy async |

### 1.3 Handlers Existentes (en orden de prioridad)

```python
# handlers/__init__.py -> get_specific_handlers()
HANDLER_PRIORITY = [
    MultiMetricHandler,           # 1. Distribución cartera (stacked)
    MetricasFinancierasHandler,   # 2. ROA, ROE, fin. metrics
    EvolucionBancoHandler,        # 3. YoY, MoM, evolución → USA bank_mv_evolucion_cartera_banco
    ResumenSistemaHandler,        # 4. Resumen sistema → USA bank_mv_resumen_sistema
    CarteraActividadHandler,      # 5. Por actividad → USA bank_mv_cartera_por_actividad
    CarteraTamanoHandler,         # 6. Por tamaño → USA bank_mv_cartera_por_tamano
    CarteraDestinoHandler,        # 7. Por destino → USA bank_mv_cartera_por_destino
    ViviendaPerfilHandler,        # 8. Vivienda → USA bank_mv_vivienda_por_perfil
    CarteraRegionHandler,         # 9. Por región → USA bank_mv_cartera_por_estado
    ComparativeRatioHandler,      # 10. Ratios comparativos
    MarketShareHandler,           # 11. PDM
    SegmentHandler,               # 12. Segmentación
    FinancialHandler,             # 13. Métricas financieras legacy
    InstitutionRankingHandler,    # 14. Rankings
]
```

**Nota**: Los handlers 3-9 YA usan MVs directamente. No hay estrategia de fallback a fact tables.

---

## 2. Versiones Detectadas

| Tecnología | Versión | Notas |
|------------|---------|-------|
| **Weaviate Server** | `1.32.2` | En docker-compose.yml |
| **weaviate-client** | `4.19.0` | En pyproject.toml |
| **API Style** | Collections API (v4) | NO usa schema/class antiguo |
| **Vectorizer** | `none` (server) | Client-side embeddings |
| **Embedding Model** | `paraphrase-multilingual-MiniLM-L12-v2` | sentence-transformers |
| **Redis** | `7-alpine` | EXISTE pero NO integrado |
| **PostgreSQL** | `16.x` (inferred) | asyncpg pool |
| **Python** | `3.11` | En Dockerfile |

---

## 3. Límites Actuales (NO Rate Limiting)

### 3.1 Límites Implícitos

| Tipo | Valor | Ubicación |
|------|-------|-----------|
| **Connection Pool Min** | 5 | `sql_execution_service.py` |
| **Connection Pool Max** | 20 | `sql_execution_service.py` |
| **Pool Acquire Timeout** | 5s | `sql_execution_service.py` |
| **Query Execution Timeout** | 30s | `QueryBudget.max_execution_time_sec` |
| **Max Rows** | 5000 | `QueryBudget.max_rows` |
| **Max Joins** | 2 | `QueryBudget.max_joins` |
| **LLM Timeout** | 10s | `runtime_config.py` |
| **Bank Cache TTL** | 3600s | `bankadvisor.yaml` |

### 3.2 Rate Limiting

**ESTADO: NO EXISTE**

```bash
# Búsqueda confirmada - no hay rate limiting
$ grep -r "rate_limit\|RateLimit\|throttle" src/ --include="*.py"
# Solo 1 resultado irrelevante (docstring "security limits")
```

**Redis está disponible** en `infra/docker-compose.yml` pero **NO hay cliente Redis** en BankAdvisor.

---

## 4. Weaviate: Estado Actual vs Propuesto

### 4.1 Estado Actual

```python
# weaviate_ontology_service.py
DEFAULT_COLLECTION = "Ontology_Term_V2"
DEFAULT_MIN_SIMILARITY = 0.70
DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# Métodos existentes:
- search_terms(query, top_k=5, min_similarity=0.70)
- find_term_by_name(term_name)
- get_all_synonyms(query, top_k=3)
```

**Colección única**: `Ontology_Term_V2` para glossario/definiciones

### 4.2 Propuesto (nuevas colecciones)

| Colección | Propósito | Vectorizer |
|-----------|-----------|------------|
| `QA_Pairs_Banking` | Cache de Q&A frecuentes | text2vec (client-side) |
| `SQL_Examples` | Few-shot para NL2SQL | text2vec (client-side) |

**Nota**: El schema debe usar API de Collections (v4), no el antiguo schema/class.

---

## 5. Top 10 Riesgos Técnicos con Mitigación

| # | Riesgo | Prob | Impacto | Mitigación |
|---|--------|------|---------|------------|
| **1** | **Python sandbox escape** (getattr chains, __class__.__bases__) | Alta | Crítico | NO hacer sandbox in-process. Usar contenedor aislado con seccomp/gVisor o DSL restringido |
| **2** | **Rate limit en RAM** con múltiples pods = bypass | Alta | Alto | Usar Redis existente para token bucket distribuido |
| **3** | **Q&A stale data** tras actualización de MVs | Media | Alto | Refresh automático + versioning por `data_date` |
| **4** | **Weaviate API cambios** v4 collections vs v3 schema | Baja | Medio | Ya usa v4.19.0 cliente. Verificar compat con server 1.32.2 |
| **5** | **Explosión cardinalidad Q&A** (todo × bancos × métricas × tiempo) | Alta | Alto | Generar solo por intents + templates. MAX 1000 pares iniciales |
| **6** | **Fallback MV→Fact lento** sin índices adecuados | Media | Alto | Asegurar índices en fact tables. Medir latencia antes/después |
| **7** | **Prompt injection via Weaviate** (texto recuperado ejecuta acciones) | Media | Crítico | Separar "datos" de "instrucciones". Policy layer que bloquea comandos en texto |
| **8** | **Connection pool exhaustion** bajo carga | Media | Alto | Ya tiene pool 5-20. Añadir métricas Prometheus para monitorear |
| **9** | **LLM timeout cascade** (intent→analysis→response) | Baja | Medio | Ya tiene 10s timeout. Añadir circuit breaker |
| **10** | **Memory leak en embedder** (sentence-transformers cargado N veces) | Baja | Medio | Ya usa lazy init singleton. Verificar en tests de carga |

---

## 6. Discrepancias: Plan Original vs Repo Real

| Aspecto | Plan Original | Repo Real | Acción |
|---------|---------------|-----------|--------|
| **SAFE_BUILTINS bug** | `"min": max` | N/A (no existe código) | ⚠️ NO implementar sandbox in-process |
| **Rate Limiter** | Token bucket en RAM | No existe | Implementar con Redis |
| **Weaviate schema** | `class` style | `collections` API | Ajustar código a v4 |
| **Sandbox executor** | exec() con builtins restringidos | No existe | NO implementar. Usar contenedor aislado |
| **MV-first strategy** | Propuesta | Handlers YA usan MVs | Solo agregar fallback + métricas |
| **Q&A generation** | Todo × Todo | No existe | Implementar con templates limitados |
| **Redis** | Asumido inexistente | Existe en docker-compose | Usar para rate limiting |

---

## 7. Decisiones de Diseño Recomendadas

### 7.1 Sandbox: NO In-Process

**Razón**: Python es un lenguaje que escapa sandboxes "caseros". Aunque bloquees `__subclasses__`, `__globals__`, etc., el ataque real casi siempre encuentra un camino.

**Recomendación**:
1. **Opción A (preferida)**: Contenedor dedicado con:
   - No filesystem, no network, seccomp/apparmor
   - User no-root, read-only FS
   - API mínima: `run_query(sql_template, params)` o `run_operation(op, params)`

2. **Opción B (si A no es viable)**: DSL restringido (no Python libre)
   - Solo operaciones predefinidas: filter, aggregate, compare
   - Sin acceso a objetos Python arbitrarios

### 7.2 Rate Limiting: Redis Token Bucket

```python
# Propuesta: src/bankadvisor/security/rate_limiter.py

class RedisRateLimiter:
    """Token bucket distribuido usando Redis."""

    LIMITS = {
        "user": (100, 60),    # 100 req/min per user
        "agent": (500, 60),   # 500 req/min per agent
        "global": (10000, 60) # 10k req/min global
    }

    def __init__(self, redis_url: str):
        self.redis = aioredis.from_url(redis_url)

    async def check(self, user_id: str, agent_id: str) -> tuple[bool, str]:
        # Usa MULTI/EXEC para atomicidad
        ...
```

### 7.3 Q&A Generation: Templates Limitados

```python
# Propuesta: limitar a intents conocidos
SUPPORTED_INTENTS = ["ranking", "evolution", "comparison", "knowledge"]
MAX_QA_PAIRS = 1000

# Parámetros acotados
TOP_BANKS = ["INVEX", "BBVA", "BANORTE", "SANTANDER", "CITIBANAMEX", "SISTEMA"]
TOP_METRICS = ["IMOR", "ICAP", "ICOR", "ROE", "ROA", "CARTERA_TOTAL"]
TIME_RANGES = ["last_3_months", "last_6_months", "last_12_months", "year_2024"]

# Cardinalidad: 4 intents × 6 banks × 6 metrics × 4 time = 576 combinaciones base
```

### 7.4 MV-First: Agregar Fallback + Métricas

Los handlers YA usan MVs. Solo necesitamos:

1. **Fallback automático**: Si MV falla/vacío → query a fact table
2. **Métricas**: `mv_hit_rate`, `fallback_rate`, `avg_latency_ms`
3. **Logging estructurado**: `source=mv|fact`, `latency_ms`

---

## 8. Próximos Pasos (PRs Propuestos)

### PR 1: Rate Limiting con Redis
- **Archivos**: `src/bankadvisor/security/rate_limiter.py` (nuevo)
- **Integración**: Middleware en MCP server
- **Tests**: Unit (mock Redis) + Integration (Redis real)

### PR 2: MV-First Strategy con Fallback
- **Archivos**: `src/bankadvisor/data_access/mv_first_strategy.py` (nuevo)
- **Migrar**: `EvolucionBancoHandler`, `RankingHandler`
- **Métricas**: Prometheus counters

### PR 3: Weaviate Q&A Cache
- **Archivos**: `src/bankadvisor/qa_generation/` (nuevo módulo)
- **Schema**: Collections API v4
- **Límite**: MAX 1000 pares iniciales

### PR 4: Security Hardening (Prompt Injection)
- **Archivos**: `src/bankadvisor/security/prompt_guard.py` (nuevo)
- **Política**: Separar datos recuperados de instrucciones
- **Tests**: Ataques conocidos (jailbreak, injection)

---

## Apéndice: Comandos de Verificación

```bash
# Verificar versión Weaviate
docker exec octavios-chat-bajaware_invex-weaviate weaviate --version

# Verificar Redis disponible
docker exec octavios-chat-bajaware_invex-redis redis-cli ping

# Verificar MVs existentes
docker exec octavios-chat-bajaware_invex-backend psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT matviewname FROM pg_matviews WHERE schemaname = 'public' AND matviewname LIKE 'bank_mv_%';"

# Verificar colecciones Weaviate
curl -s http://localhost:8080/v1/schema | jq '.classes[].class'
```
