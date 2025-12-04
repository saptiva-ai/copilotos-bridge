"""
Bank Advisor ETL Package - Unified Polars-based ETL Pipeline.

This package provides high-performance data loading and transformation
for the Bank Advisor plugin, consolidating both Legacy and Normalized
ETL pipelines.

Usage:
    from bankadvisor.etl import UnifiedETL

    etl = UnifiedETL(data_root="/app/data/raw")
    etl.run()

Or from CLI:
    python -m bankadvisor.etl.etl_unified --data-root /path/to/data

Modules:
    - loaders_polars: Unified data loaders for all 8 data sources
    - transforms_polars: Unified transformations using Polars
    - etl_unified: Main orchestrator

Deprecated modules (kept for backwards compatibility):
    - etl_processor: Use etl_unified instead
"""
from .etl_unified import UnifiedETL, run_etl
from .loaders_polars import (
    DataPaths,
    get_data_paths,
    load_all_sources,
)
from .transforms_polars import (
    transform_all,
    aggregate_monthly_kpis,
)

__all__ = [
    # Main entry points
    "UnifiedETL",
    "run_etl",
    # Loaders
    "DataPaths",
    "get_data_paths",
    "load_all_sources",
    # Transforms
    "transform_all",
    "aggregate_monthly_kpis",
]

__version__ = "2.0.0"
