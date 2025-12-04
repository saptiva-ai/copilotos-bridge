"""
Streaming Handler - SSE (Server-Sent Events) chat response handler.

This module handles streaming responses for chat messages,
following Single Responsibility Principle.

Responsibilities:
    - Stream chat responses via SSE
    - Handle document context for streaming
    - Manage streaming-specific errors
    - Save streamed responses to database
"""

import os
import json
import asyncio
import time
import re
from pathlib import Path
from typing import AsyncGenerator, Optional
from datetime import datetime, timedelta
from uuid import uuid4
from asyncio import Queue, create_task, CancelledError

import structlog
from fastapi import BackgroundTasks

from ....core.config import Settings
from ....core.redis_cache import get_redis_cache
from ....schemas.chat import ChatRequest
from ....services.chat_service import ChatService
from ....services.chat_helpers import build_chat_context
from ....services.session_context_manager import SessionContextManager
from ....services.document_service import DocumentService
from ....services.saptiva_client import get_saptiva_client
from ....services.audit_mcp_client import (
    audit_document_via_mcp,
    MCPAuditorUnavailableError,
)
from ....services.minio_storage import get_minio_storage
from ....models.document import Document, DocumentStatus
from ....models.validation_report import ValidationReport
from ....domain import ChatContext
from ....mcp.tools.ingest_files import IngestFilesTool
from ....mcp.tools.get_segments import GetRelevantSegmentsTool
from ....services.empty_response_handler import (
    EmptyResponseHandler,
    EmptyResponseScenario,
    ensure_non_empty_content
)
from ....services.artifact_service import get_artifact_service
from ....schemas.bank_chart import BankChartArtifactRequest

logger = structlog.get_logger(__name__)


AUDITOR_ANALYSIS_PATTERN = re.compile(r"^(el auditor|la auditoría|auditor)", re.IGNORECASE)
AUDITOR_ORDER = [
    "compliance",
    "format",
    "typography",
    "grammar",
    "logo",
    "color_palette",
    "entity_consistency",
    "semantic_consistency",
]
AUDITOR_DISPLAY_NAMES = {
    "compliance": "Cumplimiento",
    "format": "Formato",
    "typography": "Tipografía",
    "grammar": "Lingüístico",
    "logo": "Identidad visual",
    "color_palette": "Paleta de colores",
    "entity_consistency": "Consistencia de entidades",
    "semantic_consistency": "Consistencia semántica",
    "other": "Otros",
}
AUDITOR_HUMANIZE_NAMES = {
    "compliance": "Disclaimer Auditor",
    "format": "Format Auditor",
    "typography": "Typography Auditor",
    "grammar": "Grammar Auditor",
    "logo": "Logo Auditor",
    "color_palette": "Color Palette Auditor",
    "entity_consistency": "Entity Consistency Auditor",
    "semantic_consistency": "Semantic Consistency Auditor",
    "other": "General Auditor",
}
SEVERITY_DISPLAY = {
    "critical": "críticos",
    "high": "altos",
    "medium": "medios",
    "low": "bajos",
}


def format_auditor_markdown(text: str) -> str:
    """
    Ensure auditor analysis sentences render as markdown sub-lists.
    """
    if not text:
        return text

    formatted_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            formatted_lines.append("")
            continue

        if AUDITOR_ANALYSIS_PATTERN.match(stripped) and not stripped.startswith("-"):
            formatted_lines.append(f"   - {stripped}")
        else:
            formatted_lines.append(line)

    return "\n".join(formatted_lines)


def _normalize_auditor_key(category: str) -> str:
    value = (category or "").lower()
    if not value:
        return "other"
    if value in {"compliance", "cumplimiento"} or "disclaimer" in value:
        return "compliance"
    if value in {"format", "formato"} or "layout" in value or "margen" in value or "tabla" in value:
        return "format"
    if value in {"typography", "tipografia", "tipografía"} or "font" in value or "tipograf" in value:
        return "typography"
    if value in {"grammar", "gramatica", "gramática"} or "linguistic" in value or "ortograf" in value:
        return "grammar"
    if value in {"logo", "identidad"} or "visual" in value:
        return "logo"
    if value in {"color_palette", "color"} or "paleta" in value:
        return "color_palette"
    if value in {"entity_consistency"} or "entidad" in value or "entity" in value:
        return "entity_consistency"
    if value in {"semantic_consistency"} or "semant" in value or "coherencia" in value:
        return "semantic_consistency"
    return "other"


def _aggregate_auditors(validation_event: dict) -> dict:
    summary = validation_event.get("summary") or {}
    by_auditor = summary.get("by_auditor")
    if isinstance(by_auditor, dict) and by_auditor:
        normalized = {str(k).lower(): v for k, v in by_auditor.items()}
        return normalized

    findings = validation_event.get("findings") or []
    auditors: dict[str, dict] = {}
    for finding in findings:
        key = _normalize_auditor_key(finding.get("category", ""))
        entry = auditors.setdefault(
            key,
            {
                "total": 0,
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "findings": [],
            },
        )
        entry["total"] += 1
        severity = str(finding.get("severity", "low")).lower()
        if severity in {"critical", "high", "medium", "low"}:
            entry[severity] += 1
        entry["findings"].append(finding)

    for key, data in auditors.items():
        summary_text = humanize_auditor_result(
            AUDITOR_HUMANIZE_NAMES.get(key, "General Auditor"),
            len(data.get("findings", [])),
            data.get("findings", []),
        )
        data["summary"] = summary_text
    return auditors


def build_auditor_breakdown_markdown(validation_event: dict) -> Optional[str]:
    auditors = _aggregate_auditors(validation_event)
    if not auditors:
        return None

    lines: list[str] = []
    handled = set()

    def append_line(key: str):
        data = auditors.get(key)
        if not data:
            return
        handled.add(key)
        label = AUDITOR_DISPLAY_NAMES.get(
            key, key.replace("_", " ").title()
        )
        summary_text = data.get("summary")
        if not summary_text:
            severity_parts = []
            for severity, label_text in SEVERITY_DISPLAY.items():
                count = data.get(severity, 0)
                if count:
                    plural = "hallazgo" if count == 1 else "hallazgos"
                    severity_parts.append(f"{count} {plural} {label_text}")
            if severity_parts:
                summary_text = ", ".join(severity_parts)
            else:
                total = data.get("total", 0)
                summary_text = (
                    "Sin hallazgos reportados"
                    if total == 0
                    else f"{total} hallazgos registrados"
                )
        lines.append(f"- **{label}:** {summary_text.strip()}")

    for key in AUDITOR_ORDER:
        append_line(key)

    for key in auditors.keys():
        if key not in handled:
            append_line(key)

    if not lines:
        return None

    return "### Análisis por auditor\n" + "\n".join(lines)


def _extract_chart_statistics(bank_chart_data: dict) -> dict:
    """
    Extract key statistics from bank chart plotly_config for LLM context.

    This provides summary statistics without sending full chart data,
    optimizing context window usage (~200 tokens vs ~2000 tokens).

    Args:
        bank_chart_data: BankChartData dict with plotly_config

    Returns:
        Dict with statistics per bank: {bank_name: {min, max, avg, current, trend, change_pct}}
    """
    plotly_cfg = bank_chart_data.get("plotly_config", {})
    traces = plotly_cfg.get("data", [])

    if not traces:
        return {}

    stats_by_bank = {}
    for trace in traces:
        bank_name = trace.get("name", "N/A")
        y_values = trace.get("y", [])

        # Filter out None values
        valid_values = [v for v in y_values if v is not None]

        if valid_values:
            first_val = valid_values[0]
            current_val = valid_values[-1]
            avg_val = sum(valid_values) / len(valid_values)

            # Calculate change percentage safely
            change_pct = 0.0
            if first_val != 0:
                change_pct = ((current_val - first_val) / first_val) * 100

            # Determine trend
            if len(valid_values) >= 2:
                if current_val > first_val:
                    trend = "creciente"
                elif current_val < first_val:
                    trend = "decreciente"
                else:
                    trend = "estable"
            else:
                trend = "N/A"

            stats_by_bank[bank_name] = {
                "min": min(valid_values),
                "max": max(valid_values),
                "avg": avg_val,
                "current": current_val,
                "first": first_val,
                "trend": trend,
                "change_pct": change_pct,
                "data_points": len(valid_values)
            }

    return stats_by_bank


class _InlineValidationReport:
    """
    Lightweight report model for generating PDFs in streaming context
    without persisting to the database.
    """

    def __init__(
        self,
        *,
        document_id: str,
        user_id: str,
        job_id: str,
        status: str,
        client_name: Optional[str],
        findings: list,
        summary: dict,
        attachments: Optional[dict] = None,
    ):
        self.id = str(uuid4())
        self.document_id = document_id
        self.user_id = user_id
        self.job_id = job_id
        self.status = status
        self.client_name = client_name
        self.findings = findings
        self.summary = summary
        self.attachments = attachments or {}
        self.created_at = datetime.utcnow()


