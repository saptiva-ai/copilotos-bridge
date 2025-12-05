"""
Unified ETL Orchestrator for Bank Advisor Plugin.

Consolidates both Legacy and Normalized ETL pipelines into a single,
high-performance pipeline using Polars.

Usage:
    python -m bankadvisor.etl.etl_unified [--data-root PATH] [--dry-run]

Architecture:
    ┌─────────────────────────────────────────────────────────────────┐
    │                    ETL UNIFICADO                                │
    ├─────────────────────────────────────────────────────────────────┤
    │  ENTRADA (8 fuentes)                                            │
    │  ├─ BE_BM_202509.xlsx (16 hojas)                               │
    │  ├─ CNBV_Cartera_Bancos_V2.xlsx (histórico IFRS9)              │
    │  ├─ ICAP_Bancos.xlsx                                            │
    │  ├─ TDA.xlsx                                                    │
    │  ├─ TE_Invex_Sistema.xlsx                                       │
    │  ├─ CorporateLoan_CNBVDB.csv (219MB)                           │
    │  ├─ CASTIGOS.xlsx                                               │
    │  └─ Instituciones.xlsx                                          │
    │                                                                 │
    │  PROCESO                                                        │
    │  ├─ loaders_polars.py (lectura unificada)                      │
    │  └─ transforms_polars.py (transformaciones)                    │
    │                                                                 │
    │  SALIDA                                                         │
    │  ├─ metricas_financieras (extendido con ICAP, TDA, Tasas)     │
    │  ├─ metricas_cartera_segmentada (~4,500 registros)            │
    │  └─ monthly_kpis_v2 (VISTA para compatibilidad legacy)        │
    └─────────────────────────────────────────────────────────────────┘
"""
from __future__ import annotations

import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

import polars as pl
import structlog

logger = structlog.get_logger(__name__)


# =============================================================================
# IMPORTS (with fallbacks for different execution contexts)
# =============================================================================

try:
    from .loaders_polars import get_data_paths, load_all_sources, DataPaths
    from .transforms_polars import transform_all
except ImportError:
    # Direct execution context
    from loaders_polars import get_data_paths, load_all_sources, DataPaths
    from transforms_polars import transform_all


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

def get_database_url() -> str:
    """Get database URL from environment or settings."""
    # Try to import from core settings
    try:
        from core.config import get_settings
        settings = get_settings()
        db_url = settings.database_url_sync

        # FIX: Do NOT override host - respect settings from .env
        # The .env file now contains production PostgreSQL credentials
        # Previous behavior: if not os.path.exists("/.dockerenv"):
        #     db_url = db_url.replace(f"@{settings.postgres_host}:", "@localhost:")

        logger.info(f"Using database from settings: {db_url.split('@')[0]}@***")
        return db_url
    except ImportError:
        pass

    # Fallback to environment variable
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        logger.info("Using DATABASE_URL from environment")
        return db_url

    # Default development URL (should not be used in production)
    logger.warning("Using default development database URL - this should not happen in production")
    return "postgresql://postgres:postgres@localhost:5432/octavios"


