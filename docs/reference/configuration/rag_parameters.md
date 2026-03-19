# RAG Configuration Guide

## Overview

This document explains the RAG (Retrieval-Augmented Generation) configuration for the Capital 414 platform, including chunking strategies, semantic search tuning, and optimization recommendations.

## Architecture

```
PDF Upload → Text Extraction → Chunking → Embedding → Qdrant Storage
                                                           ↓
User Query → Embedding → Semantic Search → Top-k Results → LLM Context
```

## Configuration Parameters

### 1. Chunking Configuration

Located in `envs/.env`:

```bash
# Chunk size in tokens (GPT-style: 1 token ≈ 4 chars)
CHUNK_SIZE_TOKENS=500

# Overlap between chunks (prevents context loss at boundaries)
CHUNK_OVERLAP_TOKENS=100
```

**Rationale:**
- **500 tokens** (~2000 chars) provides optimal balance between:
  - **Context**: Enough information for meaningful semantic search
  - **Granularity**: Precise enough to avoid irrelevant content
  - **Performance**: Fits comfortably within LLM context windows

- **100 tokens overlap** (20%) prevents information loss at chunk boundaries:
  - Industry best practice (15-25% overlap)
  - Ensures questions spanning boundaries find relevant content
  - Minimal redundancy while maintaining semantic coherence

### 2. Embedding Model

```bash
EMBEDDING_MODEL_NAME=paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_DEVICE=cpu
```

**Model Characteristics:**
- **Dimension**: 384 (compact, fast)
- **Languages**: 50+ including Spanish and English
- **Performance**: ~50ms per chunk on CPU
- **Memory**: ~120 MB loaded
- **Quality**: Production-grade for corporate documents

**Alternative Models:**
- `multilingual-e5-large`: 1024-dim, slower, better quality
- `all-MiniLM-L6-v2`: 384-dim, English-only, faster

### 3. Semantic Search Tuning

```bash
# Minimum cosine similarity threshold
RAG_SIMILARITY_THRESHOLD=0.7

# Maximum chunks to retrieve per query
RAG_MAX_CHUNKS_PER_QUERY=2

# Enable semantic search (vs keyword matching)
RAG_SEMANTIC_SEARCH_ENABLED=true
```

**Similarity Threshold Guidelines:**
- **0.9+**: Near-identical content (very restrictive)
- **0.7-0.8**: High relevance (recommended for production)
- **0.5-0.6**: Medium relevance (exploratory queries)
- **0.3-0.4**: Low relevance (may include tangential content)
- **< 0.3**: Too permissive (likely irrelevant results)

**Max Chunks Per Query:**
- **2 chunks**: ~1000 tokens of context (current setting)
- **3 chunks**: ~1500 tokens (good for complex queries)
- **5+ chunks**: Risk of exceeding LLM context window

## Performance Characteristics

Based on analysis of Capital 414 documents:

```
Total chunks: 33
Documents: 3
Avg chunks/doc: 11.0

Chunk size stats:
   Avg length: 1880 chars (~470 tokens)
   Min length: 707 chars (~176 tokens)
   Max length: 1999 chars (~499 tokens)
```

**Key Insights:**
- ✅ Avg chunk utilization: 94% (470/500 tokens) - excellent
- ✅ Overlap ratio: 20% - industry best practice
- ✅ Chunks per document: 11 - good granularity for 16-page PDFs
- ✅ No chunks exceed token limit (max 499 < 500)

## Optimization Workflow

### 1. Run Analysis

```bash
python scripts/analyze-chunk-optimization.py
```

This script analyzes existing chunks in Qdrant and provides recommendations.

### 2. Adjust Parameters (if needed)

Edit `envs/.env` based on recommendations:

```bash
# For shorter documents (< 5 chunks/doc):
CHUNK_SIZE_TOKENS=400
CHUNK_OVERLAP_TOKENS=80

# For longer documents (> 20 chunks/doc):
CHUNK_SIZE_TOKENS=700
CHUNK_OVERLAP_TOKENS=140

# For technical documents with tables/diagrams:
CHUNK_SIZE_TOKENS=500  # Current optimal setting
CHUNK_OVERLAP_TOKENS=100
```

### 3. Apply Changes

```bash
# Reload environment variables
make reload-env S=api

# Re-upload documents to apply new chunking
make test-rag
```

## Qdrant Collection Schema

