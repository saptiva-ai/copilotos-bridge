"""
Tool Execution Service.

This service handles the orchestration and execution of MCP tools
with built-in Redis caching and error handling.

It abstracts the complexity of:
- Tool discovery
- Cache key generation
- TTL management
- Error resilience
"""

import json
import hashlib
from typing import Dict, Any, Optional, List
import structlog

from ..core.redis_cache import get_redis_cache
from ..domain.chat_context import ChatContext
from ..mcp import get_mcp_adapter
from ..core.constants import (
    TOOL_NAME_EXCEL,
    TOOL_NAME_RESEARCH,
    TOOL_NAME_EXTRACT,
    TOOL_NAME_BANK_ANALYTICS
)

logger = structlog.get_logger(__name__)

# TTL configuration for each tool (in seconds)
TOOL_CACHE_TTL = {
    TOOL_NAME_EXCEL: 1800,   # 30 min (data might update)
    TOOL_NAME_RESEARCH: 86400,   # 24 hours (research is expensive)
    TOOL_NAME_EXTRACT: 3600,  # 1 hour (text is stable)
    TOOL_NAME_BANK_ANALYTICS: 300,  # 5 min (queries may change)
}

class ToolExecutionService:
    """Service for executing MCP tools with caching strategies."""

    @staticmethod
    def _generate_cache_key(tool_name: str, doc_id: str, params: Dict = None) -> str:
        """
        Generate unique cache key for tool result.
        Format: mcp:tool:{tool_name}:{doc_id}:{params_hash}
        """
        if params:
            # Create deterministic hash of params
            params_str = json.dumps(params, sort_keys=True)
            params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
            return f"mcp:tool:{tool_name}:{doc_id}:{params_hash}"
        return f"mcp:tool:{tool_name}:{doc_id}"

    @classmethod
    async def _execute_tool_with_cache(
        cls,
        tool_name: str,
        doc_id: str,
        user_id: str,
        payload: Dict[str, Any],
        cache_params: Dict[str, Any],
        tool_map: Dict[str, Any],
        mcp_adapter: Any,
        cache: Any
    ) -> Optional[Dict[str, Any]]:
        """
        Generic method to execute a tool with Redis caching.
        
        Args:
            tool_name: Name of the tool to execute
            doc_id: ID of the document being processed
            user_id: ID of the user invoking the tool
            payload: Full payload to send to the tool
            cache_params: Parameters used to generate the cache key
            tool_map: Map of available tools
            mcp_adapter: Adapter to execute the tool
            cache: Redis cache instance
            
        Returns:
            The tool result dict or None if execution failed
        """
        try:
            # Generate cache key
            cache_key = cls._generate_cache_key(tool_name, doc_id, cache_params)

            # Try to get from cache first
            cached_result = None
            if cache:
                try:
                    cached_result = await cache.get(cache_key)
                    if cached_result:
                        logger.info(
                            f"{tool_name} result loaded from cache",
                            doc_id=doc_id,
                            cache_hit=True
                        )
                        return cached_result
                except Exception as e:
                    logger.warning(
                        "Failed to read from cache",
                        cache_key=cache_key,
                        error=str(e)
                    )

            # Execute tool
            logger.info(
                f"Invoking {tool_name} tool",
                doc_id=doc_id,
                user_id=user_id,
                cache_hit=False
            )

            tool_impl = tool_map[tool_name]
            result = await mcp_adapter._execute_tool_impl(
                tool_name=tool_name,
                tool_impl=tool_impl,
                payload={
                    "doc_id": str(doc_id),
                    "user_id": str(user_id),
                    "policy_id": "auto"
                },
                context=None
            )

            # Store in cache
            if cache:
                try:
                    ttl = TOOL_CACHE_TTL.get(tool_name, 3600)
                    await cache.set(cache_key, result, expire=ttl)
                    logger.debug(
                        f"Cached {tool_name} result",
                        cache_key=cache_key,
                        ttl=ttl
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to cache {tool_name} result",
                        cache_key=cache_key,
                        error=str(e)
                    )
            
            return result

        except Exception as e:
            logger.warning(
                f"{tool_name} tool failed",
                doc_id=doc_id,
                error=str(e),
                exc_type=type(e).__name__
            )
            return None

    @classmethod
    async def invoke_relevant_tools(
        cls,
        context: ChatContext,
        user_id: str
    ) -> Dict:
        """
        Invoke relevant MCP tools based on context and return results.
        """
        results = {}

        # Get Redis cache
        try:
            cache = await get_redis_cache()
        except Exception as e:
            logger.warning(
                "Failed to get Redis cache for tool results",
                error=str(e),
                exc_type=type(e).__name__
            )
            cache = None

        # Skip if no tools enabled
        if not context.tools_enabled or not any(context.tools_enabled.values()):
            logger.debug("No tools enabled, skipping tool invocation")
            return results

        # Skip if no documents attached
        if not context.document_ids:
            logger.debug("No documents attached, skipping tool invocation")
            return results

        try:
            # Get MCP adapter for internal tool invocation
            mcp_adapter = get_mcp_adapter()
            tool_map = await mcp_adapter._get_tool_map()

            logger.info(
                "🔍 [TOOL DEBUG] Checking tool execution conditions",
                tools_enabled_keys=list(context.tools_enabled.keys()),
                tool_map_keys=list(tool_map.keys()),
                document_ids=context.document_ids
            )

            # Excel Analyzer Tool
            if context.tools_enabled.get(TOOL_NAME_EXCEL, False) and TOOL_NAME_EXCEL in tool_map:
                from ..models.document import Document
                
                for doc_id in context.document_ids:
                    # Check if document is an Excel file and verify ownership
                    try:
                        doc = await Document.get(doc_id)
                        if not doc or str(doc.user_id) != user_id:
                            continue

                        is_excel = doc.content_type in [
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            "application/vnd.ms-excel"
                        ]

                        if not is_excel:
                            continue

                        excel_result = await cls._execute_tool_with_cache(
                            tool_name=TOOL_NAME_EXCEL,
                            doc_id=doc_id,
                            user_id=user_id,
                            payload={
                                "doc_id": doc_id,
                                "operations": ["stats", "preview"],
                                "user_id": user_id
                            },
                            cache_params={"operations": ["stats", "preview"]},
                            tool_map=tool_map,
                            mcp_adapter=mcp_adapter,
                            cache=cache
                        )

                        if excel_result:
                            results[f"{TOOL_NAME_EXCEL}_{doc_id}"] = excel_result
                            logger.info(
                                f"{TOOL_NAME_EXCEL} tool succeeded",
                                doc_id=doc_id
                            )
                            
                    except Exception as e:
                        logger.warning(
                            f"Error checking document for {TOOL_NAME_EXCEL}",
                            doc_id=doc_id,
                            error=str(e)
                        )
                        continue

            logger.info(
                "Tool invocation completed",
                tools_executed=len(results),
                user_id=user_id
            )

        except Exception as e:
            logger.error(
                "Failed to invoke tools",
                error=str(e),
                exc_type=type(e).__name__,
                exc_info=True
            )
            # Return empty results on error

        return results

    @classmethod
    async def invoke_bank_analytics(
        cls,
        message: str,
        user_id: str,
        mode: str = "dashboard",
        recent_messages: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Invoke bank_analytics MCP tool if message appears to be a banking query.

        This is a message-based tool (not document-based), so it uses the
        bank_analytics_client directly instead of the MCP adapter.

        Args:
            message: User message text
            user_id: User ID for logging
            mode: Visualization mode (dashboard or timeline)
            recent_messages: Optional list of recent messages for context combination

        Returns:
            BankChartData dict if successful, None otherwise
        """
        from .bank_analytics_client import (
            is_bank_query,
            query_bank_analytics,
            BankAdvisorUnavailableError,
            BankAdvisorQueryError
        )

        try:
            # Check if there's a pending clarification in recent messages
            # If so, combine original query with current message
            combined_message = message
            pending_clarification = None

            if recent_messages:
                pending_clarification = cls._find_pending_bank_clarification(recent_messages)
                if pending_clarification:
                    original_query = pending_clarification.get("original_query", "")
                    if original_query:
                        # Combine: "Reservas" + "de INVEX últimos 6 meses" → "Reservas de INVEX últimos 6 meses"
                        combined_message = f"{original_query} {message}"
                        logger.info(
                            "bank_analytics.combined_with_clarification",
                            original_query=original_query,
                            user_response=message,
                            combined_message=combined_message
                        )

            # Quick check if it's a banking query
            if not await is_bank_query(combined_message):
                logger.debug(
                    "Message is not a banking query",
                    message_preview=combined_message[:50]
                )
                return None

            logger.info(
                "bank_analytics.detected",
                message_preview=combined_message[:100],
                user_id=user_id,
                has_clarification_context=pending_clarification is not None
            )

            # Try cache first
            cache = None
            cache_key = None
            try:
                cache = await get_redis_cache()
                cache_key = cls._generate_cache_key(
                    TOOL_NAME_BANK_ANALYTICS,
                    combined_message[:100],  # Use combined message prefix as doc_id
                    {"mode": mode}
                )
                cached_result = await cache.get(cache_key)
                if cached_result:
                    logger.info(
                        "bank_analytics.cache_hit",
                        message_preview=combined_message[:50]
                    )
                    return cached_result
            except Exception as e:
                logger.warning(
                    "bank_analytics.cache_error",
                    error=str(e)
                )

            # Query bank advisor with combined message
            response = await query_bank_analytics(
                metric_or_query=combined_message,
                mode=mode
            )

            # HU3.1: Handle clarification response
            if response.success and response.clarification:
                clarification_result = {
                    "type": "clarification",
                    **response.clarification.model_dump()
                }

                logger.info(
                    "bank_analytics.clarification_returned",
                    message=response.clarification.message,
                    options_count=len(response.clarification.options)
                )

                # Don't cache clarification responses (they're context-specific)
                return clarification_result

            if response.success and response.data:
                result = response.data.model_dump()

                # Cache the result
                if cache and cache_key:
                    try:
                        ttl = TOOL_CACHE_TTL.get(TOOL_NAME_BANK_ANALYTICS, 300)
                        await cache.set(cache_key, result, expire=ttl)
                    except Exception as e:
                        logger.warning(
                            "bank_analytics.cache_set_error",
                            error=str(e)
                        )

                logger.info(
                    "bank_analytics.success",
                    metric=result.get("metric_name"),
                    banks=result.get("bank_names")
                )

                return result

            return None

        except (BankAdvisorUnavailableError, BankAdvisorQueryError) as e:
            logger.warning(
                "bank_analytics.query_failed",
                message_preview=message[:50],
                error=str(e)
            )
            return None

        except Exception as e:
            logger.error(
                "bank_analytics.unexpected_error",
                message_preview=message[:50],
                error=str(e),
                exc_info=True
            )
            return None

    @classmethod
    def _find_pending_bank_clarification(
        cls,
        recent_messages: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Search recent messages for a pending bank analytics clarification.

        Looks for assistant messages with bank_clarification_data in metadata
        that haven't been resolved yet.

        Args:
            recent_messages: List of recent messages (newest last)

        Returns:
            Clarification context dict with original_query, or None if not found
        """
        # Search from newest to oldest (reversed)
        for msg in reversed(recent_messages):
            # Check if it's an assistant message with clarification data
            if msg.get("role") == "assistant":
                metadata = msg.get("metadata", {})

                # Check for bank_clarification_data in metadata
                clarification_data = metadata.get("bank_clarification_data")
                if clarification_data and isinstance(clarification_data, dict):
                    context = clarification_data.get("context", {})
                    original_query = context.get("original_query")

                    if original_query:
                        logger.debug(
                            "bank_analytics.found_pending_clarification",
                            original_query=original_query,
                            detected_metric=context.get("detected_metric"),
                            missing_fields=context.get("missing_fields")
                        )
                        return {
                            "original_query": original_query,
                            "detected_metric": context.get("detected_metric"),
                            "missing_fields": context.get("missing_fields", [])
                        }

            # If we hit a user message after an assistant, stop searching
            # (the clarification would have been in the assistant message before this user message)
            elif msg.get("role") == "user":
                # Continue searching - the clarification might be before this
                pass

        return None
