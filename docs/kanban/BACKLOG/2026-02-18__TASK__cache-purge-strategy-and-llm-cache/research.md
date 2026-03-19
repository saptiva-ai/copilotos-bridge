# Research: Cache Purge Strategy & LLM Semantic Cache

## 1. Estrategia de Invalidacion por Trigger

### Matriz de Invalidacion Propuesta

| Cache Layer | Deploy | ETL Ingest | Cada 24hr | Cada 15d | On Event |
|-------------|--------|-----------|-----------|----------|----------|
| Chat history (5min) | NO | NO | NO | NO | On new message |
| Research tasks (10min) | NO | NO | NO | NO | On status change |
| MCP tool results (1-24hr) | FLUSH | NO | NO | NO | On doc update |
| Extraction text (24hr) | NO | NO | NO | PURGE | On doc re-upload |
| Token blacklist | NO | NO | NO | NO | Auto-expira |
| Upload idempotency (1hr) | NO | NO | NO | NO | Auto-expira |
| Query classification (1-2hr) | VERSION BUMP | FLUSH | NO | NO | On handler change |
| Embedding vectors (in-mem) | RESTART clears | NO | NO | NO | — |
| Query spec parser (in-mem) | RESTART clears | NO | NO | NO | — |
| Metric freshness (in-mem 1hr) | RESTART clears | FLUSH | NO | NO | On ETL complete |
| Bank advisor tools (in-mem 10min) | RESTART clears | NO | NO | NO | On plugin deploy |
| Rate limiter (memory) | RESTART clears | NO | NO | NO | — |
| **LLM semantic cache (NEW)** | VERSION BUMP | NO | PURGE stale | PURGE cold | On prompt change |

### Justificacion de TTLs

| TTL | Tipo de Dato | Razon |
|-----|-------------|-------|
| 2-5 min | Session/chat lists | UI necesita datos frescos, costo bajo de miss |
| 10-30 min | Tool results intermedios | Balance entre frescura y costo API |
| 1-2 hr | Clasificaciones, idempotency | Datos semi-estables, invalidacion por evento |
| 24 hr | Extracciones, deep research | Contenido estable, alto costo de regenerar |
| 7-15 dias | LLM semantic cache | Respuestas estables si datos no cambian |

---

## 2. Best Practices Redis — Invalidacion

### 2.1 Version Prefix (Deploy-time invalidation)

**Patron**: Incluir version en el key prefix para invalidar todo al deployar.

```python
# config.py
CACHE_VERSION = os.getenv("CACHE_VERSION", "v1")  # Bump en cada deploy

# redis_cache.py
def _make_key(self, prefix, identifier, params=None):
    key = f"{CACHE_VERSION}:{prefix}:{identifier}"
    ...
```

**Ventaja**: Zero-downtime invalidation. Las keys viejas expiran naturalmente.
**Desventaja**: Duplica memoria temporalmente (keys v1 + v2 hasta que v1 expira).

**Best practice**: Usar variable de entorno `CACHE_VERSION` que se setea automaticamente al SHA corto del commit:
```yaml
# docker-compose
environment:
  CACHE_VERSION: "${GIT_SHA:-v1}"
```

### 2.2 SCAN vs KEYS (Pattern invalidation)

**Problema actual**: `redis_cache.py:invalidate_chat_history()` usa `KEYS` que bloquea Redis.

```python
# MAL — bloquea Redis O(N)
keys = await self.client.keys(f"cache:chat_history:{chat_id}*")

# BIEN — iterativo, no bloquea
cursor = 0
while True:
    cursor, keys = await self.client.scan(cursor, match=pattern, count=100)
    if keys:
        await self.client.delete(*keys)
    if cursor == 0:
        break
```

**Best practice Redis**: NUNCA usar `KEYS` en produccion. Usar `SCAN` con `count=100-200`.

### 2.3 Pub/Sub para Event-driven Invalidation

