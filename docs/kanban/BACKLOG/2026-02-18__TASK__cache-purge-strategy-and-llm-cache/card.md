# TASK: Cache Purge Strategy & LLM Semantic Cache

**Created**: 2026-02-18
**Priority**: P1
**Status**: BACKLOG
**Type**: TASK (architecture + implementation)

## Objetivo

Disenar una estrategia inteligente de invalidacion/purga de cache Redis por versionado, por key, por evento, y por tiempo. Evaluar que caches invalidar en cada trigger (24hr, 15 dias, deploy, data ingest). Implementar LLM semantic cache para mejorar la ventana de contexto y memoria del chat. Evaluar e integrar LMCache en el engine de inferencia Saptiva (self-hosted, modelos open source) para KV cache reuse y reduccion de TTFT.

## Estado Actual — 9 Capas de Cache

### 1. Redis Core (`core/redis_cache.py`)
| Cache | TTL | Key Format | Invalidacion |
|-------|-----|-----------|--------------|
| Chat history | 5 min | `cache:chat_history:{chat_id}:{hash}` | Por chat_id (KEYS pattern) |
| Research tasks | 10 min | `cache:research_tasks:{session_id}:{hash}` | Por session_id (KEYS pattern) |
| Session list | 2 min | `cache:session_list:*` | N/A |

### 2. MCP Tool Cache (`services/mcp_cache.py`)
| Tool | TTL | Key Format |
|------|-----|-----------|
| audit_file | 1 hr | `mcp:tool:audit_file:{doc_id}:{hash}` |
| excel_analyzer | 30 min | `mcp:tool:excel_analyzer:{doc_id}:{hash}` |
| deep_research | 24 hr | `mcp:tool:deep_research:{doc_id}:{hash}` |
| extract_document_text | 1 hr | `mcp:tool:extract_document_text:{doc_id}:{hash}` |

Tiene: warmup batch, invalidation por doc_id, por tool, por pattern (SCAN).

### 3. Extraction Cache (`extractors/cache.py`)
| Cache | TTL | Key Format | Compresion |
|-------|-----|-----------|------------|
| PDF/Image text | 24 hr | `extract:{provider}:{media_type}:{sha256}` | zstd (>1KB) |

Content-addressed (SHA-256). Inmutable por naturaleza.

### 4. Token Blacklist (`cache_service.py`)
| Cache | TTL | Key Format |
|-------|-----|-----------|
| JWT blacklist | `exat` (token expiry) | `blacklist:{jti}` |

Auto-expira con el token. No requiere purga.

### 5. Upload Idempotency (`idempotency.py`)
| Cache | TTL | Key Format |
|-------|-----|-----------|
| Upload dedup | 1 hr | `upload-idk:{user_id}:{key}` |

### 6. Bank Query Classification (`bank_analytics_client.py`)
| Cache | TTL | Key Format |
|-------|-----|-----------|
| Keyword/regex result | 1 hr | `bank_query_classification:v5:{msg_hash}` |
| LLM classification | 2 hr | `bank_query_classification:v5:{msg_hash}` |

Unico cache con versionado en el key (`v5`). Bump manual al cambiar logica.

### 7. In-Memory Caches (NO Redis)
| Cache | Ubicacion | Tamano Max | Eviction |
|-------|-----------|-----------|----------|
| Embedding vectors | `embedding_service.py` | 1000 entries | LRU (oldest-first) |
| Query spec parser | `query_spec_parser.py` | 200 entries | Clear-all |
| Metric freshness | `metric_freshness_service.py` | Unbounded | TTL 1hr (time-check) |
| Bank advisor tools | `bank_analytics_client.py` | 1 list | TTL 600s, stale-while-revalidate |

### 8. Rate Limiter (`middleware/rate_limit.py`)
- Storage: `memory://` (in-process, no Redis)
- Limite: 1000/hr
- No persiste entre restarts

### 9. HTTP Cache-Control (`middleware/cache_control.py`)
- `no-store, no-cache` en todas las rutas `/api/*`

## Problemas Detectados

1. **Sin invalidacion coordinada en deploy** — No hay mecanismo para flush post-deploy
2. **Sin invalidacion por data ingest** — Cuando se cargan nuevos datos (ETL), los caches de MVs, metric freshness, clasificacion, etc. no se invalidan
3. **KEYS blocking** — `invalidate_chat_history()` usa `KEYS` que bloquea Redis O(N) en keyspaces grandes
4. **Rate limiter volatil** — `memory://` no sobrevive restarts ni se comparte entre instancias
5. **Sin LLM response cache** — Preguntas identicas o similares re-ejecutan todo el pipeline LLM
6. **Sin versionado consistente** — Solo `bank_query_classification:v5` usa version prefix
7. **TTLs no documentados** — TTLs van de 2 min a 24 hr sin estrategia clara
8. **In-memory caches sin limites** — `metric_freshness` es unbounded; `query_spec_parser` hace clear-all al llegar al limite

## Acceptance Criteria

- [ ] Documento de estrategia de cache con TTLs justificados por tipo
- [ ] Matriz de invalidacion: trigger (deploy/ETL/24hr/15d) x cache layer
- [ ] Implementar invalidacion por deploy (version prefix o flush)
- [ ] Implementar invalidacion por ETL data ingest (evento Pub/Sub o hook)
- [ ] Reemplazar KEYS por SCAN en invalidaciones de patron
- [ ] Implementar LLM semantic cache (embedding-based similarity)
- [ ] Rate limiter migrado a Redis storage
- [ ] Auditar determinismo de SystemPromptBuilder (beneficia semantic cache + futuro LMCache)
- [ ] Tests unitarios para cada estrategia de invalidacion

### Futuro (infra Saptiva — fuera de scope)
- [ ] Evaluar e integrar LMCache en engine Saptiva (requiere acceso a servidores de inferencia)