```python
{
  "session_id": str,        # Conversation UUID (MANDATORY for isolation)
  "document_id": str,        # MongoDB Document._id
  "chunk_id": int,           # Sequential index within document
  "text": str,               # Original chunk text (for LLM context)
  "page": int,               # Page number in PDF
  "created_at": float,       # Unix timestamp (for TTL cleanup)
  "metadata": {              # Extensible metadata
    "filename": str,
    "content_type": str,
  }
}
```

## Session Management

```bash
# TTL: How long to keep session vectors (hours)
RAG_SESSION_TTL_HOURS=24

# Cleanup interval: How often to run cleanup job (hours)
RAG_CLEANUP_INTERVAL_HOURS=1
```

**Cleanup Strategy:**
- Sessions older than 24 hours are automatically deleted
- Prevents Qdrant storage bloat
- Cleanup runs every hour in background

## Testing & Validation

### Test RAG Ingestion
```bash
make test-rag
```
Validates: PDF → Extract → Chunk → Embed → Qdrant pipeline

### Test Semantic Search
```bash
make test-semantic
```
Validates: Query → Embedding → Qdrant Search → Results

### Analyze Chunk Optimization
```bash
python scripts/analyze-chunk-optimization.py
```
Provides: Statistics + Recommendations

## Troubleshooting

### Issue: Low relevance scores (< 0.5)

**Causes:**
- Query too generic or unrelated to documents
- Chunk size too small (missing context)
- Wrong language model

**Solutions:**
1. Reformulate query with more specific terms
2. Increase `CHUNK_SIZE_TOKENS` to 600-700
3. Lower `RAG_SIMILARITY_THRESHOLD` to 0.5 (temporary)

### Issue: Too many chunks returned

**Causes:**
- `RAG_MAX_CHUNKS_PER_QUERY` too high
- `RAG_SIMILARITY_THRESHOLD` too low

**Solutions:**
1. Decrease `RAG_MAX_CHUNKS_PER_QUERY` to 2
2. Increase `RAG_SIMILARITY_THRESHOLD` to 0.75

### Issue: Missing relevant content

**Causes:**
- Chunk boundaries split important information
- Overlap too small
- Similarity threshold too high

**Solutions:**
1. Increase `CHUNK_OVERLAP_TOKENS` to 150-200
2. Decrease `RAG_SIMILARITY_THRESHOLD` to 0.6
3. Increase `RAG_MAX_CHUNKS_PER_QUERY` to 3

## Best Practices

### For Corporate Documents (Current Use Case)
✅ **CHUNK_SIZE_TOKENS=500** (optimal)
✅ **CHUNK_OVERLAP_TOKENS=100** (20% overlap)
✅ **RAG_SIMILARITY_THRESHOLD=0.7** (high precision)
✅ **RAG_MAX_CHUNKS_PER_QUERY=2** (focused context)

### For Technical Documentation
📘 **CHUNK_SIZE_TOKENS=600** (more technical context)
📘 **CHUNK_OVERLAP_TOKENS=120** (preserve code snippets)
📘 **RAG_SIMILARITY_THRESHOLD=0.65** (slightly more permissive)

### For Narrative/Long-form Content
📖 **CHUNK_SIZE_TOKENS=700** (preserve narrative flow)
📖 **CHUNK_OVERLAP_TOKENS=140** (maintain story continuity)
📖 **RAG_SIMILARITY_THRESHOLD=0.6** (broader semantic matching)

## Monitoring

### Key Metrics to Track

1. **Average chunk utilization**: `avg_tokens / CHUNK_SIZE_TOKENS`
   - Target: 80-95%
   - Too low: Increase chunk size
   - Too high: Risk of truncation

2. **Relevance score distribution**: `avg(similarity_scores)`
   - Target: > 0.7 for most queries
   - Too low: Review chunking or query formulation

3. **Chunks per document**: `total_chunks / total_docs`
   - Target: 10-15 for 10-20 page documents
   - Too many: Increase chunk size
   - Too few: Decrease chunk size

## References

- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Sentence Transformers](https://www.sbert.net/)
- [OpenAI Tokenization](https://platform.openai.com/tokenizer)

## Version History

- **v1.0** (2025-01-20): Initial configuration for Capital 414
  - Chunk size: 500 tokens
  - Overlap: 100 tokens (20%)
  - Semantic search enabled with 0.7 threshold