**Patron**: Publicar eventos cuando datos cambian, subscribers invalidan caches relevantes.

```python
# Al completar ETL ingest
await redis.publish("cache:invalidate", json.dumps({
    "event": "etl_complete",
    "periodo": "202512",
    "tables": ["bank_src_analisis_general", "bank_fact_kpis_mensual"],
    "timestamp": "2026-02-18T15:00:00Z"
}))

# Subscriber en backend startup
async def cache_invalidation_listener():
    pubsub = redis.pubsub()
    await pubsub.subscribe("cache:invalidate")
    async for message in pubsub.listen():
        if message["type"] == "message":
            event = json.loads(message["data"])
            if event["event"] == "etl_complete":
                await invalidate_etl_dependent_caches(event)
```

**Que invalidar en `etl_complete`**:
- `bank_query_classification:*` (datos subyacentes cambiaron)
- In-memory `metric_freshness` cache (nuevos periodos)
- In-memory `bank_advisor_tools` cache (si cambiaron tools)
- MCP tool results que dependan de datos bancarios

### 2.4 TTL + Lazy Invalidation (Stale-While-Revalidate)

**Patron ya existente** en `bank_analytics_client.py:_schedule_tools_cache_refresh()`.

```python
# Si cache existe pero esta stale:
# 1. Retornar valor stale inmediatamente
# 2. Lanzar background task para refrescar
# 3. Siguiente request obtiene dato fresco
```

**Best practice**: Aplicar este patron a:
- Query classification (evita cold-start penalty)
- Metric freshness (ya lo implementa)
- LLM semantic cache (ideal para respuestas costosas)

### 2.5 Redis Memory Policy

```conf
# redis.conf
maxmemory 256mb
maxmemory-policy allkeys-lfu
```

**allkeys-lfu** (Least Frequently Used): Ideal para nuestro caso porque:
- Keys de alta frecuencia (chat, clasificacion) sobreviven
- Keys de baja frecuencia (deep_research antiguo) se evictan
- Protege contra OOM sin intervencion manual

---

## 3. LLM Semantic Cache — Arquitectura

### 3.1 Que es un LLM Semantic Cache

Cache que NO usa exact-match sino **similarity-based matching**. Dos preguntas semanticamente equivalentes devuelven la misma respuesta cacheada:

```
Q1: "cual es la cartera comercial de invex?"        → CACHE MISS → LLM → response → CACHE SET
Q2: "cartera comercial invex"                        → SEMANTIC HIT (sim=0.95) → cached response
Q3: "muéstrame la cartera de crédito comercial invex" → SEMANTIC HIT (sim=0.91) → cached response
```

### 3.2 Arquitectura Propuesta

```
User Query
    │
    ▼
┌─────────────────────┐
│ 1. Embed query       │  ← embedding_service.encode_single()
│    (already exists)  │
└─────────┬───────────┘
          │ vector [768d]
          ▼
┌─────────────────────┐
│ 2. Search similar    │  ← cosine similarity > threshold (0.92)
│    in cache index    │
└─────────┬───────────┘
          │
    ┌─────┴─────┐
    │           │
  HIT         MISS
    │           │
    ▼           ▼
┌────────┐  ┌────────────┐
│ Return │  │ Run full   │
│ cached │  │ LLM pipe   │
│ response│  │ + cache    │
└────────┘  └────────────┘
```

### 3.3 Opciones de Implementacion

