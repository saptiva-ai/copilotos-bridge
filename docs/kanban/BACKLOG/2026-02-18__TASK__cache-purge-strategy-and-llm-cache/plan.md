# Plan: Cache Purge Strategy & LLM Semantic Cache

## Resumen

5 fases incrementales. Cada fase es deployable independientemente.
Fase 1-2 son Redis puro (bajo riesgo). Fase 3 agrega pgvector (nueva infra). Fase 4-5 son observabilidad y purga programada.

---

## Fase 1: Sanitizar caches existentes

**Objetivo**: Eliminar anti-patrones, agregar version prefix, migrar rate limiter.

### 1.1 Reemplazar KEYS por SCAN en `redis_cache.py`

**Archivo**: `apps/backend/src/core/redis_cache.py`

**Problema**: `invalidate_chat_history()` (L259-283), `delete_pattern()` (L314-329), `invalidate_research_tasks()` (L331-350) usan `self.client.keys(pattern)` que bloquea Redis O(N).

**Cambio**: Reemplazar los 3 usos de `self.client.keys(pattern)` por un helper `_scan_keys()`:

```python
async def _scan_keys(self, pattern: str) -> list[str]:
    """Scan for keys matching pattern without blocking Redis."""
    if not self.client:
        return []
    all_keys: list[str] = []
    cursor = 0
    while True:
        cursor, keys = await self.client.scan(cursor, match=pattern, count=200)
        all_keys.extend(keys)
        if cursor == 0:
            break
    return all_keys
```

Reemplazar en:
- `invalidate_chat_history()`: `keys = await self.client.keys(pattern)` → `keys = await self._scan_keys(pattern)` (2 usos dentro del for loop)
- `delete_pattern()`: `keys = await self.client.keys(pattern)` → `keys = await self._scan_keys(pattern)`
- `invalidate_research_tasks()`: `keys = await self.client.keys(pattern)` → `keys = await self._scan_keys(pattern)`

### 1.2 Agregar version prefix global (`CACHE_VERSION`)

**Archivos**:
- `apps/backend/src/core/config.py` — agregar field
- `apps/backend/src/core/redis_cache.py` — usar en `_make_key()`
- `apps/backend/src/services/bank_analytics_client.py` — usar en `cache_key`
- `infra/docker-compose.yml` — agregar env var

**config.py** — nuevo field:
```python
cache_version: str = Field(
    default="v1",
    description="Cache version prefix. Bump on deploy to invalidate all versioned caches.",
    alias="CACHE_VERSION",
)
```

**redis_cache.py** — modificar `_make_key()`:
```python
def _make_key(self, prefix: str, identifier: str, params: Dict[str, Any] = None) -> str:
    version = self.settings.cache_version  # "v1", "v2", etc.
    key = f"{version}:cache:{prefix}:{identifier}"
    if params:
        params_str = json.dumps(params, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        key += f":{params_hash}"
    return key
```

**bank_analytics_client.py** — reemplazar hardcoded `v5`:
```python
# ANTES:
cache_key = f"bank_query_classification:v5:{message_hash}"

# DESPUES:
settings = get_settings()
cache_key = f"{settings.cache_version}:bank_query_classification:{message_hash}"
```

**docker-compose.yml** — agregar env var:
```yaml
environment:
  CACHE_VERSION: "${CACHE_VERSION:-v1}"
```

**Nota**: Las keys viejas expiran naturalmente por TTL. Zero-downtime.

### 1.3 Migrar rate limiter a Redis

**Archivo**: `apps/backend/src/middleware/rate_limit.py`

**Problema**: `storage_uri="memory://"` — no sobrevive restarts, no comparte entre instancias.

**Cambio**: Usar Redis URL del settings:
```python
import os

def _get_rate_limit_storage_uri() -> str:
    redis_url = os.getenv("REDIS_URL", "")
    if redis_url:
        return redis_url
    return "memory://"

limiter = Limiter(
    key_func=get_user_id_or_ip,
    default_limits=["1000/hour"],
    storage_uri=_get_rate_limit_storage_uri(),
    strategy="fixed-window",
)
```

**Dependencia**: `slowapi` ya soporta Redis storage via `limits` library. No requiere instalar paquetes nuevos (ya tienen `redis.asyncio`).

### 1.4 Tests Fase 1

**Archivo nuevo**: `apps/backend/tests/unit/test_cache_strategy.py`

