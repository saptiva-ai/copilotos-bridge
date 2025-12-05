"""
BankAdvisor MCP Server - Enterprise Banking Analytics Microservice

Exposes banking analytics tools via MCP (Model Context Protocol) over HTTP.
This service is completely decoupled from the octavios-core monolith.

Architecture:
- FastMCP handles MCP protocol and tool registration
- FastAPI handles health checks and SSE endpoint
- Uses HTTP transport for remote access from octavios-core
"""
import os
import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional
from datetime import datetime

import json
import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastmcp import FastMCP
from sqlalchemy import text

# Import bankadvisor modules
from bankadvisor.db import AsyncSessionLocal, init_db
from bankadvisor.services.analytics_service import AnalyticsService
# Q1 2025: Legacy IntentService removed, only NlpIntentService remains
from bankadvisor.services.intent_service import NlpIntentService, Intent
from bankadvisor.services.visualization_service import VisualizationService

# HU3: NLP Query Interpretation imports
from bankadvisor.config_service import get_config
from bankadvisor.entity_service import EntityService

logger = structlog.get_logger(__name__)

# NL2SQL Phase 2-3 imports (optional - graceful fallback if not available)
try:
    from bankadvisor.services.query_spec_parser import QuerySpecParser
    from bankadvisor.services.nl2sql_context_service import Nl2SqlContextService
    from bankadvisor.services.sql_generation_service import SqlGenerationService
    from bankadvisor.services.sql_validator import SqlValidator
    NL2SQL_AVAILABLE = True
except ImportError as e:
    logger.warning("nl2sql.imports_failed", error=str(e), fallback="Using legacy intent-based logic")
    NL2SQL_AVAILABLE = False

# Global instances for NL2SQL services (initialized in lifespan if available)
_query_parser: Optional["QuerySpecParser"] = None
_context_service: Optional["Nl2SqlContextService"] = None
_sql_generator: Optional["SqlGenerationService"] = None


# ============================================================================
# STARTUP LOGIC: ETL Auto-Execution
# ============================================================================
async def ensure_data_populated():
    """
    Verifica si la base de datos tiene datos. Si está vacía, ejecuta el ETL.
    """
    try:
        async with AsyncSessionLocal() as session:
            # Check if table exists and has data
            result = await session.execute(
                text("""
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_name = 'monthly_kpis'
                """)
            )
            table_exists = result.scalar() > 0

            if not table_exists:
                logger.info("database.table_missing", message="Table monthly_kpis doesn't exist yet")
                return

            # Check if table has recent data
            result = await session.execute(
                text("SELECT COUNT(*) FROM monthly_kpis WHERE fecha > '2025-01-01'")
            )
            row_count = result.scalar()

            if row_count == 0:
                logger.info("database.empty", message="No data found. ETL must be run manually via: python -m bankadvisor.etl_loader")
                # Skip automatic ETL - it's too slow for startup (228MB file)
                # ETL should be run manually after first deployment
            else:
                logger.info(
                    "database.ready",
                    message=f"Data already present ({row_count} records)"
                )

    except Exception as e:
        logger.error("startup.etl_check_failed", error=str(e))
        # Don't crash the server if ETL fails - may be transient DB issue
        pass


# ============================================================================
# FASTAPI APP WITH LIFESPAN
# ============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown logic"""
    global _query_parser, _context_service, _sql_generator

    logger.info("bankadvisor.starting", version="1.0.0")

    # Initialize database
    await init_db()
    logger.info("database.initialized")

    # Q1 2025: Legacy IntentService.initialize() removed
    # NlpIntentService uses runtime config and doesn't need initialization
    logger.info("nlp.initialized")

    # Initialize NL2SQL services (Phase 2-3) if available
    if NL2SQL_AVAILABLE:
        try:
            from bankadvisor.services.rag_bridge import get_rag_bridge

            # Attempt to inject RAG services from main backend
            rag_bridge = get_rag_bridge()
            rag_available = rag_bridge.inject_from_main_backend()

            # Initialize parser (always available)
            _query_parser = QuerySpecParser()

            # Initialize SQL generator with SAPTIVA LLM client
            from bankadvisor.services.llm_client import get_saptiva_llm_client
            llm_client = get_saptiva_llm_client(model="SAPTIVA_TURBO")
            _sql_generator = SqlGenerationService(
                validator=SqlValidator(),
                llm_client=llm_client
            )

            if llm_client:
                logger.info("nl2sql.llm_enabled", provider="SAPTIVA", model="SAPTIVA_TURBO")
            else:
                logger.warning("nl2sql.llm_disabled", message="SAPTIVA client not available, using templates only")

            # Initialize context service with or without RAG
            if rag_available:
                _context_service = Nl2SqlContextService(
                    qdrant_service=rag_bridge.get_qdrant_service(),
                    embedding_service=rag_bridge.get_embedding_service()
                )

                # Ensure RAG collections exist
                _context_service.ensure_collections()

                logger.info(
                    "nl2sql.initialized",
                    rag_enabled=True,
                    qdrant_collection=rag_bridge.get_qdrant_service().collection_name,
                    note="RAG fully enabled. Seed collections with scripts/seed_nl2sql_rag.py"
                )
            else:
                _context_service = Nl2SqlContextService()  # No RAG - will use fallback

                logger.info(
                    "nl2sql.initialized",
                    rag_enabled=False,
                    note="Running in template-only mode (no RAG). RAG services not available."
                )

        except Exception as e:
            logger.error("nl2sql.initialization_failed", error=str(e), exc_info=True)
            _query_parser = None
            _context_service = None
            _sql_generator = None
    else:
        logger.info("nl2sql.disabled", reason="NL2SQL services not available, using legacy intent logic")

    # Initialize RAG Feedback Loop (Q1 2025)
    if NL2SQL_AVAILABLE and _context_service and rag_available:
        try:
            from bankadvisor.services.query_logger_service import QueryLoggerService
            from bankadvisor.services.rag_feedback_service import RagFeedbackService
            from bankadvisor.jobs.rag_feedback_job import RagFeedbackJob, set_rag_feedback_job

            # Initialize QueryLoggerService
            query_logger = QueryLoggerService(AsyncSessionLocal())

            # Initialize RagFeedbackService
            from qdrant_client import QdrantClient
            qdrant_client = QdrantClient(host="qdrant", port=6333)  # Adjust host as needed

            feedback_service = RagFeedbackService(
                query_logger=query_logger,
                qdrant_client=qdrant_client,
                collection_name="bankadvisor_queries"
            )

            # Initialize and start scheduled job (runs every hour)
            feedback_job = RagFeedbackJob(
                feedback_service=feedback_service,
                interval_hours=1,
                batch_size=50,
                min_confidence=0.7
            )
            feedback_job.start()
            set_rag_feedback_job(feedback_job)

            logger.info(
                "rag_feedback.initialized",
                interval_hours=1,
                batch_size=50,
                message="RAG Feedback Loop active - queries will auto-seed every hour"
            )

        except Exception as e:
            logger.warning(
                "rag_feedback.initialization_failed",
                error=str(e),
                message="RAG Feedback Loop disabled - queries won't auto-seed"
            )
    else:
        logger.info(
            "rag_feedback.disabled",
            reason="NL2SQL or RAG not available"
        )

    # Ensure data is populated
    await ensure_data_populated()

    port = int(os.getenv("PORT", "8002"))
    logger.info("bankadvisor.ready", port=port, nl2sql_enabled=NL2SQL_AVAILABLE)
    yield

    # Shutdown logic
    logger.info("bankadvisor.shutdown")

    # Stop RAG Feedback Job
    from bankadvisor.jobs.rag_feedback_job import get_rag_feedback_job
    feedback_job = get_rag_feedback_job()
    if feedback_job:
        feedback_job.stop()
        logger.info("rag_feedback_job.stopped")


