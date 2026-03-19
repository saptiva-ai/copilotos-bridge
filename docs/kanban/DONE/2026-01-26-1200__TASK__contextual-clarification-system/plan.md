# Plan de Implementación: Sistema de Clarificación Contextual (v2)

## Resumen Ejecutivo

Este plan implementa clarificación contextual **reutilizando la infraestructura existente** de embeddings, SemanticIntentScorer y Weaviate en lugar de crear módulos nuevos.

**Esfuerzo estimado**: 3 fases, ~1-2 días de desarrollo
**Riesgo**: Bajo (extiende servicios existentes)
**Dependencias**: Ninguna externa

---

## Principios de Diseño

1. **No reinventar la rueda**: Usar SemanticIntentScorer, WeaviateOntologyService, EmbeddingService
2. **Backend hace el trabajo pesado**: El plugin solo consume contexto enriquecido
3. **Cero archivos nuevos**: Extender servicios existentes
4. **Aprovechar cache**: EmbeddingService ya cachea 1000 queries

---

## Arquitectura Propuesta

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              BACKEND                                     │
│                                                                          │
│  User Message ──┬──> SemanticIntentScorer.score()                       │
│                 │         └─> FOLLOW_UP confidence                       │
│                 │                                                        │
│                 ├──> EmbeddingService.encode_single_async()             │
│                 │         └─> Similarity with last_metric                │
│                 │                                                        │
│                 └──> ConversationContext (existing)                      │
│                           └─> last_banks, last_metric, has_chart         │
│                                                                          │
│  ══════════════════════════════════════════════════════════════════════ │
│                                                                          │
│  EnrichedContext = {                                                     │
│      last_banks, last_metric, has_chart,     // existente               │
│      is_followup: bool,                       // NUEVO: del scorer       │
│      followup_confidence: float,              // NUEVO: confianza        │
│      context_similarity: float,               // NUEVO: similaridad      │
│  }                                                                       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              PLUGIN                                      │
│                                                                          │
│  EnrichedContext ──> ClarificationService.determine_strategy()          │
│                           │                                              │
│                           ├─> Si is_followup + last_banks → inferir     │
│                           ├─> Si ambiguous → WeaviateOntology.resolve() │
│                           └─> Else → lógica existente                   │
│                                                                          │
│  WeaviateOntologyService.resolve_ambiguous_term()                       │
│       └─> Usa OntologyTerm.category para desambiguar                    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Enriquecer Contexto en Backend

### Objetivo
Agregar señales semánticas al contexto usando servicios existentes.

### 1.1 Crear función de enriquecimiento

**Archivo**: `apps/backend/src/services/intent/context_enricher.py` (NUEVO, ~80 líneas)

