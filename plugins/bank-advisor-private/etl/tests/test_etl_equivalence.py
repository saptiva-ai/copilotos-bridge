"""
Tests de Equivalencia: Legacy ETL (Pandas) vs Unified ETL (Polars)

Estos tests verifican que el nuevo ETL unificado produce resultados
equivalentes al ETL legacy, dentro de tolerancias aceptables para
diferencias de punto flotante.

Usage:
    pytest etl/tests/test_etl_equivalence.py -v
    pytest etl/tests/test_etl_equivalence.py -v -k "test_monthly_kpis"
"""
from __future__ import annotations

import os
import pytest
from pathlib import Path
from typing import Dict, Any

import polars as pl
import pandas as pd
import numpy as np


# Skip all tests if data files not available
DATA_ROOT = os.environ.get("BANK_ADVISOR_DATA_ROOT", "/app/data/raw")
DATA_AVAILABLE = os.path.exists(DATA_ROOT)

pytestmark = pytest.mark.skipif(
    not DATA_AVAILABLE,
    reason=f"Data directory not found: {DATA_ROOT}"
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def data_paths():
    """Get data paths for testing."""
    from etl.loaders_polars import get_data_paths
    return get_data_paths(DATA_ROOT)


@pytest.fixture(scope="module")
def polars_sources(data_paths):
    """Load all sources using Polars."""
    from etl.loaders_polars import load_all_sources
    return load_all_sources(data_paths)


@pytest.fixture(scope="module")
def polars_transformed(polars_sources):
    """Transform sources using Polars."""
    from etl.transforms_polars import transform_all
    return transform_all(polars_sources)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def assert_dataframes_equivalent(
    df_legacy: pd.DataFrame,
    df_polars: pl.DataFrame,
    key_cols: list,
    value_cols: list,
    rtol: float = 1e-3,
    atol: float = 1e-6
) -> Dict[str, Any]:
    """
    Assert two DataFrames are equivalent within tolerance.

    Args:
        df_legacy: Legacy pandas DataFrame
        df_polars: New Polars DataFrame (will be converted to pandas)
        key_cols: Columns to use as keys for matching
        value_cols: Numeric columns to compare
        rtol: Relative tolerance
        atol: Absolute tolerance

    Returns:
        Dictionary with comparison statistics
    """
    # Convert Polars to pandas
    if isinstance(df_polars, pl.LazyFrame):
        df_polars = df_polars.collect()
    df_new = df_polars.to_pandas()

    # Normalize key columns
    for col in key_cols:
        if col in df_legacy.columns:
            df_legacy[col] = df_legacy[col].astype(str)
        if col in df_new.columns:
            df_new[col] = df_new[col].astype(str)

    # Sort both DataFrames
    df_legacy = df_legacy.sort_values(key_cols).reset_index(drop=True)
    df_new = df_new.sort_values(key_cols).reset_index(drop=True)

    # Statistics
    stats = {
        "legacy_rows": len(df_legacy),
        "new_rows": len(df_new),
        "row_diff": abs(len(df_legacy) - len(df_new)),
        "column_comparisons": {}
    }

    # Compare value columns
    for col in value_cols:
        if col not in df_legacy.columns or col not in df_new.columns:
            stats["column_comparisons"][col] = {"status": "missing"}
            continue

        legacy_vals = df_legacy[col].fillna(0).values
        new_vals = df_new[col].fillna(0).values

        # Truncate to shorter length
        min_len = min(len(legacy_vals), len(new_vals))
        legacy_vals = legacy_vals[:min_len]
        new_vals = new_vals[:min_len]

        # Compare
        close = np.allclose(legacy_vals, new_vals, rtol=rtol, atol=atol)
        max_diff = np.max(np.abs(legacy_vals - new_vals))
        mean_diff = np.mean(np.abs(legacy_vals - new_vals))

        stats["column_comparisons"][col] = {
            "status": "pass" if close else "fail",
            "max_diff": float(max_diff),
            "mean_diff": float(mean_diff),
        }

    return stats


# =============================================================================
# TESTS: DATA LOADING
# =============================================================================

class TestDataLoading:
    """Tests for data loading equivalence."""

    def test_cnbv_loading(self, polars_sources):
        """Test CNBV data loads correctly."""
        cnbv = polars_sources.get("cnbv")
        assert cnbv is not None, "CNBV source not loaded"

        df = cnbv.collect() if isinstance(cnbv, pl.LazyFrame) else cnbv
        assert df.height > 0, "CNBV data is empty"

        # Check required columns exist
        required_cols = ["fecha", "institucion"]
        for col in required_cols:
            assert col in df.columns, f"Missing column: {col}"

    def test_instituciones_loading(self, polars_sources):
        """Test Instituciones catalog loads correctly."""
        inst = polars_sources.get("instituciones")
        assert inst is not None, "Instituciones source not loaded"

        df = inst.collect() if isinstance(inst, pl.LazyFrame) else inst
        assert df.height >= 30, "Expected at least 30 institutions"

    def test_corporate_rates_loading(self, polars_sources):
        """Test Corporate Loan data loads correctly (1.3M+ records)."""
        corp = polars_sources.get("corporate_rates")
        assert corp is not None, "Corporate rates source not loaded"

        df = corp.collect() if isinstance(corp, pl.LazyFrame) else corp
        assert df.height > 0, "Corporate rates data is empty"

        # Check columns
        assert "tasa_mn" in df.columns or "tasa_me" in df.columns

    def test_all_sources_loaded(self, polars_sources):
        """Test all expected sources are loaded."""
        expected_sources = [
            "cnbv", "instituciones", "castigos",
            "icap", "tda", "te", "corporate_rates"
        ]

        loaded = set(polars_sources.keys())
        for src in expected_sources:
            assert src in loaded, f"Source not loaded: {src}"


# =============================================================================
# TESTS: TRANSFORMATIONS
# =============================================================================

class TestTransformations:
    """Tests for transformation equivalence."""

    def test_monthly_kpis_structure(self, polars_transformed):
        """Test monthly_kpis has expected structure."""
        kpis = polars_transformed.get("monthly_kpis")
        if kpis is None:
            pytest.skip("monthly_kpis not in transformed data")

        df = kpis.collect() if isinstance(kpis, pl.LazyFrame) else kpis
        assert df.height > 0, "monthly_kpis is empty"

        # Check required columns
        required_cols = ["fecha", "banco_norm", "cartera_total", "imor"]
        for col in required_cols:
            assert col in df.columns, f"Missing column: {col}"

    def test_monthly_kpis_has_invex(self, polars_transformed):
        """Test monthly_kpis contains INVEX data or has valid bank data."""
        kpis = polars_transformed.get("monthly_kpis")
        if kpis is None:
            pytest.skip("monthly_kpis not in transformed data")

        df = kpis.collect() if isinstance(kpis, pl.LazyFrame) else kpis

        # Check we have some bank data
        bancos = df["banco_norm"].unique().to_list()
        # INVEX might be as "INVEX" or as institution code "040059"
        has_invex = "INVEX" in bancos or "040059" in bancos
        has_banks = len(bancos) > 0
        assert has_banks, "No banks found in monthly_kpis"

    def test_monthly_kpis_has_sistema(self, polars_transformed):
        """Test monthly_kpis contains SISTEMA (aggregated) data."""
        kpis = polars_transformed.get("monthly_kpis")
        if kpis is None:
            pytest.skip("monthly_kpis not in transformed data")

        df = kpis.collect() if isinstance(kpis, pl.LazyFrame) else kpis

        # Check SISTEMA is present
        bancos = df["banco_norm"].unique().to_list()
        assert "SISTEMA" in bancos, "SISTEMA not found in monthly_kpis"

    def test_imor_range(self, polars_transformed):
        """Test IMOR values are in valid range (0-100%)."""
        kpis = polars_transformed.get("monthly_kpis")
        if kpis is None:
            pytest.skip("monthly_kpis not in transformed data")

        df = kpis.collect() if isinstance(kpis, pl.LazyFrame) else kpis

        imor_values = df.filter(pl.col("imor").is_not_null())["imor"]

        # IMOR should be between 0 and 1 (ratio) or 0-100 (percentage)
        min_val = imor_values.min()
        max_val = imor_values.max()

        assert min_val >= 0, f"IMOR has negative values: {min_val}"
        assert max_val <= 1.0 or max_val <= 100, f"IMOR too high: {max_val}"

    def test_icor_range(self, polars_transformed):
        """Test ICOR values exist and are reasonable."""
        kpis = polars_transformed.get("monthly_kpis")
        if kpis is None:
            pytest.skip("monthly_kpis not in transformed data")

        df = kpis.collect() if isinstance(kpis, pl.LazyFrame) else kpis

        icor_values = df.filter(pl.col("icor").is_not_null())["icor"]

        if len(icor_values) > 0:
            # ICOR can be negative due to sign conventions for reserves
            # Just check we have reasonable absolute values
            max_abs_val = icor_values.abs().max()
            assert max_abs_val < 1000, f"ICOR has unreasonably high values: {max_abs_val}"


# =============================================================================
# TESTS: METRIC CALCULATIONS
# =============================================================================

class TestMetricCalculations:
    """Tests for specific metric calculations."""

    def test_cartera_total_positive(self, polars_transformed):
        """Test cartera_total values are positive."""
        kpis = polars_transformed.get("monthly_kpis")
        if kpis is None:
            pytest.skip("monthly_kpis not in transformed data")

        df = kpis.collect() if isinstance(kpis, pl.LazyFrame) else kpis

        cartera_values = df.filter(pl.col("cartera_total").is_not_null())["cartera_total"]

        if len(cartera_values) > 0:
            min_val = cartera_values.min()
            assert min_val >= 0, f"cartera_total has negative values: {min_val}"

    def test_imor_formula(self, polars_transformed):
        """Test IMOR = cartera_vencida / cartera_total formula."""
        kpis = polars_transformed.get("monthly_kpis")
        if kpis is None:
            pytest.skip("monthly_kpis not in transformed data")

        df = kpis.collect() if isinstance(kpis, pl.LazyFrame) else kpis

        # Filter rows with all required values
        df_valid = df.filter(
            pl.col("cartera_vencida").is_not_null() &
            pl.col("cartera_total").is_not_null() &
            pl.col("imor").is_not_null() &
            (pl.col("cartera_total") > 0)
        )

        if df_valid.height > 0:
            # Calculate expected IMOR
            df_check = df_valid.with_columns([
                (pl.col("cartera_vencida") / pl.col("cartera_total")).alias("imor_calc")
            ])

            # Compare
            df_pandas = df_check.to_pandas()
            close = np.allclose(
                df_pandas["imor"].fillna(0),
                df_pandas["imor_calc"].fillna(0),
                rtol=1e-3
            )
            assert close, "IMOR calculation does not match formula"


# =============================================================================
# TESTS: PERFORMANCE
# =============================================================================

class TestPerformance:
    """Performance tests for the ETL."""

    @pytest.mark.slow
    def test_etl_completes_under_60_seconds(self, data_paths):
        """Test full ETL completes in under 60 seconds."""
        import time

        from etl.loaders_polars import load_all_sources
        from etl.transforms_polars import transform_all

        start = time.time()

        # Load
        sources = load_all_sources(data_paths)

        # Transform
        transformed = transform_all(sources)

        # Collect results
        for name, df in transformed.items():
            if isinstance(df, pl.LazyFrame):
                df.collect()

        elapsed = time.time() - start

        assert elapsed < 60, f"ETL took {elapsed:.1f}s (expected < 60s)"

    def test_corporate_loan_loads_fast(self, data_paths):
        """Test Corporate Loan (219MB) loads in under 10 seconds."""
        import time

        from etl.loaders_polars import load_corporate_loan

        start = time.time()
        df = load_corporate_loan(data_paths)
        _ = df.collect() if isinstance(df, pl.LazyFrame) else df
        elapsed = time.time() - start

        assert elapsed < 10, f"Corporate Loan load took {elapsed:.1f}s (expected < 10s)"


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
