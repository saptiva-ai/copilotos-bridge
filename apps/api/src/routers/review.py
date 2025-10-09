"""
Document review router - handles review workflow and SSE events.
"""

import asyncio
import json
from datetime import datetime
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
import structlog

from ..core.auth import get_current_user
from ..models.user import User
from ..models.document import Document, DocumentStatus
from ..models.review_job import ReviewJob, ReviewStatus
from ..schemas.review import (
    ReviewStartRequest,
    ReviewStartResponse,
    ReviewStatusResponse,
    ReviewReportResponse,
    ReviewEventData,
    ReviewWarningResponse,
    SpellingFindingResponse,
    GrammarFindingResponse,
    StyleNoteResponse,
    SuggestedRewriteResponse,
    SummaryBulletResponse,
    ColorAuditResponse,
    ColorPairResponse,
)
from ..services.review_service import review_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/review", tags=["review"])


@router.post("/start", response_model=ReviewStartResponse, status_code=status.HTTP_201_CREATED)
async def start_review(
    request: ReviewStartRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Start document review.

    Creates a review job and begins processing:
    1. LanguageTool grammar/spelling check
    2. Saptiva LLM suggestions
    3. Summary generation (if requested)
    4. Color accessibility audit (if requested)

    Args:
        request: Review configuration
        current_user: Authenticated user

    Returns:
        ReviewStartResponse with job_id
    """
    logger.info(
        "Review start requested",
        doc_id=request.doc_id,
        model=request.model,
        user_id=str(current_user.id),
    )

    # Get document
    doc = await Document.get(request.doc_id)

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Check ownership
    if doc.user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to review this document",
        )

    # Check document status
    if doc.status != DocumentStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document not ready for review. Status: {doc.status}",
        )

    # Create review job
    job = await review_service.create_review_job(
        doc=doc,
        user_id=str(current_user.id),
        request=request,
    )

    # Start processing in background
    asyncio.create_task(_process_review_job(job.job_id, str(doc.id)))

    logger.info(
        "Review job created",
        job_id=job.job_id,
        doc_id=request.doc_id,
    )

    return ReviewStartResponse(
        job_id=job.job_id,
        status=job.status.value,
    )


@router.get("/events/{job_id}")
async def review_events(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Server-Sent Events (SSE) for review progress.

    Streams real-time updates as review progresses through stages:
    RECEIVED → EXTRACT → LT_GRAMMAR → LLM_SUGGEST → SUMMARY → COLOR_AUDIT → READY

    Args:
        job_id: Review job ID
        current_user: Authenticated user

    Returns:
        SSE stream
    """
    logger.info("SSE connection requested", job_id=job_id, user_id=str(current_user.id))

    # Verify job exists and user owns it
    job = await ReviewJob.find_one(ReviewJob.job_id == job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review job not found",
        )

    if job.user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this job",
        )

    async def event_generator() -> AsyncGenerator[dict, None]:
        """Generate SSE events"""
        try:
            last_status = None

            # Poll for updates
            while True:
                # Refresh job
                job = await ReviewJob.find_one(ReviewJob.job_id == job_id)

                if not job:
                    break

                # Send update if status changed
                if job.status != last_status:
                    event_data = ReviewEventData(
                        job_id=job.job_id,
                        status=job.status.value,
                        progress=job.progress,
                        current_stage=job.current_stage,
                        message=job.error_message if job.status == ReviewStatus.FAILED else None,
                        timestamp=datetime.utcnow().isoformat(),
                    )

                    yield {
                        "event": "status",
                        "data": event_data.model_dump_json(),
                    }

                    last_status = job.status

                    logger.info(
                        "SSE event sent",
                        job_id=job_id,
                        status=job.status.value,
                        progress=job.progress,
                    )

                # Check if job is complete
                if job.status in [ReviewStatus.READY, ReviewStatus.FAILED, ReviewStatus.CANCELLED]:
                    break

                # Wait before next poll
                await asyncio.sleep(1.0)

        except asyncio.CancelledError:
            logger.info("SSE connection closed by client", job_id=job_id)
        except Exception as e:
            logger.error("SSE stream error", job_id=job_id, error=str(e))

    return EventSourceResponse(event_generator())