Tests:
- `test_scan_keys_replaces_keys_command` — mock Redis, verificar que `_scan_keys` usa `scan` no `keys`
- `test_cache_version_in_key` — verificar que `_make_key()` incluye version prefix
- `test_cache_version_bump_invalidates` — cambiar CACHE_VERSION, verificar cache miss
- `test_rate_limiter_uses_redis_when_available` — verificar `storage_uri` apunta a Redis

---

## Fase 2: Event-driven invalidation (Pub/Sub)

**Objetivo**: Invalidar caches automaticamente cuando cambian datos subyacentes (ETL, deploy).

### 2.1 Canal Pub/Sub + listener

**Archivo nuevo**: `apps/backend/src/core/cache_invalidation.py`

```python
"""
Event-driven cache invalidation via Redis Pub/Sub.

Triggers:
- etl_complete: After ETL loads new data
- deploy_complete: After new version deployed
- handler_change: After handler logic changes
"""

import json
from enum import Enum
from typing import Optional

import structlog
from redis.asyncio import Redis

logger = structlog.get_logger(__name__)

CHANNEL = "cache:invalidate"

class InvalidationEvent(str, Enum):
    ETL_COMPLETE = "etl_complete"
    DEPLOY_COMPLETE = "deploy_complete"
    HANDLER_CHANGE = "handler_change"

async def publish_invalidation(
    redis_client: Redis,
    event: InvalidationEvent,
    metadata: Optional[dict] = None,
) -> None:
    """Publish cache invalidation event."""
    payload = {"event": event.value, **(metadata or {})}
    await redis_client.publish(CHANNEL, json.dumps(payload))
    logger.info("cache_invalidation.published", event=event.value, metadata=metadata)

async def start_invalidation_listener(redis_client: Redis) -> None:
    """Subscribe and handle invalidation events. Run as background task."""
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(CHANNEL)
    logger.info("cache_invalidation.listener_started", channel=CHANNEL)

    async for message in pubsub.listen():
        if message["type"] != "message":
            continue
        try:
            event = json.loads(message["data"])
            await _handle_invalidation(event)
        except Exception as e:
            logger.error("cache_invalidation.handler_error", error=str(e))

async def _handle_invalidation(event: dict) -> None:
    """Route invalidation event to appropriate cache layers."""
    event_type = event.get("event")

    if event_type == "etl_complete":
        # Flush: query classification, metric freshness
        from .redis_cache import get_redis_cache
        cache = await get_redis_cache()
        await cache.delete_pattern(f"*:bank_query_classification:*")
        logger.info("cache_invalidation.etl_flushed", caches=["query_classification"])

    elif event_type == "deploy_complete":
        # Version bump handles most caches via prefix.
        # Flush MCP tool results (no version prefix).
        from ..services.mcp_cache import invalidate_all_tool_caches
        await invalidate_all_tool_caches()
        logger.info("cache_invalidation.deploy_flushed", caches=["mcp_tool_results"])

    elif event_type == "handler_change":
        handler = event.get("handler")
        if handler:
            from .redis_cache import get_redis_cache
            cache = await get_redis_cache()
            await cache.delete_pattern(f"*:bank_query_classification:*")
```

### 2.2 Integrar listener en startup

**Archivo**: `apps/backend/src/main.py`

En el `lifespan` o `on_startup`, agregar:
```python
from .core.cache_invalidation import start_invalidation_listener
from .core.redis_cache import get_redis_cache

cache = await get_redis_cache()
if cache.client:
    asyncio.create_task(start_invalidation_listener(cache.client))
```

### 2.3 Hook post-ETL

**Archivo**: `plugins/bank-advisor-private/etl/core/refresh_orchestrator.py`

Al final de `run_refresh()`, publicar evento:
```python
from apps.backend.src.core.cache_invalidation import publish_invalidation, InvalidationEvent

# Despues de validacion exitosa:
await publish_invalidation(
    redis_client=redis_client,
    event=InvalidationEvent.ETL_COMPLETE,
    metadata={"periodo": periodo, "tables": loaded_tables},
)
```

**Nota**: El orchestrator no tiene acceso directo a Redis. Alternativa: hacer POST al endpoint interno `/api/internal/cache/invalidate` (ver 2.4).

### 2.4 Endpoint interno de invalidacion

**Archivo**: `apps/backend/src/routers/internal.py`

