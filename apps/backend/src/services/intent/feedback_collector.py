"""
Feedback Collector - Learns from tool responses.

Q1 2026: When a tool returns None for a message we routed to it,
we learn that similar messages are not relevant queries.

Feedback signals:
- tool returns data → message was correctly routed (positive)
- tool returns None → message was NOT a relevant query (negative)

Uses Redis for storage with TTL-based expiration.
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)


class IntentFeedbackCollector:
    """
    Collects implicit feedback to improve intent routing.

    Storage:
    - Redis list for feedback log (for analysis)
    - Redis keys for negative cache (known non-relevant messages)

    TTLs are used to allow the system to "forget" and relearn
    as the tool's capabilities evolve.
    """

    # Redis key prefixes
    PREFIX_FEEDBACK = "intent_feedback"
    PREFIX_NEGATIVE = "intent_negative"

    # TTLs (in seconds)
    TTL_FEEDBACK_LOG = 7 * 24 * 3600  # 7 days
    TTL_NEGATIVE_CACHE = 24 * 3600  # 1 day (short, allow relearning)

    # Maximum feedback log size
    MAX_FEEDBACK_LOG_SIZE = 10000

    def __init__(self):
        """Initialize feedback collector."""
        self._redis = None

    async def _get_redis(self):
        """Get Redis client (lazy initialization)."""
        if self._redis is None:
            try:
                from ...core.redis_cache import get_redis_cache

                self._redis = await get_redis_cache()
            except Exception as e:
                logger.warning(
                    "Failed to initialize Redis for feedback",
                    error=str(e),
                )
        return self._redis

    def _hash_message(self, message: str) -> str:
        """
        Create hash for message (for cache keys).

        Normalizes the message to improve cache hit rate.
        """
        normalized = message.lower().strip()
        # Remove extra whitespace
        normalized = " ".join(normalized.split())
        return hashlib.md5(normalized.encode()).hexdigest()[:16]

    async def record_feedback(
        self,
        message: str,
        routed_to_advisor: bool,
        advisor_returned_data: bool,
        intent_scores: Optional[Dict[str, float]] = None,
        reason: Optional[str] = None,
    ):
        """
        Record routing feedback for learning.

        Args:
            message: Original user message
            routed_to_advisor: Whether we routed to tool
            advisor_returned_data: Whether tool returned chart/data
            intent_scores: Optional scores from classifier
            reason: Optional routing reason string
        """
        redis = await self._get_redis()
        if not redis:
            return

        try:
            feedback = {
                "message_hash": self._hash_message(message),
                "message_preview": message[:100],
                "routed": routed_to_advisor,
                "success": advisor_returned_data,
                "scores": intent_scores,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Log feedback for analysis
            key = f"{self.PREFIX_FEEDBACK}:log"
            await redis.lpush(key, json.dumps(feedback))
            await redis.ltrim(key, 0, self.MAX_FEEDBACK_LOG_SIZE - 1)

            # If false positive (routed but no data), mark as negative
            if routed_to_advisor and not advisor_returned_data:
                await self._mark_negative(message)

                logger.info(
                    "Intent feedback: false positive recorded",
                    message_preview=message[:50],
                    reason=reason,
                )
            elif routed_to_advisor and advisor_returned_data:
                logger.debug(
                    "Intent feedback: true positive",
                    message_preview=message[:50],
                )

        except Exception as e:
            logger.warning(
                "Failed to record intent feedback",
                error=str(e),
            )

    async def _mark_negative(self, message: str):
        """Mark message as known non-relevant query."""
        redis = await self._get_redis()
        if not redis:
            return

        try:
            key = f"{self.PREFIX_NEGATIVE}:{self._hash_message(message)}"
            await redis.setex(key, self.TTL_NEGATIVE_CACHE, "1")
        except Exception as e:
            logger.warning(
                "Failed to mark negative feedback",
                error=str(e),
            )

    async def is_known_negative(self, message: str) -> bool:
        """
        Check if message is in negative cache.

        Args:
            message: User message to check

        Returns:
            True if message (or similar) was previously a false positive
        """
        redis = await self._get_redis()
        if not redis:
            return False

        try:
            key = f"{self.PREFIX_NEGATIVE}:{self._hash_message(message)}"
            return bool(await redis.exists(key))
        except Exception as e:
            logger.warning(
                "Failed to check negative cache",
                error=str(e),
            )
            return False

    async def get_feedback_stats(self) -> Dict[str, Any]:
        """
        Get feedback statistics for monitoring.

        Returns:
            Dict with total, successes, false_positives, accuracy
        """
        redis = await self._get_redis()
        if not redis:
            return {"error": "redis_unavailable"}

        try:
            key = f"{self.PREFIX_FEEDBACK}:log"
            recent = await redis.lrange(key, 0, 999)  # Last 1000

            if not recent:
                return {"total": 0}

            total = len(recent)
            successes = 0
            false_positives = 0

            for item in recent:
                try:
                    feedback = json.loads(item)
                    if feedback.get("routed"):
                        if feedback.get("success"):
                            successes += 1
                        else:
                            false_positives += 1
                except json.JSONDecodeError:
                    pass

            return {
                "total": total,
                "routed": successes + false_positives,
                "successes": successes,
                "false_positives": false_positives,
                "accuracy": successes / (successes + false_positives)
                if (successes + false_positives) > 0
                else 0,
            }

        except Exception as e:
            logger.warning("Failed to get feedback stats", error=str(e))
            return {"error": str(e)}

    async def clear_negative_cache(self) -> int:
        """
        Clear all negative cache entries.

        Returns:
            Number of entries cleared
        """
        redis = await self._get_redis()
        if not redis:
            return 0

        try:
            # Find all negative cache keys
            pattern = f"{self.PREFIX_NEGATIVE}:*"
            keys = []
            async for key in redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                await redis.delete(*keys)

            logger.info("Negative cache cleared", entries=len(keys))
            return len(keys)

        except Exception as e:
            logger.warning("Failed to clear negative cache", error=str(e))
            return 0
