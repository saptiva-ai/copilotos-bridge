"""
RAG Feedback Service

Automatically seeds successful queries to Qdrant RAG for improved relevance.
Part of Q1 2025 RAG Feedback Loop implementation.
"""
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog

from bankadvisor.services.query_logger_service import QueryLoggerService, QueryLog

logger = structlog.get_logger(__name__)


class RagFeedbackService:
    """
    Service for feeding successful queries back to RAG.

    Flow:
    1. Get recent successful queries from query_logs
    2. Generate embeddings (batch)
    3. Upsert to Qdrant with metadata
    4. Mark queries as seeded
    """

    def __init__(
        self,
        query_logger: QueryLoggerService,
        qdrant_client: Any,  # QdrantClient from qdrant_client package
        collection_name: str = "bankadvisor_queries",
        embedding_model: str = "text-embedding-ada-002"
    ):
        """
        Initialize RAG Feedback Service.

        Args:
            query_logger: QueryLoggerService for accessing logs
            qdrant_client: Qdrant client for vector storage
            collection_name: Qdrant collection name
            embedding_model: OpenAI embedding model
        """
        self.query_logger = query_logger
        self.qdrant = qdrant_client
        self.collection_name = collection_name
        self.embedding_model = embedding_model

    async def seed_from_query_logs(
        self,
        batch_size: int = 50,
        min_age_hours: int = 1,
        max_age_days: int = 90,
        min_confidence: float = 0.7
    ) -> Dict[str, Any]:
        """
        Seed RAG from recent successful queries.

        Args:
            batch_size: Number of queries to seed per batch
            min_age_hours: Minimum age (avoid seeding too fresh queries)
            max_age_days: Maximum age (decay old patterns)
            min_confidence: Minimum confidence threshold

        Returns:
            Dict with seeding statistics
        """
        try:
            logger.info(
                "rag_feedback.seed_start",
                batch_size=batch_size,
                min_age_hours=min_age_hours,
                max_age_days=max_age_days
            )

            # Step 1: Get recent successful queries
            queries = await self.query_logger.get_recent_successful_queries(
                limit=batch_size,
                min_confidence=min_confidence,
                min_age_hours=min_age_hours,
                max_age_days=max_age_days,
                not_seeded=True
            )

            if not queries:
                logger.info("rag_feedback.no_candidates", message="No queries to seed")
                return {
                    "seeded_count": 0,
                    "skipped_count": 0,
                    "error_count": 0
                }

            logger.info(
                "rag_feedback.candidates_found",
                count=len(queries),
                avg_confidence=sum(q.rag_confidence for q in queries) / len(queries)
            )

            # Step 2: Generate embeddings (batch)
            embeddings = await self._generate_embeddings_batch(
                [q.user_query for q in queries]
            )

            # Step 3: Upsert to Qdrant
            points = self._build_qdrant_points(queries, embeddings)

            upsert_result = await self._upsert_to_qdrant(points)

            # Step 4: Mark as seeded
            seeded_ids = [q.query_id for q in queries]
            await self.query_logger.mark_as_seeded(seeded_ids)

            result = {
                "seeded_count": len(queries),
                "skipped_count": 0,
                "error_count": 0,
                "avg_confidence": sum(q.rag_confidence for q in queries) / len(queries),
                "top_metrics": self._get_top_metrics(queries)
            }

            logger.info(
                "rag_feedback.seed_complete",
                **result
            )

            return result

        except Exception as e:
            logger.error(
                "rag_feedback.seed_failed",
                error=str(e)
            )
            return {
                "seeded_count": 0,
                "skipped_count": 0,
                "error_count": 1,
                "error_message": str(e)
            }

    async def _generate_embeddings_batch(
        self,
        texts: List[str]
    ) -> List[List[float]]:
        """
        Generate embeddings for batch of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        try:
            # Import OpenAI client here to avoid circular imports
            import openai
            import os

            client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            response = await client.embeddings.create(
                model=self.embedding_model,
                input=texts
            )

            embeddings = [item.embedding for item in response.data]

            logger.debug(
                "embeddings.generated",
                count=len(embeddings),
                dimension=len(embeddings[0]) if embeddings else 0
            )

            return embeddings

        except Exception as e:
            logger.error(
                "embeddings.generation_failed",
                error=str(e),
                text_count=len(texts)
            )
            raise

    def _build_qdrant_points(
        self,
        queries: List[QueryLog],
        embeddings: List[List[float]]
    ) -> List[Dict[str, Any]]:
        """
        Build Qdrant points from queries and embeddings.

        Args:
            queries: List of QueryLog objects
            embeddings: List of embedding vectors

        Returns:
            List of Qdrant point dicts
        """
        points = []

        for query, embedding in zip(queries, embeddings):
            point = {
                "id": str(uuid.uuid4()),
                "vector": embedding,
                "payload": {
                    "type": "learned_query",
                    "source": "feedback_loop",
                    "user_query": query.user_query,
                    "generated_sql": query.generated_sql,
                    "banco": query.banco,
                    "metric": query.metric,
                    "intent": query.intent,
                    "learned_from": query.timestamp.isoformat(),
                    "execution_time_ms": query.execution_time_ms,
                    "confidence": query.rag_confidence,
                    "pipeline_used": query.pipeline_used,
                    # Metadata for filtering
                    "is_banco_specific": query.banco is not None,
                    "query_age_days": (datetime.now() - query.timestamp).days
                }
            }
            points.append(point)

        return points

    async def _upsert_to_qdrant(
        self,
        points: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Upsert points to Qdrant collection.

        Args:
            points: List of Qdrant point dicts

        Returns:
            Upsert result dict
        """
        try:
            from qdrant_client.models import PointStruct

            # Convert dicts to PointStruct
            point_structs = [
                PointStruct(
                    id=point["id"],
                    vector=point["vector"],
                    payload=point["payload"]
                )
                for point in points
            ]

            # Upsert to Qdrant
            result = self.qdrant.upsert(
                collection_name=self.collection_name,
                points=point_structs
            )

            logger.info(
                "qdrant.upsert_success",
                collection=self.collection_name,
                points_count=len(points)
            )

            return {
                "status": "success",
                "points_count": len(points)
            }

        except Exception as e:
            logger.error(
                "qdrant.upsert_failed",
                error=str(e),
                collection=self.collection_name,
                points_count=len(points)
            )
            raise

    def _get_top_metrics(
        self,
        queries: List[QueryLog],
        top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get top N most frequent metrics from queries.

        Args:
            queries: List of QueryLog objects
            top_n: Number of top metrics to return

        Returns:
            List of dicts with metric and count
        """
        from collections import Counter

        metric_counts = Counter(q.metric for q in queries)
        top_metrics = metric_counts.most_common(top_n)

        return [
            {"metric": metric, "count": count}
            for metric, count in top_metrics
        ]

    async def get_learned_query_stats(self) -> Dict[str, Any]:
        """
        Get statistics about learned queries in RAG.

        Returns:
            Dict with statistics
        """
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            # Count learned queries
            scroll_result = self.qdrant.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="type",
                            match=MatchValue(value="learned_query")
                        )
                    ]
                ),
                limit=10000,  # Get all learned queries
                with_payload=True,
                with_vectors=False
            )

            learned_queries = scroll_result[0]

            if not learned_queries:
                return {
                    "total_learned": 0,
                    "avg_confidence": 0,
                    "top_metrics": []
                }

            # Calculate statistics
            confidences = [q.payload.get("confidence", 0) for q in learned_queries]
            metrics = [q.payload.get("metric") for q in learned_queries if q.payload.get("metric")]

            from collections import Counter
            metric_counts = Counter(metrics)

            return {
                "total_learned": len(learned_queries),
                "avg_confidence": sum(confidences) / len(confidences),
                "min_confidence": min(confidences),
                "max_confidence": max(confidences),
                "top_metrics": [
                    {"metric": metric, "count": count}
                    for metric, count in metric_counts.most_common(10)
                ],
                "banco_specific_count": sum(
                    1 for q in learned_queries
                    if q.payload.get("is_banco_specific", False)
                )
            }

        except Exception as e:
            logger.error(
                "rag_stats.failed",
                error=str(e)
            )
            return {
                "total_learned": 0,
                "error": str(e)
            }

    async def cleanup_old_queries(
        self,
        max_age_days: int = 90
    ) -> int:
        """
        Remove learned queries older than max_age_days from RAG.

        Args:
            max_age_days: Maximum age to keep

        Returns:
            Number of queries removed
        """
        try:
            from qdrant_client.models import Filter, FieldCondition, Range

            # Find old queries
            scroll_result = self.qdrant.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="type",
                            match={"value": "learned_query"}
                        ),
                        FieldCondition(
                            key="query_age_days",
                            range=Range(gte=max_age_days)
                        )
                    ]
                ),
                limit=10000,
                with_payload=False,
                with_vectors=False
            )

            old_queries = scroll_result[0]
            old_ids = [q.id for q in old_queries]

            if old_ids:
                self.qdrant.delete(
                    collection_name=self.collection_name,
                    points_selector=old_ids
                )

                logger.info(
                    "rag_cleanup.complete",
                    removed_count=len(old_ids),
                    max_age_days=max_age_days
                )

            return len(old_ids)

        except Exception as e:
            logger.error(
                "rag_cleanup.failed",
                error=str(e)
            )
            return 0
