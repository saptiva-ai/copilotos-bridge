# Research: Semantic Intent Router

## Existing Services Analysis

### EmbeddingService (`src/services/embedding_service.py`)

**Model:** `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensions)

**Key Methods:**
- `encode_single_async(text, use_cache=True)` - Single text embedding with LRU cache
- `encode_async(texts, batch_size=32)` - Batch encoding
- `get_embedding_service()` - Singleton access

**Architecture:**
- Delegates to `embedding-service` plugin via gRPC
- Falls back to HTTP if gRPC unavailable
- Internal LRU cache for query embeddings (1000 entries default)

**Latency:**
- gRPC: ~10-20ms
- HTTP fallback: ~50-100ms
- Cached: <1ms

### RedisCache (`src/core/redis_cache.py`)

**Available Methods:**
- `get(key)` / `set(key, value, expire)` / `setex(key, ttl, value)`
- `lpush(key, value)` / `ltrim(key, start, stop)` / `lrange(key, start, stop)`
- `exists(key)`

**Access:** `get_redis_cache()` async function

### Current BankAdvisorPreCheckService

**Location:** `src/services/streaming/bank_advisor_precheck.py`

**Current Issues:**
1. Uses hardcoded `KNOWLEDGE_TRIGGERS` list
2. Uses regex patterns for greetings/acknowledgments
3. No semantic understanding (typos fail)
4. No context awareness
5. No feedback learning

## Semantic Similarity Approach

### Why Semantic Similarity?

| Approach | Pros | Cons |
|----------|------|------|
| Regex | Fast, predictable | Fragile, no typo handling |
| Keyword lists | Simple | Manual maintenance, no variations |
| **Semantic similarity** | Handles typos, variations | Requires embeddings |
| LLM classification | Most accurate | Slow, expensive |

### Cosine Similarity Formula

```
similarity = (A · B) / (||A|| × ||B||)
```

For normalized vectors (which MiniLM produces):
```
similarity = A · B  (just dot product)
```

### Category Exemplar Strategy

Instead of rules, we define "semantic anchors" - representative examples:

```python
GREETINGS = ["hola", "buenos días", "qué tal", ...]
DATA_QUERIES = ["dame el IMOR de BBVA", "top bancos por morosidad", ...]
```

A new message is classified by finding which category's exemplars it's most similar to.

## Feedback Learning

### Implicit Feedback Signals

| Event | Signal | Action |
|-------|--------|--------|
| Bank-advisor returns chart | Positive | Correct routing |
| Bank-advisor returns None | Negative | Mark as non-banking |

### Redis Storage Schema

```
intent_feedback:log      -> List of {message_hash, success, timestamp}
intent_negative:{hash}   -> "1" with TTL (known non-banking)
```

## Performance Considerations

### Embedding Cache Strategy

1. **Query-level cache** (EmbeddingService built-in)
   - LRU cache with 1000 entries
   - Normalized text as key

2. **Category embedding pre-computation**
   - Compute once at startup
   - Store as numpy arrays in memory

3. **Redis negative cache**
   - Fast check before semantic scoring
   - TTL-based expiration (24h)

### Expected Latency Breakdown

| Step | Time |
|------|------|
| Redis negative check | <1ms |
| Embedding (cached) | <1ms |
| Embedding (uncached) | 10-20ms |
| Cosine similarity | <1ms |
| **Total (cached)** | **<5ms** |
| **Total (uncached)** | **<25ms** |

## References

- [Sentence-Transformers Documentation](https://www.sbert.net/)
- [paraphrase-multilingual-MiniLM-L12-v2](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)
- Project embedding service: `src/services/embedding_service.py`
- Project Redis cache: `src/core/redis_cache.py`
