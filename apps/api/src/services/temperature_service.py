"""
Dynamic Temperature Service - Adjusts AI model temperature based on query complexity.

This service provides intelligent temperature adjustment for SAPTIVA models
based on query complexity analysis from the Research Coordinator.
"""

import structlog
from typing import Optional, Dict, Any, TYPE_CHECKING
from pydantic import BaseModel

if TYPE_CHECKING:
    from .research_coordinator import QueryComplexity

logger = structlog.get_logger(__name__)


class TemperatureConfig(BaseModel):
    """Configuration for dynamic temperature adjustment."""
    base_temperature: float = 0.5
    min_temperature: float = 0.1
    max_temperature: float = 0.7

    # Temperature mapping based on complexity scores
    simple_threshold: float = 0.3  # Below this: use low temperature
    complex_threshold: float = 0.7  # Above this: use high temperature


class DynamicTemperatureResult(BaseModel):
    """Result of dynamic temperature calculation."""
    temperature: float
    complexity_score: float
    reasoning: str
    complexity_factors: list[str]


class TemperatureService:
    """
    Service for calculating dynamic temperature based on query complexity.

    Temperature Strategy:
    - Simple queries (score 0.0-0.3): Low temperature (0.3-0.5) for precise, focused responses
    - Medium queries (score 0.3-0.7): Medium temperature (0.5-0.7) for balanced responses
    - Complex queries (score 0.7-1.0): High temperature (0.7-0.9) for creative, exploratory responses
    """

    def __init__(self, config: Optional[TemperatureConfig] = None):
        self.config = config or TemperatureConfig()

        # Lazy import to avoid circular dependency with research_coordinator
        from .research_coordinator import get_research_coordinator

        self.research_coordinator = get_research_coordinator()

    async def calculate_dynamic_temperature(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> DynamicTemperatureResult:
        """
        Calculate optimal temperature based on query complexity.

        Args:
            query: User query to analyze
            context: Additional context for complexity analysis

        Returns:
            DynamicTemperatureResult with calculated temperature and reasoning
        """
        try:
            # Analyze query complexity using research coordinator
            complexity: 'QueryComplexity' = await self.research_coordinator.analyze_query_complexity(
                query, context
            )

            # Calculate temperature based on complexity score
            temperature = self._map_complexity_to_temperature(complexity.score)

            # Generate reasoning
            reasoning = self._generate_temperature_reasoning(complexity.score, temperature)

            logger.info(
                "Dynamic temperature calculated",
                query_length=len(query),
                complexity_score=complexity.score,
                calculated_temperature=temperature,
                factors=len(complexity.complexity_factors)
            )

            return DynamicTemperatureResult(
                temperature=temperature,
                complexity_score=complexity.score,
                reasoning=reasoning,
                complexity_factors=complexity.complexity_factors
            )

        except Exception as e:
            logger.error("Error calculating dynamic temperature", error=str(e))
            # Safe fallback to base temperature
            return DynamicTemperatureResult(
                temperature=self.config.base_temperature,
                complexity_score=0.5,
                reasoning=f"Error occurred, using base temperature: {str(e)}",
                complexity_factors=[]
            )

    def _map_complexity_to_temperature(self, complexity_score: float) -> float:
        """
        Map complexity score (0.0-1.0) to appropriate temperature.

        Args:
            complexity_score: Query complexity score from 0.0 to 1.0

        Returns:
            Optimal temperature value
        """
        # Clamp score to valid range
        score = max(0.0, min(1.0, complexity_score))

        if score <= self.config.simple_threshold:
            # Simple queries: Linear scale from min_temp to base_temp
            # Score 0.0 -> min_temp, Score 0.3 -> base_temp
            ratio = score / self.config.simple_threshold
            temperature = self.config.min_temperature + ratio * (self.config.base_temperature - self.config.min_temperature)

        elif score <= self.config.complex_threshold:
            # Medium queries: Stay around base temperature with slight variation
            # Score 0.3-0.7 -> base_temp (0.7) with small adjustments
            temperature = self.config.base_temperature

        else:
            # Complex queries: Linear scale from base_temp to max_temp
            # Score 0.7 -> base_temp, Score 1.0 -> max_temp
            ratio = (score - self.config.complex_threshold) / (1.0 - self.config.complex_threshold)
            temperature = self.config.base_temperature + ratio * (self.config.max_temperature - self.config.base_temperature)

        # Ensure temperature stays within bounds
        return max(self.config.min_temperature, min(self.config.max_temperature, temperature))

    def _generate_temperature_reasoning(self, complexity_score: float, temperature: float) -> str:
        """Generate human-readable reasoning for temperature choice."""

        if complexity_score <= self.config.simple_threshold:
            return f"Simple query (score: {complexity_score:.2f}) - using low temperature ({temperature:.2f}) for focused, precise responses"

        elif complexity_score <= self.config.complex_threshold:
            return f"Medium complexity query (score: {complexity_score:.2f}) - using moderate temperature ({temperature:.2f}) for balanced responses"

        else:
            return f"Complex query (score: {complexity_score:.2f}) - using high temperature ({temperature:.2f}) for creative, exploratory responses"


# Singleton instance
_temperature_service: Optional[TemperatureService] = None


def get_temperature_service() -> TemperatureService:
    """Get singleton temperature service instance."""
    global _temperature_service
    if _temperature_service is None:
        _temperature_service = TemperatureService()
    return _temperature_service