Agregar endpoint:
```python
@router.post("/cache/invalidate")
async def invalidate_cache(event: str, metadata: dict = None):
    """Trigger cache invalidation from external sources (ETL, CI/CD)."""
    cache = await get_redis_cache()
    if cache.client:
        await publish_invalidation(cache.client, InvalidationEvent(event), metadata)
    return {"status": "published", "event": event}
```

Protegido por `BACKEND_INTERNAL_KEY` (ya existe en internal.py).

### 2.5 Tests Fase 2

- `test_publish_invalidation` — mock Pub/Sub, verificar publish
- `test_etl_complete_flushes_classification` — simular evento, verificar delete_pattern
- `test_deploy_complete_flushes_mcp` — simular evento, verificar invalidate_all_tool_caches
- `test_invalidation_endpoint` — HTTP test contra endpoint interno

---

## Fase 3: LLM Semantic Cache (pgvector)

**Objetivo**: Cachear respuestas LLM por similitud semantica para evitar re-computar queries equivalentes.

### 3.1 Instalar pgvector en GCP PostgreSQL

**Migracion**: `plugins/bank-advisor-private/migrations/061_add_pgvector_semantic_cache.sql`

```sql
-- Habilitar extension pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Tabla de cache semantico
CREATE TABLE IF NOT EXISTS llm_response_cache (
    id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    query_embedding vector(384) NOT NULL,  -- MiniLM-L12-v2 = 384 dims
    response_text TEXT NOT NULL,
    handler VARCHAR(50),
    bank_context JSONB DEFAULT '{}',
    cache_version VARCHAR(10) NOT NULL DEFAULT 'v1',
    hit_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_hit_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Indice HNSW para busqueda por similitud (mas rapido que IVFFlat para <100K registros)
CREATE INDEX IF NOT EXISTS idx_llm_cache_embedding
    ON llm_response_cache USING hnsw (query_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Indices auxiliares
CREATE INDEX IF NOT EXISTS idx_llm_cache_expires ON llm_response_cache (expires_at);
CREATE INDEX IF NOT EXISTS idx_llm_cache_handler ON llm_response_cache (handler);
CREATE INDEX IF NOT EXISTS idx_llm_cache_version ON llm_response_cache (cache_version);
CREATE INDEX IF NOT EXISTS idx_llm_cache_hit_count ON llm_response_cache (hit_count);

COMMENT ON TABLE llm_response_cache IS
'LLM semantic response cache. Queries with cosine similarity > 0.92 return cached response.';
```

**Prerequisito**: `pgvector` extension debe estar disponible en Cloud SQL. En Cloud SQL for PostgreSQL, pgvector esta disponible como extension predeterminada desde PostgreSQL 15+.

### 3.2 Servicio de semantic cache

**Archivo nuevo**: `apps/backend/src/services/llm_semantic_cache.py`