def save_to_postgres(
    dfs: Dict[str, pl.LazyFrame],
    db_url: str,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Save transformed DataFrames to PostgreSQL.

    Args:
        dfs: Dictionary of transformed DataFrames from transform_all()
        db_url: PostgreSQL connection URL
        dry_run: If True, only show what would be saved

    Returns:
        Dictionary with table names and row counts
    """
    logger.info("="*60)
    logger.info("SAVING TO DATABASE")
    logger.info("="*60)

    results = {}
    engine = None

    # Only create engine if not dry run
    if not dry_run:
        from sqlalchemy import create_engine, text
        engine = create_engine(db_url)

    # Table mapping
    table_mapping = {
        "monthly_kpis": "monthly_kpis",
        "metricas_financieras": "metricas_financieras_ext",
        "metricas_segmentadas": "metricas_cartera_segmentada",
        "cnbv_enriched": None,  # Intermediate, not saved
    }

    for df_name, table_name in table_mapping.items():
        if df_name not in dfs or table_name is None:
            continue

        try:
            # Collect lazy frame
            pdf = dfs[df_name].collect().to_pandas()
            row_count = len(pdf)

            if dry_run:
                logger.info(f"  [DRY-RUN] Would save {row_count:,} rows to {table_name}")
                results[table_name] = row_count
                continue

            # Save to database
            logger.info(f"  Saving {df_name} -> {table_name} ({row_count:,} rows)...")

            # Use replace for idempotent loading
            pdf.to_sql(
                table_name,
                engine,
                if_exists="replace",
                index=False,
                method="multi",
                chunksize=1000
            )

            logger.info(f"    ✓ {table_name}: {row_count:,} rows saved")
            results[table_name] = row_count

        except Exception as e:
            logger.error(f"  ✗ Error saving {df_name} to {table_name}: {e}")
            results[table_name] = -1

    # Create compatibility view
    if not dry_run:
        create_monthly_kpis_view(engine)

    return results


def create_monthly_kpis_view(engine):
    """
    Create monthly_kpis_v2 view for backward compatibility.

    This view exposes the new normalized structure in the old format.
    """
    view_sql = """
    CREATE OR REPLACE VIEW monthly_kpis_v2 AS
    SELECT
        m.fecha,
        m.banco_norm as institucion,
        m.banco_norm,
        -- Carteras
        m.cartera_total,
        m.cartera_comercial_total,
        m.cartera_consumo_total,
        m.cartera_vivienda_total,
        m.empresarial_total,
        m.entidades_financieras_total,
        m.entidades_gubernamentales_total,
        -- Calidad
        m.cartera_vencida,
        m.imor,
        m.icor,
        -- Reservas
        m.reservas_etapa_todas,
        m.reservas_variacion_mm,
        -- Pérdida Esperada
        m.pe_total,
        m.pe_empresarial,
        m.pe_consumo,
        m.pe_vivienda,
        -- Índices
        m.icap_total,
        m.tda_cartera_total,
        -- Tasas
        m.tasa_sistema,
        m.tasa_invex_consumo,
        m.tasa_mn,
        m.tasa_me,
        -- Quebrantos
        m.quebrantos_cc,
        m.quebrantos_vs_cartera_cc
    FROM monthly_kpis m;
    """

    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text(view_sql))
            conn.commit()
        logger.info("  ✓ View monthly_kpis_v2 created")
    except Exception as e:
        logger.warning(f"  ⚠ Could not create view monthly_kpis_v2: {e}")


# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================

class UnifiedETL:
    """
    Main ETL orchestrator that consolidates both Legacy and Normalized pipelines.

    Example usage:
        etl = UnifiedETL(data_root="/app/data/raw")
        etl.run()
    """

    def __init__(
        self,
        data_root: Optional[Path] = None,
        db_url: Optional[str] = None,
        dry_run: bool = False
    ):
        """
        Initialize the unified ETL.

        Args:
            data_root: Path to data directory (default: /app/data/raw)
            db_url: PostgreSQL connection URL (default: from settings)
            dry_run: If True, only show what would be done
        """
        self.data_root = self._resolve_data_root(data_root)
        self.db_url = db_url or get_database_url()
        self.dry_run = dry_run

        # Timing
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

        # Results
        self.sources: Dict[str, pl.LazyFrame] = {}
        self.transformed: Dict[str, pl.LazyFrame] = {}
        self.saved: Dict[str, int] = {}

    def _resolve_data_root(self, data_root: Optional[Path]) -> Path:
        """Resolve the data root directory."""
        if data_root:
            return Path(data_root).resolve()

        # Try Docker path first
        if os.path.exists("/app/data/raw"):
            return Path("/app/data/raw")

        # Try relative to this file
        plugin_root = Path(__file__).parent.parent
        local_data = plugin_root / "data" / "raw"
        if local_data.exists():
            return local_data

        # Try apps/api/data/raw
        workspace_root = plugin_root.parent.parent.parent
        api_data = workspace_root / "apps" / "api" / "data" / "raw"
        if api_data.exists():
            return api_data

        raise FileNotFoundError(
            "Could not find data directory. Please specify --data-root"
        )

    def run(self) -> Dict[str, int]:
        """
        Execute the full ETL pipeline.

        Returns:
            Dictionary with table names and row counts
        """
        self.start_time = time.time()

        logger.info("🚀 Starting Unified ETL (Polars)")
        logger.info(f"   Data root: {self.data_root}")
        logger.info(f"   Dry run: {self.dry_run}")
        logger.info("")

        try:
            # Phase 1: Load all sources
            self._phase_load()

            # Phase 2: Transform
            self._phase_transform()

            # Phase 3: Save to database
            self._phase_save()

            # Summary
            self._print_summary()

            return self.saved

        except Exception as e:
            logger.error(f"❌ ETL failed: {e}")
            raise

        finally:
            self.end_time = time.time()

    def _phase_load(self):
        """Phase 1: Load all data sources."""
        logger.info("="*60)
        logger.info("PHASE 1: LOADING DATA SOURCES")
        logger.info("="*60)

        paths = get_data_paths(self.data_root)
        self.sources = load_all_sources(paths)

        # Validate we have minimum required data
        required = ["cnbv", "instituciones"]
        missing = [r for r in required if r not in self.sources or self.sources[r].collect().height == 0]

        if missing:
            raise ValueError(f"Missing required data sources: {missing}")

        logger.info("✓ Phase 1 complete")

    def _phase_transform(self):
        """Phase 2: Transform all data."""
        logger.info("")
        logger.info("="*60)
        logger.info("PHASE 2: TRANSFORMING DATA")
        logger.info("="*60)

        self.transformed = transform_all(self.sources)

        logger.info("✓ Phase 2 complete")

    def _phase_save(self):
        """Phase 3: Save to database."""
        logger.info("")

        if self.dry_run:
            logger.info("="*60)
            logger.info("PHASE 3: SAVE (DRY RUN)")
            logger.info("="*60)
        else:
            logger.info("="*60)
            logger.info("PHASE 3: SAVING TO DATABASE")
            logger.info("="*60)

        self.saved = save_to_postgres(
            self.transformed,
            self.db_url,
            dry_run=self.dry_run
        )

        logger.info("✓ Phase 3 complete")

    def _print_summary(self):
        """Print execution summary."""
        logger.info("")
        logger.info("="*60)
        logger.info("EXECUTION SUMMARY")
        logger.info("="*60)

        # Timing
        elapsed = (self.end_time or time.time()) - (self.start_time or time.time())
        logger.info(f"  Total time: {elapsed:.2f}s")

        # Source counts
        logger.info("")
        logger.info("  Sources loaded:")
        for name, df in self.sources.items():
            try:
                count = df.collect().height
                logger.info(f"    {name}: {count:,} records")
            except Exception:
                pass

        # Output counts
        logger.info("")
        logger.info("  Tables saved:")
        total_rows = 0
        for table, count in self.saved.items():
            if count >= 0:
                logger.info(f"    {table}: {count:,} rows")
                total_rows += count
            else:
                logger.info(f"    {table}: ERROR")

        logger.info("")
        logger.info(f"  Total rows: {total_rows:,}")

        if self.dry_run:
            logger.info("")
            logger.info("  ⚠ DRY RUN - no data was actually saved")
        else:
            logger.info("")
            logger.info("  ✅ ETL completed successfully!")


# =============================================================================
# CLI ENTRY POINTS
# =============================================================================

def run_etl():
    """Legacy entry point for compatibility with existing scripts."""
    etl = UnifiedETL()
    etl.run()


def main():
    """CLI entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Unified ETL for Bank Advisor Plugin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m bankadvisor.etl.etl_unified
  python -m bankadvisor.etl.etl_unified --data-root /path/to/data
  python -m bankadvisor.etl.etl_unified --dry-run
        """
    )

    parser.add_argument(
        "--data-root",
        type=Path,
        help="Path to data directory containing source files"
    )

    parser.add_argument(
        "--db-url",
        type=str,
        help="PostgreSQL connection URL"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without saving to database"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(0)
        )

    # Run ETL
    try:
        etl = UnifiedETL(
            data_root=args.data_root,
            db_url=args.db_url,
            dry_run=args.dry_run
        )
        results = etl.run()

        # Exit with error if any table failed
        if any(count < 0 for count in results.values()):
            sys.exit(1)

    except FileNotFoundError as e:
        logger.error(f"❌ {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ ETL failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