# Create FastAPI app for health checks
app = FastAPI(
    title="BankAdvisor MCP Server",
    description="Enterprise Banking Analytics via MCP",
    version="1.0.0",
    lifespan=lifespan
)


# ============================================================================
# MCP SERVER INITIALIZATION
# ============================================================================
mcp = FastMCP("BankAdvisor Enterprise")


# ============================================================================
# HU3: NLP QUERY INTERPRETATION PIPELINE
# ============================================================================

# Confidence threshold for automatic execution
CONFIDENCE_THRESHOLD = 0.7


async def _try_hu3_nlp_pipeline(
    user_query: str,
    mode: str = "dashboard"
) -> Optional[Dict[str, Any]]:
    """
    HU3 NLP Query Interpretation Pipeline.

    Pipeline:
        1. Extract entities (banks, dates, metrics)
        2. Classify intent (evolution, comparison, ranking, point_value)
        3. If confidence < threshold, return clarification
        4. Execute query with filters

    Args:
        user_query: Natural language query
        mode: Visualization mode

    Returns:
        Result dict or None if pipeline should fallback
    """
    logger.info("hu3_nlp.pipeline_start", query=user_query)

    async with AsyncSessionLocal() as session:
        try:
            # =========================================================================
            # EARLY DETECTION: Financial metrics from metricas_financieras_ext (BE_BM)
            # =========================================================================
            # ROA, ROE, Activo Total, Capital Contable, etc. require special routing

            query_lower = user_query.lower()

            financial_keywords = {
                'roa': 'roa_12m',
                'return on assets': 'roa_12m',
                'retorno sobre activos': 'roa_12m',
                'rentabilidad activos': 'roa_12m',
                'roe': 'roe_12m',
                'return on equity': 'roe_12m',
                'retorno sobre capital': 'roe_12m',
                'rentabilidad capital': 'roe_12m',
                'activo total': 'activo_total',
                'activos totales': 'activo_total',
                'total assets': 'activo_total',
                'capital contable': 'capital_contable',
                'patrimonio': 'capital_contable',
                'equity': 'capital_contable',
                'captación total': 'captacion_total',
                'captacion total': 'captacion_total',
                'depósitos': 'captacion_total',
                'depositos': 'captacion_total',
                'resultado neto': 'resultado_neto',
                'utilidad neta': 'resultado_neto',
                'net income': 'resultado_neto',
                'inversiones financieras': 'inversiones_financieras',
                'portafolio inversiones': 'inversiones_financieras',
            }

            financial_metric_detected = None
            for keyword, metric_id in financial_keywords.items():
                if keyword in query_lower:
                    financial_metric_detected = metric_id
                    break

            if financial_metric_detected:
                logger.info(
                    "hu3_nlp.financial_metric_detected",
                    metric=financial_metric_detected,
                    query=user_query
                )

                # Route to financial metrics handler
                data = await AnalyticsService.get_financial_metric_data(
                    session,
                    metric_id=financial_metric_detected,
                    top_n=15
                )

                if data and data.get("type") != "error":
                    logger.info(
                        "hu3_nlp.financial_metric_success",
                        metric=financial_metric_detected,
                        result_type=data.get("type")
                    )
                    return data
                else:
                    logger.warning(
                        "hu3_nlp.financial_metric_failed",
                        metric=financial_metric_detected,
                        error=data.get("message") if data else "No data returned"
                    )
                    # Return error instead of falling through
                    return data

            # =========================================================================
            # OPCIÓN B: Early detection of IMOR/ICOR + segment patterns
            # =========================================================================
            # This prevents entity_service from confusing "IMOR consumo" with "cartera_consumo_total"
            # by intercepting the pattern before entity extraction

            # Detect if query has IMOR or ICOR
            has_imor = 'imor' in query_lower or 'morosidad' in query_lower
            has_icor = 'icor' in query_lower or 'cobertura' in query_lower
            metric_detected = None

            if has_imor:
                metric_detected = 'imor'
            elif has_icor:
                metric_detected = 'icor'

            # Detect if query has a segment keyword
            segment_keywords = {
                'consumo': 'CONSUMO_TOTAL',
                'automotriz': 'CONSUMO_AUTOMOTRIZ',
                'tarjeta': 'CONSUMO_TARJETA',
                'tarjetas': 'CONSUMO_TARJETA',
                'nomina': 'CONSUMO_NOMINA',
                'nómina': 'CONSUMO_NOMINA',
                'personales': 'CONSUMO_PERSONALES',
                'empresas': 'EMPRESAS',
                'empresarial': 'EMPRESAS',
                'vivienda': 'VIVIENDA',
                'hipotecario': 'VIVIENDA',
                'hipoteca': 'VIVIENDA'
            }

            segment_detected = None
            segment_code = None

            for keyword, code in segment_keywords.items():
                if keyword in query_lower:
                    segment_detected = keyword
                    segment_code = code
                    break

            # If both metric and segment detected, handle directly
            if metric_detected and segment_code:
                logger.info(
                    "hu3_nlp.early_pattern_detected",
                    metric=metric_detected,
                    segment=segment_code,
                    pattern="imor_icor_segment"
                )

                # Check if it's a ranking query
                is_ranking = any(kw in query_lower for kw in ['top', 'ranking', 'por banco', 'mejores', 'peores'])

                # Extract dates if present (simple extraction)
                from datetime import datetime, timedelta
                import re

                date_start = None
                date_end = datetime.now().date()
                years = 3  # Default

                # Try to extract "últimos X meses/años"
                match_months = re.search(r'[úu]ltimos?\s+(\d+)\s+mes', query_lower)
                match_years = re.search(r'[úu]ltimos?\s+(\d+)\s+a[ñn]o', query_lower)
                match_trimestre = re.search(r'[úu]ltimo?\s+trimestre', query_lower)

                if match_months:
                    months = int(match_months.group(1))
                    date_start = (datetime.now() - timedelta(days=months * 30)).date()
                    years = max(1, months // 12)
                elif match_years:
                    years = int(match_years.group(1))
                elif match_trimestre:
                    date_start = (datetime.now() - timedelta(days=90)).date()
                    years = 1

                # Route to appropriate handler
                if is_ranking:
                    data = await AnalyticsService.get_segment_ranking(
                        session,
                        segment_code=segment_code,
                        metric_column=metric_detected,
                        top_n=5
                    )
                else:
                    data = await AnalyticsService.get_segment_evolution(
                        session,
                        segment_code=segment_code,
                        metric_column=metric_detected,
                        years=years
                    )

                if data and data.get("type") != "empty":
                    logger.info(
                        "hu3_nlp.early_pattern_success",
                        metric=metric_detected,
                        segment=segment_code,
                        result_type=data.get("type")
                    )
                    return data
                else:
                    logger.warning(
                        "hu3_nlp.early_pattern_empty",
                        metric=metric_detected,
                        segment=segment_code
                    )
                    # Fall through to normal pipeline

            # =========================================================================
            # END OPCIÓN B
            # =========================================================================

            # Step 1: Extract entities
            entities = await EntityService.extract(user_query, session)
            config = get_config()

            # Step 1.3: Check for multi-metric query patterns (e.g., "etapas de deterioro")
            # These patterns require querying multiple metrics simultaneously for stacked visualizations
            multi_metric_info = config.check_multi_metric_query(user_query)
            if multi_metric_info:
                logger.info(
                    "hu3_nlp.multi_metric_query_detected",
                    query=user_query,
                    query_type=multi_metric_info["query_type"],
                    metrics=multi_metric_info["metrics"],
                    visualization=multi_metric_info["visualization"]
                )

                # Execute multi-metric query
                data = await AnalyticsService.get_multi_metric_data(
                    session,
                    metric_ids=multi_metric_info["metrics"],
                    banks=entities.banks if entities.banks else None,
                    date_start=entities.date_start,
                    date_end=entities.date_end,
                    user_query=user_query
                )

                # Check for errors
                if data.get("type") == "error":
                    logger.warning(
                        "hu3_nlp.multi_metric_error",
                        query=user_query,
                        error=data.get("message")
                    )
                    return data

                # Generate Plotly visualization for multi-metric data
                if data.get("type") == "data" and "plotly_config" in data:
                    # Already formatted with visualization by get_multi_metric_data
                    logger.info(
                        "hu3_nlp.multi_metric_success",
                        query=user_query,
                        metrics_count=len(multi_metric_info["metrics"]),
                        visualization=multi_metric_info["visualization"]
                    )
                    return data

            # Step 1.5: Check for ambiguous terms ONLY if no specific metric was found
            # This catches cases like "cartera de INVEX" where "cartera" is ambiguous
            # BUT "tasa de deterioro ajustada" should NOT trigger ambiguity for "tasa"
            if not entities.has_metric():
                ambiguity = config.check_ambiguous_term(user_query)
                if ambiguity:
                    logger.info(
                        "hu3_nlp.ambiguous_term_detected",
                        query=user_query,
                        term=ambiguity["term"],
                        action="clarification"
                    )
                    return {
                        "type": "clarification",
                        "message": ambiguity["message"],
                        "options": ambiguity["options"],
                        "context": {
                            "ambiguous_term": ambiguity["term"],
                            "banks": entities.banks,
                            "date_start": str(entities.date_start) if entities.date_start else None,
                            "date_end": str(entities.date_end) if entities.date_end else None,
                            "original_query": user_query
                        }
                    }

            # =========================================================================
            # HU3.4: ADDITIONAL CLARIFICATION CHECKS
            # =========================================================================

            # HU3.4-A: Multi-metric clarification
            # Check if user is asking for multiple metrics (e.g., "IMOR y ICOR")
            # IMPORTANT: Skip this check if we already have a single specific metric detected
            # (e.g., "cartera comercial sin gobierno" is ONE metric, not two)
            multiple_metrics = await EntityService.extract_multiple_metrics(user_query, session)
            if len(multiple_metrics) > 1 and not entities.metric_id:
                metrics_names = ", ".join([m[1] for m in multiple_metrics])
                logger.info(
                    "hu3_nlp.multi_metric_detected",
                    query=user_query,
                    metrics=multiple_metrics,
                    action="clarification"
                )
                return {
                    "type": "clarification",
                    "message": f"Detecté varias métricas: {metrics_names}. ¿Cómo quieres visualizarlas?",
                    "options": [
                        {"id": "combined", "label": "Gráfica combinada", "description": "Todas las métricas en un solo gráfico"},
                        {"id": "separate", "label": "Gráficas separadas", "description": "Un gráfico por cada métrica"},
                        {"id": "table", "label": "Tabla comparativa", "description": "Resumen en formato tabla"},
                        {"id": "first_only", "label": f"Solo {multiple_metrics[0][1]}", "description": "Mostrar solo la primera métrica"}
                    ],
                    "context": {
                        "metrics": [m[0] for m in multiple_metrics],
                        "metrics_display": [m[1] for m in multiple_metrics],
                        "banks": entities.banks,
                        "original_query": user_query
                    }
                }

            # HU3.4-B: Comparison clarification
            # Check if user wants to compare but targets are unclear
            is_comparison = EntityService.is_comparison_query(user_query)
            if is_comparison and entities.has_metric():
                # Check if comparison targets are specified
                has_multiple_banks = len(entities.banks) > 1
                has_vs_pattern = " vs " in user_query.lower() or " versus " in user_query.lower()

                if not has_multiple_banks and not has_vs_pattern:
                    logger.info(
                        "hu3_nlp.comparison_unclear",
                        query=user_query,
                        metric=entities.metric_id,
                        action="clarification"
                    )
                    return {
                        "type": "clarification",
                        "message": f"¿Qué tipo de comparación de {entities.metric_display} te interesa?",
                        "options": [
                            {"id": "invex_vs_sistema", "label": "INVEX vs Sistema", "description": "Comparar INVEX contra el promedio del sistema"},
                            {"id": "time_periods", "label": "Diferentes períodos", "description": "Comparar año actual vs anterior"},
                            {"id": "vs_other_metric", "label": "Contra otra métrica", "description": "Comparar con otro indicador"}
                        ],
                        "context": {
                            "metric": entities.metric_id,
                            "metric_display": entities.metric_display,
                            "banks": entities.banks,
                            "original_query": user_query
                        }
                    }

            # HU3.4-C: Time period clarification
            # Check for vague time references without explicit date range
            vague_time = EntityService.has_vague_time_reference(user_query)
            has_explicit_date = EntityService.has_explicit_date_range(user_query)

            if vague_time and not has_explicit_date and entities.has_metric():
                logger.info(
                    "hu3_nlp.vague_time_detected",
                    query=user_query,
                    vague_term=vague_time,
                    action="clarification"
                )
                return {
                    "type": "clarification",
                    "message": f"¿Qué período de tiempo te interesa para {entities.metric_display}?",
                    "options": [
                        {"id": "3m", "label": "Últimos 3 meses", "description": "Datos más recientes"},
                        {"id": "6m", "label": "Últimos 6 meses", "description": "Medio año"},
                        {"id": "12m", "label": "Último año", "description": "12 meses completos"},
                        {"id": "ytd", "label": "Este año (YTD)", "description": "Desde enero 2025"},
                        {"id": "all", "label": "Histórico completo", "description": "Todos los datos desde 2017"}
                    ],
                    "context": {
                        "vague_term": vague_time,
                        "metric": entities.metric_id,
                        "metric_display": entities.metric_display,
                        "banks": entities.banks,
                        "original_query": user_query
                    }
                }

            # HU3.4-D: Bank clarification (DISABLED - default to all banks)
            # If metric found but no bank specified, default to showing all banks
            # This avoids unnecessary clarifications for simple queries like "Cartera comercial"
            # Users can be more specific if they want: "Cartera comercial de INVEX"
            if entities.has_metric() and not entities.has_banks():
                logger.debug(
                    "hu3_nlp.bank_not_specified_default_all",
                    query=user_query,
                    metric=entities.metric_id,
                    action="default_to_all_banks"
                )
                # Continue without clarification - entities.banks = None means "all banks"

            # =========================================================================
            # END HU3.4 CLARIFICATION CHECKS
            # =========================================================================

            # Step 2: If no metric found, ask for clarification
            if not entities.has_metric():
                logger.info(
                    "hu3_nlp.metric_not_found",
                    query=user_query,
                    action="clarification"
                )
                return {
                    "type": "clarification",
                    "message": "No pude identificar la métrica. ¿A cuál te refieres?",
                    "options": config.get_all_metric_options()[:6],
                    "context": {
                        "banks": entities.banks,
                        "date_start": str(entities.date_start) if entities.date_start else None,
                        "date_end": str(entities.date_end) if entities.date_end else None,
                        "original_query": user_query
                    }
                }

            # Step 3: Classify intent
            intent_result = await NlpIntentService.classify(user_query, entities)

            logger.info(
                "hu3_nlp.intent_classified",
                query=user_query,
                intent=intent_result.intent.value,
                confidence=intent_result.confidence,
                explanation=intent_result.explanation
            )

            # Step 4: If low confidence, ask for clarification
            if intent_result.confidence < CONFIDENCE_THRESHOLD or intent_result.intent == Intent.UNKNOWN:
                return {
                    "type": "clarification",
                    "message": f"Encontré {entities.metric_display}. ¿Qué te gustaría ver?",
                    "options": [
                        {"id": "point_value", "label": "Valor actual"},
                        {"id": "evolution", "label": "Evolución en el tiempo"},
                        {"id": "comparison", "label": "Comparación entre bancos"},
                        {"id": "ranking", "label": "Ranking de bancos"}
                    ],
                    "context": {
                        "metric": entities.metric_id,
                        "metric_display": entities.metric_display,
                        "banks": entities.banks,
                        "date_start": str(entities.date_start) if entities.date_start else None,
                        "date_end": str(entities.date_end) if entities.date_end else None,
                        "detected_intent": intent_result.intent.value,
                        "confidence": intent_result.confidence
                    }
                }

            # =========================================================================
            # NEW: QUESTION-SPECIFIC HANDLERS (5 Business Questions)
            # =========================================================================
            # These handlers execute BEFORE the generic fallback for specific patterns

            query_lower = user_query.lower()

            # Question 1: Comparative ratio (IMOR INVEX vs Sistema)
            if (entities.metric_id in ['imor', 'icor'] and
                len(entities.banks) >= 2 and
                ('vs' in query_lower or 'contra' in query_lower or 'compara' in query_lower)):

                logger.info(
                    "hu3_nlp.question_specific.comparative_ratio",
                    metric=entities.metric_id,
                    banks=entities.banks
                )

                data = await AnalyticsService.get_comparative_ratio_data(
                    session,
                    metric_column=entities.metric_id,
                    primary_bank=entities.banks[0] if entities.banks else "INVEX",
                    comparison_bank=entities.banks[1] if len(entities.banks) > 1 else "SISTEMA",
                    date_start=str(entities.date_start) if entities.date_start else None,
                    date_end=str(entities.date_end) if entities.date_end else None
                )

            # Question 2: Market share evolution
            elif ('market share' in query_lower or 'participación de mercado' in query_lower or
                  'participacion de mercado' in query_lower):

                logger.info(
                    "hu3_nlp.question_specific.market_share",
                    banks=entities.banks
                )

                data = await AnalyticsService.get_market_share_data(
                    session,
                    primary_bank=entities.banks[0] if entities.banks else "INVEX",
                    years=3  # Default 3 years
                )

            # Question 3: Segment evolution (IMOR automotriz, tarjetas, etc.)
            elif ('automotriz' in query_lower or 'empresas' in query_lower or
                  'consumo' in query_lower or 'vivienda' in query_lower or
                  'tarjeta' in query_lower or 'nomina' in query_lower or
                  'nómina' in query_lower or 'personales' in query_lower or
                  'hipotecario' in query_lower) and \
                 entities.metric_id in ['imor', 'icor']:

                # Determine segment from query (match DB codes)
                segment_code = None
                if 'automotriz' in query_lower:
                    segment_code = 'CONSUMO_AUTOMOTRIZ'
                elif 'tarjeta' in query_lower or 'tarjetas' in query_lower:
                    segment_code = 'CONSUMO_TARJETA'
                elif 'nomina' in query_lower or 'nómina' in query_lower:
                    segment_code = 'CONSUMO_NOMINA'
                elif 'personales' in query_lower:
                    segment_code = 'CONSUMO_PERSONALES'
                elif 'empresas' in query_lower or 'empresarial' in query_lower:
                    segment_code = 'EMPRESAS'
                elif 'vivienda' in query_lower or 'hipotecario' in query_lower:
                    segment_code = 'VIVIENDA'
                elif 'consumo' in query_lower and not any(x in query_lower for x in ['automotriz', 'tarjeta', 'nomina', 'personales']):
                    segment_code = 'CONSUMO_TOTAL'

                if segment_code:
                    logger.info(
                        "hu3_nlp.question_specific.segment_evolution",
                        segment=segment_code,
                        metric=entities.metric_id
                    )

                    # Check if it's a ranking query (Top N, ranking, por banco)
                    is_ranking = any(kw in query_lower for kw in ['top', 'ranking', 'por banco', 'mejores', 'peores'])

                    if is_ranking:
                        data = await AnalyticsService.get_segment_ranking(
                            session,
                            segment_code=segment_code,
                            metric_column=entities.metric_id,
                            top_n=5  # Default top 5
                        )
                    else:
                        data = await AnalyticsService.get_segment_evolution(
                            session,
                            segment_code=segment_code,
                            metric_column=entities.metric_id,
                            years=3  # Default 3 years
                        )
                else:
                    # Fallback to generic query
                    data = None

            # Question 5: Institution ranking by assets
            elif ('ranking' in query_lower and
                  ('activo' in query_lower or 'activos' in query_lower or
                   'grande' in query_lower or 'tamaño' in query_lower)):

                logger.info(
                    "hu3_nlp.question_specific.institution_ranking",
                    metric="activo_total"
                )

                data = await AnalyticsService.get_institution_ranking(
                    session,
                    metric_column="activo_total",
                    top_n=10,  # Default top 10
                    ascending=False  # Largest first
                )

            # FALLBACK: Generic query execution
            else:
                data = None

            # If no specific handler matched, use generic pipeline
            if data is None:
                # Step 5: Execute query with high confidence
                data = await AnalyticsService.get_filtered_data(
                    session,
                    metric_id=entities.metric_id,
                    banks=entities.banks if entities.banks else None,
                    date_start=entities.date_start,
                    date_end=entities.date_end,
                    intent=intent_result.intent.value,
                    user_query=user_query
                )

            # =========================================================================
            # END QUESTION-SPECIFIC HANDLERS
            # =========================================================================

            # Check for errors from analytics service
            if data.get("type") == "error":
                logger.warning(
                    "hu3_nlp.analytics_error",
                    query=user_query,
                    error=data.get("message")
                )
                return data

            # Generate Plotly visualization if data is available
            # SOLID Principle: Delegate to specialized PlotlyGenerator service
            if data.get("type") == "data" and "values" in data:
                from bankadvisor.services.plotly_generator import PlotlyGenerator

                plotly_config = PlotlyGenerator.generate(
                    metric_id=entities.metric_id,
                    data=data,
                    intent=intent_result.intent.value,
                    metric_display=entities.metric_display
                )

                if plotly_config:
                    data["plotly_config"] = plotly_config

            # Generate SQL representation for frontend display
            # Build SQL that represents the query executed
            bank_filter = ""
            if entities.banks and len(entities.banks) > 0:
                banks_str = ", ".join([f"'{b}'" for b in entities.banks])
                bank_filter = f"\n    WHERE banco_norm IN ({banks_str})"

            date_filter = ""
            if entities.date_start or entities.date_end:
                date_conditions = []
                if entities.date_start:
                    date_conditions.append(f"fecha >= '{entities.date_start}'")
                if entities.date_end:
                    date_conditions.append(f"fecha <= '{entities.date_end}'")
                date_filter_str = " AND ".join(date_conditions)
                if bank_filter:
                    date_filter = f"\n      AND {date_filter_str}"
                else:
                    date_filter = f"\n    WHERE {date_filter_str}"

            sql_generated = f"""SELECT
    fecha,
    banco_norm,
    {entities.metric_id} AS value
FROM monthly_kpis{bank_filter}{date_filter}
ORDER BY fecha ASC;"""

            # Add metadata with sql_generated and metric_type
            # IMPORTANT: Only add if metadata doesn't already exist (preserve segment query metadata)
            metric_type = config.get_metric_type(entities.metric_id)
            if "metadata" not in data:
                data["metadata"] = {
                    "metric": entities.metric_id,
                    "metric_type": metric_type,
                    "data_as_of": data.get("data_as_of", ""),
                    "title": f"{entities.metric_display}",
                    "pipeline": "hu3_nlp",
                    "sql_generated": sql_generated
                }
            else:
                # Metadata already exists (from segment queries), just ensure these fields are present
                data["metadata"].setdefault("metric", entities.metric_id)
                data["metadata"].setdefault("metric_type", metric_type)
                data["metadata"].setdefault("title", f"{entities.metric_display}")

            data["query_info"] = {
                "original_query": user_query,
                "detected_metric": entities.metric_display,
                "detected_banks": entities.banks,
                "detected_intent": intent_result.intent.value,
                "confidence": intent_result.confidence,
                "pipeline": "hu3_nlp"
            }

            logger.info(
                "hu3_nlp.success",
                query=user_query,
                metric=entities.metric_id,
                intent=intent_result.intent.value,
                banks_count=len(entities.banks) if entities.banks else 0,
                has_sql_generated=True
            )

            return data

        except Exception as e:
            logger.error(
                "hu3_nlp.error",
                query=user_query,
                error=str(e),
                exc_info=True
            )
            # Return None to trigger fallback to legacy pipeline
            return None


# ============================================================================
# CORE BANK ANALYTICS LOGIC (callable directly)
# ============================================================================
async def _bank_analytics_impl(
    metric_or_query: str,
    mode: str = "dashboard"
) -> Dict[str, Any]:
    """
    Consulta métricas bancarias (INVEX + Sistema Financiero Mexicano).

    Esta tool consulta 103 meses de datos históricos (2017-2025) de la CNBV.
    Incluye validación de seguridad (whitelist) y NLP para entender queries.

    Phase 2-3 NL2SQL Pipeline:
        1. Parse NL → QuerySpec (if NL2SQL available)
        2. Retrieve RAG context (schema/metrics/examples)
        3. Generate SQL from templates or LLM
        4. Validate SQL security
        5. Execute and visualize

    Fallback to Legacy:
        If NL2SQL fails or unavailable → intent-based logic (backward compatible)

    Args:
        metric_or_query: Nombre de métrica o query natural.
                        Ejemplos: "cartera comercial", "IMOR de INVEX últimos 3 meses"
        mode: Modo de visualización ("dashboard" o "timeline")

    Returns:
        Dict con:
        - data: {months: [...], metadata: {...}}
        - plotly_config: Configuración de gráfico Plotly.js
        - title: Título del reporte
        - data_as_of: Fecha de corte de datos

    Examples:
        >>> await bank_analytics("cartera comercial")
        >>> await bank_analytics("IMOR de INVEX últimos 3 meses")
        >>> await bank_analytics("Compara IMOR INVEX vs Sistema 2024")

    Security:
        - Whitelist SAFE_METRIC_COLUMNS (15 métricas autorizadas)
        - SQL validation via SqlValidator (blacklist/whitelist)
        - LIMIT injection (max 1000 rows)
    """
    # =========================================================================
    # PERFORMANCE TRACKING: Start timer
    # =========================================================================
    start_time = datetime.utcnow()

    logger.info(
        "tool.bank_analytics.invoked",
        metric_or_query=metric_or_query,
        mode=mode,
        nl2sql_available=NL2SQL_AVAILABLE
    )

    # =========================================================================
    # HU3: TRY NLP QUERY INTERPRETATION PIPELINE FIRST
    # =========================================================================
    try:
        hu3_result = await _try_hu3_nlp_pipeline(metric_or_query, mode)
        if hu3_result is not None:
            # HU3 pipeline succeeded or returned clarification
            if hu3_result.get("type") in ["data", "clarification", "error", "empty"]:
                # Performance tracking
                end_time = datetime.utcnow()
                duration_ms = (end_time - start_time).total_seconds() * 1000

                logger.info(
                    "tool.bank_analytics.hu3_success",
                    query=metric_or_query,
                    result_type=hu3_result.get("type"),
                    pipeline="hu3_nlp",
                    duration_ms=round(duration_ms, 2)
                )

                logger.info(
                    "bank_analytics.performance",
                    query=metric_or_query,
                    total_ms=round(duration_ms, 2),
                    pipeline="hu3_nlp",
                    result_type=hu3_result.get("type")
                )

                return hu3_result
    except Exception as e:
        logger.warning(
            "tool.bank_analytics.hu3_failed",
            query=metric_or_query,
            error=str(e),
            fallback="nl2sql_or_legacy"
        )
        # Continue to NL2SQL or legacy fallback

    # =========================================================================
    # NL2SQL PIPELINE ONLY (Q1 2025: Legacy pipeline removed)
    # =========================================================================

    # Ensure NL2SQL services are available
    if not (NL2SQL_AVAILABLE and _query_parser and _context_service and _sql_generator):
        logger.error(
            "tool.bank_analytics.nl2sql_unavailable",
            query=metric_or_query,
            message="NL2SQL services not initialized"
        )
        return {
            "error": "service_unavailable",
            "message": "NL2SQL service not available. Check logs for initialization errors.",
            "suggestion": "Contact support if this persists."
        }

    try:
        nl2sql_result = await _try_nl2sql_pipeline(metric_or_query, mode)

        if nl2sql_result and nl2sql_result.get("success"):
            # Performance tracking
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000

            logger.info(
                "tool.bank_analytics.nl2sql_success",
                query=metric_or_query,
                pipeline="nl2sql",
                duration_ms=round(duration_ms, 2)
            )

            logger.info(
                "bank_analytics.performance",
                query=metric_or_query,
                total_ms=round(duration_ms, 2),
                pipeline="nl2sql"
            )

            return nl2sql_result

        # NL2SQL returned error or failed
        error_message = nl2sql_result.get("message", "Query processing failed") if nl2sql_result else "Unknown error"
        error_code = nl2sql_result.get("error_code", "processing_failed") if nl2sql_result else "processing_failed"

        logger.warning(
            "tool.bank_analytics.nl2sql_failed",
            query=metric_or_query,
            error_code=error_code,
            message=error_message
        )

        return {
            "error": error_code,
            "message": error_message,
            "suggestions": nl2sql_result.get("suggestions", []) if nl2sql_result else [],
            "query": metric_or_query
        }

    except Exception as e:
        logger.error(
            "tool.bank_analytics.nl2sql_exception",
            query=metric_or_query,
            error=str(e),
            exc_info=True
        )
        return {
            "error": "internal_error",
            "message": f"Error processing query: {str(e)}",
            "query": metric_or_query
        }


async def _try_nl2sql_pipeline(user_query: str, mode: str) -> Optional[Dict[str, Any]]:
    """
    Attempt NL2SQL pipeline for query processing.

    Pipeline:
        1. Parse NL → QuerySpec
        2. Retrieve RAG context
        3. Generate SQL
        4. Execute SQL
        5. Build visualization
        6. Log to query_logs (RAG Feedback Loop)

    Args:
        user_query: Natural language query
        mode: Visualization mode

    Returns:
        Result dict or None if pipeline fails

    Raises:
        Exception: If any step fails (caught by caller)
    """
    from datetime import datetime
    start_time = datetime.now()

    logger.debug("nl2sql_pipeline.start", query=user_query)

    # Step 1: Parse to QuerySpec
    spec = await _query_parser.parse(
        user_query=user_query,
        intent_hint=None,  # Let parser auto-detect
        mode_hint=mode
    )

    if not spec.is_complete():
        logger.warning(
            "nl2sql_pipeline.incomplete_spec",
            query=user_query,
            confidence=spec.confidence_score,
            missing=spec.missing_fields
        )
        # Build clarification response with suggestions based on missing fields
        missing = spec.missing_fields
        options = []
        suggestion_parts = []

        if "time_range" in missing:
            options.extend([
                {"id": "last_6_months", "label": "Últimos 6 meses", "description": "Datos de los últimos 6 meses"},
                {"id": "last_12_months", "label": "Últimos 12 meses", "description": "Datos del último año"},
                {"id": "year_2024", "label": "Año 2024", "description": "Datos completos de 2024"}
            ])
            suggestion_parts.append("el periodo de tiempo")

        if "bank_names" in missing or not spec.bank_names:
            options.extend([
                {"id": "invex", "label": "INVEX", "description": "Solo datos de INVEX"},
                {"id": "sistema", "label": "Sistema", "description": "Comparativa del sistema bancario"}
            ])
            suggestion_parts.append("el banco")

        # Return clarification instead of error
        return {
            "success": True,
            "type": "clarification",
            "message": f"Para completar tu consulta sobre '{user_query}', por favor especifica {' y '.join(suggestion_parts)}.",
            "options": options,
            "context": {
                "original_query": user_query,
                "detected_metric": spec.metric,
                "missing_fields": missing,
                "banks": spec.bank_names or []  # Include detected banks for LLM context
            }
        }

    # Step 2: Retrieve RAG context
    ctx = await _context_service.rag_context_for_spec(spec, original_query=user_query)

    # Step 3: Generate SQL
    sql_result = await _sql_generator.build_sql_from_spec(spec, ctx)

    if not sql_result.success:
        logger.warning(
            "nl2sql_pipeline.sql_generation_failed",
            query=user_query,
            error_code=sql_result.error_code,
            error_message=sql_result.error_message
        )
        return {
            "success": False,
            "error_code": sql_result.error_code,
            "error": sql_result.error_code,
            "message": sql_result.error_message,
            "metadata": sql_result.metadata
        }

    # Step 4: Execute SQL
    logger.info(
        "nl2sql_pipeline.executing_sql",
        query=user_query,
        sql_preview=sql_result.sql[:100] if sql_result.sql else None
    )

    async with AsyncSessionLocal() as session:
        result = await session.execute(text(sql_result.sql))
        rows = result.fetchall()

    # Step 5: Transform to visualization format
    # Convert SQL rows to legacy format expected by VisualizationService
    # Legacy format: [{"month_label": "Jan 2024", "data": [{"category": "INVEX", "value": 0.05}]}]

    from collections import defaultdict
    from datetime import datetime

    # Detect if this is a ranking query (no fecha column, has banco_norm)
    template_used = sql_result.metadata.get("template", "")
    is_ranking_query = template_used in ["extended_financieras", "metric_ranking"]

    metric_col = spec.metric.lower()
    months_data = []

    if is_ranking_query:
        # Ranking queries: format as bar chart with banks on x-axis
        # Extract the actual column from metadata or fallback to metric_col
        value_column = sql_result.metadata.get("column", metric_col)

        ranking_data = []
        for row in rows:
            row_dict = dict(row._mapping)
            banco = row_dict.get('banco_norm', 'Desconocido')
            # Try to get value from the actual column name (e.g., activo_total)
            value = row_dict.get(value_column)
            if value is None:
                # Fallback: try metric_col
                value = row_dict.get(metric_col)
            pct_total = row_dict.get('pct_total')

            if value is not None:
                ranking_data.append({
                    "category": banco,
                    "value": value,
                    "pct_total": pct_total
                })

        # Format as single month entry for compatibility with VisualizationService
        if ranking_data:
            months_data = [{
                "month_label": "Ranking",
                "data": ranking_data
            }]
    else:
        # Time series queries: group by fecha column
        data_by_month = defaultdict(dict)

        for row in rows:
            row_dict = dict(row._mapping)
            fecha = row_dict.get('fecha')
            banco = row_dict.get('banco_norm', 'Sistema')
            value = row_dict.get(metric_col)

            if fecha:
                # Format month label (e.g., "Jan 2024")
                if isinstance(fecha, datetime):
                    month_label = fecha.strftime("%b %Y")
                else:
                    month_label = str(fecha)[:7]  # "2024-01"

                data_by_month[month_label][banco] = value

        # Convert to legacy format
        # Sort months chronologically, not alphabetically (BA-P0-004)

        def parse_month_label(label: str):
            """Parse month label like 'Jan 2024' to datetime for sorting"""
            try:
                return datetime.strptime(label, "%b %Y")
            except:
                # Fallback: try ISO format "2024-01"
                try:
                    return datetime.strptime(label, "%Y-%m")
                except:
                    # If parsing fails, return label as-is (will sort alphabetically)
                    return label

        for month_label, banco_values in sorted(data_by_month.items(), key=lambda x: parse_month_label(x[0])):
            month_entry = {
                "month_label": month_label,
                "data": [
                    {"category": banco, "value": val}
                    for banco, val in banco_values.items()
                ]
            }
            months_data.append(month_entry)

    # Build Plotly config
    # Use spec to determine title and styling
    title = f"{spec.metric} - {' vs '.join(spec.bank_names) if spec.bank_names else 'Sistema'}"

    # Get metric type from config
    config = get_config()
    metric_type = config.get_metric_type(spec.metric.lower())

    # Convert values based on metric type
    is_ratio = metric_type == "ratio"
    for month in months_data:
        for item in month["data"]:
            if item["value"] is not None:
                if is_ratio:
                    # Convert ratio to percentage
                    item["value"] = item["value"] * 100
                # else: Database values are ALREADY in millions (MDP), no conversion needed

    # Add section_config with mode based on template
    if is_ranking_query:
        chart_mode = "ranking_bar_chart"
    elif template_used == "metric_timeseries":
        chart_mode = "timeline_with_summary"
    else:
        chart_mode = "dashboard_month_comparison"

    section_config = {
        "title": title,
        "field": spec.metric.lower(),
        "description": f"Query: {user_query}",
        "mode": chart_mode,
        "type": metric_type
    }

    plotly_config = VisualizationService.build_plotly_config(
        months_data,
        section_config
    )

    logger.info(
        "nl2sql_pipeline.success",
        query=user_query,
        rows_returned=len(months_data),
        template_used=sql_result.metadata.get("template"),
        metric_type=metric_type
    )

    # Step 6: Log successful query for RAG Feedback Loop (Q1 2025)
    try:
        from bankadvisor.services.query_logger_service import QueryLoggerService

        execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        async with AsyncSessionLocal() as log_session:
            query_logger = QueryLoggerService(log_session)
            await query_logger.log_successful_query(
                user_query=user_query,
                generated_sql=sql_result.sql,
                banco=spec.bank_names[0] if spec.bank_names else None,
                metric=spec.metric,
                intent=spec.intent if hasattr(spec, 'intent') else "metric_query",
                execution_time_ms=execution_time_ms,
                pipeline_used="nl2sql",
                mode=mode,
                result_row_count=len(rows)
            )

        logger.debug("query_logged.success", execution_time_ms=execution_time_ms)

    except Exception as log_error:
        # Don't fail the request if logging fails
        logger.warning("query_logging.failed", error=str(log_error))

    return {
        "success": True,
        "data": {"months": months_data},
        "metadata": {
            "metric": spec.metric,
            "metric_type": metric_type,
            "data_as_of": "2025-11-27",  # TODO: Extract from actual data
            "title": title,
            "pipeline": "nl2sql",
            "template_used": sql_result.metadata.get("template"),
            "sql_generated": sql_result.sql
        },
        "plotly_config": plotly_config,
        "title": title,
        "data_as_of": "2025-11-27"
    }


# ============================================================================
# MCP TOOL WRAPPER (registered with FastMCP)
# ============================================================================
@mcp.tool()
async def bank_analytics(
    metric_or_query: str,
    mode: str = "dashboard"
) -> Dict[str, Any]:
    """
    Consulta métricas bancarias (INVEX + Sistema Financiero Mexicano).
    Wrapper para FastMCP que llama a la implementación real.
    """
    return await _bank_analytics_impl(metric_or_query, mode)


# ============================================================================
# HEALTH CHECK ENDPOINT (FastAPI)
# ============================================================================
@app.get("/health")
async def health_check():
    """
    Health check endpoint for Docker healthcheck.

    Returns service status plus last ETL run information.
    """
    try:
        # Check database connectivity
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))

            # Get last ETL run info
            last_etl = await session.execute(text("""
                SELECT
                    id,
                    started_at,
                    completed_at,
                    status,
                    duration_seconds,
                    rows_processed_base
                FROM etl_runs
                ORDER BY started_at DESC
                LIMIT 1
            """))
            etl_row = last_etl.fetchone()

        response = {
            "status": "healthy",
            "service": "bank-advisor-mcp",
            "version": "1.0.0"
        }

        # Add ETL info if available
        if etl_row:
            response["etl"] = {
                "last_run_id": etl_row[0],
                "last_run_started": etl_row[1].isoformat() if etl_row[1] else None,
                "last_run_completed": etl_row[2].isoformat() if etl_row[2] else None,
                "last_run_status": etl_row[3],
                "last_run_duration_seconds": etl_row[4],
                "last_run_rows": etl_row[5]
            }
        else:
            response["etl"] = {
                "last_run_status": "never_run",
                "message": "ETL has not been executed yet. Run: python -m bankadvisor.etl_runner"
            }

        return response
    except Exception as e:
        logger.error("health_check.failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# ============================================================================
# METRICS ENDPOINT FOR OBSERVABILITY
# ============================================================================
@app.get("/metrics")
async def metrics_endpoint():
    """
    Metrics endpoint for observability.

    Returns service metrics including:
    - ETL status and timing
    - Query counts by type (if tracked)
    - Performance indicators

    This endpoint can be scraped by monitoring tools.
    """
    from datetime import timezone

    try:
        async with AsyncSessionLocal() as session:
            # ETL metrics
            etl_result = await session.execute(text("""
                SELECT
                    COUNT(*) as total_runs,
                    COUNT(*) FILTER (WHERE status = 'success') as successful_runs,
                    COUNT(*) FILTER (WHERE status = 'failure') as failed_runs,
                    MAX(completed_at) as last_run,
                    AVG(duration_seconds) FILTER (WHERE status = 'success') as avg_duration
                FROM etl_runs
                WHERE started_at > NOW() - INTERVAL '7 days'
            """))
            etl_row = etl_result.fetchone()

            # Data metrics
            data_result = await session.execute(text("""
                SELECT
                    COUNT(*) as total_rows,
                    COUNT(DISTINCT banco_norm) as bank_count,
                    MIN(fecha) as data_start,
                    MAX(fecha) as data_end
                FROM monthly_kpis
            """))
            data_row = data_result.fetchone()

            # Calculate data age
            last_run_age_minutes = None
            if etl_row and etl_row[3]:
                from datetime import datetime
                now = datetime.now(timezone.utc)
                last_run = etl_row[3]
                if last_run.tzinfo is None:
                    last_run = last_run.replace(tzinfo=timezone.utc)
                last_run_age_minutes = (now - last_run).total_seconds() / 60

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "bank-advisor-mcp",
            "version": "1.0.0",

            "etl": {
                "total_runs_7d": etl_row[0] if etl_row else 0,
                "successful_runs_7d": etl_row[1] if etl_row else 0,
                "failed_runs_7d": etl_row[2] if etl_row else 0,
                "last_run": etl_row[3].isoformat() if etl_row and etl_row[3] else None,
                "last_run_age_minutes": round(last_run_age_minutes, 1) if last_run_age_minutes else None,
                "avg_duration_seconds": round(etl_row[4], 1) if etl_row and etl_row[4] else None,
            },

            "data": {
                "total_rows": data_row[0] if data_row else 0,
                "bank_count": data_row[1] if data_row else 0,
                "date_range": {
                    "start": data_row[2].isoformat() if data_row and data_row[2] else None,
                    "end": data_row[3].isoformat() if data_row and data_row[3] else None,
                }
            },

            # Placeholder for query metrics (can be populated with tracking)
            "queries": {
                "note": "Query tracking not yet implemented",
                "total_today": None,
                "by_intent": {
                    "evolution": None,
                    "comparison": None,
                    "ranking": None,
                    "clarification": None,
                }
            },

            # Performance baseline from benchmark
            "performance": {
                "baseline": {
                    "ratios_p50_ms": 16,
                    "ratios_p95_ms": 26,
                    "timelines_p50_ms": 112,
                    "timelines_p95_ms": 206,
                    "calculated_p50_ms": 1600,
                },
                "source": "docs/performance_baseline.json"
            }
        }
    except Exception as e:
        logger.error("metrics_endpoint.failed", error=str(e))
        return {
            "timestamp": datetime.now(timezone.utc).isoformat() if 'timezone' in dir() else None,
            "error": str(e)
        }