```python
"""
LLM Semantic Cache Service.

Caches LLM responses by embedding similarity.
Two queries with cosine similarity > THRESHOLD return the same cached response.

Dependencies:
- pgvector extension in PostgreSQL
- embedding_service for query embedding
- asyncpg for direct SQL access
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)

# Configuration
SIMILARITY_THRESHOLD = 0.92  # cosine similarity threshold for cache hit
DEFAULT_TTL_DAYS = 7
MAX_CACHE_ENTRIES = 10_000


class LLMSemanticCache:
    """Cache LLM responses by semantic similarity."""

    def __init__(self, db_pool, embedding_service, cache_version: str = "v1"):
        self._pool = db_pool  # asyncpg pool
        self._embedder = embedding_service
        self._cache_version = cache_version

    async def search(
        self,
        query: str,
        handler: Optional[str] = None,
        banks: Optional[list[str]] = None,
    ) -> Optional[Tuple[str, float]]:
        """
        Search for semantically similar cached response.

        Returns (response_text, similarity) or None.
        """
        embedding = await self._embedder.encode_single_async(query)
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

        sql = """
        SELECT id, response_text,
               1 - (query_embedding <=> $1::vector) AS similarity
        FROM llm_response_cache
        WHERE expires_at > NOW()
          AND cache_version = $2
          AND 1 - (query_embedding <=> $1::vector) > $3
        """
        params = [embedding_str, self._cache_version, SIMILARITY_THRESHOLD]

        # Optional filter: same handler
        if handler:
            sql += " AND handler = $4"
            params.append(handler)

        sql += " ORDER BY query_embedding <=> $1::vector LIMIT 1"

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(sql, *params)

        if row:
            # Update hit count
            asyncio.create_task(self._record_hit(row["id"]))
            return row["response_text"], row["similarity"]

        return None

    async def store(
        self,
        query: str,
        response: str,
        handler: Optional[str] = None,
        bank_context: Optional[dict] = None,
        ttl_days: int = DEFAULT_TTL_DAYS,
    ) -> None:
        """Store query-response pair in semantic cache."""
        embedding = await self._embedder.encode_single_async(query)
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
        expires = datetime.utcnow() + timedelta(days=ttl_days)

        sql = """
        INSERT INTO llm_response_cache
            (query_text, query_embedding, response_text, handler, bank_context,
             cache_version, expires_at)
        VALUES ($1, $2::vector, $3, $4, $5::jsonb, $6, $7)
        """
        import json
        async with self._pool.acquire() as conn:
            await conn.execute(
                sql, query, embedding_str, response, handler,
                json.dumps(bank_context or {}), self._cache_version, expires,
            )

    async def _record_hit(self, cache_id: int) -> None:
        """Increment hit count and update last_hit_at."""
        sql = """
        UPDATE llm_response_cache
        SET hit_count = hit_count + 1, last_hit_at = NOW()
        WHERE id = $1
        """
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(sql, cache_id)
        except Exception:
            pass  # Non-critical

    async def purge_expired(self) -> int:
        """Delete expired entries. Returns count deleted."""
        sql = "DELETE FROM llm_response_cache WHERE expires_at < NOW()"
        async with self._pool.acquire() as conn:
            result = await conn.execute(sql)
        count = int(result.split()[-1])
        logger.info("llm_cache.purge_expired", deleted=count)
        return count

    async def purge_cold(self, days_inactive: int = 15) -> int:
        """Delete entries with 0 hits older than N days."""
        sql = """
        DELETE FROM llm_response_cache
        WHERE hit_count = 0
          AND created_at < NOW() - INTERVAL '1 day' * $1
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(sql, days_inactive)
        count = int(result.split()[-1])
        logger.info("llm_cache.purge_cold", deleted=count, days=days_inactive)
        return count
```

### 3.3 Integrar en pipeline de chat

**Archivo**: `apps/backend/src/services/streaming/chat_stream_producer.py`

Punto de integracion: **antes** de llamar a Saptiva API, checar semantic cache.

```python
# Pre-LLM check
cache_result = await semantic_cache.search(
    query=user_query,
    handler=matched_handler,
)

if cache_result:
    response_text, similarity = cache_result
    logger.info("semantic_cache.hit", similarity=similarity, handler=matched_handler)
    # Yield cached response as stream chunks (simulated)
    yield response_text
    return

# ... normal LLM flow ...

# Post-LLM store
await semantic_cache.store(
    query=user_query,
    response=full_response,
    handler=matched_handler,
    bank_context={"banks": detected_banks, "periodo": periodo},
)
```

### 3.4 Conexion asyncpg a PostgreSQL

**Archivo**: `apps/backend/src/core/pg_pool.py` (nuevo)

```python
"""PostgreSQL connection pool for direct SQL access (pgvector, etc.)."""

import os
from typing import Optional

import asyncpg
import structlog

logger = structlog.get_logger(__name__)

_pool: Optional[asyncpg.Pool] = None

async def get_pg_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        dsn = os.getenv("BANKADVISOR_DATABASE_URL", "")
        _pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
        logger.info("pg_pool.created", min=2, max=10)
    return _pool

async def close_pg_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
```

**Dependencia nueva**: `asyncpg` — agregar a `requirements.txt` del backend.

### 3.5 Tests Fase 3

- `test_semantic_cache_hit` — insertar entry, buscar query similar → hit
- `test_semantic_cache_miss` — buscar query no relacionada → miss
- `test_semantic_cache_version_isolation` — entries de v1 no aparecen si version=v2
- `test_semantic_cache_purge_expired` — insertar expired entries → purge
- `test_semantic_cache_purge_cold` — insertar entries sin hits → purge

**Nota**: Tests requieren PostgreSQL con pgvector. Usar Docker testcontainer o mock.

---

## Fase 4: Purga programada

**Objetivo**: Cron jobs para limpiar entries frias y expiradas.