```python
"""
Context Enricher - Adds semantic signals to conversation context.

Uses existing services:
- SemanticIntentScorer: Detect follow-up intent
- EmbeddingService: Compute query-context similarity
"""

from dataclasses import dataclass
from typing import Optional, List
import numpy as np
import structlog

from .semantic_scorer import SemanticIntentScorer
from .types import IntentCategory
from ..embedding_service import get_embedding_service

logger = structlog.get_logger(__name__)


@dataclass
class EnrichedContext:
    """Contexto enriquecido con señales semánticas."""
    # Campos existentes (de ConversationContext)
    last_banks: List[str]
    last_metric: Optional[str]
    has_recent_chart: bool
    turn_count: int

    # Campos nuevos
    is_followup: bool = False
    followup_confidence: float = 0.0
    context_similarity: float = 0.0
    inferred_category: Optional[str] = None


async def enrich_context(
    message: str,
    last_banks: List[str],
    last_metric: Optional[str],
    has_recent_chart: bool,
    turn_count: int
) -> EnrichedContext:
    """
    Enriquece el contexto con señales semánticas.

    Args:
        message: Mensaje actual del usuario
        last_banks: Bancos del mensaje anterior
        last_metric: Métrica del mensaje anterior
        has_recent_chart: Si hay gráfica reciente
        turn_count: Número de turnos en la conversación

    Returns:
        EnrichedContext con señales de follow-up y similaridad
    """
    enriched = EnrichedContext(
        last_banks=last_banks,
        last_metric=last_metric,
        has_recent_chart=has_recent_chart,
        turn_count=turn_count,
    )

    # Solo enriquecer si hay contexto previo
    if not has_recent_chart and not last_metric:
        return enriched

    try:
        # 1. Detectar follow-up usando SemanticIntentScorer
        scorer = await SemanticIntentScorer.get_instance()
        scores = await scorer.score(message)

        followup_score = scores.scores.get(IntentCategory.FOLLOW_UP, 0.0)
        enriched.is_followup = followup_score > 0.5 or (
            scores.top_intent == IntentCategory.FOLLOW_UP
        )
        enriched.followup_confidence = followup_score

        # 2. Calcular similaridad con contexto (usa cache de embeddings)
        if last_metric:
            embedding_svc = get_embedding_service()

            query_emb = await embedding_svc.encode_single_async(message, use_cache=True)
            context_emb = await embedding_svc.encode_single_async(last_metric, use_cache=True)

            # Cosine similarity
            query_arr = np.array(query_emb)
            context_arr = np.array(context_emb)

            norm_product = np.linalg.norm(query_arr) * np.linalg.norm(context_arr)
            if norm_product > 0:
                enriched.context_similarity = float(
                    np.dot(query_arr, context_arr) / norm_product
                )

        logger.info(
            "context_enriched",
            is_followup=enriched.is_followup,
            followup_confidence=f"{enriched.followup_confidence:.2f}",
            context_similarity=f"{enriched.context_similarity:.2f}",
            has_chart=has_recent_chart,
        )

    except Exception as e:
        logger.warning("context_enrichment_failed", error=str(e))

    return enriched
```

### 1.2 Integrar en bank_advisor_precheck

**Archivo**: `apps/backend/src/services/streaming/bank_advisor_precheck.py`

```python
# Agregar import
from ..intent.context_enricher import enrich_context, EnrichedContext

# En la función precheck_and_route(), después de extract_context():

async def precheck_and_route(...):
    # ... código existente ...

    # Extraer contexto básico (ya existe)
    context = ContextEnhancer.extract_context(recent_messages, memory_context)

    # NUEVO: Enriquecer con señales semánticas
    enriched = await enrich_context(
        message=message,
        last_banks=context.last_banks,
        last_metric=context.last_metric,
        has_recent_chart=context.has_recent_chart,
        turn_count=context.turn_count,
    )

    # NUEVO: Pasar contexto enriquecido al plugin
    plugin_request = {
        "query": message,
        "conversation_id": conversation_id,
        "context": {
            "last_banks": enriched.last_banks,
            "last_metric": enriched.last_metric,
            "has_recent_chart": enriched.has_recent_chart,
            "is_followup": enriched.is_followup,
            "followup_confidence": enriched.followup_confidence,
            "context_similarity": enriched.context_similarity,
        },
        # ... resto del request ...
    }
```

### Validación Phase 1

```bash
# Test unitario
make test T=api TEST_ARGS="-k test_context_enricher"

# Verificar logs
docker compose logs backend | grep "context_enriched"
```

---

## Phase 2: Extender WeaviateOntologyService para Desambiguación

### Objetivo
Agregar método para resolver términos ambiguos usando la categoría del contexto.

### 2.1 Agregar método de resolución

**Archivo**: `plugins/bank-advisor-private/src/bankadvisor/services/weaviate_ontology_service.py`

Agregar después de `get_all_synonyms()` (~línea 556):