#### Opcion A: Redis + Vector Search (Redis Stack)
```python
# Requiere Redis Stack (redis/redis-stack Docker image)
# Usa RediSearch para indexar embeddings

from redis.commands.search.field import VectorField, TextField, NumericField
from redis.commands.search.query import Query

# Crear indice
schema = [
    TextField("query_text"),
    VectorField("embedding", "FLAT", {
        "TYPE": "FLOAT32",
        "DIM": 768,
        "DISTANCE_METRIC": "COSINE",
    }),
    TextField("response_text"),
    TextField("handler"),
    NumericField("created_at"),
    NumericField("hit_count"),
]
await redis.ft("llm_cache").create_index(schema, prefix=["llm:"])

# Buscar similar
query_embedding = embedding_service.encode_single(user_query)
q = (
    Query(f"*=>[KNN 1 @embedding $vec AS score]")
    .return_fields("query_text", "response_text", "handler", "score")
    .sort_by("score")
    .dialect(2)
)
results = await redis.ft("llm_cache").search(q, query_params={"vec": query_embedding.tobytes()})

if results.docs and float(results.docs[0].score) < 0.08:  # cosine distance < 0.08 ≈ similarity > 0.92
    return results.docs[0].response_text  # CACHE HIT
```

**Pros**: Todo en Redis, latencia <5ms, no requiere infra adicional.
**Contras**: Requiere Redis Stack (no Redis vanilla), limite ~1M vectores.

#### Opcion B: PostgreSQL pgvector (ya tenemos PG)
```sql
-- Ya tenemos PostgreSQL en GCP
CREATE TABLE llm_response_cache (
    id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    query_embedding vector(768) NOT NULL,
    response_text TEXT NOT NULL,
    handler VARCHAR(50),
    bank_context JSONB,  -- {banks: ["INVEX"], periodo: "202510"}
    hit_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_llm_cache_embedding ON llm_response_cache
    USING ivfflat (query_embedding vector_cosine_ops) WITH (lists = 50);

-- Buscar similar
SELECT id, query_text, response_text, handler,
       1 - (query_embedding <=> $1::vector) as similarity
FROM llm_response_cache
WHERE expires_at > NOW()
  AND 1 - (query_embedding <=> $1::vector) > 0.92
ORDER BY query_embedding <=> $1::vector
LIMIT 1;
```

**Pros**: Ya tenemos PG, pgvector es maduro, persistente, SQL queries.
**Contras**: Latencia ~10-50ms (vs <5ms Redis), requiere instalar extension.

#### Opcion C: Weaviate (ya lo usamos para RAG)
```python
# Ya existe en el stack para RAG bridge
result = weaviate_client.query.get(
    "LLMResponseCache",
    ["query_text", "response_text", "handler"]
).with_near_vector({
    "vector": query_embedding,
    "certainty": 0.92
}).with_limit(1).do()
```

**Pros**: Ya esta en la infra, diseñado para similarity search.
**Contras**: Overhead de mantener otra coleccion, latencia ~20ms.

### 3.4 Recomendacion

**Opcion B (pgvector)** por estas razones:
1. Ya tenemos PostgreSQL en GCP — zero infra adicional
2. pgvector es extension madura (v0.7+, HNSW index)
3. Cache puede participar en transacciones SQL
4. EXPLAIN ANALYZE para optimizar queries
5. Backup automatico con el resto de la BD
6. `expires_at` nativo con cleanup cron
7. JOIN con `bank_dim_*` para invalidar por banco/periodo

### 3.5 Invalidacion del LLM Cache

| Trigger | Accion | Razon |
|---------|--------|-------|
| Deploy | Bump `cache_version` column | Cambios en prompts/handlers |
| ETL ingest | DELETE WHERE bank_context->periodo < new_periodo | Datos subyacentes cambiaron |
| 24hr | UPDATE hit_count, extend expires_at for hot entries | Mantener entries populares |
| 15 dias | DELETE WHERE hit_count = 0 AND created_at < 15d ago | Purgar entries frias |
| Handler change | DELETE WHERE handler = 'changed_handler' | Handler retorna datos distintos |

### 3.6 Context-Aware Cache Keys

No solo cachear por query similarity, sino tambien por **contexto**:

