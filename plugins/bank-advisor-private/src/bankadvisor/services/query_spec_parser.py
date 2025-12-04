"""
NL → QuerySpec Parser for BankAdvisor

Converts natural language banking queries to structured QuerySpec objects.

Architecture:
    1. LLM-based parsing (primary)
    2. Rule-based heuristics (fallback)

Design Philosophy:
    - LLM-first: Use LLM for complex queries
    - Fallback to rules: If LLM unavailable or fails
    - Honest about limitations: Mark queries as requiring clarification
"""

import re
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
import structlog

from ..specs import QuerySpec, TimeRangeSpec

logger = structlog.get_logger(__name__)


class QuerySpecParser:
    """
    Parses natural language queries into structured QuerySpec objects.

    Implementation: LLM-enhanced with rule-based fallback

    Usage:
        parser = QuerySpecParser()
        spec = await parser.parse(
            user_query="IMOR de INVEX últimos 3 meses",
            intent_hint="imor_cuadro",
            mode_hint="dashboard",
            llm_client=saptiva_client  # Optional
        )
    """

    # =========================================================================
    # CONFIGURATION
    # =========================================================================

    BANK_ALIASES: Dict[str, str] = {
        "invex": "INVEX",
        "banco invex": "INVEX",
        "sistema": "SISTEMA",
        "sistema bancario": "SISTEMA",
        "mercado": "SISTEMA",
        "promedio": "SISTEMA",
        "resto de bancos": "SISTEMA",
        "otros bancos": "SISTEMA",
        # Supported banks (in monthly_kpis)
        "banorte": "BANORTE",
        "bbva": "BBVA",
        "bbva bancomer": "BBVA",
        "bancomer": "BBVA",
        "santander": "SANTANDER",
        "hsbc": "HSBC",
        "citibanamex": "CITIBANAMEX",
        "banamex": "CITIBANAMEX",
        "scotiabank": "SCOTIABANK",
        "inbursa": "INBURSA",
    }

    METRIC_MAP: Dict[str, str] = {
        # IMOR - Índice de Morosidad
        "imor": "IMOR",
        "imor_cuadro": "IMOR",
        "morosidad": "IMOR",
        # ICOR - Índice de Cobertura
        "icor": "ICOR",
        "icor_cuadro": "ICOR",
        "cobertura": "ICOR",
        # Cartera
        "cartera_total": "CARTERA_TOTAL",
        "cartera total": "CARTERA_TOTAL",
        "cartera": "CARTERA_TOTAL",
        "cartera_comercial": "CARTERA_COMERCIAL",
        "cartera comercial": "CARTERA_COMERCIAL",
        "comercial": "CARTERA_COMERCIAL",
        "cartera comercial sin gobierno": "CARTERA_COMERCIAL",
        "cartera_consumo": "CARTERA_CONSUMO",
        "cartera consumo": "CARTERA_CONSUMO",
        "cartera de consumo": "CARTERA_CONSUMO",
        "cartera de crédito de consumo": "CARTERA_CONSUMO",
        "cartera de credito de consumo": "CARTERA_CONSUMO",
        "crédito de consumo": "CARTERA_CONSUMO",
        "credito de consumo": "CARTERA_CONSUMO",
        "cartera_vivienda": "CARTERA_VIVIENDA",
        "cartera vivienda": "CARTERA_VIVIENDA",
        "cartera vencida": "CARTERA_VENCIDA",
        "cartera_vencida": "CARTERA_VENCIDA",
        # Reservas
        "reservas": "RESERVAS",
        "reservas totales": "RESERVAS",
        "variación de reservas": "RESERVAS",
        "variacion de reservas": "RESERVAS",
        # ICAP - Índice de Capitalización
        "icap": "ICAP",
        "icap_cuadro": "ICAP",
        "icap_total": "ICAP",
        "capitalizacion": "ICAP",
        "capitalización": "ICAP",
        # TDA - Tasa de Deterioro Ajustada
        "tda": "TDA",
        "tda_cuadro": "TDA",
        "deterioro": "TDA",
        "tasa de deterioro": "TDA",
        "tasa deterioro ajustada": "TDA",
        # Etapas de Deterioro
        "etapas de deterioro": "ETAPAS_DETERIORO",
        "etapas deterioro": "ETAPAS_DETERIORO",
        # Pérdida Esperada
        "pérdida esperada": "PE_TOTAL",
        "perdida esperada": "PE_TOTAL",
        "pe_total": "PE_TOTAL",
        "pe total": "PE_TOTAL",
        # Quebrantos
        "quebrantos": "QUEBRANTOS",
        "quebrantos comerciales": "QUEBRANTOS",
        # Tasas de Interés - Corporativas
        "tasa_mn": "TASA_MN",
        "tasa mn": "TASA_MN",
        "tasa moneda nacional": "TASA_MN",
        "tasa corporativa mn": "TASA_MN",
        "tasa corporativa moneda nacional": "TASA_MN",
        "credito corporativo mn": "TASA_MN",
        "tasa_me": "TASA_ME",
        "tasa me": "TASA_ME",
        "tasa moneda extranjera": "TASA_ME",
        "tasa corporativa me": "TASA_ME",
        "tasa corporativa moneda extranjera": "TASA_ME",
        "credito corporativo me": "TASA_ME",
        # Tasas de Interés - Efectivas
        "tasa_sistema": "TASA_SISTEMA",
        "tasa sistema": "TASA_SISTEMA",
        "tasa efectiva": "TASA_SISTEMA",
        "tasa efectiva sistema": "TASA_SISTEMA",
        "tasa interés efectiva": "TASA_SISTEMA",
        "tasa interes efectiva": "TASA_SISTEMA",
        "tasa_invex_consumo": "TASA_INVEX_CONSUMO",
        "tasa invex consumo": "TASA_INVEX_CONSUMO",
        "tasa invex": "TASA_INVEX_CONSUMO",
        "tasa efectiva invex": "TASA_INVEX_CONSUMO",
        # Market Share / PDM
        "market share": "MARKET_SHARE",
        "participación de mercado": "MARKET_SHARE",
        "participacion de mercado": "MARKET_SHARE",
        "pdm": "MARKET_SHARE",
        "cuota de mercado": "MARKET_SHARE",
        # Activos Totales
        "activos totales": "ACTIVO_TOTAL",
        "activo total": "ACTIVO_TOTAL",
        "tamaño de bancos": "ACTIVO_TOTAL",
        "tamaño de los bancos": "ACTIVO_TOTAL",
        "tamaño de los bancos por activos": "ACTIVO_TOTAL",
        "tamaño por activos": "ACTIVO_TOTAL",
        "ranking de bancos": "ACTIVO_TOTAL",
        "ranking por activos": "ACTIVO_TOTAL",
        # Cartera por Segmento
        "cartera automotriz": "CARTERA_AUTOMOTRIZ",
        "credito automotriz": "CARTERA_AUTOMOTRIZ",
        "automotriz": "CARTERA_AUTOMOTRIZ",
        "autos": "CARTERA_AUTOMOTRIZ",
        "cartera nomina": "CARTERA_NOMINA",
        "credito nomina": "CARTERA_NOMINA",
        "nómina": "CARTERA_NOMINA",
        "nomina": "CARTERA_NOMINA",
        "tarjeta de credito": "CARTERA_TDC",
        "tarjeta credito": "CARTERA_TDC",
        "tdc": "CARTERA_TDC",
        "prestamos personales": "CARTERA_PERSONALES",
        "préstamos personales": "CARTERA_PERSONALES",
        "personales": "CARTERA_PERSONALES",
        # IMOR por Segmento
        "imor automotriz": "IMOR_AUTOMOTRIZ",
        "morosidad automotriz": "IMOR_AUTOMOTRIZ",
        "imor nomina": "IMOR_NOMINA",
        "imor tarjeta": "IMOR_TDC",
    }

    # Regex patterns for heuristic fallback
    LAST_N_MONTHS_PATTERN = re.compile(
        r"\b(?:últimos?|ultimo|ultimos)\s+(\d+)\s+(?:mes|meses)\b",
        re.IGNORECASE
    )
    LAST_N_QUARTERS_PATTERN = re.compile(
        r"\b(?:últimos?|ultimo|ultimos)\s+(\d+)?\s*(?:trimestre|trimestres)\b",
        re.IGNORECASE
    )
    YEAR_PATTERN = re.compile(r"\b(?:año\s+)?(\d{4})\b", re.IGNORECASE)
    DATE_RANGE_PATTERN = re.compile(
        r"\b(?:desde|from)\s+(\d{4}-\d{2}-\d{2})\s+(?:hasta|to|a)\s+(\d{4}-\d{2}-\d{2})\b",
        re.IGNORECASE
    )

    # =========================================================================
    # LLM PROMPT TEMPLATE
    # =========================================================================

    LLM_PROMPT_TEMPLATE = """Eres un parser de consultas bancarias. Convierte esta consulta de lenguaje natural a JSON estructurado.

Consulta del usuario: {user_query}
Pista de métrica: {intent_hint}
Modo sugerido: {mode_hint}

Métricas disponibles: IMOR, ICOR, CARTERA_COMERCIAL, CARTERA_TOTAL, CARTERA_CONSUMO, CARTERA_VIVIENDA, CARTERA_VENCIDA, RESERVAS, ICAP, TDA, TASA_MN, TASA_ME, PE_TOTAL, QUEBRANTOS, ETAPAS_DETERIORO, TASA_SISTEMA, TASA_INVEX_CONSUMO, MARKET_SHARE, ACTIVO_TOTAL, IMOR_AUTOMOTRIZ, CARTERA_AUTOMOTRIZ

Aliases importantes:
- "pérdida esperada" → PE_TOTAL
- "quebrantos comerciales" → QUEBRANTOS
- "etapas de deterioro" → ETAPAS_DETERIORO
- "tasa efectiva sistema" → TASA_SISTEMA
- "tasa invex consumo" → TASA_INVEX_CONSUMO
- "tasa corporativa mn/me" → TASA_MN/TASA_ME
- "market share" / "PDM" / "participación de mercado" → MARKET_SHARE
- "tamaño de bancos" / "activos totales" / "ranking por activos" → ACTIVO_TOTAL
- "IMOR automotriz" / "morosidad automotriz" → IMOR_AUTOMOTRIZ
- "cartera automotriz" / "crédito automotriz" → CARTERA_AUTOMOTRIZ

Bancos disponibles: INVEX, SISTEMA, BANORTE, BBVA, SANTANDER, HSBC, CITIBANAMEX, SCOTIABANK

Para rankings de bancos (como "tamaño de bancos por activos"), usa bank_names: [] (vacío) para obtener todos los bancos.

Tipos de rango temporal:
- last_n_months: "últimos 3 meses" → {{"type": "last_n_months", "n": 3}}
- last_n_quarters: "último trimestre" → {{"type": "last_n_quarters", "n": 1}}
- year: "2024" → {{"type": "year", "start_date": "2024-01-01", "end_date": "2024-12-31"}}
- between_dates: "desde 2023-01-01 hasta 2024-01-01"
- all: Sin especificar tiempo

Responde SOLO con JSON válido siguiendo este esquema:
{{
  "metric": "IMOR",
  "bank_names": ["INVEX"],
  "time_range": {{
    "type": "last_n_months",
    "n": 3,
    "start_date": null,
    "end_date": null
  }},
  "granularity": "month",
  "visualization_type": "line",
  "comparison_mode": false,
  "requires_clarification": false,
  "missing_fields": [],
  "confidence_score": 1.0
}}

Si la consulta es ambigua o menciona métricas/bancos no disponibles:
- requires_clarification: true
- missing_fields: ["metric (unsupported)" o "bank (unsupported)" o "time_range"]
- confidence_score: < 0.6

Ejemplos:

Input: "IMOR de INVEX últimos 3 meses"
Output:
{{
  "metric": "IMOR",
  "bank_names": ["INVEX"],
  "time_range": {{"type": "last_n_months", "n": 3}},
  "granularity": "month",
  "visualization_type": "line",
  "comparison_mode": false,
  "requires_clarification": false,
  "missing_fields": [],
  "confidence_score": 1.0
}}

Input: "cartera comercial 2024"
Output:
{{
  "metric": "CARTERA_COMERCIAL",
  "bank_names": [],
  "time_range": {{"type": "year", "start_date": "2024-01-01", "end_date": "2024-12-31"}},
  "granularity": "month",
  "visualization_type": "line",
  "comparison_mode": false,
  "requires_clarification": false,
  "missing_fields": [],
  "confidence_score": 0.9
}}

Input: "ICAP del sistema"
Output:
{{
  "metric": "ICAP",
  "bank_names": ["SISTEMA"],
  "time_range": {{"type": "all"}},
  "granularity": "month",
  "visualization_type": "bar",
  "comparison_mode": false,
  "requires_clarification": false,
  "missing_fields": [],
  "confidence_score": 0.9
}}

Input: "compara IMOR de INVEX vs Banorte"
Output:
{{
  "metric": "IMOR",
  "bank_names": ["INVEX"],
  "time_range": {{"type": "all"}},
  "granularity": "month",
  "visualization_type": "line",
  "comparison_mode": true,
  "requires_clarification": true,
  "missing_fields": ["bank (Banorte not available in database)"],
  "confidence_score": 0.7
}}

Ahora parsea esta consulta y responde SOLO con el JSON:"""

    async def parse(
        self,
        user_query: str,
        intent_hint: Optional[str] = None,
        mode_hint: Optional[str] = None,
        llm_client: Optional[Any] = None
    ) -> QuerySpec:
        """
        Parse natural language query to QuerySpec.

        Strategy:
            1. Try LLM parsing if client available
            2. Fall back to heuristics if LLM fails
            3. Merge results with confidence weighting

        Args:
            user_query: Raw user query
            intent_hint: Hint from IntentService
            mode_hint: Visualization mode hint
            llm_client: Optional LLM client (Saptiva/OpenAI compatible)

        Returns:
            QuerySpec
        """
        logger.info(
            "query_spec_parser.parse",
            user_query=user_query,
            intent_hint=intent_hint,
            has_llm=llm_client is not None
        )

        # Try LLM first if available
        if llm_client:
            try:
                spec = await self._parse_with_llm(
                    user_query, intent_hint, mode_hint, llm_client
                )
                if spec and spec.confidence_score >= 0.6:
                    logger.info("query_spec_parser.llm_success", confidence=spec.confidence_score)
                    return spec
                else:
                    logger.warning("query_spec_parser.llm_low_confidence", confidence=spec.confidence_score if spec else 0)
            except Exception as e:
                logger.warning("query_spec_parser.llm_failed", error=str(e))

        # Fallback to heuristics
        logger.info("query_spec_parser.using_heuristics")
        return await self._parse_with_heuristics(user_query, intent_hint, mode_hint)

    async def _parse_with_llm(
        self,
        user_query: str,
        intent_hint: Optional[str],
        mode_hint: Optional[str],
        llm_client: Any
    ) -> Optional[QuerySpec]:
        """
        Parse using LLM.

        Args:
            user_query: User query
            intent_hint: Intent hint
            mode_hint: Mode hint
            llm_client: LLM client with chat.completions.create() interface

        Returns:
            QuerySpec or None if parsing failed
        """
        prompt = self.LLM_PROMPT_TEMPLATE.format(
            user_query=user_query,
            intent_hint=intent_hint or "no hint",
            mode_hint=mode_hint or "dashboard"
        )

        try:
            # Call LLM (Saptiva/OpenAI compatible interface)
            response = await llm_client.chat.completions.create(
                model="gpt-4",  # Or Saptiva model
                messages=[
                    {"role": "system", "content": "You are a JSON parser. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=500
            )

            # Extract JSON from response
            content = response.choices[0].message.content.strip()

            # Try to extract JSON if wrapped in markdown
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            # Parse JSON
            spec_dict = json.loads(content)

            # Convert to QuerySpec
            spec = self._dict_to_query_spec(spec_dict)

            logger.info("query_spec_parser.llm_parsed", metric=spec.metric, confidence=spec.confidence_score)
            return spec

        except json.JSONDecodeError as e:
            logger.error("query_spec_parser.llm_json_error", error=str(e), content=content[:200])
            return None
        except Exception as e:
            logger.error("query_spec_parser.llm_error", error=str(e), exc_info=True)
            return None

    async def _parse_with_heuristics(
        self,
        user_query: str,
        intent_hint: Optional[str],
        mode_hint: Optional[str]
    ) -> QuerySpec:
        """
        Parse using rule-based heuristics (fallback).

        This is the same logic as Phase 1, but packaged as fallback.
        """
        missing = []
        confidence = 1.0

        # Extract metric
        metric = self._extract_metric_heuristic(user_query, intent_hint)
        if not metric:
            missing.append("metric")
            confidence *= 0.5
            metric = ""

        # Extract banks
        bank_names = self._extract_banks_heuristic(user_query)
        if any(b is None for b in bank_names):
            missing.append("bank (unsupported bank requested)")
            confidence *= 0.3
        bank_names = [b for b in bank_names if b is not None]

        # Extract time range
        time_range = self._extract_time_range_heuristic(user_query)
        if time_range is None:
            # Ranking metrics don't require time_range - they use latest period
            ranking_metrics = {"ACTIVO_TOTAL", "MARKET_SHARE"}
            if metric not in ranking_metrics:
                missing.append("time_range")
                confidence *= 0.7
            time_range = TimeRangeSpec(type="all")

        # Comparison mode
        comparison_mode = len(bank_names) > 1 or "compar" in user_query.lower()

        # Visualization type
        viz_type = self._determine_viz_type(mode_hint, time_range)

        spec = QuerySpec(
            metric=metric,
            bank_names=bank_names,
            time_range=time_range,
            granularity="month",
            visualization_type=viz_type,
            comparison_mode=comparison_mode,
            requires_clarification=bool(missing),
            missing_fields=missing,
            confidence_score=confidence
        )

        logger.info(
            "query_spec_parser.heuristic_result",
            metric=spec.metric,
            requires_clarification=spec.requires_clarification,
            confidence=spec.confidence_score
        )

        return spec

    # =========================================================================
    # HEURISTIC EXTRACTION METHODS
    # =========================================================================

    def _extract_metric_heuristic(self, user_query: str, intent_hint: Optional[str]) -> Optional[str]:
        """Extract metric using rules."""
        if intent_hint:
            metric = self.METRIC_MAP.get(intent_hint.lower())
            if metric is not None:
                return metric

        query_lower = user_query.lower()
        # Sort by keyword length descending to match longer phrases first
        # e.g., "cartera de consumo" should match before "cartera"
        sorted_keywords = sorted(self.METRIC_MAP.items(), key=lambda x: len(x[0]), reverse=True)
        for keyword, canonical_name in sorted_keywords:
            if keyword in query_lower:
                return canonical_name

        return None

    def _extract_banks_heuristic(self, user_query: str) -> List[Optional[str]]:
        """Extract banks using rules."""
        query_lower = user_query.lower()
        found_banks = []

        for alias, canonical in self.BANK_ALIASES.items():
            if alias in query_lower:
                found_banks.append(canonical)

        # Deduplicate
        seen = set()
        deduped = []
        for bank in found_banks:
            if bank not in seen:
                seen.add(bank)
                deduped.append(bank)

        return deduped

    def _extract_time_range_heuristic(self, user_query: str) -> Optional[TimeRangeSpec]:
        """Extract time range using regex."""
        # Last N months
        match = self.LAST_N_MONTHS_PATTERN.search(user_query)
        if match:
            n = int(match.group(1))
            return TimeRangeSpec(type="last_n_months", n=n)

        # Last N quarters
        match = self.LAST_N_QUARTERS_PATTERN.search(user_query)
        if match:
            n_str = match.group(1)
            n = int(n_str) if n_str else 1
            return TimeRangeSpec(type="last_n_quarters", n=n)

        # Year
        match = self.YEAR_PATTERN.search(user_query)
        if match:
            year = match.group(1)
            return TimeRangeSpec(
                type="year",
                start_date=f"{year}-01-01",
                end_date=f"{year}-12-31"
            )

        # Date range
        match = self.DATE_RANGE_PATTERN.search(user_query)
        if match:
            start, end = match.groups()
            return TimeRangeSpec(
                type="between_dates",
                start_date=start,
                end_date=end
            )

        return None

    def _determine_viz_type(self, mode_hint: Optional[str], time_range: TimeRangeSpec) -> str:
        """Determine visualization type."""
        if mode_hint and "timeline" in mode_hint.lower():
            return "line"
        if time_range.type in ["last_n_months", "last_n_quarters", "year", "between_dates"]:
            return "line"
        return "bar"

    def _dict_to_query_spec(self, spec_dict: Dict[str, Any]) -> QuerySpec:
        """Convert LLM JSON response to QuerySpec."""
        time_range_dict = spec_dict.get("time_range", {})
        time_range = TimeRangeSpec(
            type=time_range_dict.get("type", "all"),
            n=time_range_dict.get("n"),
            start_date=time_range_dict.get("start_date"),
            end_date=time_range_dict.get("end_date")
        )

        return QuerySpec(
            metric=spec_dict.get("metric", ""),
            bank_names=spec_dict.get("bank_names", []),
            time_range=time_range,
            granularity=spec_dict.get("granularity", "month"),
            visualization_type=spec_dict.get("visualization_type", "line"),
            comparison_mode=spec_dict.get("comparison_mode", False),
            requires_clarification=spec_dict.get("requires_clarification", False),
            missing_fields=spec_dict.get("missing_fields", []),
            confidence_score=spec_dict.get("confidence_score", 1.0)
        )


# =========================================================================
# CONVENIENCE FUNCTION
# =========================================================================

async def parse_query(
    user_query: str,
    intent_hint: Optional[str] = None,
    mode_hint: Optional[str] = None,
    llm_client: Optional[Any] = None
) -> QuerySpec:
    """
    Convenience function for parsing queries.

    Example:
        >>> spec = await parse_query(
        ...     "IMOR de INVEX últimos 3 meses",
        ...     llm_client=saptiva_client
        ... )
    """
    parser = QuerySpecParser()
    return await parser.parse(user_query, intent_hint, mode_hint, llm_client)
