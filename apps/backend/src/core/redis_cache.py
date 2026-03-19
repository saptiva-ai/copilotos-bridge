"""
Redis cache for chat history and research tasks.
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, Optional

import redis.asyncio as redis
import structlog
from redis.exceptions import RedisError

from .config import get_settings

logger = structlog.get_logger(__name__)


class RedisCache:
    """Redis cache for chat history and research data"""

    def __init__(self):
        self.settings = get_settings()
        self.client: Optional[redis.Redis] = None

        # Cache TTL settings (in seconds)
        self.ttl_chat_history = 300  # 5 minutes
        self.ttl_research_tasks = 600  # 10 minutes
        self.ttl_session_list = 120  # 2 minutes
        self.ttl_bank_response = 604800  # 7 days (CNBV data updates monthly)

    async def _scan_keys(self, pattern: str) -> list:
        """Scan for keys matching pattern without blocking Redis.

        Uses SCAN instead of KEYS to avoid O(N) blocking on large keyspaces.
        """
        if not self.client:
            return []
        all_keys: list = []
        cursor = 0
        while True:
            cursor, keys = await self.client.scan(cursor, match=pattern, count=200)
            all_keys.extend(keys)
            if cursor == 0:
                break
        return all_keys

    async def connect(self):
        """Connect to Redis"""
        try:
            # Use redis_url from settings (respects REDIS_URL environment variable)
            redis_url = self.settings.redis_url

            self.client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )

            # Test connection
            await self.client.ping()
            logger.info(
                "Redis cache connected successfully", url=redis_url.split("@")[-1]
            )

        except RedisError as redis_err:
            # Redis-specific connection/timeout errors
            logger.warning(
                "Redis cache connection failed",
                error=str(redis_err),
                error_type=type(redis_err).__name__,
            )
            self.client = None
        except Exception as e:
            # Unexpected errors (config issues, etc.) - cache degrades gracefully
            logger.warning(
                "Redis cache connection failed (unexpected)",
                error=str(e),
                error_type=type(e).__name__,
            )
            self.client = None

    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            self.client = None

    def _make_key(
        self, prefix: str, identifier: str, params: Dict[str, Any] = None
    ) -> str:
        """Generate cache key with version prefix and optional parameters hash"""
        version = self.settings.cache_version
        key = f"{version}:cache:{prefix}:{identifier}"

        if params:
            # Create stable hash of parameters
            params_str = json.dumps(params, sort_keys=True)
            params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
            key += f":{params_hash}"

        return key

    async def get_chat_history(
        self,
        chat_id: str,
        limit: int = 50,
        offset: int = 0,
        include_research: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Get cached chat history"""

        if not self.client:
            return None

        try:
            params = {
                "limit": limit,
                "offset": offset,
                "include_research": include_research,
            }

            cache_key = self._make_key("chat_history", chat_id, params)
            cached_data = await self.client.get(cache_key)

            if cached_data:
                logger.debug("Cache hit for chat history", chat_id=chat_id)
                return json.loads(cached_data)

            logger.debug("Cache miss for chat history", chat_id=chat_id)
            return None

        except RedisError as redis_err:
            # Redis errors are non-fatal - fall back to uncached behavior
            logger.warning(
                "Redis error getting chat history",
                error=str(redis_err),
                error_type=type(redis_err).__name__,
                chat_id=chat_id,
            )
            return None
        except (json.JSONDecodeError, TypeError) as parse_err:
            # Corrupted cache data - return None to trigger fresh fetch
            logger.warning(
                "Cache data parse error",
                error=str(parse_err),
                chat_id=chat_id,
            )
            return None
        except Exception as e:
            # Unexpected error - cache degrades gracefully
            logger.warning(
                "Unexpected error getting cached chat history",
                error=str(e),
                error_type=type(e).__name__,
                chat_id=chat_id,
            )
            return None

    async def set_chat_history(
        self,
        chat_id: str,
        data: Dict[str, Any],
        limit: int = 50,
        offset: int = 0,
        include_research: bool = True,
    ):
        """Cache chat history"""

        if not self.client:
            return

        try:
            params = {
                "limit": limit,
                "offset": offset,
                "include_research": include_research,
            }

            cache_key = self._make_key("chat_history", chat_id, params)

            # Add cache metadata
            cache_data = {
                **data,
                "_cached_at": datetime.utcnow().isoformat(),
                "_cache_params": params,
            }

            await self.client.setex(
                cache_key, self.ttl_chat_history, json.dumps(cache_data, default=str)
            )

            logger.debug("Cached chat history", chat_id=chat_id)

        except RedisError as redis_err:
            # Redis write errors are non-fatal - next request will just miss cache
            logger.warning(
                "Redis error caching chat history",
                error=str(redis_err),
                error_type=type(redis_err).__name__,
                chat_id=chat_id,
            )
        except Exception as e:
            # Unexpected error - cache degrades gracefully
            logger.warning(
                "Unexpected error caching chat history",
                error=str(e),
                error_type=type(e).__name__,
                chat_id=chat_id,
            )

    async def get_research_tasks(
        self,
        session_id: str,
        limit: int = 20,
        offset: int = 0,
        status_filter: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get cached research tasks"""

        if not self.client:
            return None

        try:
            params = {"limit": limit, "offset": offset, "status_filter": status_filter}

            cache_key = self._make_key("research_tasks", session_id, params)
            cached_data = await self.client.get(cache_key)

            if cached_data:
                logger.debug("Cache hit for research tasks", session_id=session_id)
                return json.loads(cached_data)

            logger.debug("Cache miss for research tasks", session_id=session_id)
            return None

        except Exception as e:
            logger.warning("Error getting cached research tasks", error=str(e))
            return None

    async def set_research_tasks(
        self,
        session_id: str,
        data: Dict[str, Any],
        limit: int = 20,
        offset: int = 0,
        status_filter: Optional[str] = None,
    ):
        """Cache research tasks"""

        if not self.client:
            return

        try:
            params = {"limit": limit, "offset": offset, "status_filter": status_filter}

            cache_key = self._make_key("research_tasks", session_id, params)

            cache_data = {
                **data,
                "_cached_at": datetime.utcnow().isoformat(),
                "_cache_params": params,
            }

            await self.client.setex(
                cache_key, self.ttl_research_tasks, json.dumps(cache_data, default=str)
            )

            logger.debug("Cached research tasks", session_id=session_id)

        except Exception as e:
            logger.warning("Error caching research tasks", error=str(e))

    async def invalidate_chat_history(self, chat_id: str):
        """Invalidate all cache entries for a chat"""

        if not self.client:
            return

        try:
            # Find all keys for this chat (versioned and legacy)
            patterns = [
                f"*:cache:chat_history:{chat_id}*",
                f"chat_timeline:{chat_id}:*",
            ]

            all_keys = []
            for pattern in patterns:
                keys = await self._scan_keys(pattern)
                all_keys.extend(keys)

            if all_keys:
                await self.client.delete(*all_keys)
                logger.debug(
                    "Invalidated chat history cache",
                    chat_id=chat_id,
                    keys_deleted=len(all_keys),
                )

        except Exception as e:
            logger.warning("Error invalidating chat history cache", error=str(e))

    # ======================================
    # UNIFIED HISTORY CACHE METHODS (New)
    # ======================================

    async def get(self, key: str):
        """Generic get method for unified history service"""
        if not self.client:
            return None

        try:
            cached_data = await self.client.get(key)
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            logger.warning("Error getting cache", key=key, error=str(e))
            return None

    async def set(self, key: str, value: dict, expire: int = 300):
        """Generic set method for unified history service"""
        if not self.client:
            return

        try:
            await self.client.setex(key, expire, json.dumps(value, default=str))
            logger.debug("Set cache", key=key, expire=expire)
        except Exception as e:
            logger.warning("Error setting cache", key=key, error=str(e))

    async def delete_pattern(self, pattern: str):
        """Delete all keys matching a pattern"""
        if not self.client:
            return

        try:
            keys = await self._scan_keys(pattern)
            if keys:
                await self.client.delete(*keys)
                logger.debug(
                    "Deleted cache pattern", pattern=pattern, keys_deleted=len(keys)
                )
        except Exception as e:
            logger.warning(
                "Error deleting cache pattern", pattern=pattern, error=str(e)
            )

    # ======================================
    # BANK RESPONSE CACHE (PERF-001)
    # ======================================

    @staticmethod
    def _normalize_query(query: str) -> str:
        """Normalize query for cache key: strip accents, lowercase, collapse whitespace."""
        import re
        import unicodedata

        nfkd = unicodedata.normalize("NFKD", query)
        stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
        return re.sub(r"\s+", " ", stripped.lower().strip())

    def _make_bank_response_key(self, user_query: str) -> str:
        """Generate cache key from normalized user query hash."""
        query_norm = self._normalize_query(user_query)
        query_hash = hashlib.sha256(query_norm.encode()).hexdigest()[:16]
        version = self.settings.cache_version
        return f"{version}:bank_resp:{query_hash}"

    async def get_bank_response(self, user_query: str) -> Optional[Dict[str, Any]]:
        """Get cached bank analytics response by user query."""
        if not self.client:
            return None

        try:
            cache_key = self._make_bank_response_key(user_query)
            cached = await self.client.get(cache_key)
            if cached:
                logger.info(
                    "bank_response_cache.hit",
                    cache_key=cache_key,
                    query_preview=user_query[:60],
                )
                return json.loads(cached)
            logger.debug("bank_response_cache.miss", query_preview=user_query[:60])
            return None
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning("bank_response_cache.get_error", error=str(e))
            return None

    async def set_bank_response(
        self,
        user_query: str,
        response_data: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> None:
        """Cache bank analytics response for reuse on repeat queries."""
        if not self.client:
            return

        try:
            cache_key = self._make_bank_response_key(user_query)
            _ttl = ttl or self.ttl_bank_response
            await self.client.setex(
                cache_key,
                _ttl,
                json.dumps(response_data, default=str),
            )
            logger.info(
                "bank_response_cache.stored",
                cache_key=cache_key,
                ttl=_ttl,
                query_preview=user_query[:60],
            )
        except (RedisError, TypeError) as e:
            logger.warning("bank_response_cache.set_error", error=str(e))

    async def invalidate_bank_responses(self) -> int:
        """Invalidate all bank response caches (e.g., after CNBV data refresh)."""
        if not self.client:
            return 0

        try:
            keys = await self._scan_keys("*:bank_resp:*")
            if keys:
                await self.client.delete(*keys)
                logger.info(
                    "bank_response_cache.invalidated_all",
                    keys_deleted=len(keys),
                )
                return len(keys)
            return 0
        except RedisError as e:
            logger.warning("bank_response_cache.invalidate_error", error=str(e))
            return 0

    async def invalidate_research_tasks(self, session_id: str):
        """Invalidate all cache entries for research tasks"""

        if not self.client:
            return

        try:
            pattern = f"*:cache:research_tasks:{session_id}*"
            keys = await self._scan_keys(pattern)

            if keys:
                await self.client.delete(*keys)
                logger.debug(
                    "Invalidated research tasks cache",
                    session_id=session_id,
                    keys_deleted=len(keys),
                )

        except Exception as e:
            logger.warning("Error invalidating research tasks cache", error=str(e))

    async def invalidate_all_for_chat(self, chat_id: str):
        """Invalidate all cache for a chat session"""
        await self.invalidate_chat_history(chat_id)
        await self.invalidate_research_tasks(chat_id)


# Singleton instance
_redis_cache: Optional[RedisCache] = None


async def get_redis_cache() -> RedisCache:
    """Get singleton Redis cache instance"""
    global _redis_cache

    if _redis_cache is None:
        _redis_cache = RedisCache()
        await _redis_cache.connect()

    return _redis_cache


async def close_redis_cache():
    """Close Redis cache connection"""
    global _redis_cache

    if _redis_cache:
        await _redis_cache.close()
        _redis_cache = None
