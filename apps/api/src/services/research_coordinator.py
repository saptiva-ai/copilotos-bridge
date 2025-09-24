"""
Research Coordinator Service - Bridge between SAPTIVA chat and Aletheia deep research.

This service provides intelligent routing between simple chat and deep research
based on query complexity and user preferences.
"""

import re
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import uuid4

import structlog
from pydantic import BaseModel

from ..core.config import get_settings
from ..models.chat import ChatSession, ChatMessage
from ..models.task import Task as TaskModel, TaskStatus
from ..schemas.research import DeepResearchRequest, DeepResearchParams, ResearchType
from ..services.saptiva_client import get_saptiva_client
from ..services.aletheia_client import get_aletheia_client
from ..services.history_service import HistoryService

logger = structlog.get_logger(__name__)


class QueryComplexity(BaseModel):
    """Analysis of query complexity for routing decisions."""
    score: float  # 0.0 to 1.0
    reasoning: str
    requires_research: bool
    estimated_sources: int
    estimated_time_minutes: int
    complexity_factors: List[str]


class ResearchDecision(BaseModel):
    """Decision on whether to use chat or deep research."""
    use_deep_research: bool
    reasoning: str
    complexity: QueryComplexity
    recommended_params: Optional[DeepResearchParams] = None
    fallback_to_chat: bool = True