```python
async def resolve_ambiguous_term(
    self,
    term: str,
    context_metric: Optional[str] = None,
    min_similarity: float = 0.65
) -> Optional[Tuple[str, str]]:
    """
    Resuelve un término ambiguo usando el contexto.

    Estrategia:
    1. Buscar candidatos en Weaviate
    2. Si hay 1 candidato → no hay ambigüedad
    3. Si hay múltiples → usar categoría del context_metric para elegir

    Args:
        term: Término ambiguo (ej: "capitalización")
        context_metric: Métrica del contexto (ej: "IMOR") para inferir categoría
        min_similarity: Umbral mínimo de similaridad

    Returns:
        Tuple (linked_field, category) si se resuelve, None si no

    Examples:
        # Contexto regulatorio (IMOR)
        >>> resolve_ambiguous_term("capitalización", context_metric="IMOR")
        ("ICAP", "capital")

        # Sin contexto
        >>> resolve_ambiguous_term("capitalización", context_metric=None)
        None  # Ambigüedad no resuelta
    """
    logger.info(
        "weaviate_ontology.resolve_ambiguous",
        term=term,
        context_metric=context_metric
    )

    # 1. Buscar candidatos para el término ambiguo
    candidates = await self.search_terms(
        term,
        top_k=5,
        min_similarity=min_similarity,
        exclude_conceptual=True
    )

    if not candidates:
        logger.debug("weaviate_ontology.no_candidates", term=term)
        return None

    # 2. Si solo hay un candidato, no hay ambigüedad
    if len(candidates) == 1:
        result = (candidates[0].linked_field, candidates[0].category)
        logger.info(
            "weaviate_ontology.single_candidate",
            term=term,
            resolved_to=result[0]
        )
        return result

    # 3. Múltiples candidatos - intentar resolver con contexto
    if not context_metric:
        logger.info(
            "weaviate_ontology.ambiguous_no_context",
            term=term,
            candidates=[c.linked_field for c in candidates]
        )
        return None  # No podemos resolver sin contexto

    # 4. Obtener categoría del contexto
    context_terms = await self.search_terms(
        context_metric,
        top_k=1,
        min_similarity=0.8
    )

    if not context_terms:
        logger.debug(
            "weaviate_ontology.context_metric_not_found",
            context_metric=context_metric
        )
        return None

    context_category = context_terms[0].category

    # 5. Seleccionar candidato de la misma categoría
    for candidate in candidates:
        if candidate.category == context_category:
            result = (candidate.linked_field, candidate.category)
            logger.info(
                "weaviate_ontology.resolved_by_category",
                term=term,
                resolved_to=result[0],
                category=context_category
            )
            return result

    # 6. No hay candidato de la misma categoría
    logger.info(
        "weaviate_ontology.category_mismatch",
        term=term,
        context_category=context_category,
        candidate_categories=[c.category for c in candidates]
    )
    return None


async def get_term_category(self, metric: str) -> Optional[str]:
    """
    Obtiene la categoría de una métrica.

    Útil para determinar el dominio semántico del contexto.

    Args:
        metric: Nombre de métrica (ej: "IMOR", "ICAP")

    Returns:
        Categoría (ej: "riesgo", "capital") o None
    """
    terms = await self.search_terms(metric, top_k=1, min_similarity=0.85)
    if terms:
        return terms[0].category
    return None
```

### 2.2 Mapeo de categorías a dominio

Las categorías en `Ontology_Term_V2` ya definen el dominio:

| Categoría | Dominio Implícito | Métricas Típicas |
|-----------|------------------|------------------|
| `riesgo` | Regulatory | IMOR, ICOR, TDA |
| `capital` | Regulatory | ICAP, CAPITAL_NETO |
| `cartera` | Credit Risk | CARTERA_*, QUEBRANTOS |
| `mercado` | Market | MARKET_CAP, MARKET_SHARE |
| `rentabilidad` | Regulatory | ROE, ROA |

### Validación Phase 2