async def generate_executive_summary(validation_event: dict, saptiva_client) -> str:
    """
    Generate executive summary using Saptiva Turbo based on all audit findings.

    Args:
        validation_event: The validation_complete event with all findings
        saptiva_client: Saptiva API client

    Returns:
        Executive summary with prioritized recommendations
    """
    summary = validation_event.get("summary", {})
    findings_by_severity = summary.get("findings_by_severity", {})

    critical = findings_by_severity.get('critical', 0)
    high = findings_by_severity.get('high', 0)
    medium = findings_by_severity.get('medium', 0)
    low = findings_by_severity.get('low', 0)

    # Get findings by category with examples
    findings = validation_event.get("findings", [])
    categories = {}
    category_examples = {}  # Store sample findings per category

    for finding in findings:
        cat = finding.get("category", "Sin categoría")
        sev = finding.get("severity", "low")
        if cat not in categories:
            categories[cat] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
            category_examples[cat] = []
        categories[cat][sev] = categories[cat].get(sev, 0) + 1

        # Store first 2 examples per category
        if len(category_examples[cat]) < 2:
            category_examples[cat].append({
                "severity": sev,
                "message": finding.get("message", "")[:80]
            })

    # Build detailed context for LLM
    context = f"""Hallazgos por severidad:
- Críticos: {critical}
- Altos: {high}
- Medios: {medium}
- Bajos: {low}

Hallazgos por categoría (con ejemplos):
"""
    for cat, counts in categories.items():
        if any(counts.values()):
            context += f"\n{cat}:\n"
            if counts["critical"] > 0:
                context += f"  - {counts['critical']} críticos\n"
            if counts["high"] > 0:
                context += f"  - {counts['high']} altos\n"
            if counts["medium"] > 0:
                context += f"  - {counts['medium']} medios\n"
            if counts["low"] > 0:
                context += f"  - {counts['low']} bajos\n"

            # Add examples
            if category_examples.get(cat):
                context += f"  Ejemplos:\n"
                for ex in category_examples[cat]:
                    context += f"    [{ex['severity']}] {ex['message']}\n"

    prompt = f"""Eres un analista de cumplimiento corporativo. Genera un análisis detallado pero conciso del documento auditado.

{context}

GENERA UN ANÁLISIS CON LA SIGUIENTE ESTRUCTURA:

1. CONTEXTO DEL DOCUMENTO (1-2 oraciones):
   - Tipo de documento y su propósito

2. HALLAZGOS PRINCIPALES (lista breve, máximo 4 puntos):
   - Prioriza por severidad crítico > alto > medio
   - Menciona categorías específicas y algunos ejemplos concretos

3. ANÁLISIS POR AUDITOR (1 oración por auditor con hallazgos):
   - Resume cada auditor mencionando cantidad y gravedad
   - Da ejemplos específicos para críticos/altos

4. RECOMENDACIÓN GENERAL (1 oración):
   - Qué hacer primero

Sé directo, profesional, sin emojis. Usa párrafos cortos.
"""

    try:
        response = await saptiva_client.chat_completion(
            model="SAPTIVA_TURBO",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.3
        )

        logger.info("LLM response received", has_response=bool(response), response_type=type(response).__name__)

        if response and hasattr(response, "choices") and len(response.choices) > 0:
            choice = response.choices[0]
            content = choice.get("message", {}).get("content", "") if isinstance(choice, dict) else ""
            logger.info("LLM content extracted", content_length=len(content) if content else 0, content_preview=content[:100] if content else "")
            if content:
                analysis = format_auditor_markdown(content.strip())
                return analysis
            else:
                logger.warning("No content in LLM response", choice_keys=list(choice.keys()) if isinstance(choice, dict) else [])
                return None
        else:
            logger.warning("No valid response from LLM", response_type=type(response).__name__ if response else None)
            return None

    except RuntimeError as e:
        logger.error("Failed to generate executive summary", error=str(e), exc_type=type(e).__name__)
        raise
    except Exception as e:
        logger.warning("Failed to generate executive summary", error=str(e), exc_type=type(e).__name__)
        return None


def generate_document_summary(filename: str, page_count: int, extracted_text: str = "") -> str:
    """
    Generate executive summary of the document based on filename and content.

    Args:
        filename: Document filename
        page_count: Number of pages
        extracted_text: Extracted text from document (optional)

    Returns:
        Formatted executive summary string
    """
    # Infer document type from filename patterns
    doc_type = "Documento corporativo"
    if any(kw in filename.lower() for kw in ["presentacion", "presentation", "pitch"]):
        doc_type = "Presentación corporativa"
    elif any(kw in filename.lower() for kw in ["prospecto", "prospectus"]):
        doc_type = "Prospecto financiero"
    elif any(kw in filename.lower() for kw in ["reporte", "report", "informe"]):
        doc_type = "Reporte ejecutivo"
    elif any(kw in filename.lower() for kw in ["proceso", "process", "procedimiento"]):
        doc_type = "Documento de proceso"
    elif any(kw in filename.lower() for kw in ["politica", "policy", "manual"]):
        doc_type = "Documento normativo"
    elif any(kw in filename.lower() for kw in ["uso", "guia", "guide"]):
        doc_type = "Guía de uso"

    # Extract potential topic from filename
    topic = "No especificado"
    if "valoracion" in filename.lower():
        topic = "Proceso de valoración de activos"
    elif "ia" in filename.lower() or "ai" in filename.lower():
        topic = "Inteligencia Artificial y uso de tecnología"
    elif "inversion" in filename.lower():
        topic = "Estrategia de inversión"
    elif "riesgo" in filename.lower():
        topic = "Gestión de riesgos"

    summary = f"📄 **{doc_type}** • {page_count} páginas\n"
    summary += f"_{topic}_\n\n"

    return summary


def humanize_auditor_result(auditor_name: str, findings_count: int, findings: list) -> str:
    """
    Generate human-readable interpretation of auditor results.

    Args:
        auditor_name: Name of the auditor (e.g., "Grammar Auditor")
        findings_count: Number of findings
        findings: List of finding dictionaries with 'severity' key

    Returns:
        Human-readable summary string
    """
    if findings_count == 0:
        no_issues_messages = {
            "Grammar Auditor": "No se detectaron errores ortográficos ni gramaticales. El texto está impecable.",
            "Format Auditor": "El formato del documento cumple perfectamente con los estándares.",
            "Logo Auditor": "Los logos están correctamente posicionados y con la calidad esperada.",
            "Color Palette Auditor": "La paleta de colores está bien aplicada en todo el documento.",
            "Disclaimer Auditor": "Todos los disclaimers requeridos están presentes y correctos.",
            "Typography Auditor": "La tipografía cumple con las especificaciones del manual de marca.",
            "Entity Consistency Auditor": "Las entidades están nombradas de forma consistente en todo el documento.",
            "Semantic Consistency Auditor": "El contenido mantiene coherencia semántica en todas las secciones.",
        }
        return no_issues_messages.get(auditor_name, f"No se encontraron problemas en {auditor_name}.")

    # Count by severity
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for finding in findings:
        severity = finding.get("severity", "low").lower()
        if severity in severity_counts:
            severity_counts[severity] += 1

    # Build interpretation based on severity distribution
    critical = severity_counts["critical"]
    high = severity_counts["high"]
    medium = severity_counts["medium"]
    low = severity_counts["low"]

    if critical > 0:
        level = "🔴 Crítico"
        interpretation = f"Se encontraron {critical} {'problema' if critical == 1 else 'problemas'} {'crítico' if critical == 1 else 'críticos'} que requieren atención inmediata"
    elif high > 0:
        level = "🟠 Alto"
        interpretation = f"Hay {high} {'hallazgo' if high == 1 else 'hallazgos'} de prioridad alta que deben corregirse"
    elif medium > 0:
        level = "🟡 Medio"
        interpretation = f"Se detectaron {medium} {'aspecto' if medium == 1 else 'aspectos'} a mejorar de prioridad media"
    else:
        level = "🟢 Bajo"
        interpretation = f"Solo {low} {'detalle' if low == 1 else 'detalles'} menores detectados"

    return f"{level} - {interpretation}"


