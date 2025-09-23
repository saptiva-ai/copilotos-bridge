"""
Research reports API endpoints.
"""

import os
import tempfile
from datetime import datetime
from typing import Optional, BinaryIO
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import FileResponse, StreamingResponse

from ..core.config import get_settings, Settings
from ..models.task import Task as TaskModel, TaskStatus
from ..schemas.common import ApiResponse

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/report/{task_id}", tags=["reports"])
async def download_research_report(
    task_id: str,
    format: str = Query(default="md", pattern="^(md|html|pdf)$", description="Report format"),
    include_sources: bool = Query(default=True, description="Include source references"),
    http_request: Request = None,
    settings: Settings = Depends(get_settings)
):
    """
    Download research report in specified format.
    
    Retrieves the final report from Aletheia artifacts and serves it to the user.
    """
    
    user_id = getattr(http_request.state, 'user_id', 'anonymous')
    
    try:
        # Verify task exists and user has access
        task = await TaskModel.get(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        if task.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to task"
            )
        
        # Check if task is completed
        if task.status != TaskStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Report not available. Task status: {task.status.value}"
            )
        
        # TODO: Fetch actual report from Aletheia artifacts
        # For now, generate a mock report
        report_content = _generate_mock_report(task, format, include_sources)
        
        # Determine content type and filename
        content_type_map = {
            "md": "text/markdown",
            "html": "text/html",
            "pdf": "application/pdf"
        }
        
        filename = f"research_report_{task_id}.{format}"
        content_type = content_type_map[format]
        
        logger.info(
            "Serving research report",
            task_id=task_id,
            format=format,
            user_id=user_id,
            include_sources=include_sources
        )
        
        # Create temporary file for the report
        with tempfile.NamedTemporaryFile(mode='w+b', suffix=f'.{format}', delete=False) as tmp_file:
            if format == "pdf":
                # For PDF, we'd need to convert content to bytes
                tmp_file.write(report_content.encode('utf-8'))
            else:
                tmp_file.write(report_content.encode('utf-8'))
            tmp_file_path = tmp_file.name
        
        # Return file response
        return FileResponse(
            path=tmp_file_path,
            filename=filename,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "X-Task-ID": task_id,
                "X-Generated-At": datetime.utcnow().isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error serving research report", error=str(e), task_id=task_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report"
        )


@router.get("/report/{task_id}/preview", tags=["reports"])
async def preview_research_report(
    task_id: str,
    format: str = Query(default="html", pattern="^(html|md)$", description="Preview format"),
    http_request: Request = None
):
    """
    Preview research report in browser without downloading.
    """
    
    user_id = getattr(http_request.state, 'user_id', 'anonymous')
    
    try:
        # Verify task and access (same as download)
        task = await TaskModel.get(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        if task.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to task"
            )
        
        if task.status != TaskStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Report not available. Task status: {task.status.value}"
            )
        
        # Generate preview content
        content = _generate_mock_report(task, format, include_sources=True)
        
        content_type = "text/html" if format == "html" else "text/plain"
        
        logger.info("Serving report preview", task_id=task_id, format=format, user_id=user_id)
        
        return StreamingResponse(
            iter([content.encode('utf-8')]),
            media_type=content_type,
            headers={
                "X-Task-ID": task_id,
                "X-Preview-Mode": "true"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error serving report preview", error=str(e), task_id=task_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate preview"
        )


@router.get("/report/{task_id}/metadata", tags=["reports"])
async def get_report_metadata(
    task_id: str,
    http_request: Request = None
):
    """
    Get metadata about the research report.
    """
    
    user_id = getattr(http_request.state, 'user_id', 'anonymous')
    
    try:
        # Verify task and access
        task = await TaskModel.get(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        if task.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to task"
            )
        
        # Generate metadata
        metadata = {
            "task_id": task_id,
            "status": task.status.value,
            "query": task.input_data.get("query", ""),
            "created_at": task.created_at.isoformat(),
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "available_formats": ["md", "html", "pdf"],
            "estimated_size_mb": 0.5,  # Mock size
            "source_count": 15,  # Mock count
            "evidence_count": 8,  # Mock count
            "processing_time_seconds": 120.0,  # Mock time
            "can_download": task.status == TaskStatus.COMPLETED,
            "artifacts": {
                "report": True,
                "sources": True,
                "citations": True,
                "metadata": True
            }
        }
        
        logger.info("Retrieved report metadata", task_id=task_id, user_id=user_id)
        
        return metadata
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving report metadata", error=str(e), task_id=task_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metadata"
        )


@router.post("/report/{task_id}/share", tags=["reports"])
async def create_shareable_link(
    task_id: str,
    http_request: Request,
    format: str = "html",
    expires_in_hours: int = 24,
    settings: Settings = Depends(get_settings)
):
    """
    Create a shareable link for a research report.
    """

    user_id = getattr(http_request.state, 'user_id', 'anonymous')

    try:
        # Verify task exists and user has access
        task = await TaskModel.get(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        if task.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to task"
            )

        if task.status != TaskStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Report not available. Task status: {task.status.value}"
            )

        # Generate shareable token
        import secrets
        import base64
        import json

        share_data = {
            "task_id": task_id,
            "user_id": user_id,
            "format": format,
            "expires_at": (datetime.utcnow().timestamp() + (expires_in_hours * 3600))
        }

        encoded_data = base64.urlsafe_b64encode(
            json.dumps(share_data).encode()
        ).decode()

        # Create shareable URL
        base_url = str(http_request.base_url).rstrip('/')
        shareable_url = f"{base_url}/api/report/shared/{encoded_data}"

        logger.info(
            "Created shareable link",
            task_id=task_id,
            user_id=user_id,
            expires_in_hours=expires_in_hours
        )

        return {
            "success": True,
            "shareable_url": shareable_url,
            "expires_in_hours": expires_in_hours,
            "expires_at": datetime.fromtimestamp(share_data["expires_at"]).isoformat(),
            "format": format
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating shareable link", error=str(e), task_id=task_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create shareable link"
        )


