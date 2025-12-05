"""
Entity extraction service - extracts banks, dates, metrics from natural language.
Production-grade: loads banks from DB, uses dateparser library.

HU3 - NLP Query Interpretation
"""

import re
import logging
from datetime import date, datetime
from typing import List, Optional, Set, Tuple, Dict, Any
from dataclasses import dataclass, field

import dateparser
from sqlalchemy import select, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from bankadvisor.models.kpi import MonthlyKPI
from bankadvisor.config_service import get_config

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ExtractedEntities:
    """Container for extracted entities from a query."""
    banks: List[str] = field(default_factory=list)
    metric_id: Optional[str] = None
    metric_display: Optional[str] = None
    metric_column: Optional[str] = None
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    raw_query: str = ""
    clean_query: str = ""  # Query with entities removed
    # HU3.4: Multi-metric support
    metrics: List[str] = field(default_factory=list)
    metrics_display: List[str] = field(default_factory=list)

    def has_date_range(self) -> bool:
        """Check if a date range was extracted."""
        return self.date_start is not None or self.date_end is not None

    def has_banks(self) -> bool:
        """Check if any banks were extracted."""
        return len(self.banks) > 0

    def has_metric(self) -> bool:
        """Check if a metric was extracted."""
        return self.metric_id is not None

    def has_multiple_metrics(self) -> bool:
        """HU3.4: Check if multiple metrics were detected."""
        return len(self.metrics) > 1


