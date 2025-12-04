"""
ETL Runner with structured logging and execution tracking.

This module wraps the Unified ETL pipeline with:
- Structured logging
- Execution tracking (stored in etl_runs table)
- Error handling and recovery
- Performance metrics

Usage:
    # Run manually (unified Polars ETL - default)
    python -m bankadvisor.etl_runner

    # Run with legacy Pandas ETL (deprecated)
    python -m bankadvisor.etl_runner --legacy

    # Run from cron
    0 2 * * * cd /app && python -m bankadvisor.etl_runner >> /var/log/etl.log 2>&1

    # Dry run (no DB writes)
    python -m bankadvisor.etl_runner --dry-run
"""
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any
import structlog
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from bankadvisor.models.etl_run import ETLRun, Base as ETLBase
from core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

# ETL Version - increment when ETL logic changes significantly
ETL_VERSION = "2.0"  # v2.0 = Unified Polars ETL


def get_db_engine():
    """Get database engine with proper host resolution."""
    db_url = settings.database_url_sync

    # Override host if running outside docker
    if not os.path.exists("/.dockerenv"):
        db_url = db_url.replace(f"@{settings.postgres_host}:", "@localhost:")

    return create_engine(db_url)


def ensure_etl_runs_table_exists(engine):
    """
    Create etl_runs table if it doesn't exist.

    We use a separate Base to avoid circular imports with kpi.py.
    """
    logger.info("Ensuring etl_runs table exists...")
    ETLBase.metadata.create_all(engine)
    logger.info("etl_runs table ready")


def run_unified_etl(dry_run: bool = False) -> Dict[str, int]:
    """
    Execute the unified Polars-based ETL pipeline.

    This is the new high-performance ETL that consolidates:
    - CNBV data loading
    - ICAP, TDA, Corporate Rates enrichment
    - BE_BM normalized data

    Args:
        dry_run: If True, don't write to database

    Returns:
        Dictionary with table names and row counts
    """
    # Import here to avoid circular imports and allow legacy fallback
    from etl.etl_unified import UnifiedETL

    etl = UnifiedETL(dry_run=dry_run)
    return etl.run()


def run_legacy_etl() -> Dict[str, int]:
    """
    Execute the legacy Pandas-based ETL pipeline.

    DEPRECATED: Use run_unified_etl() instead.
    This is kept for backward compatibility and debugging.

    Returns:
        Dictionary with row counts
    """
    import warnings
    warnings.warn(
        "Legacy ETL is deprecated. Use unified ETL (default) for better performance.",
        DeprecationWarning,
        stacklevel=2
    )

    from bankadvisor.etl_loader import run_etl as run_base_etl
    from bankadvisor.etl_loader_enhanced import run_etl_enhancement

    # Phase 1: Base ETL
    logger.info("etl.legacy.phase.base.started")
    run_base_etl()

    # Phase 2: Enhanced ETL
    logger.info("etl.legacy.phase.enhanced.started")
    run_etl_enhancement()

    return {"monthly_kpis": -1}  # Row count fetched separately


