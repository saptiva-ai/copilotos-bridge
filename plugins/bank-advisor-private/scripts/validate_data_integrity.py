#!/usr/bin/env python3
"""
Data Integrity Validation for BankAdvisor
Verifies data quality, coverage, and correctness for all metrics.

Usage:
    python scripts/validate_data_integrity.py
"""

import os
import sys
import asyncio
import asyncpg
from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://octavios:secure_postgres_password@localhost:5432/bankadvisor")

# Metrics to validate with expected ranges
METRICS_CONFIG = {
    "imor": {"name": "IMOR", "expected_range": (0, 300), "unit": "%"},
    "icor": {"name": "ICOR", "expected_range": (0, 500), "unit": "%"},  # Now positive with abs()
    "icap_total": {"name": "ICAP", "expected_range": (0, 30), "unit": "%"},
    "tda_cartera_total": {"name": "TDA", "expected_range": (0, 100), "unit": "%"},
    "tasa_mn": {"name": "TASA_MN", "expected_range": (0, 50), "unit": "%"},
    "tasa_me": {"name": "TASA_ME", "expected_range": (0, 20), "unit": "%"},
    "cartera_total": {"name": "Cartera Total", "expected_range": (0, 1e12), "unit": "MXN"},
}

BANKS = ["INVEX", "SISTEMA", "BBVA", "SANTANDER", "BANORTE", "HSBC", "CITIBANAMEX"]


@dataclass
class MetricBankValidation:
    metric: str
    bank: str
    total_records: int
    non_null_records: int
    null_pct: float
    zero_records: int
    zero_pct: float
    min_value: float
    max_value: float
    mean_value: float
    latest_value: float
    latest_date: str
    out_of_range: int
    data_quality_score: float  # 0-100


async def validate_metric_bank(conn: asyncpg.Connection, metric: str, bank: str) -> MetricBankValidation:
    """Validate a specific metric for a specific bank."""

    query = f"""
    WITH metric_data AS (
        SELECT
            {metric} as value,
            fecha
        FROM monthly_kpis
        WHERE banco_norm = $1
    )
    SELECT
        COUNT(*) as total,
        COUNT(value) as non_null,
        (COUNT(*) - COUNT(value))::float / NULLIF(COUNT(*), 0) * 100 as null_pct,
        SUM(CASE WHEN value = 0 THEN 1 ELSE 0 END) as zeros,
        SUM(CASE WHEN value = 0 THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) * 100 as zero_pct,
        MIN(value) as min_val,
        MAX(value) as max_val,
        AVG(value) as mean_val,
        (SELECT value FROM metric_data WHERE value IS NOT NULL ORDER BY fecha DESC LIMIT 1) as latest_val,
        (SELECT fecha FROM metric_data WHERE value IS NOT NULL ORDER BY fecha DESC LIMIT 1) as latest_date
    FROM metric_data
    """

    row = await conn.fetchrow(query, bank)

    # Check out of range values
    expected_min, expected_max = METRICS_CONFIG[metric]["expected_range"]

    out_of_range_query = f"""
    SELECT COUNT(*)
    FROM monthly_kpis
    WHERE banco_norm = $1
      AND {metric} IS NOT NULL
      AND ({metric} < $2 OR {metric} > $3)
    """
    out_of_range = await conn.fetchval(out_of_range_query, bank, expected_min, expected_max)

    # Calculate data quality score (0-100)
    # Factors: null%, zero%, out_of_range%, recency
    null_pct = row['null_pct'] or 0
    zero_pct = row['zero_pct'] or 0
    out_of_range_pct = (out_of_range / row['total'] * 100) if row['total'] > 0 else 0

    # Scoring: 100 - penalties
    score = 100.0
    score -= null_pct * 0.5  # -0.5 per % of nulls
    score -= zero_pct * 0.3  # -0.3 per % of zeros
    score -= out_of_range_pct * 1.0  # -1.0 per % out of range
    score = max(0, score)

    return MetricBankValidation(
        metric=metric,
        bank=bank,
        total_records=row['total'],
        non_null_records=row['non_null'],
        null_pct=null_pct,
        zero_records=row['zeros'],
        zero_pct=zero_pct,
        min_value=row['min_val'] if row['min_val'] is not None else 0,
        max_value=row['max_val'] if row['max_val'] is not None else 0,
        mean_value=row['mean_val'] if row['mean_val'] is not None else 0,
        latest_value=row['latest_val'] if row['latest_val'] is not None else 0,
        latest_date=str(row['latest_date']) if row['latest_date'] else "N/A",
        out_of_range=out_of_range,
        data_quality_score=score
    )


