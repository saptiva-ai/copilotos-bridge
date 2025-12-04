"""
RAG Feedback Job - Scheduled task for automatic RAG seeding

Runs periodically to seed successful queries from query_logs to Qdrant RAG.
Part of Q1 2025 RAG Feedback Loop implementation.
"""
import asyncio
from datetime import datetime
from typing import Optional
import structlog

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from bankadvisor.services.rag_feedback_service import RagFeedbackService

logger = structlog.get_logger(__name__)


class RagFeedbackJob:
    """
    Scheduled job to seed RAG from query logs.

    Runs every hour to:
    1. Get recent successful queries (last hour, confidence >= 0.7)
    2. Generate embeddings
    3. Seed to Qdrant
    4. Mark as seeded

    Features:
    - Automatic error recovery
    - Metrics logging
    - Configurable interval
    """

    def __init__(
        self,
        feedback_service: RagFeedbackService,
        interval_hours: int = 1,
        batch_size: int = 50,
        min_confidence: float = 0.7
    ):
        """
        Initialize RAG Feedback Job.

        Args:
            feedback_service: RagFeedbackService instance
            interval_hours: How often to run (default: 1 hour)
            batch_size: Max queries to seed per run
            min_confidence: Minimum confidence threshold
        """
        self.feedback_service = feedback_service
        self.interval_hours = interval_hours
        self.batch_size = batch_size
        self.min_confidence = min_confidence

        self.scheduler = AsyncIOScheduler()
        self._is_running = False
        self._last_run: Optional[datetime] = None
        self._total_runs = 0
        self._total_seeded = 0
        self._total_errors = 0

    def start(self):
        """
        Start the scheduled job.

        Job runs every `interval_hours` hours.
        First run happens immediately on start.
        """
        if self._is_running:
            logger.warning("rag_feedback_job.already_running")
            return

        # Add job to scheduler
        self.scheduler.add_job(
            self._run_feedback_loop,
            trigger=IntervalTrigger(hours=self.interval_hours),
            id='rag_feedback_loop',
            replace_existing=True,
            max_instances=1,  # Only one instance at a time
            coalesce=True,     # If missed, run once (not multiple times)
        )

        # Start scheduler
        self.scheduler.start()
        self._is_running = True

        logger.info(
            "rag_feedback_job.started",
            interval_hours=self.interval_hours,
            batch_size=self.batch_size,
            min_confidence=self.min_confidence
        )

        # Run immediately on start
        asyncio.create_task(self._run_feedback_loop())

    def stop(self):
        """Stop the scheduled job."""
        if not self._is_running:
            return

        self.scheduler.shutdown(wait=False)
        self._is_running = False

        logger.info(
            "rag_feedback_job.stopped",
            total_runs=self._total_runs,
            total_seeded=self._total_seeded,
            total_errors=self._total_errors
        )

    async def _run_feedback_loop(self):
        """
        Execute feedback loop - seed last hour's queries.

        This is the main job logic that runs periodically.
        """
        run_start = datetime.now()

        try:
            logger.info(
                "rag_feedback_job.run_start",
                run_number=self._total_runs + 1,
                last_run=self._last_run.isoformat() if self._last_run else None
            )

            # Execute seeding
            result = await self.feedback_service.seed_from_query_logs(
                batch_size=self.batch_size,
                min_age_hours=1,      # Wait 1 hour before seeding
                max_age_days=90,       # Only seed queries < 90 days old
                min_confidence=self.min_confidence
            )

            # Update stats
            self._total_runs += 1
            self._total_seeded += result.get("seeded_count", 0)
            self._last_run = run_start

            # Log results
            logger.info(
                "rag_feedback_job.run_complete",
                run_number=self._total_runs,
                duration_ms=(datetime.now() - run_start).total_seconds() * 1000,
                seeded_count=result.get("seeded_count", 0),
                avg_confidence=result.get("avg_confidence", 0),
                top_metrics=result.get("top_metrics", []),
                total_seeded_all_time=self._total_seeded
            )

            # If no queries seeded, log at debug level
            if result.get("seeded_count", 0) == 0:
                logger.debug("rag_feedback_job.no_candidates", message="No queries ready for seeding")

        except Exception as e:
            self._total_errors += 1

            logger.error(
                "rag_feedback_job.run_failed",
                error=str(e),
                run_number=self._total_runs + 1,
                total_errors=self._total_errors,
                exc_info=True
            )

            # Don't crash - continue on next interval
            # This ensures the job keeps trying even if one run fails

    def get_stats(self) -> dict:
        """
        Get job statistics.

        Returns:
            Dict with job stats (total_runs, total_seeded, etc.)
        """
        return {
            "is_running": self._is_running,
            "interval_hours": self.interval_hours,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "total_runs": self._total_runs,
            "total_seeded": self._total_seeded,
            "total_errors": self._total_errors,
            "success_rate": (
                (self._total_runs - self._total_errors) / self._total_runs
                if self._total_runs > 0 else 0
            ),
            "avg_seeded_per_run": (
                self._total_seeded / self._total_runs
                if self._total_runs > 0 else 0
            )
        }

    async def run_now(self) -> dict:
        """
        Manually trigger a feedback loop run (for testing/admin).

        Returns:
            Result dict from feedback service
        """
        logger.info("rag_feedback_job.manual_run_triggered")

        result = await self.feedback_service.seed_from_query_logs(
            batch_size=self.batch_size,
            min_age_hours=0,  # No age restriction for manual run
            max_age_days=90,
            min_confidence=self.min_confidence
        )

        logger.info(
            "rag_feedback_job.manual_run_complete",
            seeded_count=result.get("seeded_count", 0)
        )

        return result


# Global instance (initialized in main.py lifespan)
_rag_feedback_job: Optional[RagFeedbackJob] = None


def get_rag_feedback_job() -> Optional[RagFeedbackJob]:
    """Get the global RAG feedback job instance."""
    return _rag_feedback_job


def set_rag_feedback_job(job: RagFeedbackJob):
    """Set the global RAG feedback job instance."""
    global _rag_feedback_job
    _rag_feedback_job = job
