"""
MCP Client for BankAdvisor Analytics Plugin (BA-P0-001).

This module provides a client wrapper to invoke the bank_analytics
MCP tool on the bank-advisor microservice.

Usage:
    from services.bank_analytics_client import query_bank_analytics

    result = await query_bank_analytics(
        metric_or_query="IMOR de INVEX últimos 3 meses",
        mode="dashboard",
    )
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional

import httpx
import structlog

from ..schemas.bank_chart import BankChartData, BankAnalyticsResponse, BankClarificationData, ClarificationOption

logger = structlog.get_logger(__name__)

# Configuration from environment
BANK_ADVISOR_URL = os.getenv("BANK_ADVISOR_URL", "http://bank-advisor:8002")
BANK_ADVISOR_TIMEOUT = int(os.getenv("BANK_ADVISOR_TIMEOUT", "30"))
USE_BANK_ADVISOR = os.getenv("USE_BANK_ADVISOR", "true").lower() == "true"


class BankAdvisorUnavailableError(Exception):
    """Raised when the bank-advisor MCP service is unavailable."""
    pass


class BankAdvisorQueryError(Exception):
    """Raised when a query to bank-advisor fails."""
    pass


async def query_bank_analytics(
    metric_or_query: str,
    mode: str = "dashboard",
) -> BankAnalyticsResponse:
    """
    Query banking analytics via MCP protocol to bank-advisor service.

    Args:
        metric_or_query: Natural language query or metric name
            Examples: "IMOR", "cartera comercial", "ICAP de INVEX últimos 3 meses"
        mode: Visualization mode ("dashboard" or "timeline")

    Returns:
        BankAnalyticsResponse with BankChartData if successful

    Raises:
        BankAdvisorUnavailableError: If bank-advisor service is unavailable
        BankAdvisorQueryError: If the query fails (ambiguous, invalid, etc.)
    """
    if not USE_BANK_ADVISOR:
        raise BankAdvisorUnavailableError(
            "Bank advisor is disabled. Set USE_BANK_ADVISOR=true in environment."
        )

    logger.info(
        "bank_analytics.query",
        url=BANK_ADVISOR_URL,
        metric_or_query=metric_or_query,
        mode=mode,
    )

    try:
        async with httpx.AsyncClient(timeout=BANK_ADVISOR_TIMEOUT) as client:
            # JSON-RPC 2.0 call to RPC endpoint (direct endpoint, not FastMCP)
            response = await client.post(
                f"{BANK_ADVISOR_URL}/rpc",
                json={
                    "jsonrpc": "2.0",
                    "id": "bank-analytics-call",
                    "method": "tools/call",
                    "params": {
                        "name": "bank_analytics",
                        "arguments": {
                            "metric_or_query": metric_or_query,
                            "mode": mode,
                        },
                    },
                },
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            rpc_response = response.json()

            # Handle JSON-RPC error
            if "error" in rpc_response:
                error = rpc_response["error"]
                raise BankAdvisorQueryError(
                    f"MCP error: {error.get('message', str(error))}"
                )

            # Extract result from JSON-RPC response
            result = rpc_response.get("result", {})

            # Handle nested content structure from FastMCP
            if isinstance(result, dict) and "content" in result:
                content = result["content"]
                if isinstance(content, list) and len(content) > 0:
                    first_content = content[0]
                    if isinstance(first_content, dict) and "text" in first_content:
                        result = json.loads(first_content["text"])

            # Handle enhanced response format with metadata wrapper (v1.0.0+)
            if isinstance(result, dict) and "success" in result and "data" in result:
                # New format: {success: true, data: {...}, metadata: {...}}
                if not result.get("success"):
                    # Tool returned success=false
                    error_msg = result.get("metadata", {}).get("error", "Unknown error")
                    raise BankAdvisorQueryError(f"Tool execution failed: {error_msg}")

                # Extract the actual data payload
                tool_data = result.get("data", {})
                tool_metadata = result.get("metadata", {})

                # Check for legacy error format within data
                if isinstance(tool_data, dict) and tool_data.get("error"):
                    error_type = tool_data.get("error")
                    message = tool_data.get("message", "Unknown error")
                    raise BankAdvisorQueryError(f"{error_type}: {message}")

                # HU3.1: Check for clarification response
                if isinstance(tool_data, dict) and tool_data.get("type") == "clarification":
                    logger.info(
                        "bank_analytics.clarification_detected",
                        message=tool_data.get("message"),
                        options_count=len(tool_data.get("options", [])),
                    )

                    # Build ClarificationOption list from raw options
                    options = []
                    for opt in tool_data.get("options", []):
                        if isinstance(opt, dict):
                            options.append(ClarificationOption(
                                id=opt.get("id", ""),
                                label=opt.get("label", opt.get("id", "")),
                                description=opt.get("description")
                            ))

                    clarification_data = BankClarificationData(
                        type="clarification",
                        message=tool_data.get("message", "Por favor, especifica tu consulta."),
                        options=options,
                        context=tool_data.get("context")
                    )

                    return BankAnalyticsResponse(
                        success=True,
                        clarification=clarification_data,
                    )

                # Build BankChartData from tool_data (which has plotly_config, title, etc.)
                # BA-P0-004: Pass tool_metadata to merge sql_generated into metadata
                # Note: tool_data is result["data"], where plotly_config actually lives
                chart_data = _build_chart_data(tool_data, metric_or_query, external_metadata=tool_metadata)

                # Log metadata if available
                if tool_metadata:
                    logger.info(
                        "bank_analytics.metadata",
                        version=tool_metadata.get("version"),
                        pipeline=tool_metadata.get("pipeline"),
                        execution_time_ms=tool_metadata.get("execution_time_ms"),
                        template=tool_metadata.get("template_used")
                    )
            else:
                # Legacy format without metadata wrapper
                # Check for tool-level errors (ambiguous query, validation failed)
                if isinstance(result, dict) and result.get("error"):
                    error_type = result.get("error")
                    message = result.get("message", "Unknown error")

                    if error_type == "ambiguous_query":
                        options = result.get("options", [])
                        suggestion = result.get("suggestion", "")
                        raise BankAdvisorQueryError(
                            f"Ambiguous query: {message}. Options: {options}. {suggestion}"
                        )
                    elif error_type == "validation_failed":
                        raise BankAdvisorQueryError(f"Validation failed: {message}")
                    else:
                        raise BankAdvisorQueryError(f"{error_type}: {message}")

                # HU3.1: Check for clarification response (legacy format)
                if isinstance(result, dict) and result.get("type") == "clarification":
                    logger.info(
                        "bank_analytics.clarification_detected_legacy",
                        message=result.get("message"),
                        options_count=len(result.get("options", [])),
                    )

                    # Build ClarificationOption list from raw options
                    options = []
                    for opt in result.get("options", []):
                        if isinstance(opt, dict):
                            options.append(ClarificationOption(
                                id=opt.get("id", ""),
                                label=opt.get("label", opt.get("id", "")),
                                description=opt.get("description")
                            ))

                    clarification_data = BankClarificationData(
                        type="clarification",
                        message=result.get("message", "Por favor, especifica tu consulta."),
                        options=options,
                        context=result.get("context")
                    )

                    return BankAnalyticsResponse(
                        success=True,
                        clarification=clarification_data,
                    )

                # Build BankChartData from successful result
                chart_data = _build_chart_data(result, metric_or_query)

            logger.info(
                "bank_analytics.success",
                metric=chart_data.metric_name,
                banks=chart_data.bank_names,
                data_as_of=chart_data.data_as_of,
            )

            return BankAnalyticsResponse(
                success=True,
                data=chart_data,
            )

    except httpx.HTTPStatusError as e:
        logger.error(
            "bank_analytics.http_error",
            status_code=e.response.status_code,
            detail=e.response.text,
        )
        raise BankAdvisorUnavailableError(
            f"Bank advisor returned HTTP {e.response.status_code}: {e.response.text}"
        )

    except httpx.RequestError as e:
        logger.error("bank_analytics.connection_error", error=str(e))
        raise BankAdvisorUnavailableError(
            f"Failed to connect to bank advisor at {BANK_ADVISOR_URL}: {str(e)}"
        )

    except BankAdvisorQueryError:
        raise  # Re-raise query errors as-is

    except Exception as e:
        logger.error("bank_analytics.unexpected_error", error=str(e), exc_info=True)
        raise BankAdvisorQueryError(f"Unexpected error: {str(e)}")


def _build_chart_data(result: Dict[str, Any], query: str, external_metadata: Optional[Dict[str, Any]] = None) -> BankChartData:
    """
    Transform MCP tool result into BankChartData schema.

    Args:
        result: Raw result from bank_analytics MCP tool
        query: Original query string
        external_metadata: Optional metadata from wrapper (for new format responses)

    Returns:
        BankChartData instance
    """
    # Extract metadata - merge external metadata (from wrapper) with internal metadata
    # BA-P0-004: External metadata contains sql_generated, pipeline, etc.
    internal_metadata = result.get("metadata", {})
    metadata = {**internal_metadata, **(external_metadata or {})}

    # Log metadata merge for debugging
    logger.info(
        "bank_analytics._build_chart_data.metadata_merge",
        has_internal=bool(internal_metadata),
        has_external=bool(external_metadata),
        has_sql_generated=bool(metadata.get("sql_generated")),
        metadata_keys=list(metadata.keys()) if metadata else []
    )

    data = result.get("data", {})
    plotly_config = result.get("plotly_config", {})

    # Extract time range from data
    months = data.get("months", [])
    time_range = {
        "start": months[0].get("fecha", "") if months else "",
        "end": months[-1].get("fecha", "") if months else "",
    }

    # Extract bank names from plotly traces
    bank_names = []
    if "data" in plotly_config:
        for trace in plotly_config["data"]:
            if trace.get("name"):
                bank_names.append(trace["name"])

    # Determine metric name from result or query
    metric_name = metadata.get("metric", query)
    if "title" in result:
        # Try to extract metric from title
        title = result["title"]
        if " - " in title:
            metric_name = title.split(" - ")[0].strip()

    return BankChartData(
        type="bank_chart",
        metric_name=metric_name,
        bank_names=bank_names or ["INVEX", "Sistema"],
        time_range={"start": time_range["start"], "end": time_range["end"]},
        plotly_config={
            "data": plotly_config.get("data", []),
            "layout": plotly_config.get("layout", {}),
            "config": plotly_config.get("config", {"responsive": True}),
        },
        data_as_of=result.get("data_as_of", metadata.get("data_as_of", "")),
        source="bank-advisor-mcp",
        title=result.get("title"),
        metadata=metadata,  # BA-P0-004: Include metadata with sql_generated
    )


async def check_bank_advisor_health() -> bool:
    """
    Check if the bank-advisor service is healthy.

    Returns:
        True if service is available, False otherwise
    """
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{BANK_ADVISOR_URL}/health")
            return response.status_code == 200
    except Exception:
        return False


async def _classify_with_llm(message: str) -> bool:
    """
    Use LLM to classify if a message is a banking query.

    This is called only for ambiguous cases where keywords are not sufficient.
    Uses a small, fast model with a focused prompt.
    """
    try:
        from .saptiva_client import SaptivaClient, SaptivaRequest, SaptivaMessage

        client = SaptivaClient()

        # Focused prompt for classification with edge case handling
        classification_prompt = """Eres un clasificador especializado de consultas bancarias y financieras mexicanas.