### 4.1 Background task en startup

**Archivo**: `apps/backend/src/main.py`

```python
async def _scheduled_cache_purge():
    """Run every 24 hours: purge expired + cold entries."""
    while True:
        await asyncio.sleep(86400)  # 24 hours
        try:
            cache = get_llm_semantic_cache()
            await cache.purge_expired()
            await cache.purge_cold(days_inactive=15)
        except Exception as e:
            logger.error("scheduled_purge.error", error=str(e))

# En lifespan/startup:
asyncio.create_task(_scheduled_cache_purge())
```

### 4.2 Endpoint manual de purga

**Archivo**: `apps/backend/src/routers/internal.py`

```python
@router.post("/cache/purge")
async def purge_cache(target: str = "all"):
    """Manual cache purge. Targets: expired, cold, all."""
    cache = get_llm_semantic_cache()
    results = {}
    if target in ("expired", "all"):
        results["expired"] = await cache.purge_expired()
    if target in ("cold", "all"):
        results["cold"] = await cache.purge_cold()
    return results
```

---

## Fase 5: Observabilidad

**Objetivo**: Metricas para cada capa de cache.

### 5.1 Metricas structlog (minimo viable)

En lugar de Prometheus (overhead de infra), usar structlog counters que ya exportan a Cloud Logging:

```python
# En cada cache hit/miss, log con campo estandarizado:
logger.info("cache.hit", cache_layer="semantic", latency_ms=12.3, query_preview="cartera...")
logger.info("cache.miss", cache_layer="semantic", query_preview="cartera...")
logger.info("cache.hit", cache_layer="redis_classification", latency_ms=0.8)
```

### 5.2 Endpoint de stats

**Archivo**: `apps/backend/src/routers/internal.py`

```python
@router.get("/cache/stats")
async def cache_stats():
    """Get cache statistics across all layers."""
    redis_cache = await get_redis_cache()
    extraction_cache = get_extraction_cache()
    mcp_stats = await get_cache_stats()

    return {
        "extraction": extraction_cache.get_metrics(),
        "mcp_tools": mcp_stats,
        "semantic": await semantic_cache.get_stats(),
    }
```

---

## Resumen de archivos afectados

### Modificados
| Archivo | Fase | Cambio |
|---------|------|--------|
| `apps/backend/src/core/redis_cache.py` | 1 | SCAN helper, version prefix en `_make_key()` |
| `apps/backend/src/core/config.py` | 1 | Field `cache_version` |
| `apps/backend/src/middleware/rate_limit.py` | 1 | Redis storage URI |
| `apps/backend/src/services/bank_analytics_client.py` | 1 | Version prefix en cache key |
| `apps/backend/src/main.py` | 2, 4 | Pub/Sub listener, scheduled purge |
| `apps/backend/src/routers/internal.py` | 2, 4, 5 | Endpoints: invalidate, purge, stats |
| `apps/backend/src/services/streaming/chat_stream_producer.py` | 3 | Pre-LLM semantic cache check |
| `infra/docker-compose.yml` | 1 | `CACHE_VERSION` env var |

### Nuevos
| Archivo | Fase | Proposito |
|---------|------|-----------|
| `apps/backend/src/core/cache_invalidation.py` | 2 | Pub/Sub invalidation events |
| `apps/backend/src/services/llm_semantic_cache.py` | 3 | pgvector semantic cache service |
| `apps/backend/src/core/pg_pool.py` | 3 | asyncpg connection pool |
| `migrations/061_add_pgvector_semantic_cache.sql` | 3 | pgvector extension + table |
| `apps/backend/tests/unit/test_cache_strategy.py` | 1-5 | Tests para toda la estrategia |

### Dependencias nuevas
| Paquete | Fase | Motivo |
|---------|------|--------|
| `asyncpg` | 3 | Acceso directo a PostgreSQL para pgvector queries |

---

## Orden de ejecucion

```
Fase 1 → deploy → validar SCAN + version prefix funcionan
Fase 2 → deploy → validar Pub/Sub invalida caches correctamente
Fase 3 → instalar pgvector en GCP → migration 061 → deploy → validar semantic cache
Fase 4 → deploy → validar purga programada
Fase 5 → deploy → validar stats endpoint
```

Cada fase es independiente y reversible. Fase 3 tiene el mayor riesgo (nueva extension + nueva dependencia) pero tambien el mayor impacto.