class EntityService:
    """
    Extracts entities from natural language queries.
    Banks are loaded from database, not hardcoded.
    """

    _bank_cache: Set[str] = set()
    _bank_cache_loaded: bool = False
    _bank_variations: dict = {}  # Maps variations to normalized names

    @classmethod
    async def load_banks_from_db(cls, session: AsyncSession) -> Set[str]:
        """
        Load all known bank names from database.
        Cached after first load.
        """
        if cls._bank_cache_loaded:
            return cls._bank_cache

        try:
            result = await session.execute(
                select(distinct(MonthlyKPI.banco_norm))
            )
            banks = {row[0] for row in result.fetchall() if row[0]}

            # Build variations map (lowercase -> original)
            cls._bank_variations = {}
            for bank in banks:
                # Original lowercase
                cls._bank_variations[bank.lower()] = bank
                # Without accents
                no_accents = (
                    bank.lower()
                    .replace("á", "a")
                    .replace("é", "e")
                    .replace("í", "i")
                    .replace("ó", "o")
                    .replace("ú", "u")
                    .replace("ñ", "n")
                )
                cls._bank_variations[no_accents] = bank

            cls._bank_cache = banks
            cls._bank_cache_loaded = True

            logger.info(
                "entity_service.banks_loaded",
                bank_count=len(cls._bank_cache),
                sample=list(cls._bank_cache)[:5]
            )

        except Exception as e:
            logger.error("entity_service.bank_load_error", error=str(e))
            # Fallback to empty set - will still work, just won't extract banks
            cls._bank_cache = set()
            cls._bank_cache_loaded = True

        return cls._bank_cache

    @classmethod
    def clear_cache(cls):
        """Clear the bank cache (useful for testing)."""
        cls._bank_cache = set()
        cls._bank_cache_loaded = False
        cls._bank_variations = {}

    @classmethod
    async def extract(cls, query: str, session: AsyncSession) -> ExtractedEntities:
        """
        Main extraction pipeline.
        Returns ExtractedEntities with all found entities.

        Args:
            query: Natural language query
            session: Database session for bank lookup

        Returns:
            ExtractedEntities with extracted banks, metric, dates
        """
        result = ExtractedEntities(raw_query=query)
        clean = query.lower()
        config = get_config()

        # CHANGED ORDER: Extract metric FIRST before removing banks
        # This prevents issues like "tasa efectiva del sistema" where "sistema" is both a bank and part of metric name

        # 1. Extract metric using config (from original query)
        result.metric_id = config.find_metric(clean)
        if result.metric_id:
            result.metric_display = config.get_metric_display_name(result.metric_id)
            result.metric_column = config.get_metric_column(result.metric_id)

        # 2. Extract dates using dateparser
        result.date_start, result.date_end, clean = cls._extract_dates(clean)

        # 3. Extract banks (from database)
        await cls.load_banks_from_db(session)
        result.banks = []

        for variation, normalized_bank in cls._bank_variations.items():
            # Use word boundary matching to avoid partial matches
            # e.g., "INVEX" should match but not "INVEXTRA"
            pattern = r'\b' + re.escape(variation) + r'\b'
            if re.search(pattern, clean, re.IGNORECASE):
                if normalized_bank not in result.banks:
                    result.banks.append(normalized_bank)
                # Remove from query to avoid confusion
                clean = re.sub(pattern, ' ', clean, flags=re.IGNORECASE)

        # 4. Clean up query
        result.clean_query = re.sub(r'\s+', ' ', clean).strip()

        logger.debug(
            "entity_service.extracted",
            banks=result.banks,
            metric=result.metric_id,
            date_start=str(result.date_start) if result.date_start else None,
            date_end=str(result.date_end) if result.date_end else None,
            clean_query=result.clean_query
        )

        return result

    @classmethod
    def _extract_dates(cls, text: str) -> Tuple[Optional[date], Optional[date], str]:
        """
        Extract date range from text using dateparser.
        Returns (start_date, end_date, cleaned_text).

        Supports patterns like:
        - "últimos 3 meses"
        - "últimos 6 meses"
        - "último año"
        - "desde enero 2024 hasta marzo 2024"
        - "en 2024"
        """
        today = date.today()
        start_date = None
        end_date = today
        clean_text = text

        # Pattern 1: "últimos X meses/años/semanas"
        pattern_ultimos = r'[úu]ltimos?\s+(\d+)\s+(mes(?:es)?|año(?:s)?|a[ñn]o(?:s)?|semana(?:s)?)'
        match = re.search(pattern_ultimos, text, re.IGNORECASE)

        if match:
            amount = int(match.group(1))
            unit = match.group(2).lower()

            if 'mes' in unit:
                parsed = dateparser.parse(
                    f"hace {amount} meses",
                    languages=['es'],
                    settings={'RELATIVE_BASE': datetime.now()}
                )
                if parsed:
                    start_date = parsed.date()
            elif 'año' in unit or 'ano' in unit:
                parsed = dateparser.parse(
                    f"hace {amount} años",
                    languages=['es'],
                    settings={'RELATIVE_BASE': datetime.now()}
                )
                if parsed:
                    start_date = parsed.date()
            elif 'semana' in unit:
                parsed = dateparser.parse(
                    f"hace {amount} semanas",
                    languages=['es'],
                    settings={'RELATIVE_BASE': datetime.now()}
                )
                if parsed:
                    start_date = parsed.date()

            # Remove matched text
            clean_text = re.sub(pattern_ultimos, ' ', clean_text, flags=re.IGNORECASE)
            return start_date, end_date, clean_text

        # Pattern 2: "desde X hasta Y"
        pattern_desde_hasta = r'desde\s+(.+?)\s+hasta\s+(.+?)(?:\s|$|,)'
        match = re.search(pattern_desde_hasta, text, re.IGNORECASE)
        if match:
            parsed_start = dateparser.parse(match.group(1), languages=['es'])
            parsed_end = dateparser.parse(match.group(2), languages=['es'])
            if parsed_start:
                start_date = parsed_start.date()
            if parsed_end:
                end_date = parsed_end.date()
            clean_text = re.sub(pattern_desde_hasta, ' ', clean_text, flags=re.IGNORECASE)
            return start_date, end_date, clean_text

        # Pattern 3: "entre X y Y"
        pattern_entre = r'entre\s+(.+?)\s+y\s+(.+?)(?:\s|$|,)'
        match = re.search(pattern_entre, text, re.IGNORECASE)
        if match:
            parsed_start = dateparser.parse(match.group(1), languages=['es'])
            parsed_end = dateparser.parse(match.group(2), languages=['es'])
            if parsed_start:
                start_date = parsed_start.date()
            if parsed_end:
                end_date = parsed_end.date()
            clean_text = re.sub(pattern_entre, ' ', clean_text, flags=re.IGNORECASE)
            return start_date, end_date, clean_text

        # Pattern 4: "en [mes] [año]" or "en [año]"
        pattern_en = r'en\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+(?:de\s+)?(\d{4})'
        match = re.search(pattern_en, text, re.IGNORECASE)
        if match:
            month_str = match.group(1)
            year_str = match.group(2)
            parsed = dateparser.parse(f"{month_str} {year_str}", languages=['es'])
            if parsed:
                start_date = parsed.date().replace(day=1)
                # End of month
                if parsed.month == 12:
                    end_date = date(parsed.year + 1, 1, 1)
                else:
                    end_date = date(parsed.year, parsed.month + 1, 1)
            clean_text = re.sub(pattern_en, ' ', clean_text, flags=re.IGNORECASE)
            return start_date, end_date, clean_text

        # Pattern 5: Just a year "en 2024" or "2024"
        pattern_year = r'\b(20\d{2})\b'
        match = re.search(pattern_year, text)
        if match:
            year = int(match.group(1))
            start_date = date(year, 1, 1)
            end_date = date(year, 12, 31)
            # Don't remove year from text as it might be part of other context

        return start_date, end_date, clean_text

    # =========================================================================
    # HU3.4: Helper methods for clarification detection
    # =========================================================================

    @staticmethod
    def has_vague_time_reference(query: str) -> Optional[str]:
        """
        HU3.4: Detect vague time references that need clarification.
        Returns the vague term found, or None.

        Examples:
            "IMOR reciente" -> "reciente"
            "evolución del ICOR" -> "evolución"
            "tendencia histórica" -> "histórico"
        """
        vague_terms = {
            "reciente": "reciente",
            "recientemente": "reciente",
            "actual": "actual",
            "actualidad": "actual",
            "pasado": "pasado",
            "anterior": "anterior",
            "histórico": "histórico",
            "historico": "histórico",
            "tendencia": "tendencia",
            "evolución": "evolución",
            "evolucion": "evolución",
        }

        query_lower = query.lower()
        for term, category in vague_terms.items():
            # Use word boundary to avoid partial matches
            pattern = r'\b' + re.escape(term) + r'\b'
            if re.search(pattern, query_lower):
                return category
        return None

    @staticmethod
    def is_comparison_query(query: str) -> bool:
        """
        HU3.4: Detect if query is asking for a comparison.

        Examples:
            "compara el IMOR" -> True
            "INVEX vs Sistema" -> True
            "diferencia de morosidad" -> True
        """
        comparison_keywords = [
            "compara", "comparar", "comparación", "comparacion",
            "versus", " vs ", " vs.", "contra",
            "diferencia", "diferencias",
            "mejor", "peor",
        ]

        query_lower = query.lower()
        return any(kw in query_lower for kw in comparison_keywords)

    @staticmethod
    def has_explicit_date_range(query: str) -> bool:
        """
        HU3.4: Check if query has explicit date specification.
        Used to determine if vague time clarification is needed.

        Examples:
            "IMOR de 2024" -> True
            "últimos 3 meses" -> True
            "IMOR reciente" -> False (vague)
        """
        explicit_patterns = [
            r'[úu]ltimos?\s+\d+\s+(mes|año|semana)',  # últimos X meses/años
            r'\b20\d{2}\b',  # Year like 2024
            r'desde\s+.+\s+hasta',  # desde X hasta Y
            r'entre\s+.+\s+y\s+',  # entre X y Y
            r'(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)',  # Month names
        ]

        query_lower = query.lower()
        return any(re.search(p, query_lower) for p in explicit_patterns)

    @classmethod
    async def extract_multiple_metrics(cls, query: str, session: AsyncSession) -> List[Tuple[str, str]]:
        """
        HU3.4: Extract ALL metrics mentioned in a query (for multi-metric detection).
        Returns list of (metric_id, metric_display) tuples.

        Examples:
            "IMOR y ICOR de INVEX" -> [("imor", "IMOR"), ("icor", "ICOR")]
            "cartera comercial y consumo" -> [("cartera_comercial", "..."), ("cartera_consumo", "...")]
        """
        config = get_config()
        found_metrics = []

        # Get all known metrics from config
        all_metrics = config.get_all_metric_options()

        query_lower = query.lower()

        for metric_opt in all_metrics:
            metric_id = metric_opt.get("id", "")
            metric_label = metric_opt.get("label", "")

            # Check if this metric's ID or label appears in query
            # Use word boundaries to avoid partial matches
            id_pattern = r'\b' + re.escape(metric_id.lower()) + r'\b'
            label_pattern = r'\b' + re.escape(metric_label.lower()) + r'\b'

            if re.search(id_pattern, query_lower) or re.search(label_pattern, query_lower):
                if metric_id not in [m[0] for m in found_metrics]:
                    found_metrics.append((metric_id, metric_label))

        return found_metrics