def calculate_dynamic_max_tokens(
    messages: list[dict],
    model_limit: int = 8192,
    min_tokens: int = 500,
    max_tokens: int = 3000,
    safety_margin: int = 100
) -> int:
    """
    Calculate optimal max_tokens based on actual prompt size.

    This prevents context length errors by dynamically adjusting the response
    budget based on how much space the prompt (system + RAG context + user message) takes.

    Args:
        messages: List of message dicts with 'content' key
        model_limit: Total token limit for the model (default: 8192 for Saptiva Turbo)
        min_tokens: Minimum tokens to allow for response (default: 500)
        max_tokens: Maximum tokens to allow for response (default: 3000)
        safety_margin: Extra buffer to prevent edge cases (default: 100)

    Returns:
        Optimal max_tokens value that fits within model limits

    Example:
        messages = [
            {"role": "system", "content": "You are a helpful assistant..."},
            {"role": "user", "content": "What is AI?"}
        ]
        max_tokens = calculate_dynamic_max_tokens(messages)
        # Returns ~7500 if prompt is small, or ~1000 if prompt has large RAG context
    """
    # Estimate tokens from character count
    # GPT-style tokenization: ~1 token per 4 characters (conservative estimate)
    total_chars = sum(len(str(msg.get("content", ""))) for msg in messages)
    estimated_prompt_tokens = total_chars // 4

    # Calculate available space for response
    available_tokens = model_limit - estimated_prompt_tokens - safety_margin

    # Clamp to reasonable bounds
    optimal_tokens = max(min_tokens, min(available_tokens, max_tokens))

    logger.debug(
        "Calculated dynamic max_tokens | prompt_chars=%s estimated_prompt_tokens=%s available_tokens=%s optimal_max_tokens=%s model_limit=%s",
        total_chars,
        estimated_prompt_tokens,
        available_tokens,
        optimal_tokens,
        model_limit,
    )

    return optimal_tokens