@router.get("/status/{job_id}", response_model=ReviewStatusResponse)
async def get_review_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get review job status"""
    job = await ReviewJob.find_one(ReviewJob.job_id == job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review job not found",
        )

    if job.user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this job",
        )

    return ReviewStatusResponse(
        job_id=job.job_id,
        status=job.status.value,
        progress=job.progress,
        current_stage=job.current_stage,
        error_message=job.error_message,
    )


@router.get("/report/{doc_id}", response_model=ReviewReportResponse)
async def get_review_report(
    doc_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get completed review report.

    Returns comprehensive findings including:
    - Summary (if generated)
    - Spelling errors
    - Grammar issues
    - Style notes
    - Suggested rewrites
    - Color accessibility audit

    Args:
        doc_id: Document ID
        current_user: Authenticated user

    Returns:
        ReviewReportResponse
    """
    # Get document
    doc = await Document.get(doc_id)

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    if doc.user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this document",
        )

    # Get most recent completed job for this document
    job = await ReviewJob.find_one(
        ReviewJob.doc_id == doc_id,
        ReviewJob.status == ReviewStatus.READY,
    ).sort(-ReviewJob.created_at)

    if not job or not job.report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completed review found for this document",
        )

    # Build response
    report = job.report

    # Convert color audit
    color_audit_data = report.color_audit or {}
    color_audit = ColorAuditResponse(
        pairs=[
            ColorPairResponse(
                fg=pair.get("fg", "#000000"),
                bg=pair.get("bg", "#FFFFFF"),
                ratio=pair.get("ratio", 0.0),
                wcag=pair.get("wcag", "fail"),
                location=pair.get("location"),
            )
            for pair in color_audit_data.get("pairs", [])
        ],
        pass_count=color_audit_data.get("pass_count", 0),
        fail_count=color_audit_data.get("fail_count", 0),
    )

    # Build response
    response = ReviewReportResponse(
        doc_id=doc_id,
        job_id=job.job_id,
        summary=[
            SummaryBulletResponse(page=s.page, bullets=s.bullets)
            for s in report.summary
        ],
        spelling=[
            SpellingFindingResponse(
                page=s.page,
                span=s.span,
                suggestions=s.suggestions,
            )
            for s in report.spelling
        ],
        grammar=[
            GrammarFindingResponse(
                page=g.page,
                span=g.span,
                rule=g.rule,
                explain=g.explain,
                suggestions=g.suggestions,
            )
            for g in report.grammar
        ],
        style_notes=[
            StyleNoteResponse(
                page=s.page,
                issue=s.issue,
                advice=s.advice,
                span=s.span,
            )
            for s in report.style_notes
        ],
        suggested_rewrites=[
            SuggestedRewriteResponse(
                page=r.page,
                block_id=r.block_id,
                original=r.original,
                proposal=r.proposal,
                rationale=r.rationale,
            )
            for r in report.suggested_rewrites
        ],
        color_audit=color_audit,
        artifacts=report.artifacts,
        metrics={
            "lt_findings_count": job.lt_findings_count,
            "llm_calls_count": job.llm_calls_count,
            "tokens_in": job.tokens_in,
            "tokens_out": job.tokens_out,
            "processing_time_ms": job.processing_time_ms,
        },
        created_at=job.created_at.isoformat(),
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        warnings=[
            ReviewWarningResponse(
                stage=w.stage,
                code=w.code,
                message=w.message,
            )
            for w in report.warnings
        ],
        llm_status=report.llm_status,
    )

    logger.info(
        "Review report retrieved",
        doc_id=doc_id,
        job_id=job.job_id,
        findings_count=len(report.spelling) + len(report.grammar),
    )

    return response


async def _process_review_job(job_id: str, doc_id: str):
    """Background task to process review job"""
    try:
        # Get job and document
        job = await ReviewJob.find_one(ReviewJob.job_id == job_id)
        doc = await Document.get(doc_id)

        if not job or not doc:
            logger.error("Job or document not found", job_id=job_id, doc_id=doc_id)
            return

        # Start processing
        job.started_at = datetime.utcnow()
        await job.save()

        # Run review pipeline
        await review_service.process_review(job, doc)

        logger.info("Review job completed", job_id=job_id)

    except Exception as e:
        logger.error("Review job failed", job_id=job_id, error=str(e))
        # Update job status
        job = await ReviewJob.find_one(ReviewJob.job_id == job_id)
        if job:
            await review_service.update_job_status(
                job,
                ReviewStatus.FAILED,
                error=str(e),
            )