@router.get("/report/shared/{share_token}", tags=["reports"])
async def get_shared_report(
    share_token: str,
    settings: Settings = Depends(get_settings)
):
    """
    Access a shared research report via shareable link.
    """

    try:
        import base64
        import json

        # Decode share token
        try:
            decoded_data = base64.urlsafe_b64decode(share_token.encode()).decode()
            share_data = json.loads(decoded_data)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid share token"
            )

        # Check expiry
        if datetime.utcnow().timestamp() > share_data["expires_at"]:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Shared link has expired"
            )

        task_id = share_data["task_id"]
        format = share_data.get("format", "html")

        # Verify task still exists
        task = await TaskModel.get(task_id)
        if not task or task.status != TaskStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report no longer available"
            )

        # Generate and serve the report
        content = _generate_mock_report(task, format, include_sources=True)

        content_type = "text/html" if format == "html" else "text/plain"

        logger.info("Served shared report", task_id=task_id, format=format)

        return StreamingResponse(
            iter([content.encode('utf-8')]),
            media_type=content_type,
            headers={
                "X-Task-ID": task_id,
                "X-Shared-Report": "true"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error serving shared report", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load shared report"
        )


@router.delete("/report/{task_id}", response_model=ApiResponse, tags=["reports"])
async def delete_research_report(
    task_id: str,
    http_request: Request = None
):
    """
    Delete research report and associated artifacts.
    """
    
    user_id = getattr(http_request.state, 'user_id', 'anonymous')
    
    try:
        # Verify task and access
        task = await TaskModel.get(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        if task.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to task"
            )
        
        # TODO: Delete artifacts from Aletheia/MinIO storage
        # For now, just mark task as deleted or remove from database
        
        await task.delete()
        
        logger.info("Deleted research report", task_id=task_id, user_id=user_id)
        
        return ApiResponse(
            success=True,
            message="Research report deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting research report", error=str(e), task_id=task_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete report"
        )


def _generate_mock_report(task: TaskModel, format: str, include_sources: bool) -> str:
    """
    Generate a mock research report for testing.
    
    In production, this would fetch the actual report from Aletheia artifacts.
    """
    
    query = task.input_data.get("query", "Unknown query")
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    if format == "md":
        content = f"""# Research Report: {query}

**Generated:** {timestamp}  
**Task ID:** {task.id}  
**Status:** {task.status.value}

## Executive Summary

This is a mock research report generated for testing purposes. In a real implementation, this would contain the actual research findings from the Aletheia orchestrator.

## Key Findings

1. **Finding 1:** This is a placeholder finding that demonstrates the report structure.
2. **Finding 2:** Another important discovery from the research process.
3. **Finding 3:** Additional insights gathered during the investigation.

## Detailed Analysis

### Section 1: Background
The research query "{query}" was processed using advanced AI agents and web search capabilities.

### Section 2: Methodology
- Web search and source collection
- Evidence extraction and analysis
- Synthesis and fact-checking
- Quality assessment and validation

### Section 3: Results
The analysis revealed several important patterns and insights relevant to the original query.

## Conclusions

Based on the comprehensive analysis, we can conclude that the research objectives have been met successfully.
"""
        
        if include_sources:
            content += """
## Sources

1. [Example Source 1](https://example1.com) - Primary research article
2. [Example Source 2](https://example2.com) - Supporting documentation
3. [Example Source 3](https://example3.com) - Expert analysis

## Citations

- Source 1: Cited in findings 1 and 2
- Source 2: Referenced in methodology section
- Source 3: Used for validation and fact-checking
"""
    
    elif format == "html":
        content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Research Report: {query}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
        h1 {{ color: #333; border-bottom: 2px solid #eee; }}
        h2 {{ color: #666; }}
        .metadata {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
        .finding {{ margin: 10px 0; padding: 10px; background: #f9f9f9; border-left: 4px solid #007cba; }}
    </style>
</head>
<body>
    <h1>Research Report: {query}</h1>
    
    <div class="metadata">
        <strong>Generated:</strong> {timestamp}<br>
        <strong>Task ID:</strong> {task.id}<br>
        <strong>Status:</strong> {task.status.value}
    </div>

    <h2>Executive Summary</h2>
    <p>This is a mock research report generated for testing purposes. In a real implementation, this would contain the actual research findings from the Aletheia orchestrator.</p>

    <h2>Key Findings</h2>
    <div class="finding"><strong>Finding 1:</strong> This is a placeholder finding that demonstrates the report structure.</div>
    <div class="finding"><strong>Finding 2:</strong> Another important discovery from the research process.</div>
    <div class="finding"><strong>Finding 3:</strong> Additional insights gathered during the investigation.</div>

    <h2>Detailed Analysis</h2>
    <h3>Background</h3>
    <p>The research query "{query}" was processed using advanced AI agents and web search capabilities.</p>
    
    <h3>Results</h3>
    <p>The analysis revealed several important patterns and insights relevant to the original query.</p>

    <h2>Conclusions</h2>
    <p>Based on the comprehensive analysis, we can conclude that the research objectives have been met successfully.</p>
</body>
</html>"""
    
    else:  # PDF format - return markdown that could be converted to PDF
        content = _generate_mock_report(task, "md", include_sources)
    
    return content