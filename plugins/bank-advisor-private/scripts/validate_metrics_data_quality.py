#!/usr/bin/env python3
"""
Data Quality Validation for ICAP/TDA/TASA Metrics
Validates and reports on nullable metrics in monthly_kpis table.

Usage:
    python scripts/validate_metrics_data_quality.py

Validates:
- icap_total (ICAP - Índice de Capitalización)
- tda_cartera_total (TDA - Tasa de Deterioro Ajustada)
- tasa_mn (Tasa Corporativo Moneda Nacional)
- tasa_me (Tasa Corporativo Moneda Extranjera)
"""

import os
import sys
from datetime import datetime
from typing import Dict, List, Any
import asyncio
import asyncpg
from dataclasses import dataclass

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://octavios:secure_postgres_password@localhost:5432/bankadvisor")


@dataclass
class MetricValidation:
    metric_name: str
    total_records: int
    non_null_records: int
    null_records: int
    null_percentage: float
    min_value: float
    max_value: float
    mean_value: float
    banks_with_data: List[str]
    banks_missing_data: List[str]
    date_range_start: datetime
    date_range_end: datetime
    data_gaps: List[str]  # Months with no data


async def validate_metric(conn: asyncpg.Connection, metric_name: str) -> MetricValidation:
    """Validate a single metric for data quality."""

    # Basic stats
    stats_query = f"""
    SELECT
        COUNT(*) as total,
        COUNT({metric_name}) as non_null,
        COUNT(*) - COUNT({metric_name}) as nulls,
        (COUNT(*) - COUNT({metric_name}))::float / COUNT(*) * 100 as null_pct,
        MIN({metric_name}) as min_val,
        MAX({metric_name}) as max_val,
        AVG({metric_name}) as mean_val,
        MIN(fecha) as date_start,
        MAX(fecha) as date_end
    FROM monthly_kpis
    WHERE banco_norm IN ('INVEX', 'SISTEMA', 'BBVA', 'SANTANDER', 'BANORTE', 'HSBC', 'CITIBANAMEX')
    """

    row = await conn.fetchrow(stats_query)

    # Banks with data
    banks_query = f"""
    SELECT DISTINCT banco_norm
    FROM monthly_kpis
    WHERE {metric_name} IS NOT NULL
    ORDER BY banco_norm
    """
    banks_with_data = [r['banco_norm'] for r in await conn.fetch(banks_query)]

    # Banks missing data
    all_banks_query = """
    SELECT DISTINCT banco_norm
    FROM monthly_kpis
    WHERE banco_norm IN ('INVEX', 'SISTEMA', 'BBVA', 'SANTANDER', 'BANORTE', 'HSBC', 'CITIBANAMEX')
    ORDER BY banco_norm
    """
    all_banks = [r['banco_norm'] for r in await conn.fetch(all_banks_query)]
    banks_missing_data = [b for b in all_banks if b not in banks_with_data]

    # Data gaps (months with no data for any bank)
    gaps_query = f"""
    WITH all_months AS (
        SELECT DISTINCT DATE_TRUNC('month', fecha) as month
        FROM monthly_kpis
        WHERE fecha >= '2020-01-01'
    )
    SELECT TO_CHAR(month, 'YYYY-MM') as month_label
    FROM all_months
    WHERE month NOT IN (
        SELECT DISTINCT DATE_TRUNC('month', fecha)
        FROM monthly_kpis
        WHERE {metric_name} IS NOT NULL
    )
    ORDER BY month_label
    """
    data_gaps = [r['month_label'] for r in await conn.fetch(gaps_query)]

    return MetricValidation(
        metric_name=metric_name,
        total_records=row['total'],
        non_null_records=row['non_null'],
        null_records=row['nulls'],
        null_percentage=row['null_pct'],
        min_value=row['min_val'] if row['min_val'] is not None else 0,
        max_value=row['max_val'] if row['max_val'] is not None else 0,
        mean_value=row['mean_val'] if row['mean_val'] is not None else 0,
        banks_with_data=banks_with_data,
        banks_missing_data=banks_missing_data,
        date_range_start=row['date_start'],
        date_range_end=row['date_end'],
        data_gaps=data_gaps
    )


