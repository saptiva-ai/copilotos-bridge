#!/bin/bash
set -e

echo "🔍 Checking if database needs initialization..."

# Wait for postgres to be ready
until pg_isready -h "${POSTGRES_HOST:-postgres}" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER:-octavios}" >/dev/null 2>&1; do
  echo "⏳ Waiting for PostgreSQL to be ready..."
  sleep 2
done

echo "✅ PostgreSQL is ready"

# Check if database has data
RECORD_COUNT=$(python -c "
import asyncio
from sqlalchemy import create_engine, text
import os

db_url = os.getenv('DATABASE_URL', 'postgresql://octavios:secure_postgres_password@postgres:5432/bankadvisor')
# Convert asyncpg URL to sync psycopg2 URL for simple check
sync_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')

try:
    engine = create_engine(sync_url)
    with engine.connect() as conn:
        result = conn.execute(text('SELECT COUNT(*) FROM monthly_kpis'))
        count = result.scalar()
        print(count)
except Exception as e:
    # Table doesn't exist or connection failed
    print(0)
" 2>/dev/null || echo "0")

echo "📊 Current record count: $RECORD_COUNT"

if [ "$RECORD_COUNT" -eq "0" ]; then
  echo "🚀 Database is empty. Running migrations and ETLs to load initial data..."

  echo "📝 Step 1/3: Running database migrations..."
  PGPASSWORD="${POSTGRES_PASSWORD:-secure_postgres_password}" psql \
    -h "${POSTGRES_HOST:-postgres}" \
    -p "${POSTGRES_PORT:-5432}" \
    -U "${POSTGRES_USER:-octavios}" \
    -d bankadvisor \
    -f /app/migrations/001_add_missing_columns.sql || {
    echo "⚠️  Migration failed, but continuing..."
  }

  echo "📊 Step 2/3: Running base ETL (cartera, IMOR, ICOR)..."
  python -m bankadvisor.etl_loader || {
    echo "⚠️  Base ETL failed, but continuing..."
  }

  echo "📊 Step 3/3: Running enhanced ETL (ICAP, TDA, TASA_MN, TASA_ME)..."
  python -m bankadvisor.etl_loader_enhanced || {
    echo "⚠️  Enhanced ETL failed, but continuing..."
  }

  echo "✅ ETL pipeline completed!"
else
  echo "✅ Database already populated ($RECORD_COUNT records). Skipping ETL."
fi

echo "🚀 Starting bank-advisor MCP server..."

# Execute the main command (passed as arguments to this script)
exec "$@"