```python
# tests/unit/test_weaviate_ontology_disambiguation.py

@pytest.mark.asyncio
async def test_resolve_capitalizacion_with_imor_context():
    """En contexto de IMOR (riesgo), capitalización → ICAP."""
    service = WeaviateOntologyService()

    result = await service.resolve_ambiguous_term(
        term="capitalización",
        context_metric="IMOR"
    )

    assert result is not None
    assert result[0] == "ICAP"  # linked_field
    assert result[1] == "capital"  # category

@pytest.mark.asyncio
async def test_resolve_capitalizacion_no_context():
    """Sin contexto, capitalización es ambiguo."""
    service = WeaviateOntologyService()

    result = await service.resolve_ambiguous_term(
        term="capitalización",
        context_metric=None
    )

    assert result is None  # No se puede resolver
```

---

## Phase 3: Actualizar ClarificationService

### Objetivo
Usar el contexto enriquecido para inferir campos y resolver ambigüedades.

### 3.1 Modificar determine_strategy

**Archivo**: `plugins/bank-advisor-private/src/bankadvisor/services/clarification_service.py`

```python
from typing import Dict, Any

# Agregar dataclass para contexto
@dataclass
class PluginContext:
    """Contexto enriquecido recibido del backend."""
    last_banks: List[str] = field(default_factory=list)
    last_metric: Optional[str] = None
    has_recent_chart: bool = False
    is_followup: bool = False
    followup_confidence: float = 0.0
    context_similarity: float = 0.0

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "PluginContext":
        if not data:
            return cls()
        return cls(
            last_banks=data.get("last_banks", []),
            last_metric=data.get("last_metric"),
            has_recent_chart=data.get("has_recent_chart", False),
            is_followup=data.get("is_followup", False),
            followup_confidence=data.get("followup_confidence", 0.0),
            context_similarity=data.get("context_similarity", 0.0),
        )


class ClarificationService:

    def __init__(self, weaviate_ontology: Optional[WeaviateOntologyService] = None):
        self.ontology = weaviate_ontology
        logger.info("clarification_service.initialized")

    def determine_strategy(
        self,
        spec: QuerySpec,
        context: Optional[PluginContext] = None
    ) -> Tuple[ClarificationStrategy, str]:
        """
        Determina estrategia de clarificación usando contexto enriquecido.

        Orden de prioridad:
        1. Query completo → NONE
        2. Follow-up + contexto → Inferir campos
        3. Ambigüedad + contexto → Resolver con Weaviate
        4. Falta información → HARD_ASK
        """
        has_metric = bool(spec.metric)
        has_bank = bool(spec.bank_names)
        has_confidence = spec.confidence_score >= 0.7

        # ═══════════════════════════════════════════════════════════════
        # NUEVO: Inferencia desde contexto enriquecido
        # ═══════════════════════════════════════════════════════════════

        if context:
            # Caso 1: Follow-up detectado por embeddings + tenemos bancos en contexto
            if self._should_infer_from_context(spec, context):
                if not has_bank and context.last_banks:
                    spec.bank_names = context.last_banks.copy()
                    spec.inferred_from_context = True
                    has_bank = True
                    logger.info(
                        "clarification.inferred_bank_from_context",
                        banks=spec.bank_names,
                        followup_confidence=context.followup_confidence,
                        similarity=context.context_similarity
                    )

        # ═══════════════════════════════════════════════════════════════
        # Lógica existente (sin cambios)
        # ═══════════════════════════════════════════════════════════════

        metric_is_ambiguous = spec.metric.lower() in AMBIGUOUS_METRICS if spec.metric else False

        # NONE: Query completo
        if has_metric and has_bank and has_confidence and not metric_is_ambiguous:
            return ClarificationStrategy.NONE, "Query complete"

        # NONE: Ranking no necesita banco
        if has_metric and spec.intent == "ranking" and has_confidence:
            return ClarificationStrategy.NONE, "Ranking query - bank not required"

        # ═══════════════════════════════════════════════════════════════
        # NUEVO: Resolver ambigüedad con Weaviate antes de HARD_ASK
        # ═══════════════════════════════════════════════════════════════

        if metric_is_ambiguous and context and self.ontology:
            resolved = self._try_resolve_ambiguity(spec.metric, context)
            if resolved:
                spec.metric = resolved
                metric_is_ambiguous = False
                logger.info(
                    "clarification.ambiguity_resolved",
                    original=spec.metric,
                    resolved_to=resolved
                )

        # HARD_ASK: Tiene métrica pero falta banco
        if has_metric and not has_bank and spec.intent not in NO_BANK_REQUIRED_INTENTS:
            return ClarificationStrategy.HARD_ASK, "Bank required for this query"

        # SOFT_ASK: Métrica ambigua no resuelta
        if metric_is_ambiguous:
            return ClarificationStrategy.SOFT_ASK, f"Metric '{spec.metric}' is ambiguous"

        # SOFT_ASK: Banco pero sin métrica
        if has_bank and not has_metric:
            return ClarificationStrategy.SOFT_ASK, "Bank specified but no metric"

        # HARD_ASK: Nada identificable
        if not has_metric and not has_bank:
            return ClarificationStrategy.HARD_ASK, "No metric or bank identified"

        return ClarificationStrategy.SOFT_ASK, "Partial information"

    def _should_infer_from_context(
        self,
        spec: QuerySpec,
        context: PluginContext
    ) -> bool:
        """
        Determina si debemos inferir campos desde el contexto.

        Condiciones (todas deben cumplirse):
        1. Hay chart reciente
        2. Es follow-up (detectado por embeddings) O alta similaridad
        3. Contexto tiene datos útiles
        """
        if not context.has_recent_chart:
            return False

        # Follow-up detectado por SemanticIntentScorer
        if context.is_followup and context.followup_confidence > 0.5:
            return True

        # Alta similaridad semántica con el contexto
        if context.context_similarity > 0.65:
            return True

        # Mensaje muy corto después de chart (heurística simple como fallback)
        query = getattr(spec, '_original_query', '')
        if len(query.split()) <= 5 and context.has_recent_chart:
            return True

        return False

    def _try_resolve_ambiguity(
        self,
        ambiguous_metric: str,
        context: PluginContext
    ) -> Optional[str]:
        """
        Intenta resolver ambigüedad usando WeaviateOntologyService.

        Usa la categoría del last_metric para desambiguar.
        """
        if not self.ontology or not context.last_metric:
            return None

        import asyncio

        try:
            # Llamar al método de resolución de Weaviate
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(
                self.ontology.resolve_ambiguous_term(
                    term=ambiguous_metric,
                    context_metric=context.last_metric
                )
            )

            if result:
                return result[0]  # linked_field

        except Exception as e:
            logger.warning(
                "clarification.ambiguity_resolution_failed",
                error=str(e)
            )

        return None
```