def print_validation_report(validations: List[MetricValidation]):
    """Print formatted validation report."""

    print("\n" + "="*80)
    print("MÉTRICAS DATA QUALITY VALIDATION REPORT")
    print("="*80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'local'}")
    print("="*80 + "\n")

    for v in validations:
        print(f"📊 {v.metric_name.upper()}")
        print("-" * 80)

        # Coverage stats
        print(f"Coverage:")
        print(f"  Total records:    {v.total_records}")
        print(f"  Non-null:         {v.non_null_records} ({100-v.null_percentage:.1f}%)")
        print(f"  Null:             {v.null_records} ({v.null_percentage:.1f}%)")

        # Quality assessment
        if v.null_percentage > 70:
            status = "🔴 CRITICAL"
        elif v.null_percentage > 40:
            status = "🟡 WARNING"
        elif v.null_percentage > 10:
            status = "🟢 ACCEPTABLE"
        else:
            status = "✅ GOOD"
        print(f"  Status:           {status}")

        # Value ranges
        if v.non_null_records > 0:
            print(f"\nValue Range:")
            print(f"  Min:              {v.min_value:.2f}")
            print(f"  Max:              {v.max_value:.2f}")
            print(f"  Mean:             {v.mean_value:.2f}")

        # Bank coverage
        print(f"\nBank Coverage:")
        print(f"  Banks with data:  {len(v.banks_with_data)}/{len(v.banks_with_data) + len(v.banks_missing_data)}")
        if v.banks_with_data:
            print(f"    → {', '.join(v.banks_with_data)}")
        if v.banks_missing_data:
            print(f"  Banks missing:    {', '.join(v.banks_missing_data)}")

        # Date range
        print(f"\nDate Range:")
        print(f"  Start:            {v.date_range_start.strftime('%Y-%m')}")
        print(f"  End:              {v.date_range_end.strftime('%Y-%m')}")

        # Data gaps
        if v.data_gaps:
            gap_count = len(v.data_gaps)
            print(f"  Data gaps:        {gap_count} months")
            if gap_count <= 10:
                print(f"    → {', '.join(v.data_gaps)}")
            else:
                print(f"    → {', '.join(v.data_gaps[:5])} ... (+{gap_count-5} more)")
        else:
            print(f"  Data gaps:        None ✅")

        print("\n")

    # Summary recommendations
    print("="*80)
    print("RECOMMENDATIONS")
    print("="*80)

    for v in validations:
        if v.null_percentage > 50:
            print(f"\n🔴 {v.metric_name}:")
            print(f"   - {v.null_percentage:.1f}% nulls is too high for production queries")
            print(f"   - Consider: Forward-fill from previous month or mark as 'Data Not Available'")
            print(f"   - Queries will return incomplete results")
        elif v.null_percentage > 20:
            print(f"\n🟡 {v.metric_name}:")
            print(f"   - {v.null_percentage:.1f}% nulls acceptable but should be documented")
            print(f"   - Add warning to user: 'Data available for {100-v.null_percentage:.0f}% of records'")

        if v.banks_missing_data:
            print(f"\n⚠️  {v.metric_name}: Missing data for {len(v.banks_missing_data)} banks")
            print(f"   - Banks: {', '.join(v.banks_missing_data)}")
            print(f"   - Action: Verify if these banks report this metric to CNBV")

    print("\n" + "="*80)


async def test_queries(conn: asyncpg.Connection):
    """Test actual queries that users might run."""

    print("\n" + "="*80)
    print("QUERY TESTING")
    print("="*80 + "\n")

    test_cases = [
        {
            "name": "ICAP de INVEX 2024",
            "sql": """
                SELECT fecha, banco_norm, icap_total
                FROM monthly_kpis
                WHERE banco_norm = 'INVEX'
                  AND fecha >= '2024-01-01'
                  AND icap_total IS NOT NULL
                ORDER BY fecha DESC
                LIMIT 12
            """
        },
        {
            "name": "TDA de INVEX vs SISTEMA 2024",
            "sql": """
                SELECT fecha, banco_norm, tda_cartera_total
                FROM monthly_kpis
                WHERE banco_norm IN ('INVEX', 'SISTEMA')
                  AND fecha >= '2024-01-01'
                  AND tda_cartera_total IS NOT NULL
                ORDER BY fecha DESC, banco_norm
            """
        },
        {
            "name": "TASA_MN últimos 12 meses",
            "sql": """
                SELECT fecha, banco_norm, tasa_mn
                FROM monthly_kpis
                WHERE banco_norm = 'INVEX'
                  AND fecha >= CURRENT_DATE - INTERVAL '12 months'
                  AND tasa_mn IS NOT NULL
                ORDER BY fecha DESC
            """
        },
        {
            "name": "TASA_ME últimos 12 meses",
            "sql": """
                SELECT fecha, banco_norm, tasa_me
                FROM monthly_kpis
                WHERE banco_norm = 'INVEX'
                  AND fecha >= CURRENT_DATE - INTERVAL '12 months'
                  AND tasa_me IS NOT NULL
                ORDER BY fecha DESC
            """
        }
    ]

    for test in test_cases:
        print(f"🧪 Test: {test['name']}")
        rows = await conn.fetch(test['sql'])

        if rows:
            print(f"   ✅ Returned {len(rows)} rows")
            # Show first 3 rows
            for i, row in enumerate(rows[:3], 1):
                fecha = row['fecha'].strftime('%Y-%m')
                banco = row['banco_norm']
                metric_name = [k for k in row.keys() if k not in ['fecha', 'banco_norm']][0]
                value = row[metric_name]
                print(f"      {i}. {fecha} - {banco}: {value:.2f}")
            if len(rows) > 3:
                print(f"      ... (+{len(rows)-3} more rows)")
        else:
            print(f"   ❌ No data returned - metric likely has too many nulls")

        print()


async def main():
    """Main validation routine."""

    print("\n🔍 Connecting to database...")

    try:
        conn = await asyncpg.connect(DATABASE_URL)
        print("✅ Connected\n")

        # Validate each metric
        metrics_to_validate = [
            'icap_total',
            'tda_cartera_total',
            'tasa_mn',
            'tasa_me'
        ]

        print("🔍 Validating metrics...")
        validations = []
        for metric in metrics_to_validate:
            validation = await validate_metric(conn, metric)
            validations.append(validation)

        # Print report
        print_validation_report(validations)

        # Test queries
        await test_queries(conn)

        await conn.close()

        # Exit code based on critical issues
        critical_issues = sum(1 for v in validations if v.null_percentage > 70)
        if critical_issues > 0:
            print(f"\n❌ VALIDATION FAILED: {critical_issues} metrics have critical data quality issues")
            sys.exit(1)
        else:
            print("\n✅ VALIDATION PASSED: All metrics have acceptable data quality")
            sys.exit(0)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
