"""
Intent classification service for NLP query interpretation.

Q1 2025: Legacy IntentService removed - only NlpIntentService remains.

- NlpIntentService: LLM-based intent classification used by NL2SQL pipeline
"""

import os
import json
from typing import Any, Optional
from dataclasses import dataclass
from enum import Enum

import httpx
import structlog

from bankadvisor.runtime_config import get_runtime_config

logger = structlog.get_logger(__name__)


class Intent(str, Enum):
    """Query intent types for NLP processing."""
    EVOLUTION = "evolution"       # Show trend over time
    COMPARISON = "comparison"     # Compare banks
    RANKING = "ranking"           # Top/bottom banks
    POINT_VALUE = "point_value"   # Current value
    UNKNOWN = "unknown"


@dataclass
class ParsedIntent:
    """Result of intent classification."""
    intent: Intent
    confidence: float
    explanation: Optional[str] = None


class NlpIntentService:
    """
    Classifies user intent using Saptiva LLM.
    Requires LLM - no fallback. If LLM unavailable, returns UNKNOWN to trigger clarification.

    HU3 - NLP Query Interpretation
    """

    INTENT_PROMPT = """Eres un asistente que clasifica consultas bancarias.

Dada la siguiente consulta del usuario, determina la intención:

- "evolution": El usuario quiere ver cómo ha cambiado una métrica en el tiempo (tendencia, histórico, evolución)
- "comparison": El usuario quiere comparar entre bancos (vs, contra, comparar)
- "ranking": El usuario quiere ver un ranking (top, mejores, peores, ordenar)
- "point_value": El usuario quiere saber un valor específico actual (cuál es, cuánto, valor actual)
- "unknown": No está claro qué quiere el usuario

Contexto extraído:
- Métrica detectada: {metric}
- Bancos mencionados: {banks}
- Rango de fechas: {date_range}

Consulta: "{query}"

Responde SOLO con JSON válido:
{{"intent": "evolution|comparison|ranking|point_value|unknown", "confidence": 0.0-1.0, "explanation": "breve explicación"}}
"""

    @classmethod
    async def classify(
        cls,
        query: str,
        entities: Any,  # ExtractedEntities
        settings: Any = None  # Settings with saptiva config
    ) -> ParsedIntent:
        """
        Classify intent using HYBRID strategy: Rules-first, LLM-fallback.

        Strategy (SOLID - Open/Closed Principle):
        1. Try rule-based classification FIRST
        2. If rules are confident (>= 0.9), use them
        3. If rules uncertain (< 0.9), consult LLM for second opinion
        4. If LLM unavailable/fails, use rule result anyway

        This ensures:
        - Fast, deterministic classification for clear cases
        - LLM only for ambiguous cases (cost & latency optimization)
        - Graceful degradation if LLM fails

        Args:
            query: User query
            entities: ExtractedEntities from EntityService
            settings: Settings with Saptiva API config

        Returns:
            ParsedIntent with intent type and confidence
        """
        runtime_config = get_runtime_config()

        # Step 1: ALWAYS try rules first (fast, deterministic)
        rule_result = cls._classify_with_rules(query, entities)

        # Step 2: If rules are confident, trust them
        confidence_threshold = runtime_config.rules_confidence_threshold
        if rule_result.confidence >= confidence_threshold:
            logger.debug(
                "nlp_intent.rules_confident",
                intent=rule_result.intent.value,
                confidence=rule_result.confidence,
                threshold=confidence_threshold,
                explanation=rule_result.explanation
            )
            return rule_result

        # Step 3: Check if LLM fallback is enabled
        if not runtime_config.llm_fallback_enabled:
            logger.info(
                "nlp_intent.llm_fallback_disabled",
                action="using_rule_result",
                rule_confidence=rule_result.confidence
            )
            return rule_result

        # Step 4: Rules uncertain -> consult LLM for second opinion
        saptiva_key = os.getenv("SAPTIVA_API_KEY", "")
        if not saptiva_key:
            logger.info(
                "nlp_intent.llm_not_configured",
                action="using_rule_result",
                rule_confidence=rule_result.confidence
            )
            return rule_result

        try:
            llm_result = await cls._classify_with_llm(query, entities, settings)

            # If LLM is more confident than rules, use LLM
            if llm_result.confidence > rule_result.confidence:
                logger.debug(
                    "nlp_intent.llm_override",
                    rule_intent=rule_result.intent.value,
                    rule_confidence=rule_result.confidence,
                    llm_intent=llm_result.intent.value,
                    llm_confidence=llm_result.confidence
                )
                return llm_result

            # Otherwise stick with rules
            return rule_result

        except Exception as e:
            logger.warning(
                "nlp_intent.llm_failed",
                error=str(e),
                action="using_rule_result"
            )
            return rule_result

    @classmethod
    async def _classify_with_llm(
        cls,
        query: str,
        entities: Any,
        settings: Any
    ) -> ParsedIntent:
        """Use Saptiva LLM for intent classification."""
        import os

        saptiva_key = os.getenv("SAPTIVA_API_KEY", "")
        saptiva_url = os.getenv("SAPTIVA_BASE_URL", "https://api.saptiva.com")

        # Build context for prompt
        date_range = "no especificado"
        if hasattr(entities, 'date_start') and hasattr(entities, 'date_end'):
            if entities.date_start and entities.date_end:
                date_range = f"{entities.date_start} a {entities.date_end}"
            elif entities.date_start:
                date_range = f"desde {entities.date_start}"

        metric_display = getattr(entities, 'metric_display', None) or "no detectada"
        banks = getattr(entities, 'banks', []) or []

        prompt = cls.INTENT_PROMPT.format(
            metric=metric_display,
            banks=", ".join(banks) if banks else "ninguno",
            date_range=date_range,
            query=query
        )

        # Call Saptiva API (ensure trailing slash to avoid 307 redirect)
        api_url = f"{saptiva_url.rstrip('/')}/v1/chat/completions/"
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.post(
                api_url,
                headers={
                    "Authorization": f"Bearer {saptiva_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "Saptiva Turbo",
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,  # Low temperature for consistent classification
                    "max_tokens": 150
                }
            )
            response.raise_for_status()

            result = response.json()
            content = result["choices"][0]["message"]["content"]

            # Parse JSON response (handle markdown code blocks)
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            parsed = json.loads(content.strip())

            intent_str = parsed.get("intent", "unknown")
            try:
                intent = Intent(intent_str)
            except ValueError:
                intent = Intent.UNKNOWN

            return ParsedIntent(
                intent=intent,
                confidence=float(parsed.get("confidence", 0.5)),
                explanation=parsed.get("explanation")
            )

    @classmethod
    def _classify_with_rules(cls, query: str, entities: Any) -> ParsedIntent:
        """
        Rule-based intent classification (fallback when LLM unavailable).

        Rules (in priority order):
        1. Has "vs"/"contra"/"compara" → comparison (highest priority)
        2. Has "top"/"mejores"/"peores" → ranking
        3. Has date range (year/months) + metric → evolution (IMPORTANT)
        4. Has evolution keywords → evolution
        5. Default → point_value (with medium confidence)

        Args:
            query: User query
            entities: ExtractedEntities

        Returns:
            ParsedIntent with classified intent
        """
        query_lower = query.lower()

        # Rule 1: Comparison keywords (highest priority)
        comparison_keywords = ["vs", "contra", "compara", "comparar", "comparación", "comparacion", "versus"]
        if any(kw in query_lower for kw in comparison_keywords):
            return ParsedIntent(
                intent=Intent.COMPARISON,
                confidence=0.95,
                explanation="Detected comparison keywords (vs/contra/compara)"
            )

        # Rule 2: Ranking keywords
        ranking_keywords = ["top", "mejores", "peores", "ranking", "ordenar", "clasificación"]
        if any(kw in query_lower for kw in ranking_keywords):
            return ParsedIntent(
                intent=Intent.RANKING,
                confidence=0.95,
                explanation="Detected ranking keywords"
            )

        # Rule 3: Evolution indicators - Date range (CRITICAL)
        # If query has a date range (year, date range, months), it's asking for evolution
        has_date_range = False
        if hasattr(entities, 'date_start') and hasattr(entities, 'date_end'):
            if entities.date_start and entities.date_end:
                # Has both start and end dates -> evolution over time
                has_date_range = True
            elif entities.date_start:
                # Has start date only -> evolution from that point
                has_date_range = True

        if has_date_range:
            return ParsedIntent(
                intent=Intent.EVOLUTION,
                confidence=0.95,
                explanation="Detected date range - implies evolution over time"
            )

        # Rule 4: Multiple banks indicator -> comparison/evolution
        # "todos los bancos", "todos bancos", "all banks" suggests showing all banks over time
        # HIGH CONFIDENCE (0.96) to override LLM's tendency to interpret as ranking
        multi_bank_keywords = ["todos los bancos", "todos bancos", "all banks", "múltiples bancos", "varios bancos"]
        if any(kw in query_lower for kw in multi_bank_keywords):
            # Always return COMPARISON when "todos los bancos" is detected
            # User wants to compare all banks, not rank them
            return ParsedIntent(
                intent=Intent.COMPARISON,
                confidence=0.96,
                explanation="Query mentions 'todos los bancos' - implies comparison over time"
            )

        # Rule 4.5: "por banco" indicator -> comparison (not ranking)
        # Queries like "Reservas totales por banco" should show temporal comparison, not ranking
        # HIGH CONFIDENCE (0.96) to override LLM which interprets "por banco" as ranking
        if "por banco" in query_lower or "por bancos" in query_lower:
            return ParsedIntent(
                intent=Intent.COMPARISON,
                confidence=0.96,
                explanation="Query mentions 'por banco' - implies comparison over time, not ranking"
            )

        # Rule 5: Evolution keywords
        evolution_keywords = ["evolución", "evolucion", "tendencia", "histórico", "historico", "cambio", "variación", "variacion"]
        has_evolution_keyword = any(kw in query_lower for kw in evolution_keywords)

        if has_evolution_keyword:
            return ParsedIntent(
                intent=Intent.EVOLUTION,
                confidence=0.9,
                explanation="Detected evolution keywords"
            )

        # Rule 6: Default to point_value with medium confidence
        # This allows clarification to trigger if confidence threshold is high
        return ParsedIntent(
            intent=Intent.POINT_VALUE,
            confidence=0.6,
            explanation="No strong indicators - defaulting to point value"
        )