### 3.2 Actualizar opciones contextuales

```python
def _get_options_for_field(
    self,
    field: str,
    context: Optional[PluginContext] = None
) -> List[Dict[str, str]]:
    """Genera opciones priorizando el contexto."""

    if field == "bank" and context and context.last_banks:
        # Priorizar bancos del contexto
        contextual = [
            {"label": f"{b} (anterior)", "value": b, "contextual": True}
            for b in context.last_banks[:2]
        ]

        existing = {opt["value"] for opt in contextual}
        others = [b for b in self.TOP_BANKS if b["value"] not in existing]

        return contextual + others[:3]

    # Fallback a opciones estáticas
    if field == "metric":
        return self.TOP_METRICS
    if field == "bank":
        return self.TOP_BANKS
    if field == "period":
        return self.TOP_PERIODS

    return []
```

### Validación Phase 3

```python
# tests/unit/clarification/test_contextual_clarification.py

def test_infer_bank_when_followup():
    """Follow-up debe inferir banco del contexto."""
    spec = QuerySpec(metric="CARTERA_TOTAL", bank_names=[])
    context = PluginContext(
        last_banks=["BBVA"],
        has_recent_chart=True,
        is_followup=True,
        followup_confidence=0.75
    )

    service = ClarificationService()
    strategy, reason = service.determine_strategy(spec, context)

    assert spec.bank_names == ["BBVA"]
    assert spec.inferred_from_context is True
    assert strategy == ClarificationStrategy.NONE

def test_resolve_ambiguity_with_context():
    """Ambigüedad debe resolverse usando categoría del contexto."""
    spec = QuerySpec(metric="capitalización", bank_names=["INVEX"])
    context = PluginContext(
        last_metric="IMOR",  # Categoría: riesgo
        has_recent_chart=True
    )

    ontology = WeaviateOntologyService()
    service = ClarificationService(weaviate_ontology=ontology)
    strategy, reason = service.determine_strategy(spec, context)

    assert spec.metric == "ICAP"  # Resuelto a ICAP por categoría
    assert strategy == ClarificationStrategy.NONE
```