Tu tarea: Determinar si la consulta es sobre BANCA, FINANZAS o INDICADORES BANCARIOS.

Responde SOLO con "SÍ" o "NO".

Ejemplos de consultas bancarias (responde SÍ):
- Indicadores: IMOR, ICOR, ICAP, ROE, ROA, morosidad, cartera vencida
- Bancos: INVEX, Banorte, BBVA, Santander, Banamex, HSBC, Scotiabank
- Métricas: capitalización, liquidez, solvencia, reservas, provisiones
- Productos: créditos, hipotecas, tarjetas (en contexto bancario)
- Reguladores: CNBV, Banxico, reportes financieros
- Análisis: comparaciones de bancos, evolución de indicadores

Ejemplos de consultas NO bancarias (responde NO):
1. HISTORIA GENERAL: "Historia de la revolución mexicana" → NO (aunque tenga "histórico")
2. GEOGRAFÍA: "Capital de Francia" → NO (capital geográfico, no financiero)
3. NOMBRES DE CALLES: "Hipotecario el nombre de una calle" → NO (nombre de lugar, no producto)
4. PRODUCTOS FÍSICOS: "Cartera de mano de cuero", "Banco de madera" → NO
5. OTROS TEMAS: Clima, recetas, películas, programación, deportes, salud