```python
cache_key_components = {
    "query_embedding": encode(user_query),
    "banks": sorted(detected_banks),      # ["INVEX"] vs ["INVEX", "BBVA"]
    "periodo": detected_periodo,           # "202510"
    "handler": matched_handler,            # "evolucion_banco"
    "cache_version": CACHE_VERSION,        # "v6"
}
```

Dos queries identicas pero con distinto banco o periodo = CACHE MISS (correcto).

### 3.7 Mejora de Ventana de Contexto

El LLM cache tambien mejora la **memoria conversacional**:

```python
# Al construir el system prompt, inyectar respuestas previas cacheadas
previous_responses = await get_cached_responses_for_session(
    session_id=session_id,
    limit=3,  # ultimas 3 respuestas relevantes
)

system_prompt += f"""
## Contexto de respuestas previas en esta sesion:
{format_previous_responses(previous_responses)}
"""
```

Esto reduce tokens al evitar re-generar context que ya fue computado, y mantiene coherencia entre respuestas consecutivas.

---

## 4. Plan de Implementacion (5 Fases)

### Fase 1: Sanitizar caches existentes
- Reemplazar KEYS por SCAN en `redis_cache.py`
- Agregar version prefix (`CACHE_VERSION` env var)
- Migrar rate limiter a Redis storage
- Documentar TTLs actuales

### Fase 2: Event-driven invalidation
- Crear canal Pub/Sub `cache:invalidate`
- Hook post-ETL: publicar evento `etl_complete`
- Hook post-deploy: publicar evento `deploy_complete`
- Subscriber que invalida caches por tipo de evento

### Fase 3: LLM semantic cache (pgvector)
- Instalar extension pgvector en GCP PostgreSQL
- Crear tabla `llm_response_cache` con indice HNSW
- Implementar `LLMCacheService` con search/store/invalidate
- Integrar en el pipeline de chat (pre-LLM check)

### Fase 4: Purga programada
- Cron job: cada 24hr purgar entries con 0 hits y >7d
- Cron job: cada 15d purgar extraction cache antiguo
- Metricas: cache hit rate, memory usage, eviction count

### Fase 5: Observabilidad
- Prometheus metrics para cada cache layer
- Grafana dashboard: hit rates, latency, memory
- Alertas: cache hit rate < 30%, memory > 80%

### Fase futura (infra): LMCache en engine Saptiva
> **Nota**: LMCache se instala en los servidores de inferencia Saptiva, no en esta aplicacion.
> Queda como recomendacion para el equipo de infra cuando se priorice.
- Confirmar con equipo infra que engine = vLLM (o SGLang)
- Instalar LMCache: `pip install lmcache` en servidor de inferencia
- Configurar tiered storage: GPU → CPU → Redis (DB separada)
- Benchmark: TTFT antes/despues con queries reales del Bank Advisor

---

## 5. Analisis de LMCache (github.com/LMCache/LMCache)

### 5.1 Que es

LMCache (6.9K stars, Apache 2.0, v0.3.14) es un **KV cache layer para inference engines** (vLLM, SGLang). Cachea los tensores internos de atencion (key-value pairs) que el transformer computa durante el prefill phase, almacenandolos en tiers: GPU -> CPU -> Disk -> S3/Redis.

Impacto: 3-10x reduccion en TTFT (Time To First Token) para long-context y multi-turn.

### 5.2 Como funciona

```
Request 1: "system prompt + RAG context + query A"
  GPU computa KV pairs para todo el texto (~2000 tokens)
  LMCache guarda KV tensors: GPU VRAM -> CPU RAM -> NVMe

Request 2: "system prompt + RAG context + query B"
  LMCache detecta que "system prompt + RAG context" (~1800 tokens) es reutilizable
  Carga KV cache pre-computado desde CPU/Disk (skip prefill)
  GPU solo computa KV para "query B" (~200 tokens nuevos)
  TTFT: 150ms en vez de 1500ms
```

Key: reutiliza KV para **cualquier texto repetido** (no solo prefijo).

### 5.3 Integraciones del ecosistema