class StreamingHandler:
    """
    Handles streaming SSE responses for chat messages.

    This class encapsulates all streaming-specific logic,
    following Single Responsibility Principle.
    """

    def __init__(self, settings: Settings):
        """
        Initialize streaming handler.

        Args:
            settings: Application settings
        """
        self.settings = settings

    @staticmethod
    def _build_tools_markdown(has_documents: bool) -> Optional[str]:
        """
        Build a minimal markdown section describing available tools.

        Today we only expose get_relevant_segments when there are documents
        so the LLM knows it can retrieve context for RAG.
        """
        if not has_documents:
            return None

        return (
            "* **get_relevant_segments** — Retrieve relevant document segments for RAG\n"
            "  - Parameters: conversation_id (string), question (string), max_segments (int)\n"
            "  - Use when: User asks about uploaded documents\n"
            "  - conversation_id: use the active chat/session id\n"
            "  - question: user question as-is\n"
            "  - max_segments: default 2"
        )

    async def handle_stream(
        self,
        request: ChatRequest,
        user_id: str,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> AsyncGenerator[dict, None]:
        """
        Handle streaming SSE response for chat request.

        Yields Server-Sent Events with incremental chunks from Saptiva API.

        Args:
            request: ChatRequest from endpoint
            user_id: Authenticated user ID

        Yields:
            dict: SSE events with format {"event": str, "data": str}

        Note:
            Audit commands are NOT supported in streaming mode.
            An error event is yielded if audit is requested.
        """
        try:
            # Build context
            context = build_chat_context(request, user_id, self.settings)

            logger.info(
                "Processing streaming chat request",
                request_id=context.request_id,
                user_id=context.user_id,
                model=context.model
            )

            # Initialize services
            chat_service = ChatService(self.settings)
            cache = await get_redis_cache()

            # Get or create session
            chat_session = await chat_service.get_or_create_session(
                chat_id=context.chat_id,
                user_id=context.user_id,
                first_message=context.message,
                tools_enabled=context.tools_enabled
            )

            context = context.with_session(chat_session.id)

            # Prepare session context (files)
            request_file_ids = list(
                (request.file_ids or []) + (request.document_ids or [])
            )

            # DEBUG: Log session attached_file_ids for RAG troubleshooting
            logger.info(
                "🔍 [RAG DEBUG] Session file context",
                session_id=chat_session.id,
                session_attached_file_ids=getattr(chat_session, 'attached_file_ids', []),
                request_file_ids=request_file_ids,
                timestamp=context.timestamp
            )

            current_file_ids = await SessionContextManager.prepare_session_context(
                chat_session=chat_session,
                request_file_ids=request_file_ids,
                user_id=user_id,
                redis_cache=cache,
                request_id=context.request_id
            )

            # DEBUG: Log resolved file IDs
            logger.info(
                "✅ [RAG DEBUG] Resolved file IDs",
                session_id=chat_session.id,
                current_file_ids=current_file_ids,
                will_use_rag=bool(current_file_ids)
            )

            # Update context with resolved file IDs
            if current_file_ids:
                context = ChatContext(
                    user_id=context.user_id,
                    request_id=context.request_id,
                    timestamp=context.timestamp,
                    chat_id=context.chat_id,
                    session_id=context.session_id,
                    message=context.message,
                    context=context.context,
                    document_ids=current_file_ids,
                    model=context.model,
                    tools_enabled=context.tools_enabled,
                    stream=context.stream,
                    temperature=context.temperature,
                    max_tokens=context.max_tokens,
                    kill_switch_active=context.kill_switch_active
                )

                # NEW: Ingest files using IngestFilesTool (async processing)
                if background_tasks and current_file_ids:
                    # If all documents are already READY and contain extracted
                    # content (typical in tests with cached pages), skip
                    # re-ingestion to avoid MinIO errors.
                    ready_docs = []
                    for _doc_id in current_file_ids:
                        doc_obj = await Document.get(_doc_id)
                        if doc_obj and doc_obj.status == DocumentStatus.READY:
                            ready_docs.append(doc_obj)
                    all_ready = len(ready_docs) == len(current_file_ids)

                    if all_ready:
                        logger.info(
                            "Skipping ingestion - documents already READY",
                            session_id=chat_session.id,
                            file_count=len(current_file_ids)
                        )
                    else:
                        try:
                            ingest_tool = IngestFilesTool()
                            result = await ingest_tool.execute(
                                payload={
                                    "conversation_id": chat_session.id,
                                    "file_refs": current_file_ids
                                },
                                context={"background_tasks": background_tasks}
                            )

                            logger.info(
                                "Document ingestion dispatched",
                                session_id=chat_session.id,
                                file_count=len(current_file_ids),
                                ingested=result.get("ingested", 0),
                                status=result.get("status")
                            )

                            # CRITICAL FIX: Add delay to allow MongoDB write to propagate
                            await asyncio.sleep(0.1)

                            logger.info(
                                "🕐 [RAG DEBUG] Waited for MongoDB write propagation",
                                session_id=chat_session.id,
                                delay_ms=100,
                                timestamp=datetime.utcnow().isoformat()
                            )

                            # ANTI-HALLUCINATION: Wait until docs are READY
                            max_wait_seconds = 30
                            poll_interval = 0.5
                            elapsed = 0

                            while elapsed < max_wait_seconds:
                                docs_ready = True
                                for doc_id in current_file_ids:
                                    doc = await Document.get(doc_id)
                                    if doc and doc.status != DocumentStatus.READY:
                                        docs_ready = False
                                        break

                                if docs_ready:
                                    logger.info(
                                        "✅ [RAG ANTI-HALLUCINATION] All documents READY",
                                        session_id=chat_session.id,
                                        elapsed_seconds=round(elapsed, 2),
                                        file_count=len(current_file_ids)
                                    )
                                    break

                                await asyncio.sleep(poll_interval)
                                elapsed += poll_interval

                            if elapsed >= max_wait_seconds:
                                logger.warning(
                                    "⚠️ [RAG ANTI-HALLUCINATION] Timeout waiting for documents",
                                    session_id=chat_session.id,
                                    timeout_seconds=max_wait_seconds,
                                    file_count=len(current_file_ids)
                                )
                        except Exception as ingest_exc:
                            logger.error(
                                "Document ingestion failed",
                                session_id=chat_session.id,
                                error=str(ingest_exc),
                                exc_info=True
                            )

            # Add user message
            user_message_metadata = request.metadata.copy() if request.metadata else {}
            if current_file_ids:
                user_message_metadata["file_ids"] = current_file_ids

            user_message = await chat_service.add_user_message(
                chat_session=chat_session,
                content=context.message,
                metadata=user_message_metadata if user_message_metadata else None
            )

            # BA-P0-004: Check for bank analytics query BEFORE streaming
            # GLOBAL MODE: Bank Advisor is always active and automatically detects relevant queries
            # The is_bank_query() function determines if the message is banking-related
            bank_chart_data = None
            from ....services.tool_execution_service import ToolExecutionService
            from ....models.chat import ChatMessage as ChatMessageModel

            logger.debug(
                "Bank advisor global mode - checking for bank analytics query",
                message_preview=context.message[:100],
                request_id=context.request_id
            )

            # Get recent messages for clarification context detection
            recent_messages = []
            try:
                recent_msgs = await ChatMessageModel.find(
                    ChatMessageModel.chat_id == chat_session.id
                ).sort(-ChatMessageModel.created_at).limit(5).to_list()

                # Convert to dict format with metadata for clarification detection
                for msg in reversed(recent_msgs):
                    recent_messages.append({
                        "role": msg.role.value,
                        "content": msg.content,
                        "metadata": msg.metadata if hasattr(msg, 'metadata') else {}
                    })
            except Exception as e:
                logger.warning(
                    "Failed to load recent messages for clarification context",
                    error=str(e)
                )

            bank_chart_data = await ToolExecutionService.invoke_bank_analytics(
                message=context.message,
                user_id=user_id,
                recent_messages=recent_messages if recent_messages else None
            )

            # Note: bank_chart_data will be passed to _stream_chat_response
            if bank_chart_data:
                logger.info(
                    "Bank analytics result detected and will be streamed",
                    metric=bank_chart_data.get("metric_name"),
                    request_id=context.request_id
                )
            else:
                logger.debug(
                    "No bank analytics data returned (message not banking-related)",
                    request_id=context.request_id
                )

            # Check for audit command (NOW supported in streaming!)
            if context.message.strip().startswith("Auditar archivo:"):
                async for event in self._stream_audit_response(
                    chat_service, chat_session, context, user_message
                ):
                    yield event
                return

            # Stream chat response
            async for event in self._stream_chat_response(
                context, chat_service, chat_session, cache, user_message,
                bank_chart_data=bank_chart_data  # BA-P0-004: Pass bank analytics result
            ):
                yield event

        except Exception as exc:
            import traceback
            # ISSUE-020: Enhanced error logging with full context
            error_details = {
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "traceback": traceback.format_exc(),
                "user_id": user_id,
                "model": request.model if request.model else "default",
                "stream": request.stream if hasattr(request, 'stream') else None
            }

            # Add context fields if available (may not exist if error during context creation)
            if 'context' in locals():
                error_details.update({
                    "chat_id": context.chat_id,
                    "session_id": getattr(context, 'session_id', None),
                    "message_preview": context.message[:100] if context.message else None,
                    "request_id": context.request_id,
                })

            logger.error(
                "🚨 STREAMING CHAT FAILED - CRITICAL ERROR",
                **error_details,
                exc_info=True
            )

            # Also print to stderr for immediate visibility (ISSUE-020: with context)
            print(f"\n{'='*80}")
            print(f"🚨 STREAMING ERROR: {type(exc).__name__}")
            print(f"Message: {str(exc)}")
            print(f"User: {user_id}")
            if 'context' in locals():
                print(f"Chat ID: {context.chat_id}")
                print(f"Model: {context.model}")
                print(f"Message Preview: {context.message[:100] if context.message else 'N/A'}")
            print(f"Traceback:\n{traceback.format_exc()}")
            print(f"{'='*80}\n")

            yield {
                "event": "error",
                "data": json.dumps({
                    "error": type(exc).__name__,
                    "message": str(exc),
                    "details": "Check server logs for full traceback"
                })
            }

    async def _stream_audit_response(
        self,
        chat_service: ChatService,
        chat_session,
        context: ChatContext,
        user_message
    ) -> AsyncGenerator[dict, None]:
        """
        Stream audit validation progress in real-time.

        Args:
            chat_service: ChatService instance
            chat_session: ChatSession model
            context: ChatContext with request data
            user_message: Saved user message model

        Yields:
            SSE events for audit progress
        """
        logger.info(
            "Streaming audit command",
            message=context.message,
            user_id=context.user_id,
            file_ids=context.document_ids
        )

        # Extract filename from command: "Auditar archivo: filename.pdf"
        filename = context.message.strip().replace("Auditar archivo:", "").strip()

        # Find document by filename in document_ids
        document = None
        if context.document_ids and len(context.document_ids) > 0:
            doc_service = DocumentService()
            for file_id in context.document_ids:
                try:
                    doc = await Document.get(file_id)
                    if doc and doc.filename == filename:
                        document = doc
                        break
                except Exception as e:
                    logger.warning(f"Could not load document {file_id}: {e}")

        if not document:
            error_msg = f"❌ No se encontró el archivo: {filename}"
            await chat_service.add_assistant_message(
                chat_session=chat_session,
                content=error_msg,
                model=context.model,
                metadata={"error": "document_not_found"}
            )
            yield {
                "event": "error",
                "data": json.dumps({
                    "error": "document_not_found",
                    "message": error_msg
                })
            }
            return

        # Materialize PDF - follow pattern from audit_handler.py
        pdf_path = Path(document.minio_key)
        is_temp = False

        if not pdf_path.exists():
            minio_storage = get_minio_storage()
            if minio_storage:
                try:
                    pdf_path, is_temp = minio_storage.materialize_document(
                        document.minio_key,
                        filename=document.filename,
                        bucket=document.minio_bucket
                    )
                except Exception as storage_exc:
                    logger.error(
                        "Failed to materialize PDF from MinIO",
                        doc_id=str(document.id),
                        error=str(storage_exc)
                    )
                    error_msg = f"❌ Error al cargar el archivo: {str(storage_exc)}"
                    await chat_service.add_assistant_message(
                        chat_session=chat_session,
                        content=error_msg,
                        model=context.model,
                        metadata={"error": "pdf_materialization_failed"}
                    )
                    yield {
                        "event": "error",
                        "data": json.dumps({
                            "error": "pdf_materialization_failed",
                            "message": error_msg
                        })
                    }
                    return
            else:
                error_msg = "❌ Sistema de almacenamiento no disponible"
                await chat_service.add_assistant_message(
                    chat_session=chat_session,
                    content=error_msg,
                    model=context.model,
                    metadata={"error": "storage_unavailable"}
                )
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "error": "storage_unavailable",
                        "message": error_msg
                    })
                }
                return

        # Yield metadata event
        yield {
            "event": "meta",
            "data": json.dumps({
                "chat_id": str(chat_session.id),
                "user_message_id": str(user_message.id),
                "model": context.model,
                "audit_streaming": True,
                "document_id": str(document.id),
                "filename": document.filename,
            })
        }

        accumulated_content = []
        validation_complete_event = None

        try:
            # Yield initial progress message
            start_content = f"🔍 Analizando **{document.filename}**\n\n"
            accumulated_content.append(start_content)
            yield {
                "event": "chunk",
                "data": json.dumps({
                    "content": start_content,
                    "audit_event": {"type": "validation_start", "filename": document.filename},
                })
            }

            # Call MCP auditor service (non-streaming)
            mcp_result = await audit_document_via_mcp(
                file_path=str(pdf_path),
                policy_id="auto",
                client_name=None,
                enable_disclaimer=True,
                enable_format=True,
                enable_typography=True,
                enable_grammar=True,
                enable_logo=True,
                enable_color_palette=True,
                enable_entity_consistency=True,
                enable_semantic_consistency=True,
            )

            # Build validation_complete_event from MCP result
            validation_complete_event = {
                "type": "validation_complete",
                "job_id": mcp_result.get("job_id"),
                "status": mcp_result.get("status"),
                "filename": document.filename,
                "duration_ms": mcp_result.get("validation_duration_ms", 0),
                "summary": {
                    "total_findings": mcp_result.get("total_findings", 0),
                    "findings_by_severity": mcp_result.get("findings_by_severity", {}),
                    "findings_by_category": mcp_result.get("findings_by_category", {}),
                    "disclaimer_coverage": mcp_result.get("disclaimer_coverage"),
                },
                "findings": mcp_result.get("top_findings", []),
                "policy_id": mcp_result.get("policy_id"),
                "policy_name": mcp_result.get("policy_name"),
                "attachments": {
                    "pdf_report_path": mcp_result.get("pdf_report_path"),
                } if mcp_result.get("pdf_report_path") else {},
            }

            # Build result content
            total_findings = mcp_result.get("total_findings", 0)
            duration = mcp_result.get("validation_duration_ms", 0)
            findings_by_severity = mcp_result.get("findings_by_severity", {})

            critical = findings_by_severity.get('critical', 0)
            high = findings_by_severity.get('high', 0)
            medium = findings_by_severity.get('medium', 0)
            low = findings_by_severity.get('low', 0)

            # Build result content
            content = f"**Resultado de Auditoría**\n\n"

            # Use executive summary from MCP if available
            executive_summary_md = mcp_result.get("executive_summary_markdown")
            if executive_summary_md:
                content += f"{executive_summary_md}\n\n"
                content += f"---\n\n"

            # Build auditor breakdown from findings_by_category
            findings_by_category = mcp_result.get("findings_by_category", {})
            if findings_by_category:
                content += "**Desglose por auditor:**\n\n"
                for category, count in findings_by_category.items():
                    display_name = AUDITOR_DISPLAY_NAMES.get(category, category)
                    content += f"- {display_name}: {count} hallazgo{'s' if count != 1 else ''}\n"
                content += "\n"

            # PRIORITIZED: Critical first
            if critical > 0:
                content += f"⚠️ **ATENCIÓN:** {critical} {'problema crítico' if critical == 1 else 'problemas críticos'} {'detectado' if critical == 1 else 'detectados'}\n"
                content += f"_Corrección obligatoria antes de publicar_\n\n"

            # PRIORITIZED: High priority second
            if high > 0:
                content += f"📝 **{high} recomendación{'' if high == 1 else 'es'}** de prioridad alta\n"
                content += f"_Se sugiere revisar para cumplir estándares corporativos_\n\n"

            # PRIORITIZED: Medium and Low together
            if medium > 0 or low > 0:
                suggestions_count = medium + low
                content += f"✓ **{suggestions_count} sugerencia{'' if suggestions_count == 1 else 's'}** opcional{'' if suggestions_count == 1 else 'es'}\n"
                content += f"_Mejoras de estilo y calidad_\n\n"

            # Perfect document
            if total_findings == 0:
                content += f"✅ **Documento aprobado**\n"
                content += f"_Cumple con todos los estándares de calidad_\n\n"

            # Footer with meta info
            content += f"---\n"
            content += f"_Análisis completado • {duration}ms_\n"

            accumulated_content.append(content)

            # Yield result chunk
            yield {
                "event": "chunk",
                "data": json.dumps({
                    "content": content,
                    "audit_event": validation_complete_event,
                })
            }

            # Save ValidationReport to MongoDB
            validation_report_id = None
            try:
                validation_report_doc = ValidationReport(
                    document_id=str(document.id),
                    user_id=str(document.user_id),
                    job_id=mcp_result.get("job_id") or str(uuid4()),
                    status="done" if mcp_result.get("status") == "completed" else "error",
                    client_name=mcp_result.get("policy_name"),
                    auditors_enabled={
                        "disclaimer": True,
                        "format": True,
                        "typography": True,
                        "grammar": True,
                        "logo": True,
                        "color_palette": True,
                        "entity_consistency": True,
                        "semantic_consistency": True,
                    },
                    findings=mcp_result.get("top_findings", []),
                    summary={
                        "total_findings": total_findings,
                        "findings_by_severity": findings_by_severity,
                        "findings_by_category": findings_by_category,
                        "disclaimer_coverage": mcp_result.get("disclaimer_coverage"),
                        "policy_id": mcp_result.get("policy_id"),
                        "policy_name": mcp_result.get("policy_name"),
                        "validation_duration_ms": duration,
                    },
                    attachments=validation_complete_event.get("attachments", {}),
                )
                await validation_report_doc.insert()
                validation_report_id = str(validation_report_doc.id)
                validation_complete_event["validation_report_id"] = validation_report_id
                logger.info(
                    "MCP audit: ValidationReport persisted",
                    validation_report_id=validation_report_id,
                    findings=total_findings,
                )
            except Exception as persist_exc:
                logger.error(
                    "MCP audit: failed to persist ValidationReport",
                    error=str(persist_exc),
                    exc_type=type(persist_exc).__name__,
                )

            # Transform findings list into categories dict (grouped by category)
            findings_list = validation_complete_event.get("findings", [])
            categories = {}
            for finding in findings_list:
                category = finding.get("category", "Sin categoría")
                if category not in categories:
                    categories[category] = []
                categories[category].append(finding)

            # Build complete AuditReportResponse structure
            audit_artifact = {
                "type": "audit_report_ui",
                "doc_name": document.filename,
                "metadata": {
                    "display_name": document.filename,
                    "filename": document.filename,
                    "policy_used": {
                        "id": validation_complete_event.get("policy_id"),
                        "name": validation_complete_event.get("policy_name", "N/D"),
                    },
                    "attachments": validation_complete_event.get("attachments", {}),
                    "validation_report_id": validation_complete_event.get("validation_report_id"),
                    "report_pdf_url": validation_complete_event.get("attachments", {}).get("pdf_report_path"),
                },
                "stats": {
                    "critical": validation_complete_event.get("summary", {}).get("findings_by_severity", {}).get("critical", 0),
                    "high": validation_complete_event.get("summary", {}).get("findings_by_severity", {}).get("high", 0),
                    "medium": validation_complete_event.get("summary", {}).get("findings_by_severity", {}).get("medium", 0),
                    "low": validation_complete_event.get("summary", {}).get("findings_by_severity", {}).get("low", 0),
                    "total": validation_complete_event.get("summary", {}).get("total_findings", 0),
                },
                "categories": categories,
                "actions": [],
                "payload": validation_complete_event,
            }

            # Save final response with artifact in metadata
            full_content = "".join(accumulated_content)
            artifact_report_url = (
                audit_artifact.get("metadata", {}).get("report_pdf_url")
                if audit_artifact
                else None
            )
            artifact_attachments = (
                validation_complete_event.get("attachments", {}) if validation_complete_event else {}
            )
            message_metadata = {
                "audit_completed": True,
                "document_id": str(document.id),
                "filename": document.filename,
                "job_id": validation_complete_event.get("job_id") if validation_complete_event else None,
                "artifact": audit_artifact,
                "report_pdf_url": artifact_report_url,
                "attachments": artifact_attachments,
                "validation_report_id": validation_complete_event.get("validation_report_id") if validation_complete_event else None,
                "decision_metadata": {
                    "report_pdf_url": artifact_report_url,
                    "attachments": artifact_attachments,
                    "audit_artifact": audit_artifact,
                    "validation_report_id": validation_complete_event.get("validation_report_id") if validation_complete_event else None,
                },
            }

            assistant_message = await chat_service.add_assistant_message(
                chat_session=chat_session,
                content=full_content,
                model=context.model,
                metadata=message_metadata,
            )
            logger.info(
                "Streaming audit: assistant message saved with PDF metadata",
                message_id=str(assistant_message.id),
                has_report_pdf=bool(artifact_report_url),
                report_pdf_url=artifact_report_url,
                validation_report_id=message_metadata.get("validation_report_id"),
            )

            # Yield done event
            done_data = {
                "message_id": str(assistant_message.id),
                "content": full_content,
                "model": context.model,
                "chat_id": str(chat_session.id),
                "metadata": message_metadata,
            }

            # Include artifact if audit completed successfully
            if audit_artifact:
                done_data["artifact"] = audit_artifact

            yield {
                "event": "done",
                "data": json.dumps(done_data)
            }

        except Exception as exc:
            logger.error(
                "Audit streaming failed",
                error=str(exc),
                exc_info=True
            )

            error_msg = f"❌ Error durante la auditoría: {str(exc)}"
            await chat_service.add_assistant_message(
                chat_session=chat_session,
                content=error_msg,
                model=context.model,
                metadata={"error": "audit_execution_failed"}
            )

            yield {
                "event": "error",
                "data": json.dumps({
                    "error": "audit_execution_failed",
                    "message": error_msg,
                    "details": str(exc)
                })
            }

        finally:
            # Clean up temporary PDF file
            if is_temp and pdf_path.exists():
                pdf_path.unlink()

    async def _stream_chat_response(
        self,
        context: ChatContext,
        chat_service: ChatService,
        chat_session,
        cache,
        user_message,
        bank_chart_data=None  # BA-P0-004: Optional bank analytics result
    ) -> AsyncGenerator[dict, None]:
        """
        Stream chat response from Saptiva API.

        Args:
            context: ChatContext with request data
            chat_service: ChatService instance
            chat_session: ChatSession model
            cache: Redis cache instance
            user_message: User message model with ID

        Yields:
            SSE events with message chunks and completion
        """
        # FIX-001: Wrap entire streaming logic in try-catch for proper error propagation
        try:
            # NEW: Prepare document context for RAG using GetRelevantSegmentsTool
            document_context = None
            doc_warnings = []

            # DEBUG: Log before RAG retrieval
            logger.info(
                "🔍 [RAG DEBUG] Checking if should retrieve segments",
                has_document_ids=bool(context.document_ids),
                document_ids_count=len(context.document_ids) if context.document_ids else 0,
                document_ids=context.document_ids
            )

            if context.document_ids:
                logger.info(
                    "🚀 [RAG DEBUG] Starting GetRelevantSegmentsTool",
                    conversation_id=context.session_id,
                    question_preview=context.message[:100]
                )

                try:
                    # Use new GetRelevantSegmentsTool for semantic retrieval
                    get_segments_tool = GetRelevantSegmentsTool()
                    segments_result = await get_segments_tool.execute(
                        payload={
                            "conversation_id": context.session_id,
                            "question": context.message,
                            "max_segments": 2  # Reduced for token budget optimization
                        }
                    )

                    segments = segments_result.get("segments", [])

                    if segments:
                        # Build context from retrieved segments
                        segment_texts = []
                        for seg in segments:
                            source = f"**{seg['doc_name']}** (relevancia: {seg['score']:.2f})"
                            segment_texts.append(f"{source}\n{seg['text']}")

                        document_context = "\n\n---\n\n".join(segment_texts)

                        logger.info(
                            "Document segments retrieved for RAG",
                            session_id=context.session_id,
                            segments_count=len(segments),
                            ready_docs=segments_result.get("ready_docs", 0),
                            total_docs=segments_result.get("total_docs", 0)
                        )
                    else:
                        # No segments from Qdrant - fallback to loading full text from Redis/MongoDB
                        logger.info(
                            "🔄 [RAG FALLBACK] No segments from Qdrant, loading full text from cache",
                            session_id=context.session_id,
                            document_ids=context.document_ids
                        )

                        try:
                            # Fallback: Load document text directly from Redis cache
                            doc_texts = await DocumentService.get_document_text_from_cache(
                                document_ids=context.document_ids,
                                user_id=context.user_id
                            )

                            if doc_texts:
                                segment_texts = []
                                for doc_id, doc_data in doc_texts.items():
                                    text = doc_data.get("text", "")
                                    filename = doc_data.get("filename", doc_id)
                                    if text:
                                        # Truncate to avoid token overflow (4000 chars ~ 1000 tokens)
                                        truncated_text = text[:4000]
                                        segment_texts.append(f"**{filename}**\n{truncated_text}")

                                if segment_texts:
                                    document_context = "\n\n---\n\n".join(segment_texts)
                                    logger.info(
                                        "✅ [RAG FALLBACK] Successfully loaded document text from cache",
                                        session_id=context.session_id,
                                        docs_loaded=len(segment_texts),
                                        total_chars=len(document_context)
                                    )
                                else:
                                    logger.warning(
                                        "⚠️ [RAG FALLBACK] Documents in cache but no extractable text",
                                        session_id=context.session_id
                                    )
                            else:
                                # No documents in cache - check if they're still processing
                                message = segments_result.get("message", "")
                                if "procesando" in message.lower() or "processing" in message.lower():
                                    warning_msg = "⏳ Los documentos se están procesando. Estarán disponibles en breve."
                                    doc_warnings.append(warning_msg)
                                    logger.warning(
                                        "⚠️ [RAG DEBUG] Documents still processing - warning added",
                                        session_id=context.session_id,
                                        warning_message=warning_msg,
                                        total_docs=segments_result.get("total_docs", 0),
                                        ready_docs=segments_result.get("ready_docs", 0),
                                        timestamp=datetime.utcnow().isoformat()
                                    )

                        except Exception as fallback_exc:
                            logger.error(
                                "❌ [RAG FALLBACK] Failed to load documents from cache",
                                error=str(fallback_exc),
                                exc_type=type(fallback_exc).__name__,
                                session_id=context.session_id
                            )
                            # Don't fail - continue without document context

                except Exception as doc_exc:
                    logger.error(
                        "Document segment retrieval failed - continuing without documents",
                        error=str(doc_exc),
                        exc_type=type(doc_exc).__name__,
                        document_ids=context.document_ids,
                        user_id=context.user_id
                    )
                    # Don't fail the entire request - continue without document context
                    doc_warnings.append(
                        f"No se pudieron cargar los documentos adjuntos: {str(doc_exc)[:100]}"
                    )

            # Initialize Saptiva client (singleton managed async factory)
            saptiva_client = await get_saptiva_client()

            # FIX-001: Use centralized prompt registry instead of hardcoded string
            # This ensures consistent Saptiva branding across all models
            from ....core.prompt_registry import get_prompt_registry
            prompt_registry = get_prompt_registry()

            # Build tools markdown when documents are available so the LLM knows about RAG tool
            has_docs_available = bool(
                document_context
                or context.document_ids
                or (locals().get("current_file_ids") and len(locals().get("current_file_ids")) > 0)
            )

            # Resolve system prompt for this model
            system_prompt, model_params = prompt_registry.resolve(
                model=context.model,
                tools_markdown=self._build_tools_markdown(has_documents=has_docs_available),
                channel="chat"
            )

            # Add document context if available
            if document_context:
                system_prompt += f"\n\n**Documentos adjuntos por el usuario:**\n{document_context}"

            # BA-P0-004 + HU3.1: Add bank analytics context if available
            if bank_chart_data:
                # HU3.1: Check if this is a clarification response
                if isinstance(bank_chart_data, dict) and bank_chart_data.get("type") == "clarification":
                    # Build clarification context for LLM
                    clarification_message = bank_chart_data.get("message", "")
                    clarification_options = bank_chart_data.get("options", [])
                    clarification_context_data = bank_chart_data.get("context", {})

                    options_text = "\n".join([
                        f"  - **{opt.get('label', opt.get('id', ''))}**: {opt.get('description', '')}"
                        for opt in clarification_options
                    ])

                    bank_context = f"""

**ACLARACIÓN REQUERIDA - Se está mostrando un selector de opciones al usuario:**

Mensaje mostrado: "{clarification_message}"

Opciones disponibles:
{options_text}

Contexto detectado:
- Bancos mencionados: {', '.join(clarification_context_data.get('banks', [])) or 'No especificados'}
- Consulta original: {clarification_context_data.get('original_query', 'N/A')}

**IMPORTANTE**: El usuario está viendo un selector con las opciones de arriba.
Genera una respuesta BREVE que:
1. Confirme que necesitas más información para responder su consulta
2. Mencione brevemente las opciones disponibles (sin repetir la lista completa)
3. Invite al usuario a seleccionar una opción del selector mostrado

NO intentes adivinar qué opción quiere el usuario. Espera a que seleccione una."""

                    system_prompt += bank_context
                else:
                    # Regular chart data context
                    metric_name = bank_chart_data.get("metric_name", "N/A")
                    bank_names = ", ".join(bank_chart_data.get("bank_names", []))
                    time_range = bank_chart_data.get("time_range", {})
                    data_as_of = bank_chart_data.get("data_as_of", "N/A")

                    # Extract SQL if available (from metadata or direct field)
                    sql_query = None
                    metadata = {}
                    if isinstance(bank_chart_data, dict):
                        metadata = bank_chart_data.get("metadata", {})
                        sql_query = metadata.get("sql_generated") or bank_chart_data.get("sql_generated")

                    # Extract statistics from plotly_config for enriched LLM context
                    chart_stats = _extract_chart_statistics(bank_chart_data)
                    is_ratio = metadata.get("type") == "ratio" or metadata.get("metric_type") == "ratio"
                    unit_label = "%" if is_ratio else "MDP"

                    bank_context = f"""

**Análisis bancario disponible:**
- Métrica consultada: {metric_name}
- Bancos: {bank_names}
- Período: {time_range.get('start', 'N/A')} a {time_range.get('end', 'N/A')}
- Datos actualizados al: {data_as_of}"""

                    # Add statistics by bank if available
                    if chart_stats:
                        bank_context += f"""

**Estadísticas de {metric_name}:**"""
                        for bank, stats in chart_stats.items():
                            if is_ratio:
                                # Format as percentage
                                bank_context += f"""
- **{bank}**:
  - Actual: {stats['current']:.2f}{unit_label}
  - Mín: {stats['min']:.2f}{unit_label} | Máx: {stats['max']:.2f}{unit_label}
  - Promedio: {stats['avg']:.2f}{unit_label}
  - Tendencia: {stats['trend']} ({stats['change_pct']:+.1f}%)"""
                            else:
                                # Format as MDP (thousands separator)
                                bank_context += f"""
- **{bank}**:
  - Actual: {stats['current']:,.0f} {unit_label}
  - Mín: {stats['min']:,.0f} {unit_label} | Máx: {stats['max']:,.0f} {unit_label}
  - Promedio: {stats['avg']:,.0f} {unit_label}
  - Tendencia: {stats['trend']} ({stats['change_pct']:+.1f}%)"""

                    bank_context += f"""

**IMPORTANTE**: Los datos del gráfico de {metric_name} ya están siendo enviados al usuario.
Genera una respuesta COMPLETA que incluya:
1. Confirma que se encontraron los datos solicitados sobre {metric_name}
2. Menciona el período analizado ({time_range.get('start', 'N/A')} a {time_range.get('end', 'N/A')}) y que los datos están actualizados al {data_as_of}
3. Indica que el gráfico interactivo con la evolución de la métrica ya ha sido generado y está disponible para visualización
4. **ANALIZA las estadísticas proporcionadas**: compara los valores entre bancos, menciona tendencias y cambios porcentuales"""

                    if sql_query:
                        bank_context += f"""
5. Proporciona una breve explicación de qué representa {metric_name} y por qué es importante
6. Si es posible, menciona qué se puede observar o analizar con estos datos
7. **AL FINAL del mensaje**, incluye la consulta SQL utilizada en el siguiente formato exacto:
   "La consulta SQL utilizada fue:"
   ```sql
   {sql_query}
   ```"""
                    else:
                        bank_context += f"""
5. Proporciona una breve explicación de qué representa {metric_name} y por qué es importante"""

                    bank_context += """

NO digas que no tienes información - los datos YA ESTÁN disponibles en el gráfico.
Usa las estadísticas proporcionadas para dar un análisis más profundo y contextualizado.
Escribe la respuesta de forma fluida y profesional, como un analista financiero."""

                    system_prompt += bank_context

            # Determine if bank_chart_data is a clarification or chart
            is_bank_clarification = (
                isinstance(bank_chart_data, dict) and
                bank_chart_data.get("type") == "clarification"
            ) if bank_chart_data else False

            logger.info(
                "Resolved system prompt for streaming",
                model=context.model,
                prompt_hash=model_params.get("_metadata", {}).get("system_hash"),
                has_documents=bool(document_context),
                has_bank_chart=bool(bank_chart_data) and not is_bank_clarification,
                has_bank_clarification=is_bank_clarification
            )

            # ISSUE-004: Implement backpressure with producer-consumer pattern
            # Queue with maxsize=10 provides backpressure when client is slow
            event_queue: Queue = Queue(maxsize=10)
            full_response = ""
            producer_error = None

            async def producer():
                """
                Producer task: reads chunks from Saptiva and puts them in queue.

                If queue is full (slow consumer), put() will block, providing backpressure.
                This prevents unbounded memory growth on the server.
                """
                nonlocal full_response, producer_error

                try:
                    logger.info(
                        "Starting Saptiva stream (producer)",
                        model=context.model,
                        user_id=context.user_id,
                        has_document_context=bool(document_context)
                    )

                    # Send metadata event first
                    await event_queue.put({
                        "event": "meta",
                        "data": json.dumps({
                            "chat_id": str(chat_session.id),
                            "user_message_id": str(user_message.id),
                            "model": context.model
                        })
                    })

                    # BA-P0-004 + HU3.1: Send bank_chart or bank_clarification event
                    if bank_chart_data:
                        # Serialize as dict, preserving all fields including nested xaxis
                        chart_data_dict = bank_chart_data if isinstance(bank_chart_data, dict) else bank_chart_data.model_dump(mode='json')

                        # HU3.1: Check if this is a clarification response
                        if chart_data_dict.get("type") == "clarification":
                            await event_queue.put({
                                "event": "bank_clarification",
                                "data": json.dumps(chart_data_dict)
                            })
                            logger.info(
                                "Sent bank_clarification event to stream",
                                message=chart_data_dict.get("message"),
                                options_count=len(chart_data_dict.get("options", []))
                            )
                        else:
                            await event_queue.put({
                                "event": "bank_chart",
                                "data": json.dumps(chart_data_dict)
                            })
                            logger.info(
                                "Sent bank_chart event to stream",
                                metric=chart_data_dict.get("metric_name")
                            )

                            # 🆕 Persist bank_chart artifact in background
                            try:
                                artifact_service = get_artifact_service()

                                # Extract metadata for enrichment
                                metadata = chart_data_dict.get("metadata", {})
                                sql_query = metadata.get("sql_generated")
                                metric_interpretation = metadata.get("metric_interpretation")

                                # Create artifact request
                                artifact_request = BankChartArtifactRequest(
                                    user_id=context.user_id,
                                    session_id=str(chat_session.id),
                                    chart_data=chart_data_dict,
                                    sql_query=sql_query,
                                    metric_interpretation=metric_interpretation,
                                )

                                # Persist artifact
                                artifact = await artifact_service.create_bank_chart_artifact(
                                    artifact_request
                                )

                                # Send artifact_created event to frontend
                                await event_queue.put({
                                    "event": "artifact_created",
                                    "data": json.dumps({
                                        "artifact_id": artifact.id,
                                        "type": "bank_chart",
                                        "title": artifact.title,
                                        "created_at": artifact.created_at.isoformat(),
                                    })
                                })

                                logger.info(
                                    "bank_chart_artifact_persisted",
                                    artifact_id=artifact.id,
                                    session_id=str(chat_session.id),
                                    metric=chart_data_dict.get("metric_name"),
                                )

                            except Exception as artifact_exc:
                                logger.error(
                                    "Failed to persist bank_chart artifact",
                                    error=str(artifact_exc),
                                    exc_type=type(artifact_exc).__name__,
                                    session_id=str(chat_session.id),
                                    exc_info=True
                                )
                                # Don't block stream on artifact persistence failure
                                # User will still see the chart preview in chat

                    # FIX-001: Use resolved system_prompt (not hardcoded system_message)
                    # Use model_params for temperature/max_tokens (registry overrides context)

                    # FIX-002: Build context with MEMORY system
                    # Includes: system_prompt + memory_facts + recent messages + current message
                    # Falls back to legacy 20-message context if MEMORY_ENABLED=false
                    messages_for_api = await chat_service.build_message_context_with_memory(
                        chat_session=chat_session,
                        current_message=context.message,
                        system_prompt=system_prompt,
                    )

                    # Log para debugging de memoria
                    logger.info(
                        "Chat context built with memory system",
                        total_messages=len(messages_for_api),
                        session_id=str(chat_session.id),
                        memory_enabled=getattr(chat_service.settings, 'memory_enabled', False)
                    )

                    # Calculate dynamic max_tokens based on actual prompt size
                    dynamic_max_tokens = calculate_dynamic_max_tokens(
                        messages=messages_for_api,
                        model_limit=8192,  # Saptiva Turbo limit
                        min_tokens=500,
                        max_tokens=model_params.get("max_tokens", 3000)
                    )

                    # Estimate prompt size to detect potential overflows
                    total_prompt_chars = sum(len(str(msg.get("content", ""))) for msg in messages_for_api)
                    estimated_prompt_tokens = total_prompt_chars // 4

                    logger.info(
                        "Token budget calculation | prompt_chars=%s estimated_prompt_tokens=%s dynamic_max_tokens=%s total_estimated=%s model_limit=%s will_exceed=%s",
                        total_prompt_chars,
                        estimated_prompt_tokens,
                        dynamic_max_tokens,
                        estimated_prompt_tokens + dynamic_max_tokens,
                        8192,
                        estimated_prompt_tokens + dynamic_max_tokens > 8192,
                    )

                    # FIX-002: Truncar historial si excede limite de tokens
                    # Mantener system prompt (indice 0) y mensaje actual (ultimo)
                    # Eliminar mensajes mas antiguos del medio hasta que quepa
                    messages_truncated = 0
                    while estimated_prompt_tokens > 6000 and len(messages_for_api) > 2:
                        # Eliminar el mensaje mas antiguo (indice 1, despues del system prompt)
                        removed_msg = messages_for_api.pop(1)
                        messages_truncated += 1
                        # Recalcular tokens
                        total_prompt_chars = sum(len(str(msg.get("content", ""))) for msg in messages_for_api)
                        estimated_prompt_tokens = total_prompt_chars // 4

                    if messages_truncated > 0:
                        logger.warning(
                            "Historial truncado por limite de tokens",
                            messages_removed=messages_truncated,
                            remaining_messages=len(messages_for_api),
                            estimated_tokens=estimated_prompt_tokens
                        )

                    # Si aun excede despues de truncar, log de advertencia
                    if estimated_prompt_tokens > 7500:
                        logger.error(
                            "⚠️ Prompt exceeds safe token limit - request will likely fail | estimated_prompt_tokens=%s model_limit=%s",
                            estimated_prompt_tokens,
                            8192,
                        )

                    # Use non-streaming for RAG to avoid RemoteProtocolError
                    has_rag_context = context.document_ids and len(context.document_ids) > 0

                    if has_rag_context:
                        # Non-streaming mode for RAG (more stable)
                        logger.info(
                            "Using non-streaming mode for RAG",
                            has_documents=True,
                            document_count=len(context.document_ids)
                        )

                        try:
                            response = await saptiva_client.chat_completion(
                                messages=messages_for_api,
                                model=context.model,
                                temperature=model_params.get("temperature", context.temperature),
                                max_tokens=dynamic_max_tokens
                            )
                        except Exception as e:
                            logger.error(
                                "Non-streaming API call failed",
                                error=str(e),
                                error_type=type(e).__name__
                            )
                            raise

                        # Extract full response
                        response_content = ""

                        if isinstance(response, str):
                            # Some mock/edge cases can return raw strings; treat them as full content
                            response_content = response or ""
                        elif response and response.choices and len(response.choices) > 0:
                            choice = response.choices[0]  # This is a Dict, not an object

                            # Access dict keys instead of attributes
                            if isinstance(choice, dict):
                                message = choice.get("message", {}) or {}
                                response_content = message.get("content", "") if isinstance(message, dict) else ""
                                # Saptiva Cortex sometimes sends reasoning_content only
                                reasoning_content = (
                                    message.get("reasoning_content", "") if isinstance(message, dict) else ""
                                )
                                if not response_content and reasoning_content:
                                    response_content = reasoning_content
                            else:
                                # Fallback for object-style access (shouldn't happen)
                                message = getattr(choice, "message", None)
                                response_content = getattr(message, "content", "") if message else ""
                                reasoning_content = getattr(message, "reasoning_content", "") if message else ""
                                if not response_content and reasoning_content:
                                    response_content = reasoning_content
                        else:
                            logger.warning(
                                "Non-streaming response missing choices - using fallback content"
                            )

                        # ANTI-EMPTY-RESPONSE: Use centralized handler with contextual messages
                        response_content = ensure_non_empty_content(
                            response_content,
                            scenario=EmptyResponseScenario.API_EMPTY_CONTENT,
                            model=context.model,
                            has_documents=bool(context.document_ids),
                            document_count=len(context.document_ids) if context.document_ids else 0,
                            user_id=context.user_id
                        )

                        # Update the nonlocal full_response variable
                        full_response = response_content

                        logger.info(
                            "Non-streaming response extracted",
                            response_length=len(full_response),
                            response_preview=full_response[:100] if full_response else "(empty)",
                            has_reasoning="reasoning_content" in (locals().get("message") or {}),
                            choice_keys=list(choice.keys()) if "choice" in locals() and isinstance(choice, dict) else "n/a"
                        )

                        # Simulate streaming by sending in chunks
                        chunk_size = 50  # Characters per chunk
                        total_chunks = (len(full_response) + chunk_size - 1) // chunk_size
                        logger.info(
                            "📤 [DEBUG] Starting to send chunks",
                            total_response_length=len(full_response),
                            chunk_size=chunk_size,
                            total_chunks=total_chunks
                        )
                        for i in range(0, len(full_response), chunk_size):
                            chunk_text = full_response[i:i + chunk_size]
                            chunk_event = {
                                "event": "chunk",
                                "data": json.dumps({"content": chunk_text})
                            }
                            await event_queue.put(chunk_event)
                            logger.debug(
                                "📤 [DEBUG] Chunk queued",
                                chunk_index=i // chunk_size,
                                chunk_length=len(chunk_text),
                                chunk_preview=chunk_text[:20]
                            )

                    else:
                        # Streaming mode for normal chat (without RAG)
                        async for chunk in saptiva_client.chat_completion_stream(
                            messages=messages_for_api,
                            model=context.model,
                            temperature=model_params.get("temperature", context.temperature),
                            max_tokens=dynamic_max_tokens
                        ):
                            # Extract content from chunk
                            # choices is a List[Dict] according to SaptivaStreamChunk model
                            content = ""
                            if hasattr(chunk, 'choices') and chunk.choices:
                                choice = chunk.choices[0]  # This is a dict
                                if isinstance(choice, dict):
                                    delta = choice.get('delta', {})
                                    if isinstance(delta, dict):
                                        content = delta.get('content', '')
                                # Fallback for object-style access (shouldn't happen)
                                elif hasattr(choice, 'delta'):
                                    delta = choice.delta
                                    if hasattr(delta, 'content'):
                                        content = delta.content or ''

                            if content:
                                # Backpressure: this blocks if queue is full (maxsize=10)
                                await event_queue.put({
                                    "event": "chunk",
                                    "data": json.dumps({"content": content})
                                })
                                full_response += content

                    # Signal end of stream
                    await event_queue.put(None)

                    logger.info(
                        "Producer completed successfully",
                        response_length=len(full_response)
                    )

                except CancelledError:
                    logger.info("Producer cancelled by consumer")
                    raise
                except Exception as e:
                    logger.error(
                        "Producer error",
                        error=str(e),
                        exc_type=type(e).__name__
                    )
                    producer_error = e
                    # Signal error to consumer
                    await event_queue.put(None)

            # Start producer task
            producer_task = create_task(producer())

            try:
                # Consumer loop: yield events from queue
                event_count = 0
                while True:
                    event = await event_queue.get()

                    if event is None:  # End signal
                        logger.info("🏁 [DEBUG] Consumer received end signal (None)")
                        break

                    event_count += 1
                    logger.debug(
                        "📥 [DEBUG] Consumer yielding event",
                        event_number=event_count,
                        event_type=event.get("event"),
                        data_preview=str(event.get("data", ""))[:50]
                    )
                    yield event

            finally:
                # Cleanup: cancel producer if consumer exits early
                if not producer_task.done():
                    producer_task.cancel()
                    try:
                        await producer_task
                    except CancelledError:
                        logger.info("Producer task cancelled in cleanup")

                # Check if producer had an error
                if producer_error:
                    logger.error(
                        "Producer error detected in cleanup",
                        error=str(producer_error)
                    )
                    raise producer_error

                # ANTI-EMPTY-RESPONSE: Ensure we never persist or emit an empty response
                if not full_response:
                    has_documents = bool(context.document_ids)

                    # Determine the most likely scenario using the in-memory document list on context
                    if doc_warnings:
                        scenario = EmptyResponseScenario.DOCS_PROCESSING
                    elif has_documents:
                        scenario = EmptyResponseScenario.DOCS_NOT_FOUND
                    else:
                        scenario = EmptyResponseScenario.STREAM_NO_CHUNKS

                    full_response = EmptyResponseHandler.get_fallback_message(
                        scenario=scenario,
                        context={
                            "user_id": context.user_id,
                            "chat_id": str(chat_session.id),
                            "session_id": context.session_id,
                            "model": context.model,
                            "has_documents": bool(context.document_ids),
                            "document_count": len(context.document_ids) if context.document_ids else 0,
                            "stream_mode": True
                        }
                    )

                    # Log the incident for monitoring
                    EmptyResponseHandler.log_empty_response_incident(
                        scenario=scenario,
                        context={
                            "user_id": context.user_id,
                            "chat_id": str(chat_session.id),
                            "session_id": context.session_id,
                            "model": context.model,
                            "has_documents": bool(context.document_ids),
                            "document_count": len(context.document_ids) if context.document_ids else 0,
                            "stream_mode": True,
                            "doc_warnings": doc_warnings if doc_warnings else None
                        }
                    )

                    # Emit a last-minute chunk so the UI has something to render
                    yield {
                        "event": "chunk",
                        "data": json.dumps({"content": full_response})
                    }

                # Prepare metadata for assistant message
                assistant_metadata = {
                    "streaming": True,
                    "has_documents": bool(context.document_ids),
                    "document_warnings": doc_warnings if doc_warnings else None
                }

                # BA-P0-004: Include bank_chart_data in metadata for persistence
                if bank_chart_data:
                    chart_data_dict = bank_chart_data if isinstance(bank_chart_data, dict) else bank_chart_data.model_dump(mode='json')

                    # HU3.1: Check if this is a clarification response
                    if chart_data_dict.get("type") == "clarification":
                        assistant_metadata["bank_clarification_data"] = chart_data_dict
                        logger.info(
                            "💾 Saving bank_clarification_data in message metadata",
                            original_query=chart_data_dict.get("context", {}).get("original_query"),
                            options_count=len(chart_data_dict.get("options", []))
                        )
                    else:
                        assistant_metadata["bank_chart_data"] = chart_data_dict
                        logger.info(
                            "💾 Saving bank_chart_data in message metadata",
                            metric=chart_data_dict.get("metric_name"),
                            has_sql=bool(chart_data_dict.get("metadata", {}).get("sql_generated"))
                        )

                # Save assistant message
                assistant_message = await chat_service.add_assistant_message(
                    chat_session=chat_session,
                    content=full_response,
                    model=context.model,
                    metadata=assistant_metadata
                )

                # Yield completion event
                done_event = {
                    "event": "done",
                    "data": json.dumps({
                        "message_id": str(assistant_message.id),
                        "chat_id": str(chat_session.id),
                        # Include final content as a safety net for UIs that rely on the done payload
                        "content": full_response
                    })
                }
                logger.info(
                    "✅ [DEBUG] Yielding done event",
                    message_id=str(assistant_message.id),
                    chat_id=str(chat_session.id),
                    content_length=len(full_response),
                    content_preview=full_response[:100] if full_response else "(empty)"
                )
                yield done_event

                # Invalidate cache
                await cache.invalidate_chat_history(chat_session.id)

        # FIX-001: Catch all streaming errors and propagate to frontend
        except Exception as stream_exc:
            logger.error(
                "CRITICAL: Streaming chat failed",
                error=str(stream_exc),
                exc_type=type(stream_exc).__name__,
                model=context.model,
                user_id=context.user_id,
                has_documents=bool(context.document_ids),
                exc_info=True
            )

            # Save error message to database for visibility
            error_content = (
                f"❌ Error al procesar la solicitud: {str(stream_exc)[:200]}\n\n"
                f"Por favor, intenta nuevamente o contacta al equipo de soporte si el error persiste."
            )
            try:
                await chat_service.add_assistant_message(
                    chat_session=chat_session,
                    content=error_content,
                    model=context.model,
                    metadata={
                        "error": True,
                        "error_type": type(stream_exc).__name__,
                        "error_message": str(stream_exc)[:500]
                    }
                )
            except Exception as save_exc:
                logger.error(
                    "Failed to save error message to database",
                    error=str(save_exc),
                    exc_info=True
                )

            # Yield error event to frontend
            yield {
                "event": "error",
                "data": json.dumps({
                    "error": type(stream_exc).__name__,
                    "message": str(stream_exc),
                    "details": "Ocurrió un error al procesar tu solicitud. Por favor, intenta nuevamente."
                })
            }