# ============================================================================
# JSON-RPC 2.0 ENDPOINT FOR BACKEND COMPATIBILITY
# ============================================================================
@app.post("/rpc")
async def json_rpc_endpoint(request: Request):
    """
    JSON-RPC 2.0 endpoint for direct tool invocation from OctaviOS backend.

    This endpoint provides a simple JSON-RPC interface that matches the
    pattern used by other MCP clients in the monolith (audit_mcp_client).
    """
    try:
        body = await request.json()

        # Validate JSON-RPC 2.0 structure
        if body.get("jsonrpc") != "2.0":
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "error": {"code": -32600, "message": "Invalid Request: jsonrpc must be '2.0'"}
            }, status_code=400)

        method = body.get("method")
        params = body.get("params", {})
        rpc_id = body.get("id", "1")

        # Handle tools/call method
        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name == "bank_analytics":
                # Track execution time
                import time
                start_time = time.time()

                try:
                    # Invoke the bank_analytics implementation directly
                    result = await _bank_analytics_impl(
                        metric_or_query=arguments.get("metric_or_query", ""),
                        mode=arguments.get("mode", "dashboard")
                    )

                    execution_time_ms = int((time.time() - start_time) * 1000)

                    # MEJORA: Wrap result with enhanced metadata
                    enhanced_result = {
                        "success": True,
                        "data": result,
                        "metadata": {
                            "version": "1.0.0",
                            "pipeline": result.get("metadata", {}).get("pipeline", "nl2sql"),
                            "template_used": result.get("metadata", {}).get("template_used"),
                            "execution_time_ms": execution_time_ms,
                            "requires_clarification": False,  # For future P0-3
                            "clarification_options": None,
                            "timestamp": datetime.utcnow().isoformat() + "Z"
                        }
                    }

                    logger.info(
                        "rpc.tool_success",
                        tool=tool_name,
                        execution_time_ms=execution_time_ms,
                        metric=result.get("metadata", {}).get("metric")
                    )

                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": rpc_id,
                        "result": {
                            "content": [{"type": "text", "text": json.dumps(enhanced_result)}]
                        }
                    })

                except Exception as e:
                    execution_time_ms = int((time.time() - start_time) * 1000)
                    logger.error(
                        "rpc.tool_execution_failed",
                        tool=tool_name,
                        error=str(e),
                        execution_time_ms=execution_time_ms,
                        exc_info=True
                    )
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": rpc_id,
                        "error": {
                            "code": -32603,
                            "message": "Tool execution failed",
                            "data": {
                                "tool": tool_name,
                                "error": str(e),
                                "error_type": type(e).__name__,
                                "execution_time_ms": execution_time_ms
                            }
                        }
                    }, status_code=500)
            else:
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": rpc_id,
                    "error": {"code": -32601, "message": f"Tool not found: {tool_name}"}
                }, status_code=404)

        # Handle tools/list method
        elif method == "tools/list":
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": rpc_id,
                "result": {
                    "tools": [{
                        "name": "bank_analytics",
                        "description": "Consulta métricas bancarias (INVEX + Sistema Financiero Mexicano)",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "metric_or_query": {"type": "string", "description": "Metric name or natural language query"},
                                "mode": {"type": "string", "enum": ["dashboard", "timeline"], "default": "dashboard"}
                            },
                            "required": ["metric_or_query"]
                        }
                    }]
                }
            })

        else:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": rpc_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            }, status_code=404)

    except json.JSONDecodeError:
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32700, "message": "Parse error"}
        }, status_code=400)

    except Exception as e:
        logger.error("json_rpc.error", error=str(e), exc_info=True)
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": body.get("id") if 'body' in dir() else None,
            "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
        }, status_code=500)


# ============================================================================
# MOUNT MCP SERVER TO FASTAPI (for native MCP clients)
# ============================================================================
# Get the ASGI app from FastMCP and mount it
mcp_app = mcp.http_app(path="/mcp")
app.mount("/mcp", mcp_app)

# Also mount SSE endpoint for compatibility
sse_app = mcp.sse_app(path="/sse")
app.mount("/sse", sse_app)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8002"))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info("bankadvisor.server_starting", host=host, port=port)

    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        log_level="info",
        reload=False  # Production mode
    )