- **Inference**: vLLM, SGLang, NVIDIA Dynamo, KServe, llm-d
- **Storage**: Redis, Valkey, S3, Weka, Mooncake, NVMe
- **Cloud**: Google Cloud GKE, CoreWeave, AWS SageMaker Hyperpod
- **Hardware**: NVIDIA CUDA, AMD ROCm, Ascend NPU

### 5.4 Aplicabilidad Directa — Saptiva es Self-Hosted

**IMPORTANTE**: Saptiva Turbo, Saptiva Legacy, etc. son modelos open source self-hosted en servidores propios. La API (`api.saptiva.com`) es un gateway OpenAI-compatible frente al engine de inferencia.

| Requerimiento LMCache | Nuestro Stack | Status |
|----------------------|---------------|--------|
| Self-hosted LLM (vLLM/SGLang) | Saptiva = self-hosted con modelos open source | CUMPLE |
| GPU con CUDA/ROCm | GPUs propias en servidores Saptiva | CUMPLE |
| Control del inference engine | Control total del servidor | CUMPLE |
| KV tensors en GPU VRAM | Acceso directo al engine | CUMPLE |

**Evidencia de compatibilidad con vLLM/SGLang**:
- API 100% OpenAI-compatible (`/v1/chat/completions`, `/v1/models`)
- SSE streaming con `data: [DONE]` — patron exacto de vLLM
- Saptiva Cortex tiene `reasoning_content` — campo tipico de DeepSeek R1 servido via vLLM
- Multiples modelos detras de un endpoint — patron de model routing

**Prerequisito**: Confirmar que engine de inferencia es vLLM o SGLang (no TGI, que no soporta LMCache). Verificar con equipo de infra Saptiva.

### 5.5 Ruta de Integracion con LMCache

#### Paso 1: Verificar engine (dia 1)

```bash
# Verificar si vLLM corre en el servidor Saptiva
ssh saptiva-server "pip list | grep -E 'vllm|sglang|lmcache'"

# O verificar via la API (vLLM expone version en /v1/models metadata)
curl https://api.saptiva.com/v1/models -H "Authorization: Bearer $KEY" | jq
```

#### Paso 2: Instalar LMCache como plugin vLLM

```bash
# En el servidor de inferencia Saptiva
pip install lmcache  # v0.3.14+

# Iniciar vLLM con LMCache habilitado
vllm serve "model-name" \
    --kv-cache-dtype auto \
    --enable-prefix-caching \
    --lmcache-config-file /etc/lmcache/config.yaml
```

#### Paso 3: Configurar tiered storage

```yaml
# /etc/lmcache/config.yaml
chunk_size: 256
local_device: "cuda"  # Tier 1: GPU VRAM

# Tier 2: CPU RAM (spillover)
local_cpu:
  enabled: true
  max_size_gb: 32

# Tier 3: Redis compartido entre instancias
remote:
  backend: "redis"
  url: "${REDIS_URL}/3"  # DB separada del cache aplicativo
  max_size_gb: 64
```

#### Paso 4: Beneficios esperados para nuestro caso

| Escenario | Sin LMCache | Con LMCache | Mejora |
|-----------|------------|------------|--------|
| System prompt bancario (~3K tokens) | Prefill 1.5s | Skip prefill 0.15s | **10x TTFT** |
| Multi-turn (historial 20 msgs) | Re-compute all | Reuse KV prefix | **3-5x TTFT** |
| RAG context (docs inyectados) | Compute per-request | Cache prefix comun | **2-3x TTFT** |
| Modelos grandes (70B+) | GPU-bound prefill | Precomputed KV | **5-10x TTFT** |

El system prompt de Bank Advisor es particularmente beneficiado porque:
- `SystemPromptBuilder.build()` genera ~3000 tokens de contexto bancario
- Es semi-deterministico (cambia solo cuando cambian los datos subyacentes)
- Multi-turn: cada request re-envia system + historial completo
- LMCache reutilizaria KV para todo el prefijo compartido entre turns