def run_etl_once(
    triggered_by: str = "manual",
    use_legacy: bool = False,
    dry_run: bool = False
) -> Optional[int]:
    """
    Execute the complete ETL pipeline with tracking.

    This function:
    1. Creates an ETL run record with status='running'
    2. Executes ETL (unified Polars or legacy Pandas)
    3. Updates run record with results (success/failure)
    4. Logs structured metrics

    Args:
        triggered_by: Source of execution ('cron', 'manual', 'api')
        use_legacy: If True, use deprecated Pandas ETL
        dry_run: If True, don't write to database

    Returns:
        ETL run ID if successful, None if failed
    """
    engine = get_db_engine()
    ensure_etl_runs_table_exists(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    # Determine ETL version
    etl_version = "1.0-legacy" if use_legacy else ETL_VERSION

    # Create run record
    etl_run = ETLRun(
        started_at=datetime.utcnow(),
        status="running",
        triggered_by=triggered_by,
        etl_version=etl_version
    )
    session.add(etl_run)
    session.commit()

    run_id = etl_run.id
    logger.info(
        "etl.started",
        run_id=run_id,
        triggered_by=triggered_by,
        etl_version=etl_version,
        use_legacy=use_legacy,
        dry_run=dry_run,
        started_at=etl_run.started_at.isoformat()
    )

    try:
        # =====================================================================
        # Execute ETL
        # =====================================================================
        if use_legacy:
            logger.info("etl.using_legacy_pandas", run_id=run_id)
            run_legacy_etl()
        else:
            logger.info("etl.using_unified_polars", run_id=run_id)
            results = run_unified_etl(dry_run=dry_run)

            # Log results from unified ETL
            for table_name, row_count in results.items():
                logger.info(
                    "etl.table.saved",
                    run_id=run_id,
                    table=table_name,
                    rows=row_count
                )

        # =====================================================================
        # Count final rows in database
        # =====================================================================
        if not dry_run:
            with engine.begin() as conn:
                # Base metrics
                result = conn.execute(text("SELECT COUNT(*) FROM monthly_kpis"))
                rows_base = result.scalar() or 0

                # Enhanced metrics (ICAP, TDA, Tasas)
                result = conn.execute(text("""
                    SELECT
                        COUNT(icap_total) as icap_count,
                        COUNT(tda_cartera_total) as tda_count,
                        COUNT(tasa_mn) + COUNT(tasa_me) as tasas_count
                    FROM monthly_kpis
                """))
                row = result.fetchone()
                icap_count = row[0] if row else 0
                tda_count = row[1] if row else 0
                tasas_count = row[2] if row else 0

            etl_run.rows_processed_base = rows_base
            etl_run.rows_processed_icap = icap_count
            etl_run.rows_processed_tda = tda_count
            etl_run.rows_processed_tasas = tasas_count
        else:
            rows_base = icap_count = tda_count = tasas_count = 0

        session.commit()

        # =====================================================================
        # Success: Mark run as completed
        # =====================================================================
        etl_run.completed_at = datetime.utcnow()
        etl_run.status = "success" if not dry_run else "dry_run"
        etl_run.duration_seconds = (
            etl_run.completed_at - etl_run.started_at
        ).total_seconds()
        session.commit()

        logger.info(
            "etl.completed",
            run_id=run_id,
            status=etl_run.status,
            duration_seconds=etl_run.duration_seconds,
            rows_base=rows_base,
            rows_icap=icap_count,
            rows_tda=tda_count,
            rows_tasas=tasas_count
        )

        return run_id

    except Exception as e:
        # =====================================================================
        # Failure: Log error and mark run as failed
        # =====================================================================
        etl_run.completed_at = datetime.utcnow()
        etl_run.status = "failure"
        etl_run.error_message = str(e)
        etl_run.duration_seconds = (
            etl_run.completed_at - etl_run.started_at
        ).total_seconds()
        session.commit()

        logger.error(
            "etl.failed",
            run_id=run_id,
            error=str(e),
            duration_seconds=etl_run.duration_seconds,
            exc_info=True
        )

        return None

    finally:
        session.close()


def main():
    """
    CLI entry point.

    Supports flags:
        --legacy: Use deprecated Pandas ETL instead of unified Polars ETL
        --dry-run: Don't write to database
        --cron: Mark as triggered by cron job
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="BankAdvisor ETL Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m bankadvisor.etl_runner              # Run unified Polars ETL
    python -m bankadvisor.etl_runner --dry-run    # Test without DB writes
    python -m bankadvisor.etl_runner --legacy     # Use deprecated Pandas ETL
    python -m bankadvisor.etl_runner --cron       # Mark as cron-triggered
        """
    )
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="Use deprecated Pandas-based ETL (slower)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't write to database"
    )
    parser.add_argument(
        "--cron",
        action="store_true",
        help="Mark as triggered by cron job"
    )

    args = parser.parse_args()

    # Determine trigger source
    if os.getenv("ETL_TRIGGER") == "cron" or args.cron:
        triggered_by = "cron"
    else:
        triggered_by = "manual"

    logger.info(
        "etl_runner.main.started",
        triggered_by=triggered_by,
        use_legacy=args.legacy,
        dry_run=args.dry_run
    )

    run_id = run_etl_once(
        triggered_by=triggered_by,
        use_legacy=args.legacy,
        dry_run=args.dry_run
    )

    if run_id:
        logger.info("etl_runner.main.success", run_id=run_id)
        sys.exit(0)
    else:
        logger.error("etl_runner.main.failure")
        sys.exit(1)


if __name__ == "__main__":
    main()