REGLAS CRÍTICAS:
- "Histórico/historia" en contexto general → NO (solo SÍ si es historia bancaria)
- "Capital" en contexto geográfico → NO (solo SÍ si es capital financiero)
- "Hipotecario" como nombre de lugar → NO (solo SÍ si es producto bancario)
- "Banco" como mueble/estructura → NO (solo SÍ si es institución financiera)
- "Cartera" como bolso/accesorio → NO (solo SÍ si es cartera de crédito)

Consulta a clasificar: "{message}"

Responde SÍ solo si es claramente sobre banca/finanzas. En duda, responde NO.

Tu respuesta (SÍ o NO):"""

        request = SaptivaRequest(
            model="gpt-4o-mini",  # Fast, cheap model for classification
            messages=[
                SaptivaMessage(role="user", content=classification_prompt.format(message=message))
            ],
            temperature=0.0,  # Deterministic
            max_tokens=10,  # We only need "SÍ" or "NO"
            stream=False
        )

        response = await client.chat_completion(request)

        if response and response.choices:
            answer = response.choices[0].get("message", {}).get("content", "").strip().upper()
            # Check if answer contains affirmative
            is_banking = any(word in answer for word in ["SÍ", "SI", "YES", "TRUE", "VERDADERO"])

            logger.debug(
                "LLM classification completed",
                message_preview=message[:50],
                llm_answer=answer,
                classified_as_banking=is_banking
            )

            return is_banking

        # Fallback to False if no response
        return False

    except Exception as e:
        logger.warning(
            "LLM classification failed, falling back to False",
            error=str(e),
            message_preview=message[:50]
        )
        return False


async def is_bank_query(message: str) -> bool:
    """
    Hybrid banking query detection with LLM fallback.

    Strategy:
    1. Check Redis cache for previous classification
    2. Fast-path: High-confidence keywords → return True immediately
    3. Negative keywords → return False immediately
    4. Ambiguous cases → Use LLM classifier
    5. Cache result in Redis

    Args:
        message: User message text

    Returns:
        True if message appears to be a banking query
    """
    # 1. Check cache first
    from ..core.redis_cache import get_redis_cache
    import hashlib
    import re

    try:
        cache = await get_redis_cache()
        # Create cache key from message hash
        message_hash = hashlib.md5(message.encode()).hexdigest()
        cache_key = f"bank_query_classification:{message_hash}"

        if cache:
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                logger.debug(
                    "Bank query classification loaded from cache",
                    message_preview=message[:50],
                    cached_result=cached_result
                )
                return cached_result
    except Exception as e:
        logger.warning("Failed to access cache for bank query classification", error=str(e))
        cache = None

    message_lower = message.lower()

    # 1. Financial metrics and indicators (high priority)
    financial_metrics = [
        # Core risk metrics
        "imor", "icor", "icap", "roi", "roe", "roa",
        "morosidad", "mora", "vencida", "vencido",

        # Portfolio and credit metrics
        "cartera", "portafolio", "portfolio",
        "cartera comercial", "cartera consumo", "cartera vivienda",
        "sin gob", "sin gobierno", "cc",

        # Reserves and provisions
        "reservas", "provisiones", "reservas totales",

        # Capital and solvency
        "capitalización", "capitalizacion", "capital",
        "solvencia", "liquidez",

        # Margins and rates
        "margen", "spread", "diferencial",
        "tasa", "tasas", "interés", "interes",
        "tasa efectiva", "tasa de interés efectiva",
        "tasa corporativo", "tasa corporativa",
        "mn", "me", "moneda nacional", "moneda extranjera",

        # Growth and performance
        "crecimiento", "variación", "variacion",
        "rendimiento", "rentabilidad",

        # Balance sheet items
        "activos", "pasivos", "patrimonio",
        "utilidad", "utilidades", "ganancia",

        # Credit quality and loss metrics
        "quebranto", "quebrantos", "castigo", "castigos",
        "quebrantos comerciales",
        "pérdida esperada", "perdida esperada", "pérdida esperada total",
        "deterioro", "etapa", "etapas", "etapas de deterioro",
        "tasa de deterioro", "deterioro ajustada"
    ]

    # 2. Bank names (Mexican financial institutions)
    bank_names = [
        "invex", "banorte", "bancomer", "bbva", "banamex", "citibanamex",
        "santander", "hsbc", "scotiabank", "inbursa", "azteca",
        "banregio", "bajio", "banjercito", "afirme", "mifel",
        "ve por mas", "multiva", "intercam", "actinver",
        "banco", "bancos", "banca", "bancario", "bancaria", "bancarios"
    ]

    # 3. Banking product types
    banking_products = [
        "comercial", "consumo", "vivienda", "hipotecario", "hipoteca",
        "automotriz", "automotor", "autos", "vehículos", "vehiculos",
        "pyme", "empresarial", "corporativo",
        "tarjeta", "crédito", "credito", "préstamo", "prestamo",
        "crédito de consumo", "credito de consumo",
        "financiamiento", "leasing", "arrendamiento",
        "ahorro", "inversión", "inversion", "cuenta", "depósito", "deposito",
        "nómina", "nomina"
    ]

    # 4. Regulatory and institutional terms
    regulatory_terms = [
        "cnbv", "banxico", "banco de méxico", "banco de mexico",
        "comisión nacional", "comision nacional",
        "regulación", "regulacion", "normativa",
        "indicador", "indicadores", "métrica", "metrica",
        "reporte", "informe", "estadística", "estadistica"
    ]

    # 5. Query patterns that suggest comparison or analysis
    query_patterns = [
        "comparar", "comparación", "comparacion", "versus", "vs",
        "frente a", "frente al", "contra", "respecto a", "respecto al",
        "evolución", "evolucion", "tendencia", "histórico", "historico",
        "ha evolucionado", "cómo ha", "como ha",
        "análisis", "analisis", "desempeño", "desempeno", "performance",
        "ranking", "top", "mejor", "peor", "líder", "lider",
        "trimestre", "semestre", "anual", "mensual",
        "últimos", "ultimos", "último", "ultimo", "reciente", "actual",
        "porcentaje", "participación", "participacion", "%",
        "cuánto", "cuanto", "qué", "que"
    ]

    # 6. Financial/banking context words
    financial_context = [
        "financiero", "financiera", "financieros", "financieras",
        "económico", "economico", "economía", "economia",
        "sector bancario", "sistema financiero", "sistema bancario",
        "mercado", "industria", "resto de bancos", "otros bancos",
        "competencia", "competidores", "pares",
        "tamaño", "ranking", "cada banco", "por banco"
    ]

    # Check all categories
    all_keywords = (
        financial_metrics +
        bank_names +
        banking_products +
        regulatory_terms +
        query_patterns +
        financial_context
    )

    # 2. Fast-path: High-confidence banking keywords (immediate True)
    high_confidence_keywords = [
        "imor", "icor", "icap", "roi", "roe", "roa",
        "invex", "banorte", "bbva", "santander", "citibanamex",
        "cnbv", "banxico",
        "morosidad", "cartera vencida",
    ]

    for keyword in high_confidence_keywords:
        if keyword in message_lower:
            result = True
            logger.debug(
                "Bank query detected (high-confidence keyword)",
                keyword=keyword,
                message_preview=message[:50]
            )
            # Cache result
            if cache:
                try:
                    await cache.set(cache_key, result, expire=3600)  # 1 hour cache
                except Exception:
                    pass
            return result

    # 3. Negative keywords - very unlikely to be banking (immediate False)
    negative_keywords = [
        # Food & Cooking
        "receta", "cocina", "cocinar", "ingredientes", "menú",
        "restaurante", "comida", "platillo", "bebida",

        # Weather & Nature
        "clima", "tiempo atmosférico", "lluvia", "temperatura", "pronóstico",

        # Entertainment
        "película", "serie", "música", "canción", "artista", "actor",
        "videojuego", "juego", "película", "documental", "anime",

        # Programming & Tech
        "código python", "código javascript", "programación", "código",
        "función python", "script", "algoritmo", "debugear",
        "variable", "sintaxis", "compilar",

        # Sports
        "deporte", "fútbol", "basketball", "tenis", "partido",
        "jugador", "equipo deportivo", "gol",

        # History (general, non-banking)
        "historia de la revolución", "guerra mundial", "época prehispánica",
        "conquista española", "independencia de méxico",

        # Geography
        "capital de", "país de", "ciudad de", "ubicado en",
        "geografía", "continente", "océano",

        # Health & Fitness
        "salud", "ejercicio", "dieta", "médico", "enfermedad",
        "hospital", "síntoma", "tratamiento",

        # Education (non-financial)
        "escuela", "universidad", "curso de", "aprender",
        "estudiar", "examen", "tarea",

        # Physical Products
        "de cuero", "de madera", "de metal", "de plástico",
        "mueble", "decoración", "jardín",

        # Street/Place Names
        "nombre de una calle", "ubicación de", "dirección de",
        "colonia", "avenida", "boulevard",

        # General Non-Banking
        "hora en", "traducir", "significado de", "sinónimo",
        "horario de", "cómo llegar", "distancia entre"
    ]

    for keyword in negative_keywords:
        if keyword in message_lower:
            result = False
            logger.debug(
                "Bank query rejected (negative keyword)",
                keyword=keyword,
                message_preview=message[:50]
            )
            # Cache result
            if cache:
                try:
                    await cache.set(cache_key, result, expire=3600)
                except Exception:
                    pass
            return result

    # 3.5. Special filtering for ambiguous banking terms in non-banking contexts
    # Filter "histórico" when used for general history (not banking history)
    if "histórico" in message_lower or "historia" in message_lower:
        # If it's about general history topics, reject
        history_topics = [
            "revolución", "guerra", "conquista", "época", "siglo",
            "prehispánico", "colonial", "independencia", "antigua",
            "medieval", "romano", "griego"
        ]
        if any(topic in message_lower for topic in history_topics):
            result = False
            logger.debug(
                "Bank query rejected (general history context)",
                message_preview=message[:50]
            )
            if cache:
                try:
                    await cache.set(cache_key, result, expire=3600)
                except Exception:
                    pass
            return result

    # Filter "hipotecario" when used as street/place name
    if "hipotecario" in message_lower:
        place_indicators = [
            "nombre de", "calle", "avenida", "boulevard", "colonia",
            "ubicado en", "dirección", "zona", "fraccionamiento"
        ]
        if any(indicator in message_lower for indicator in place_indicators):
            result = False
            logger.debug(
                "Bank query rejected (hipotecario as place name)",
                message_preview=message[:50]
            )
            if cache:
                try:
                    await cache.set(cache_key, result, expire=3600)
                except Exception:
                    pass
            return result

    # 4. Check all banking keywords with ambiguity handling
    ambiguous_words = ["banco", "bancos", "capital", "cartera", "comercial", "consumo"]
    found_banking_keywords = False

    for keyword in all_keywords:
        if keyword in ambiguous_words:
            # Use word boundary for ambiguous words
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, message_lower):
                # Additional context check
                context_nearby = message_lower[max(0, message_lower.find(keyword) - 50):
                                              min(len(message_lower), message_lower.find(keyword) + 50)]

                banking_context_found = any(
                    bk in context_nearby
                    for bk in ["imor", "icor", "icap", "invex", "banorte", "santander",
                              "financiero", "financiera", "bancario", "bancaria",
                              "morosidad", "crédito", "credito", "tasa", "cnbv"]
                )

                if banking_context_found or keyword in ["bancos", "bancario", "bancaria"]:
                    found_banking_keywords = True
                    break
        else:
            if keyword in message_lower:
                found_banking_keywords = True
                break

    # 5. Pattern matching for metric-like queries
    metric_patterns = [
        r'\b(cuál|cual|dame|muestra|obtener|consultar)\b.{0,30}\b(indicador|métrica|metrica|índice|indice|ratio)\b',
        r'\b(cómo|como)\b.{0,30}\b(está|esta|van|anda)\b.{0,20}\b(banco|cartera|mora)\b',
        r'\b(qué|que)\b.{0,30}\b(banco|bancos)\b.{0,30}\b(mejor|peor|líder|lider)\b'
    ]

    for pattern in metric_patterns:
        if re.search(pattern, message_lower):
            found_banking_keywords = True
            break

    # If we found banking keywords, return True immediately
    if found_banking_keywords:
        result = True
        logger.debug(
            "Bank query detected (keyword match)",
            message_preview=message[:50]
        )
        # Cache result
        if cache:
            try:
                await cache.set(cache_key, result, expire=3600)
            except Exception:
                pass
        return result

    # 6. Ambiguous case - Use LLM classifier
    logger.info(
        "Bank query classification ambiguous, using LLM",
        message_preview=message[:50]
    )

    result = await _classify_with_llm(message)

    # Cache LLM result (longer TTL for expensive operations)
    if cache:
        try:
            await cache.set(cache_key, result, expire=7200)  # 2 hours cache for LLM results
        except Exception:
            pass

    logger.info(
        "Bank query LLM classification completed",
        message_preview=message[:50],
        result=result
    )

    return result


# Convenience function for chat integration
async def get_bank_chart_for_message(
    message: str,
    mode: str = "dashboard",
) -> Optional[BankChartData]:
    """
    Convenience function to get bank chart data for a message.

    Returns None if:
    - Message doesn't appear to be a banking query
    - Bank advisor is unavailable
    - Query fails for any reason

    Args:
        message: User message text
        mode: Visualization mode

    Returns:
        BankChartData if successful, None otherwise
    """
    # Quick check if it's a banking query
    if not await is_bank_query(message):
        return None

    try:
        response = await query_bank_analytics(
            metric_or_query=message,
            mode=mode,
        )
        return response.data
    except (BankAdvisorUnavailableError, BankAdvisorQueryError) as e:
        logger.warning(
            "bank_analytics.skipped",
            message=message[:100],
            reason=str(e),
        )
        return None
