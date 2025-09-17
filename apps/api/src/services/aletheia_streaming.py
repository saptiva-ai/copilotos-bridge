"""
Aletheia event streaming service for real-time research updates.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import AsyncGenerator, Dict, Any, Optional

import aiohttp
import structlog
from pydantic import BaseModel

from ..core.config import get_settings
from ..services.aletheia_client import get_aletheia_client

logger = structlog.get_logger(__name__)


class StreamEvent(BaseModel):
    """Real-time stream event from Aletheia."""
    event_type: str
    task_id: str
    timestamp: datetime
    data: Dict[str, Any]
    sequence: Optional[int] = None


class AletheiaEventStreamer:
    """Service for streaming events from Aletheia's NDJSON endpoint."""

    def __init__(self):
        self.settings = get_settings()
        self._active_streams: Dict[str, bool] = {}

    async def stream_task_events(
        self,
        task_id: str,
        max_duration: int = 3600  # 1 hour max
    ) -> AsyncGenerator[str, None]:
        """
        Stream events from Aletheia's events.ndjson endpoint as SSE.

        Args:
            task_id: The research task ID
            max_duration: Maximum stream duration in seconds

        Yields:
            SSE-formatted event strings
        """
        self._active_streams[task_id] = True
        start_time = time.time()

        try:
            logger.info("Starting Aletheia event stream", task_id=task_id)

            # Get Aletheia client
            aletheia_client = await get_aletheia_client()

            # Get the events stream URL from Aletheia
            events_url = await aletheia_client.get_events_stream_url(task_id)

            # Create HTTP session for streaming
            timeout = aiohttp.ClientTimeout(total=None, sock_read=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:

                # Stream events from Aletheia
                async for event in self._stream_from_aletheia(session, events_url, task_id):
                    # Check if stream should stop
                    if not self._active_streams.get(task_id, False):
                        logger.info("Stream stopped by request", task_id=task_id)
                        break

                    # Check max duration
                    if time.time() - start_time > max_duration:
                        logger.info("Stream reached max duration", task_id=task_id)
                        break

                    yield event

        except Exception as e:
            logger.error("Error in Aletheia event stream", task_id=task_id, error=str(e))
            # Send error event
            error_event = StreamEvent(
                event_type="stream_error",
                task_id=task_id,
                timestamp=datetime.utcnow(),
                data={"error": str(e), "error_type": "stream_error"}
            )
            yield self._format_sse_event(error_event)

        finally:
            self._active_streams.pop(task_id, None)
            logger.info("Aletheia event stream closed", task_id=task_id)

    async def _stream_from_aletheia(
        self,
        session: aiohttp.ClientSession,
        events_url: str,
        task_id: str
    ) -> AsyncGenerator[str, None]:
        """
        Stream NDJSON events from Aletheia and convert to SSE format.
        """
        last_heartbeat = time.time()
        sequence = 0

        try:
            async with session.get(events_url) as response:
                if response.status != 200:
                    raise Exception(f"Failed to connect to Aletheia stream: {response.status}")

                logger.info("Connected to Aletheia events stream", task_id=task_id, url=events_url)

                # Send initial connection event
                connection_event = StreamEvent(
                    event_type="stream_connected",
                    task_id=task_id,
                    timestamp=datetime.utcnow(),
                    data={"message": "Connected to research stream"},
                    sequence=sequence
                )
                yield self._format_sse_event(connection_event)
                sequence += 1

                # Read NDJSON lines from Aletheia
                async for line in response.content:
                    if line:
                        try:
                            # Parse NDJSON event
                            event_data = json.loads(line.decode('utf-8').strip())

                            # Convert to StreamEvent
                            stream_event = StreamEvent(
                                event_type=event_data.get("type", "progress"),
                                task_id=task_id,
                                timestamp=datetime.utcnow(),
                                data=event_data,
                                sequence=sequence
                            )

                            yield self._format_sse_event(stream_event)
                            sequence += 1

                            # Update heartbeat
                            last_heartbeat = time.time()

                        except (json.JSONDecodeError, ValueError) as e:
                            logger.warning("Failed to parse Aletheia event", error=str(e), line=line)
                            continue

                    # Send heartbeat if no events for 30 seconds
                    if time.time() - last_heartbeat > 30:
                        heartbeat_event = StreamEvent(
                            event_type="heartbeat",
                            task_id=task_id,
                            timestamp=datetime.utcnow(),
                            data={"message": "Stream alive"},
                            sequence=sequence
                        )
                        yield self._format_sse_event(heartbeat_event)
                        sequence += 1
                        last_heartbeat = time.time()

                    # Small delay to prevent overwhelming the client
                    await asyncio.sleep(0.1)

        except aiohttp.ClientError as e:
            logger.error("HTTP error streaming from Aletheia", task_id=task_id, error=str(e))
            raise Exception(f"Connection to Aletheia failed: {str(e)}")

    def _format_sse_event(self, event: StreamEvent) -> str:
        """
        Format StreamEvent as SSE event string.
        """
        event_json = event.model_dump_json()
        return f"data: {event_json}\n\n"

    async def stop_stream(self, task_id: str):
        """Stop an active event stream."""
        if task_id in self._active_streams:
            self._active_streams[task_id] = False
            logger.info("Requested stream stop", task_id=task_id)

    async def create_mock_stream(
        self,
        task_id: str,
        duration: int = 180
    ) -> AsyncGenerator[str, None]:
        """
        Create a mock event stream for testing when Aletheia is unavailable.
        """
        self._active_streams[task_id] = True
        start_time = time.time()
        sequence = 0

        try:
            logger.info("Starting mock event stream", task_id=task_id)

            # Mock research phases
            phases = [
                {"phase": "initialization", "progress": 0.0, "message": "Initializing research task"},
                {"phase": "search", "progress": 0.1, "message": "Searching for relevant sources"},
                {"phase": "analysis", "progress": 0.3, "message": "Analyzing source content"},
                {"phase": "evidence", "progress": 0.5, "message": "Extracting evidence and key findings"},
                {"phase": "synthesis", "progress": 0.7, "message": "Synthesizing research results"},
                {"phase": "citation", "progress": 0.9, "message": "Generating citations and references"},
                {"phase": "completion", "progress": 1.0, "message": "Research completed successfully"}
            ]

            for phase in phases:
                if not self._active_streams.get(task_id, False):
                    break

                # Send phase update
                phase_event = StreamEvent(
                    event_type="progress_update",
                    task_id=task_id,
                    timestamp=datetime.utcnow(),
                    data={
                        "phase": phase["phase"],
                        "progress": phase["progress"],
                        "message": phase["message"],
                        "step": sequence + 1,
                        "total_steps": len(phases)
                    },
                    sequence=sequence
                )

                yield self._format_sse_event(phase_event)
                sequence += 1

                # Wait between phases
                await asyncio.sleep(duration / len(phases))

            # Send completion event
            completion_event = StreamEvent(
                event_type="task_completed",
                task_id=task_id,
                timestamp=datetime.utcnow(),
                data={
                    "status": "completed",
                    "message": "Research task completed successfully",
                    "results_available": True,
                    "total_time": time.time() - start_time
                },
                sequence=sequence
            )

            yield self._format_sse_event(completion_event)

        except Exception as e:
            logger.error("Error in mock stream", task_id=task_id, error=str(e))
            error_event = StreamEvent(
                event_type="stream_error",
                task_id=task_id,
                timestamp=datetime.utcnow(),
                data={"error": str(e), "error_type": "mock_stream_error"}
            )
            yield self._format_sse_event(error_event)

        finally:
            self._active_streams.pop(task_id, None)
            logger.info("Mock event stream completed", task_id=task_id)

    async def get_stream_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of an active stream."""
        is_active = self._active_streams.get(task_id, False)

        return {
            "task_id": task_id,
            "stream_active": is_active,
            "timestamp": datetime.utcnow().isoformat()
        }


# Singleton instance
_event_streamer: Optional[AletheiaEventStreamer] = None


def get_event_streamer() -> AletheiaEventStreamer:
    """Get singleton event streamer instance."""
    global _event_streamer
    if _event_streamer is None:
        _event_streamer = AletheiaEventStreamer()
    return _event_streamer