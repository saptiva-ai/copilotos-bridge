#!/usr/bin/env python3
"""
Test PostgreSQL Connection Script

Tests connectivity to the new PostgreSQL instance and verifies:
- Database connection
- Schema existence
- Table structure
- Data presence

Usage:
    python scripts/test_postgres_connection.py
"""
import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from core.config import get_settings

logger = structlog.get_logger(__name__)


async def test_connection():
    """Test PostgreSQL connection and database state."""
    settings = get_settings()

    print("=" * 80)
    print("PostgreSQL Connection Test")
    print("=" * 80)
    print(f"\nConnection Details:")
    print(f"  Host: {settings.postgres_host}")
    print(f"  Port: {settings.postgres_port}")
    print(f"  User: {settings.postgres_user}")
    print(f"  Database: {settings.postgres_db}")
    print(f"  URL: {settings.database_url.replace(settings.postgres_password, '***')}")
    print()

    # Create test engine
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True
    )

    try:
        async with engine.begin() as conn:
            # Test 1: Basic connectivity
            print("✓ Test 1: Basic Connectivity")
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"  PostgreSQL Version: {version}\n")

            # Test 2: Check if database exists
            print("✓ Test 2: Database Existence")
            result = await conn.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            print(f"  Current Database: {db_name}\n")

            # Test 3: Check if monthly_kpis table exists
            print("✓ Test 3: Table Structure")
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'monthly_kpis'
                )
            """))
            table_exists = result.scalar()

            if table_exists:
                print("  ✓ Table 'monthly_kpis' exists")

                # Get column info
                result = await conn.execute(text("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = 'monthly_kpis'
                    ORDER BY ordinal_position
                """))
                columns = result.fetchall()
                print(f"  ✓ Columns: {len(columns)}")
                for col_name, col_type in columns[:5]:  # Show first 5
                    print(f"    - {col_name}: {col_type}")
                if len(columns) > 5:
                    print(f"    ... and {len(columns) - 5} more columns")
            else:
                print("  ✗ Table 'monthly_kpis' does NOT exist")
                print("  → Run migrations: python -m bankadvisor.db or start the server")

            print()

            # Test 4: Check data presence
            print("✓ Test 4: Data Presence")
            if table_exists:
                result = await conn.execute(text("""
                    SELECT
                        COUNT(*) as total_rows,
                        COUNT(DISTINCT banco_norm) as banks,
                        MIN(fecha) as earliest_date,
                        MAX(fecha) as latest_date
                    FROM monthly_kpis
                """))
                row = result.fetchone()

                if row[0] > 0:
                    print(f"  ✓ Total rows: {row[0]:,}")
                    print(f"  ✓ Unique banks: {row[1]}")
                    print(f"  ✓ Date range: {row[2]} to {row[3]}")
                else:
                    print("  ✗ Table is EMPTY")
                    print("  → Run ETL: python -m bankadvisor.etl_loader")
            else:
                print("  ⊘ Skipped (table doesn't exist)")

            print()

            # Test 5: Check ETL runs table
            print("✓ Test 5: ETL Run History")
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'etl_runs'
                )
            """))
            etl_table_exists = result.scalar()

            if etl_table_exists:
                result = await conn.execute(text("""
                    SELECT
                        COUNT(*) as total_runs,
                        MAX(completed_at) as last_run,
                        COUNT(*) FILTER (WHERE status = 'success') as successful
                    FROM etl_runs
                """))
                row = result.fetchone()

                if row[0] > 0:
                    print(f"  ✓ Total ETL runs: {row[0]}")
                    print(f"  ✓ Successful runs: {row[2]}")
                    print(f"  ✓ Last run: {row[1] or 'Never'}")
                else:
                    print("  ✗ No ETL runs recorded")
            else:
                print("  ⊘ ETL runs table doesn't exist (will be created on first run)")

            print()

            # Test 6: Query performance test
            print("✓ Test 6: Query Performance")
            if table_exists and row[0] > 0:
                import time
                start = time.time()
                result = await conn.execute(text("""
                    SELECT banco_norm, AVG(cartera_total)
                    FROM monthly_kpis
                    WHERE fecha >= NOW() - INTERVAL '12 months'
                    GROUP BY banco_norm
                    LIMIT 5
                """))
                rows = result.fetchall()
                elapsed = (time.time() - start) * 1000

                print(f"  ✓ Sample query executed in {elapsed:.1f}ms")
                print(f"  ✓ Sample results: {len(rows)} banks")
            else:
                print("  ⊘ Skipped (no data)")

            print()

        print("=" * 80)
        print("✓ All tests completed successfully!")
        print("=" * 80)
        print("\nNext steps:")

        if not table_exists:
            print("  1. Run migrations to create tables")
            print("     → Start the server or run: python -m bankadvisor.db")

        if table_exists and row[0] == 0:
            print("  2. Load data with ETL")
            print("     → python -m bankadvisor.etl_loader")

        if table_exists and row[0] > 0:
            print("  ✓ Database is ready for use!")
            print("  ✓ Start the server: python -m src.main")

        return True

    except Exception as e:
        print("\n" + "=" * 80)
        print("✗ Connection Test FAILED")
        print("=" * 80)
        print(f"\nError: {e}")
        print(f"Error Type: {type(e).__name__}")

        print("\nTroubleshooting:")
        print("  1. Check if PostgreSQL is running")
        print("  2. Verify credentials in .env file")
        print("  3. Check network connectivity to host")
        print("  4. Ensure database 'bankadvisor' exists")
        print("  5. Verify user has proper permissions")

        return False

    finally:
        await engine.dispose()


if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)