def print_validation_report(validations: List[MetricBankValidation]):
    """Print comprehensive validation report."""

    print("\n" + "="*100)
    print("DATA INTEGRITY VALIDATION REPORT")
    print("="*100)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*100 + "\n")

    # Group by metric
    metrics = sorted(set(v.metric for v in validations))

    for metric in metrics:
        metric_vals = [v for v in validations if v.metric == metric]
        config = METRICS_CONFIG[metric]

        print(f"\n{'#'*100}")
        print(f"# {config['name']} ({metric})")
        print(f"# Expected Range: {config['expected_range'][0]} - {config['expected_range'][1]} {config['unit']}")
        print(f"{'#'*100}\n")

        # Table header
        print(f"{'Banco':<15} {'Records':<10} {'Non-Null':<10} {'Null%':<8} {'Zero%':<8} {'Min':<10} {'Max':<10} {'Mean':<10} {'Latest':<10} {'Date':<12} {'Score':<6}")
        print("-" * 100)

        for v in sorted(metric_vals, key=lambda x: x.data_quality_score, reverse=True):
            # Color code score
            if v.data_quality_score >= 80:
                score_indicator = "✅"
            elif v.data_quality_score >= 60:
                score_indicator = "🟡"
            elif v.data_quality_score >= 40:
                score_indicator = "🟠"
            else:
                score_indicator = "🔴"

            print(f"{v.bank:<15} {v.total_records:<10} {v.non_null_records:<10} {v.null_pct:<7.1f}% {v.zero_pct:<7.1f}% {v.min_value:<10.2f} {v.max_value:<10.2f} {v.mean_value:<10.2f} {v.latest_value:<10.2f} {v.latest_date:<12} {score_indicator} {v.data_quality_score:.0f}")

        # Summary stats for this metric
        avg_score = sum(v.data_quality_score for v in metric_vals) / len(metric_vals)
        banks_with_data = sum(1 for v in metric_vals if v.non_null_records > 0)
        banks_zero_only = sum(1 for v in metric_vals if v.non_null_records > 0 and v.zero_pct == 100)

        print(f"\nMetric Summary:")
        print(f"  Average Quality Score: {avg_score:.1f}/100")
        print(f"  Banks with Data: {banks_with_data}/{len(metric_vals)}")
        print(f"  Banks with Only Zeros: {banks_zero_only}")

    # Overall summary
    print(f"\n\n{'='*100}")
    print("OVERALL SUMMARY")
    print("="*100 + "\n")

    total_score = sum(v.data_quality_score for v in validations) / len(validations)
    critical_issues = sum(1 for v in validations if v.data_quality_score < 40)
    warnings = sum(1 for v in validations if 40 <= v.data_quality_score < 60)
    good = sum(1 for v in validations if v.data_quality_score >= 80)

    print(f"Overall Data Quality Score: {total_score:.1f}/100\n")
    print(f"Status Breakdown:")
    print(f"  ✅ Good (≥80):        {good}/{len(validations)} ({good/len(validations)*100:.1f}%)")
    print(f"  🟡 Acceptable (60-79): {len(validations) - critical_issues - warnings - good}/{len(validations)}")
    print(f"  🟠 Warning (40-59):    {warnings}/{len(validations)}")
    print(f"  🔴 Critical (<40):     {critical_issues}/{len(validations)}")

    # Action items
    print(f"\n\n{'='*100}")
    print("RECOMMENDED ACTIONS")
    print("="*100 + "\n")

    critical_validations = [v for v in validations if v.data_quality_score < 40]
    if critical_validations:
        print("🔴 CRITICAL: Fix these immediately\n")
        for v in sorted(critical_validations, key=lambda x: x.data_quality_score):
            print(f"  - {v.bank} / {METRICS_CONFIG[v.metric]['name']}: Score {v.data_quality_score:.0f}/100")

            if v.null_pct > 50:
                print(f"    → {v.null_pct:.0f}% NULL values - Check ETL source data")
            if v.zero_pct > 80:
                print(f"    → {v.zero_pct:.0f}% ZERO values - Verify data transformation")
            if v.out_of_range > 0:
                print(f"    → {v.out_of_range} values out of expected range {METRICS_CONFIG[v.metric]['expected_range']}")

            print()

    warning_validations = [v for v in validations if 40 <= v.data_quality_score < 60]
    if warning_validations:
        print("\n🟠 WARNING: Address when possible\n")
        for v in warning_validations[:5]:  # Top 5 warnings
            print(f"  - {v.bank} / {METRICS_CONFIG[v.metric]['name']}: {v.null_pct:.0f}% NULL, {v.zero_pct:.0f}% ZERO")

    # Data freshness check
    print(f"\n\n{'='*100}")
    print("DATA FRESHNESS")
    print("="*100 + "\n")

    for metric in metrics:
        metric_vals = [v for v in validations if v.metric == metric]
        latest_dates = [v.latest_date for v in metric_vals if v.latest_date != "N/A"]

        if latest_dates:
            most_recent = max(latest_dates)
            print(f"{METRICS_CONFIG[metric]['name']:<20} Latest: {most_recent}")


async def main():
    """Main validation routine."""

    print("\n🔍 Connecting to database...")

    try:
        conn = await asyncpg.connect(DATABASE_URL)
        print("✅ Connected\n")

        # Validate all metrics for all banks
        print("🔍 Validating metrics...")
        validations = []

        for metric in METRICS_CONFIG.keys():
            for bank in BANKS:
                validation = await validate_metric_bank(conn, metric, bank)
                validations.append(validation)

        # Print report
        print_validation_report(validations)

        await conn.close()

        # Exit code based on critical issues
        critical_issues = sum(1 for v in validations if v.data_quality_score < 40)
        if critical_issues > 0:
            print(f"\n❌ VALIDATION FAILED: {critical_issues} critical data quality issues")
            sys.exit(1)
        else:
            print("\n✅ VALIDATION PASSED: Data quality acceptable")
            sys.exit(0)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