class ResearchCoordinator:
    """
    Coordinates between SAPTIVA chat and Aletheia deep research.

    Provides intelligent routing based on query complexity and automatic
    escalation from chat to research when needed.
    """

    def __init__(self):
        self.settings = get_settings()

        # Complexity analysis patterns
        self.research_indicators = [
            # Academic/research queries
            r'\b(research|study|analysis|investigate|compare|evaluate)\b',
            r'\b(literature review|systematic review|meta-analysis)\b',
            r'\b(what does research show|what do studies say)\b',

            # Complex comparative queries
            r'\b(compare|versus|vs|differences between|similarities)\b.*\b(and|with)\b',
            r'\b(pros and cons|advantages and disadvantages)\b',
            r'\b(best|worst|top \d+|ranking)\b',

            # Multi-faceted questions
            r'\b(comprehensive|detailed|thorough|in-depth)\b.*\b(analysis|overview|guide)\b',
            r'\b(everything about|all about|complete guide)\b',

            # Factual verification
            r'\b(is it true|fact check|verify|evidence|sources|citations)\b',
            r'\b(according to|based on research|studies show)\b',

            # Current/recent information
            r'\b(latest|recent|current|up-to-date|2024|this year)\b',
            r'\b(news|developments|trends|updates)\b',

            # Technical/specialized domains
            r'\b(technical|scientific|academic|peer-reviewed)\b',
            r'\b(methodology|framework|algorithm|protocol)\b',
        ]

        self.chat_indicators = [
            # Simple definitions
            r'^\s*what is\s+\w+\s*\??\s*$',
            r'^\s*define\s+\w+\s*\??\s*$',

            # Simple how-to
            r'^\s*how to\s+\w+.*\??\s*$',

            # Personal/opinion questions
            r'\b(what do you think|your opinion|do you believe)\b',
            r'\b(I think|I believe|in my opinion)\b',

            # Simple calculations
            r'\b(calculate|math|arithmetic|\+|\-|\*|\/|\=)\b',

            # Short questions (less than 10 words often simple)
            r'^\s*\S+(\s+\S+){0,8}\s*\??\s*$'
        ]

    async def analyze_query_complexity(self, query: str, context: Optional[Dict[str, Any]] = None) -> QueryComplexity:
        """
        Analyze query complexity to determine if deep research is needed.

        Args:
            query: User query to analyze
            context: Additional context (chat history, user preferences, etc.)

        Returns:
            QueryComplexity analysis
        """

        factors = []
        score = 0.0

        # Length factor (longer queries often more complex)
        word_count = len(query.split())
        if word_count > 20:
            score += 0.3
            factors.append(f"Long query ({word_count} words)")
        elif word_count > 10:
            score += 0.1
            factors.append(f"Medium query ({word_count} words)")

        # Research indicator patterns
        research_matches = 0
        for pattern in self.research_indicators:
            if re.search(pattern, query, re.IGNORECASE):
                research_matches += 1
                score += 0.2
                factors.append(f"Research indicator: {pattern}")

        # Chat indicator patterns (reduce score)
        chat_matches = 0
        for pattern in self.chat_indicators:
            if re.search(pattern, query, re.IGNORECASE):
                chat_matches += 1
                score -= 0.3
                factors.append(f"Simple query indicator: {pattern}")

        # Question complexity
        question_marks = query.count('?')
        if question_marks > 1:
            score += 0.2
            factors.append(f"Multiple questions ({question_marks})")

        # AND/OR logic
        if re.search(r'\b(and|or|but|however|although)\b', query, re.IGNORECASE):
            score += 0.1
            factors.append("Complex logical structure")

        # Context factors
        if context:
            # Previous research in conversation
            if context.get('has_previous_research'):
                score += 0.2
                factors.append("Previous research in conversation")

            # User explicitly requests research
            if context.get('user_prefers_research'):
                score += 0.5
                factors.append("User preference for research")

        # Normalize score to 0-1 range
        score = max(0.0, min(1.0, score))

        # Determine if research is needed
        requires_research = score > 0.4 or research_matches >= 2

        # Estimate complexity
        if score > 0.7:
            estimated_sources = 15 + research_matches * 5
            estimated_time = 4 + research_matches * 2
        elif score > 0.4:
            estimated_sources = 8 + research_matches * 3
            estimated_time = 2 + research_matches
        else:
            estimated_sources = 3
            estimated_time = 1

        reasoning = f"Complexity score: {score:.2f}. "
        if requires_research:
            reasoning += f"Detected {research_matches} research indicators. "
        if chat_matches > 0:
            reasoning += f"Detected {chat_matches} simple query indicators. "

        return QueryComplexity(
            score=score,
            reasoning=reasoning,
            requires_research=requires_research,
            estimated_sources=estimated_sources,
            estimated_time_minutes=estimated_time,
            complexity_factors=factors
        )

    async def make_research_decision(
        self,
        query: str,
        chat_id: Optional[str] = None,
        user_preferences: Optional[Dict[str, Any]] = None,
        force_research: bool = False
    ) -> ResearchDecision:
        """
        Make an intelligent decision about whether to use chat or deep research.

        Args:
            query: User query
            chat_id: Chat session ID for context
            user_preferences: User preferences
            force_research: Force deep research regardless of complexity

        Returns:
            ResearchDecision with routing recommendation
        """

        try:
            # Gather context
            context = {}

            if chat_id:
                # Check if there's previous research in this conversation
                session = await ChatSession.get(chat_id)
                if session:
                    messages = await ChatMessage.find(
                        ChatMessage.chat_id == chat_id
                    ).sort(-ChatMessage.created_at).limit(10).to_list()

                    # Look for research tasks in recent messages
                    for message in messages:
                        if message.metadata and message.metadata.get('task_id'):
                            context['has_previous_research'] = True
                            break

            # User preferences
            if user_preferences:
                context.update(user_preferences)

            # Analyze complexity
            complexity = await self.analyze_query_complexity(query, context)

            # Force research if requested
            if force_research:
                complexity.requires_research = True
                complexity.score = max(complexity.score, 0.8)
                complexity.reasoning += " (Forced by user request)"

            # Make decision
            use_research = complexity.requires_research

            # Generate reasoning
            if force_research:
                reasoning = "Deep research forced by user request"
            elif complexity.score > 0.7:
                reasoning = f"High complexity query (score: {complexity.score:.2f}) - deep research recommended"
            elif complexity.score > 0.4:
                reasoning = f"Medium complexity query (score: {complexity.score:.2f}) - deep research beneficial"
            else:
                reasoning = f"Simple query (score: {complexity.score:.2f}) - chat sufficient"

            # Recommended research parameters
            recommended_params = None
            if use_research:
                recommended_params = DeepResearchParams(
                    max_iterations=3 if complexity.score > 0.7 else 2,
                    sources_limit=complexity.estimated_sources,
                    include_citations=True,
                    focus_areas=self._extract_focus_areas(query),
                    depth_level="deep" if complexity.score > 0.7 else "medium"
                )

            logger.info(
                "Research decision made",
                query_length=len(query),
                complexity_score=complexity.score,
                use_research=use_research,
                estimated_time=complexity.estimated_time_minutes
            )

            return ResearchDecision(
                use_deep_research=use_research,
                reasoning=reasoning,
                complexity=complexity,
                recommended_params=recommended_params,
                fallback_to_chat=True
            )

        except Exception as e:
            logger.error("Error making research decision", error=str(e))
            # Safe fallback to chat
            return ResearchDecision(
                use_deep_research=False,
                reasoning=f"Error in decision making: {str(e)}",
                complexity=QueryComplexity(
                    score=0.0,
                    reasoning="Error occurred",
                    requires_research=False,
                    estimated_sources=0,
                    estimated_time_minutes=0,
                    complexity_factors=[]
                ),
                fallback_to_chat=True
            )

    def _extract_focus_areas(self, query: str) -> List[str]:
        """Extract focus areas from the query for targeted research."""

        focus_areas = []

        # Domain-specific patterns
        domain_patterns = {
            'technology': r'\b(AI|artificial intelligence|machine learning|blockchain|cloud|software|programming)\b',
            'healthcare': r'\b(health|medical|medicine|treatment|diagnosis|patient|clinical)\b',
            'business': r'\b(business|marketing|finance|strategy|management|economy|market)\b',
            'science': r'\b(research|study|scientific|biology|chemistry|physics|environmental)\b',
            'education': r'\b(education|learning|teaching|university|academic|school)\b',
            'legal': r'\b(law|legal|regulation|compliance|policy|court|legislation)\b'
        }

        for domain, pattern in domain_patterns.items():
            if re.search(pattern, query, re.IGNORECASE):
                focus_areas.append(domain)

        # If no specific domain, add general focus
        if not focus_areas:
            focus_areas = ['general']

        return focus_areas

    async def execute_coordinated_research(
        self,
        query: str,
        user_id: str,
        chat_id: Optional[str] = None,
        force_research: bool = False,
        stream: bool = True
    ) -> Dict[str, Any]:
        """
        Execute coordinated research - either chat or deep research based on complexity.

        Args:
            query: User query
            user_id: User ID
            chat_id: Chat session ID
            force_research: Force deep research
            stream: Enable streaming

        Returns:
            Coordinated response with routing information
        """

        start_time = time.time()

        try:
            # Make routing decision
            decision = await self.make_research_decision(
                query=query,
                chat_id=chat_id,
                force_research=force_research
            )

            if decision.use_deep_research:
                # Execute deep research
                task_id = str(uuid4())

                # Create research request
                research_request = DeepResearchRequest(
                    query=query,
                    research_type=ResearchType.DEEP_RESEARCH,
                    params=decision.recommended_params,
                    stream=stream,
                    chat_id=chat_id,
                    context={
                        'routing_decision': decision.dict(),
                        'coordinated_research': True
                    }
                )

                # Start deep research task
                task = TaskModel(
                    id=task_id,
                    user_id=user_id,
                    task_type="deep_research",
                    status=TaskStatus.PENDING,
                    input_data={
                        "query": query,
                        "research_type": research_request.research_type.value,
                        "params": research_request.params.model_dump(),
                        "stream": stream,
                        "context": research_request.context
                    },
                    chat_id=chat_id,
                    created_at=datetime.utcnow()
                )
                await task.insert()

                # Persist research start in unified history when linked to a chat
                if chat_id:
                    try:
                        await HistoryService.record_research_started(
                            chat_id=chat_id,
                            user_id=user_id,
                            task=task,
                            query=query,
                            params=(research_request.params.model_dump()
                                    if research_request.params else None)
                        )
                    except Exception as history_error:
                        logger.warning(
                            "Failed to persist coordinated research start",
                            error=str(history_error),
                            chat_id=chat_id,
                            task_id=task_id
                        )

                # Submit to Aletheia
                try:
                    aletheia_client = await get_aletheia_client()
                    aletheia_response = await aletheia_client.start_deep_research(
                        query=query,
                        task_id=task_id,
                        user_id=user_id,
                        params=research_request.params.model_dump(),
                        context=research_request.context
                    )

                    if aletheia_response.status != "error":
                        task.status = TaskStatus.RUNNING
                        task.started_at = datetime.utcnow()
                        await task.save()

                except Exception as aletheia_error:
                    logger.warning("Aletheia unavailable for research", error=str(aletheia_error))
                    task.status = TaskStatus.RUNNING
                    await task.save()

                return {
                    "type": "deep_research",
                    "task_id": task_id,
                    "stream_url": f"/api/stream/{task_id}" if stream else None,
                    "status": "started",
                    "decision": decision.dict(),
                    "estimated_time_minutes": decision.complexity.estimated_time_minutes,
                    "processing_time_ms": round((time.time() - start_time) * 1000, 2)
                }

            else:
                # Execute simple chat
                saptiva_client = await get_saptiva_client()

                # Build message history for context
                messages = [{"role": "user", "content": query}]

                if chat_id:
                    # Get recent chat history
                    chat_messages = await ChatMessage.find(
                        ChatMessage.chat_id == chat_id
                    ).sort(ChatMessage.created_at).limit(10).to_list()

                    history = []
                    for msg in chat_messages[:-1]:  # Exclude the current query
                        history.append({
                            "role": msg.role.value,
                            "content": msg.content
                        })

                    messages = history + messages

                # Get chat response
                saptiva_response = await saptiva_client.chat_completion(
                    messages=messages,
                    model="SAPTIVA_CORTEX",
                    temperature=0.7,
                    max_tokens=1024,
                    stream=False
                )

                return {
                    "type": "chat",
                    "response": saptiva_response,
                    "decision": decision.dict(),
                    "fallback_available": True,
                    "escalation_available": True,
                    "processing_time_ms": round((time.time() - start_time) * 1000, 2)
                }

        except Exception as e:
            logger.error("Error in coordinated research", error=str(e))

            # Fallback to simple response
            return {
                "type": "error",
                "error": str(e),
                "fallback_to_chat": True,
                "processing_time_ms": round((time.time() - start_time) * 1000, 2)
            }


# Singleton instance
_research_coordinator: Optional[ResearchCoordinator] = None


def get_research_coordinator() -> ResearchCoordinator:
    """Get singleton research coordinator instance."""
    global _research_coordinator
    if _research_coordinator is None:
        _research_coordinator = ResearchCoordinator()
    return _research_coordinator