---

## Tests E2E

```python
# tests/e2e/clarification/test_contextual_flow.py

@pytest.mark.asyncio
async def test_followup_without_bank_uses_context(client):
    """
    E2E: "IMOR de BBVA" → "¿y la cartera?"
    Debe mostrar cartera de BBVA sin pedir clarificación.
    """
    # 1. Establecer contexto
    r1 = await client.post("/chat", json={"message": "IMOR de BBVA"})
    assert "chart" in r1.json()

    # 2. Follow-up sin banco
    r2 = await client.post("/chat", json={"message": "¿y la cartera?"})
    data = r2.json()

    assert data.get("type") != "clarification"
    assert "BBVA" in str(data)

@pytest.mark.asyncio
async def test_capitalizacion_resolved_by_context(client):
    """
    E2E: "ICAP de INVEX" → "¿capitalización?"
    Debe resolver a ICAP por contexto regulatorio.
    """
    # 1. Establecer contexto regulatorio
    await client.post("/chat", json={"message": "ICAP de INVEX"})

    # 2. Término ambiguo
    r2 = await client.post("/chat", json={"message": "¿cómo está su capitalización?"})
    data = r2.json()

    assert data.get("type") != "clarification"
    # Debe haber usado ICAP, no MARKET_CAP
```

---

## Resumen de Cambios

| Archivo | Cambio | Líneas |
|---------|--------|--------|
| `apps/backend/src/services/intent/context_enricher.py` | NUEVO: enrich_context() | ~80 |
| `apps/backend/src/services/streaming/bank_advisor_precheck.py` | Integrar enricher | ~15 |
| `plugins/.../services/weaviate_ontology_service.py` | resolve_ambiguous_term() | ~80 |
| `plugins/.../services/clarification_service.py` | Usar contexto enriquecido | ~60 |
| Tests unitarios | 4 nuevos | ~100 |
| Tests E2E | 2 nuevos | ~50 |
| **Total** | | **~385** |

**Comparación con plan original**:
- Plan original: ~400 líneas + 1 archivo nuevo (`semantic_domain.py`)
- Plan revisado: ~385 líneas, 1 archivo nuevo pero reutiliza infraestructura

---

## Rollback Plan

```python
# Feature flag en envs/.env
CLARIFICATION_USE_CONTEXT=false

# En clarification_service.py
def determine_strategy(self, spec, context=None):
    if not config.CLARIFICATION_USE_CONTEXT:
        context = None  # Ignorar contexto, usar lógica original
    # ... resto del código
```

---

## Checklist de Validación

### Funcionalidad
- [ ] Follow-up sin banco usa last_banks
- [ ] "capitalización" + contexto IMOR → ICAP
- [ ] "capitalización" sin contexto → HARD_ASK
- [ ] Opciones priorizan bancos del contexto

### Performance
- [ ] Latencia < 50ms adicional (embeddings en cache)
- [ ] Cache hit rate > 80% para queries similares

### Observabilidad
- [ ] Log "context_enriched" en backend
- [ ] Log "clarification.inferred_bank_from_context"
- [ ] Log "clarification.ambiguity_resolved"

### Regresión
- [ ] Tests existentes de clarificación pasan
- [ ] Happy path sin cambios