### 5.6 Complemento: LMCache + Semantic Cache (dos capas)

LMCache y nuestro semantic cache (seccion 3) son **complementarios**, no excluyentes:

```
Capa 1: LMCache (engine-level)
  └─ Cachea KV tensors internos del transformer
  └─ Beneficia: prefix repetido (system prompt, historial)
  └─ Requiere: texto exacto repetido al inicio
  └─ Reduccion: TTFT (latencia de primer token)

Capa 2: Semantic Cache (application-level, pgvector)
  └─ Cachea respuestas completas por similarity
  └─ Beneficia: queries semanticamente iguales
  └─ No requiere: texto exacto, usa embedding similarity
  └─ Reduccion: llamada completa al LLM (100% skip)
```

**Flujo combinado**:
```
User query
    │
    ▼
┌──────────────────┐
│ Semantic Cache    │ ← cosine similarity > 0.92?
│ (pgvector)        │
└────────┬─────────┘
    │ MISS          │ HIT → return cached response (0ms LLM)
    ▼
┌──────────────────┐
│ LMCache           │ ← prefix KV reuse
│ (engine-level)    │
└────────┬─────────┘
    │ KV loaded (skip prefill)
    ▼
┌──────────────────┐
│ LLM generation    │ ← solo genera tokens nuevos
│ (fast TTFT)       │
└────────┬─────────┘
    │
    ▼
Store in Semantic Cache + LMCache auto-stores KV
```

### 5.7 Tiered Storage (adaptado a nuestro stack)

LMCache: GPU (0.01ms) -> CPU (0.1ms) -> Disk (1ms) -> S3/Redis (50ms)
Nuestro stack completo:
```
Tier 0: LMCache KV     (<0.01ms) — KV tensors en GPU VRAM (engine-level)
Tier 1: In-memory dict  (<0.1ms)  — embeddings, metric freshness, tools list
Tier 2: Redis            (<5ms)    — query classification, chat history, MCP results
Tier 3: pgvector/PG     (<50ms)   — LLM semantic cache, respuestas historicas
Tier 4: GCS/S3          (<200ms)  — extraction cache, documentos grandes
```

**Accion**: Clasificar cada cache en el tier correcto segun latencia vs persistencia.

### 5.8 Stale-While-Revalidate (ya implementado parcialmente)

LMCache usa async refresh de cache entries. Nosotros ya lo implementamos en:
- `bank_analytics_client.py:_schedule_tools_cache_refresh()` — retorna stale, refresca async
- **Accion**: Extender SWR al LLM semantic cache y query classification.

### 5.9 System Prompt Determinism (critico para LMCache)

LMCache reutiliza KV para **prefijos exactos**. Si el system prompt varia entre requests (timestamps, datos volatiles), se pierde el beneficio.

**Accion**: Auditar `SystemPromptBuilder.build()` para asegurar output deterministico:
- Verificar que NO inyecta `datetime.now()` o timestamps
- Verificar que datos bancarios inyectados son estables entre requests
- Si hay componentes volatiles, moverlos al final del prompt (despues del prefijo estable)

### 5.10 Conclusion

| Aspecto | Decision |
|---------|----------|
| LMCache aplica a Saptiva | **SI** — self-hosted, modelos open source |
| Implementar en esta app | **NO** — se instala en los servidores de inferencia |
| Scope de este ticket | Recomendacion documentada para equipo infra |
| LLM semantic cache (pgvector) | **SI** — app-level, implementar en Fase 3 |
| Complementariedad | LMCache (engine) + Semantic Cache (app) = maximo ahorro |
| Auditar SystemPromptBuilder | **SI** — beneficia tanto semantic cache como futuro LMCache |
| Impacto estimado LMCache | 3-10x TTFT (cuando infra lo implemente) |
