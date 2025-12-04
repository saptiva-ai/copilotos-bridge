#!/usr/bin/env python3
"""Apply migration 004: query_logs for RAG feedback loop."""
import asyncio
import asyncpg
from pathlib import Path

DATABASE_URL = "postgresql://octavios:secure_postgres_password@localhost:5432/bankadvisor"

async def apply_migration():
    """Apply migration and verify."""
    conn = await asyncpg.connect(DATABASE_URL)

    migration_file = Path(__file__).parent.parent / "migrations" / "004_query_logs_rag_feedback.sql"

    with open(migration_file, 'r') as f:
        migration_sql = f.read()

    try:
        # Apply migration
        await conn.execute(migration_sql)
        print('✅ Migration 004 applied successfully')
        print()

        # Verify table created
        table_exists = await conn.fetchval(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'query_logs'"
        )

        if table_exists > 0:
            print('✅ Table query_logs created')

            # Test insert with trigger
            test_id = await conn.fetchval("""
                INSERT INTO query_logs (
                    user_query, generated_sql, banco, metric, intent,
                    execution_time_ms, success, pipeline_used
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING query_id
            """,
                'IMOR de INVEX en 2024',
                "SELECT fecha, imor FROM monthly_kpis WHERE banco_norm = 'INVEX'",
                'INVEX',
                'IMOR',
                'metric_query',
                150.5,
                True,
                'nl2sql'
            )
            print(f'✅ Test record inserted: {test_id}')

            # Check auto-calculated confidence
            confidence = await conn.fetchval(
                "SELECT rag_confidence FROM query_logs WHERE query_id = $1",
                test_id
            )
            print(f'✅ RAG confidence auto-calculated: {confidence:.3f}')

            # Check view
            candidates = await conn.fetchval("SELECT COUNT(*) FROM rag_feedback_candidates")
            print(f'✅ View rag_feedback_candidates: {candidates} candidates')

            # Check indexes
            indexes = await conn.fetch(
                "SELECT indexname FROM pg_indexes WHERE tablename = 'query_logs' ORDER BY indexname"
            )
            print(f'✅ {len(indexes)} indexes created')

            print()
            print('🎉 Migration complete! Ready for QueryLoggerService implementation.')

        else:
            print('❌ Table query_logs not found')

    except Exception as e:
        print(f'❌ Migration failed: {e}')
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(apply_migration())
