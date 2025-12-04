"""
NL2SQL Context Service - RAG-based context retrieval for SQL generation

Retrieves relevant schema, metrics, and examples from Qdrant vector database
to augment SQL generation with domain knowledge.

Architecture:
    QuerySpec → Build search queries → Qdrant retrieval → RagContext

Dependencies:
    - QdrantService (from main backend, injected)
    - EmbeddingService (from main backend, injected)
    - Falls back to hardcoded schema if Qdrant unavailable
"""

from typing import Optional, List, Dict, Any
import structlog

from ..specs import QuerySpec, RagContext
from ..services.analytics_service import AnalyticsService

logger = structlog.get_logger(__name__)


class Nl2SqlContextService:
    """
    Retrieves RAG context for SQL generation from vector database.

    Responsibilities:
    - Ensure RAG collections exist (schema, metrics, examples)
    - Query Qdrant for relevant context given a QuerySpec
    - Build search queries from QuerySpec attributes
    - Populate RagContext with retrieved metadata
    - Fallback to hardcoded schema if RAG unavailable

    Thread-safety: QdrantService and EmbeddingService are thread-safe.
    """

    # Collection names in Qdrant
    COLLECTION_SCHEMA = "bankadvisor_schema"
    COLLECTION_METRICS = "bankadvisor_metrics"
    COLLECTION_EXAMPLES = "bankadvisor_examples"

    def __init__(
        self,
        qdrant_service: Optional[Any] = None,
        embedding_service: Optional[Any] = None,
    ):
        """
        Initialize NL2SQL context service.

        Args:
            qdrant_service: QdrantService instance (injected from main backend)
            embedding_service: EmbeddingService instance (injected from main backend)

        Note:
            If services are None, RAG will be disabled and fallback to
            hardcoded schema from AnalyticsService.SAFE_METRIC_COLUMNS
        """
        self.qdrant = qdrant_service
        self.embedding = embedding_service

        # Flag to track if RAG is available
        self._rag_enabled = (qdrant_service is not None and embedding_service is not None)

        if not self._rag_enabled:
            logger.warning(
                "nl2sql_context.rag_disabled",
                reason="QdrantService or EmbeddingService not provided",
                fallback="Will use hardcoded schema from AnalyticsService"
            )
        else:
            logger.info(
                "nl2sql_context.initialized",
                rag_enabled=True,
                collections=[
                    self.COLLECTION_SCHEMA,
                    self.COLLECTION_METRICS,
                    self.COLLECTION_EXAMPLES
                ]
            )

    def ensure_collections(self) -> None:
        """
        Ensure RAG collections exist in Qdrant.

        Creates collections if they don't exist. This is idempotent.
        Should be called during plugin startup.

        Note:
            Collections must be seeded separately via seed_nl2sql_rag.py script.
            This method only ensures structure exists, not data.

        Raises:
            RuntimeError: If Qdrant is unavailable or collection creation fails
        """
        if not self._rag_enabled:
            logger.debug("nl2sql_context.ensure_collections.skipped", reason="RAG disabled")
            return

        try:
            # Get embedding dimension from service
            embedding_dim = self.embedding.embedding_dim

            # Check existing collections
            existing_collections = [
                c.name for c in self.qdrant.client.get_collections().collections
            ]

            collections_to_create = [
                self.COLLECTION_SCHEMA,
                self.COLLECTION_METRICS,
                self.COLLECTION_EXAMPLES,
            ]

            for collection_name in collections_to_create:
                if collection_name in existing_collections:
                    logger.debug(
                        "nl2sql_context.collection_exists",
                        collection=collection_name
                    )
                else:
                    # Create collection with same config as main RAG collection
                    from qdrant_client.models import Distance, VectorParams

                    self.qdrant.client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=embedding_dim,
                            distance=Distance.COSINE,
                        ),
                    )

                    logger.info(
                        "nl2sql_context.collection_created",
                        collection=collection_name,
                        embedding_dim=embedding_dim,
                        distance="COSINE"
                    )

        except Exception as e:
            logger.error(
                "nl2sql_context.ensure_collections.failed",
                error=str(e),
                exc_info=True
            )
            raise RuntimeError(f"Failed to ensure NL2SQL RAG collections: {e}") from e

    async def rag_context_for_spec(
        self,
        spec: QuerySpec,
        original_query: Optional[str] = None
    ) -> RagContext:
        """
        Retrieve RAG context for a given QuerySpec.

        Args:
            spec: Structured query specification
            original_query: Original NL query (optional, used for example search)

        Returns:
            RagContext populated with:
            - metric_definitions (from COLLECTION_METRICS)
            - schema_snippets (from COLLECTION_SCHEMA)
            - example_queries (from COLLECTION_EXAMPLES)
            - available_columns (from AnalyticsService whitelist)

        Fallback:
            If RAG is disabled or retrieval fails, returns minimal context
            with only available_columns from AnalyticsService.
        """
        logger.info(
            "nl2sql_context.retrieving",
            metric=spec.metric,
            bank_names=spec.bank_names,
            time_range_type=spec.time_range.type,
            rag_enabled=self._rag_enabled
        )

        # Always include available columns from whitelist
        available_columns = list(AnalyticsService.SAFE_METRIC_COLUMNS.keys())

        # If RAG disabled, return minimal context
        if not self._rag_enabled:
            logger.debug("nl2sql_context.fallback", reason="RAG disabled")
            return RagContext(
                metric_definitions=[],
                schema_snippets=[],
                example_queries=[],
                available_columns=available_columns
            )

        try:
            # Build search queries from QuerySpec
            metric_query = self._build_metric_query(spec)
            schema_query = self._build_schema_query(spec)
            example_query = original_query or self._build_example_query(spec)

            # Retrieve from each collection
            metric_defs = await self._search_collection(
                collection=self.COLLECTION_METRICS,
                query_text=metric_query,
                top_k=3,
                score_threshold=0.7
            )

            schema_snippets = await self._search_collection(
                collection=self.COLLECTION_SCHEMA,
                query_text=schema_query,
                top_k=5,
                score_threshold=0.7
            )

            # Search for learned queries first (from feedback loop)
            learned_examples = await self._search_learned_queries(
                query_text=example_query,
                top_k=2,
                score_threshold=0.75
            )

            # Search for static examples
            static_examples = await self._search_collection(
                collection=self.COLLECTION_EXAMPLES,
                query_text=example_query,
                top_k=3,
                score_threshold=0.70  # Slightly lower for static
            )

            # Merge: prioritize learned queries with boost
            examples = self._merge_examples(learned_examples, static_examples, max_total=3)

            logger.info(
                "nl2sql_context.retrieved",
                metric_defs_count=len(metric_defs),
                schema_snippets_count=len(schema_snippets),
                examples_count=len(examples)
            )

            return RagContext(
                metric_definitions=metric_defs,
                schema_snippets=schema_snippets,
                example_queries=examples,
                available_columns=available_columns
            )

        except Exception as e:
            logger.error(
                "nl2sql_context.retrieval_failed",
                error=str(e),
                exc_info=True,
                fallback="Returning minimal context"
            )

            # Fallback to minimal context
            return RagContext(
                metric_definitions=[],
                schema_snippets=[],
                example_queries=[],
                available_columns=available_columns
            )

    async def _search_learned_queries(
        self,
        query_text: str,
        top_k: int = 2,
        score_threshold: float = 0.75
    ) -> List[Dict[str, Any]]:
        """
        Search for learned queries from feedback loop.

        Args:
            query_text: Natural language query
            top_k: Number of results to return
            score_threshold: Minimum similarity score

        Returns:
            List of learned query dicts with metadata
        """
        if not self._rag_enabled:
            return []

        try:
            # Use new collection for learned queries
            results = await self._search_collection(
                collection="bankadvisor_queries",
                query_text=query_text,
                top_k=top_k,
                score_threshold=score_threshold,
                filter_conditions={"type": "learned_query"}
            )

            # Boost learned queries
            for result in results:
                result["source"] = "learned"
                if "score" in result:
                    result["score"] *= 1.2

            logger.debug("nl2sql_context.learned_queries_found", count=len(results))
            return results

        except Exception as e:
            logger.warning("nl2sql_context.learned_search_failed", error=str(e))
            return []

    def _merge_examples(
        self,
        learned: List[Dict[str, Any]],
        static: List[Dict[str, Any]],
        max_total: int = 3
    ) -> List[Dict[str, Any]]:
        """Merge learned and static examples, prioritizing learned queries."""
        all_examples = learned + static
        all_examples.sort(key=lambda x: x.get("score", 0), reverse=True)
        merged = all_examples[:max_total]

        logger.debug(
            "nl2sql_context.examples_merged",
            learned_count=len(learned),
            static_count=len(static),
            merged_count=len(merged),
            learned_in_top=sum(1 for ex in merged if ex.get("source") == "learned")
        )

        return merged

    def _build_metric_query(self, spec: QuerySpec) -> str:
        """
        Build search query for metric collection.

        Args:
            spec: QuerySpec

        Returns:
            Search query string like "IMOR INVEX banking metric"
        """
        parts = [spec.metric]

        if spec.bank_names:
            parts.extend(spec.bank_names)

        parts.append("banking metric")

        return " ".join(parts)

    def _build_schema_query(self, spec: QuerySpec) -> str:
        """
        Build search query for schema collection.

        Args:
            spec: QuerySpec

        Returns:
            Search query string like "IMOR monthly_kpis database column"
        """
        return f"{spec.metric} monthly_kpis database column"

    def _build_example_query(self, spec: QuerySpec) -> str:
        """
        Build search query for examples collection.

        Args:
            spec: QuerySpec

        Returns:
            Natural language query reconstructed from spec
            Example: "IMOR de INVEX últimos 3 meses"
        """
        parts = [spec.metric]

        if spec.bank_names:
            parts.append("de")
            parts.append(" y ".join(spec.bank_names))

        # Add time range expression
        if spec.time_range.type == "last_n_months":
            parts.append(f"últimos {spec.time_range.n} meses")
        elif spec.time_range.type == "year":
            parts.append(spec.time_range.start_date[:4])  # Extract year
        elif spec.time_range.type == "between_dates":
            parts.append(f"desde {spec.time_range.start_date} hasta {spec.time_range.end_date}")

        return " ".join(parts)

    async def _search_collection(
        self,
        collection: str,
        query_text: str,
        top_k: int,
        score_threshold: float
    ) -> List[Dict[str, Any]]:
        """
        Search a Qdrant collection and return payloads.

        Args:
            collection: Collection name
            query_text: Search query
            top_k: Maximum results
            score_threshold: Minimum similarity score

        Returns:
            List of payload dicts from matching points
        """
        try:
            # Generate embedding for query
            query_vector = self.embedding.encode_single(query_text, use_cache=True)

            # Check if collection exists
            existing_collections = [
                c.name for c in self.qdrant.client.get_collections().collections
            ]

            if collection not in existing_collections:
                logger.warning(
                    "nl2sql_context.collection_not_found",
                    collection=collection,
                    message="Collection not seeded yet. Run seed_nl2sql_rag.py"
                )
                return []

            # Search collection
            # Use query_points for Qdrant 1.7+ compatibility
            search_results = self.qdrant.client.query_points(
                collection_name=collection,
                query=query_vector,
                limit=top_k,
                score_threshold=score_threshold,
            ).points

            # Extract payloads
            results = [hit.payload for hit in search_results]

            logger.debug(
                "nl2sql_context.search_completed",
                collection=collection,
                query_preview=query_text[:50],
                results_count=len(results),
                avg_score=sum(hit.score for hit in search_results) / len(search_results) if search_results else 0
            )

            return results

        except Exception as e:
            logger.error(
                "nl2sql_context.search_failed",
                collection=collection,
                error=str(e),
                exc_info=True
            )
            return []


# Singleton instance (optional - can be dependency-injected instead)
_context_service: Optional[Nl2SqlContextService] = None


def get_nl2sql_context_service(
    qdrant_service: Optional[Any] = None,
    embedding_service: Optional[Any] = None
) -> Nl2SqlContextService:
    """
    Get or create NL2SQL context service instance.

    Args:
        qdrant_service: QdrantService instance (required for RAG)
        embedding_service: EmbeddingService instance (required for RAG)

    Returns:
        Nl2SqlContextService instance

    Usage:
        # With RAG enabled (inject services from main backend)
        context_svc = get_nl2sql_context_service(
            qdrant_service=get_qdrant_service(),
            embedding_service=get_embedding_service()
        )

        # Without RAG (fallback mode)
        context_svc = get_nl2sql_context_service()
    """
    global _context_service

    if _context_service is None:
        _context_service = Nl2SqlContextService(
            qdrant_service=qdrant_service,
            embedding_service=embedding_service
        )

    return _context_service
