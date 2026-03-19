"""
MCP Client for Capital 414 Auditor Plugin.

This module provides a client wrapper to invoke the COPILOTO_414
audit system via MCP protocol to the capital414-auditor microservice.

The audit logic has been extracted to plugins/capital414-private.
This client is the ONLY way to invoke document audits from the Core API.

Usage:
    from services.audit_mcp_client import audit_document_via_mcp

    result = await audit_document_via_mcp(
        file_path="/tmp/document.pdf",
        policy_id="414-std",
        client_name="Banamex",
    )
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx
import structlog

logger = structlog.get_logger(__name__)

# Configuration
MCP_AUDITOR_URL = os.getenv("CAPITAL414_AUDITOR_URL", "http://file-auditor:8002")
MCP_TIMEOUT = int(os.getenv("CAPITAL414_AUDITOR_TIMEOUT", "120"))  # 2 minutes
USE_MCP_AUDITOR = os.getenv("USE_MCP_AUDITOR", "true").lower() == "true"


class MCPAuditorUnavailableError(Exception):
    """Raised when the MCP auditor service is unavailable."""

    pass


async def audit_document_via_mcp(
    file_path: str,
    policy_id: str = "auto",
    client_name: Optional[str] = None,
    enable_disclaimer: bool = True,
    enable_format: bool = True,
    enable_typography: bool = True,
    enable_grammar: bool = True,
    enable_logo: bool = True,
    enable_color_palette: bool = True,
    enable_entity_consistency: bool = True,
    enable_semantic_consistency: bool = True,
) -> Dict[str, Any]:
    """
    Audit a document via MCP protocol to capital414-auditor service.

    Args:
        file_path: Path to the PDF file
        policy_id: Policy ID (default: "auto")
        client_name: Client name for disclaimer validation
        enable_*: Toggle individual auditors

    Returns:
        Audit result dict with findings, summary, and report paths

    Raises:
        MCPAuditorUnavailableError: If MCP auditor is disabled or unavailable
        httpx.HTTPStatusError: If MCP call returns an error status
    """
    if not USE_MCP_AUDITOR:
        raise MCPAuditorUnavailableError(
            "MCP auditor is disabled. Set USE_MCP_AUDITOR=true in environment."
        )

    logger.info(
        "Invoking MCP auditor",
        url=MCP_AUDITOR_URL,
        file_path=file_path,
        policy_id=policy_id,
    )

    try:
        async with httpx.AsyncClient(timeout=MCP_TIMEOUT) as client:
            # JSON-RPC 2.0 call to MCP endpoint
            response = await client.post(
                f"{MCP_AUDITOR_URL}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "audit-call",
                    "method": "tools/call",
                    "params": {
                        "name": "audit_document_full",
                        "arguments": {
                            "file_path": file_path,
                            "policy_id": policy_id,
                            "client_name": client_name,
                            "enable_disclaimer": enable_disclaimer,
                            "enable_format": enable_format,
                            "enable_typography": enable_typography,
                            "enable_grammar": enable_grammar,
                            "enable_logo": enable_logo,
                            "enable_color_palette": enable_color_palette,
                            "enable_entity_consistency": enable_entity_consistency,
                            "enable_semantic_consistency": enable_semantic_consistency,
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
                raise MCPAuditorUnavailableError(
                    f"MCP auditor error: {error.get('message', str(error))}"
                )

            # Extract result from JSON-RPC response
            result = rpc_response.get("result", {})

            # Handle nested content structure from FastMCP
            if isinstance(result, dict) and "content" in result:
                content = result["content"]
                if isinstance(content, list) and len(content) > 0:
                    first_content = content[0]
                    if isinstance(first_content, dict) and "text" in first_content:
                        import json

                        result = json.loads(first_content["text"])

            logger.info(
                "MCP audit completed",
                job_id=result.get("job_id"),
                total_findings=result.get("total_findings"),
            )

            return result

    except httpx.HTTPStatusError as e:
        logger.error(
            "MCP auditor HTTP error",
            status_code=e.response.status_code,
            detail=e.response.text,
        )
        raise MCPAuditorUnavailableError(
            f"MCP auditor returned HTTP {e.response.status_code}: {e.response.text}"
        )

    except httpx.RequestError as e:
        logger.error("MCP auditor connection error", error=str(e))
        raise MCPAuditorUnavailableError(
            f"Failed to connect to MCP auditor at {MCP_AUDITOR_URL}: {str(e)}"
        )


async def check_mcp_auditor_health() -> bool:
    """
    Check if the MCP auditor service is healthy.

    Returns:
        True if service is available, False otherwise
    """
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{MCP_AUDITOR_URL}/health")
            return response.status_code == 200
    except Exception:
        return False


async def list_policies_via_mcp() -> List[Dict[str, Any]]:
    """
    List available policies from MCP auditor.

    Returns:
        List of policy configurations

    Raises:
        MCPAuditorUnavailableError: If MCP auditor is unavailable
    """
    if not USE_MCP_AUDITOR:
        raise MCPAuditorUnavailableError(
            "MCP auditor is disabled. Set USE_MCP_AUDITOR=true in environment."
        )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{MCP_AUDITOR_URL}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "list-policies",
                    "method": "tools/call",
                    "params": {
                        "name": "list_policies",
                        "arguments": {},
                    },
                },
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            rpc_response = response.json()

            if "error" in rpc_response:
                error = rpc_response["error"]
                raise MCPAuditorUnavailableError(
                    f"MCP auditor error: {error.get('message', str(error))}"
                )

            result = rpc_response.get("result", {})

            # Handle nested content structure from FastMCP
            if isinstance(result, dict) and "content" in result:
                content = result["content"]
                if isinstance(content, list) and len(content) > 0:
                    first_content = content[0]
                    if isinstance(first_content, dict) and "text" in first_content:
                        import json

                        return json.loads(first_content["text"])

            return result if isinstance(result, list) else []

    except httpx.RequestError as e:
        logger.warning("Failed to list policies via MCP", error=str(e))
        raise MCPAuditorUnavailableError(f"Failed to connect to MCP auditor: {str(e)}")


async def get_policy_details_via_mcp(policy_id: str) -> Dict[str, Any]:
    """
    Get detailed configuration for a specific policy.

    Args:
        policy_id: The policy ID to retrieve

    Returns:
        Full policy configuration including auditor settings

    Raises:
        MCPAuditorUnavailableError: If MCP auditor is unavailable
    """
    if not USE_MCP_AUDITOR:
        raise MCPAuditorUnavailableError(
            "MCP auditor is disabled. Set USE_MCP_AUDITOR=true in environment."
        )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{MCP_AUDITOR_URL}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "get-policy",
                    "method": "tools/call",
                    "params": {
                        "name": "get_policy_details",
                        "arguments": {"policy_id": policy_id},
                    },
                },
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            rpc_response = response.json()

            if "error" in rpc_response:
                error = rpc_response["error"]
                raise MCPAuditorUnavailableError(
                    f"MCP auditor error: {error.get('message', str(error))}"
                )

            result = rpc_response.get("result", {})

            # Handle nested content structure from FastMCP
            if isinstance(result, dict) and "content" in result:
                content = result["content"]
                if isinstance(content, list) and len(content) > 0:
                    first_content = content[0]
                    if isinstance(first_content, dict) and "text" in first_content:
                        import json

                        return json.loads(first_content["text"])

            return result

    except httpx.RequestError as e:
        logger.warning("Failed to get policy details via MCP", error=str(e))
        raise MCPAuditorUnavailableError(f"Failed to connect to MCP auditor: {str(e)}")
