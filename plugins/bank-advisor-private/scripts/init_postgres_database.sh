#!/bin/bash
################################################################################
# PostgreSQL Database Initialization Script
#
# Creates the bankadvisor database and runs all migrations.
#
# Usage:
#   ./scripts/init_postgres_database.sh
#
# Prerequisites:
#   - PostgreSQL credentials in .env file
#   - psql command available
#   - Network access to PostgreSQL server
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  PostgreSQL Database Initialization${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Load environment variables
if [ -f .env ]; then
    echo -e "${GREEN}✓${NC} Loading .env file..."
    export $(grep -v '^#' .env | xargs)
else
    echo -e "${RED}✗${NC} .env file not found!"
    exit 1
fi

# Check required variables
if [ -z "$POSTGRES_HOST" ] || [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_PASSWORD" ] || [ -z "$POSTGRES_DB" ]; then
    echo -e "${RED}✗${NC} Missing required environment variables!"
    echo "Required: POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB"
    exit 1
fi

echo -e "${BLUE}Connection Details:${NC}"
echo "  Host: $POSTGRES_HOST"
echo "  Port: ${POSTGRES_PORT:-5432}"
echo "  User: $POSTGRES_USER"
echo "  Database: $POSTGRES_DB"
echo ""

# Export PGPASSWORD to avoid password prompts
export PGPASSWORD="$POSTGRES_PASSWORD"

# Step 1: Test connectivity to postgres database (default)
echo -e "${YELLOW}→${NC} Step 1: Testing connection to PostgreSQL server..."
if psql -h "$POSTGRES_HOST" -p "${POSTGRES_PORT:-5432}" -U "$POSTGRES_USER" -d postgres -c "SELECT version();" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Connected successfully"
else
    echo -e "${RED}✗${NC} Failed to connect to PostgreSQL server"
    echo "  Please verify:"
    echo "  - PostgreSQL is running"
    echo "  - Credentials are correct"
    echo "  - Network connectivity"
    echo "  - Firewall allows connection"
    exit 1
fi

# Step 2: Check if database exists
echo ""
echo -e "${YELLOW}→${NC} Step 2: Checking if database '$POSTGRES_DB' exists..."
DB_EXISTS=$(psql -h "$POSTGRES_HOST" -p "${POSTGRES_PORT:-5432}" -U "$POSTGRES_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$POSTGRES_DB'")

if [ "$DB_EXISTS" = "1" ]; then
    echo -e "${YELLOW}⚠${NC}  Database '$POSTGRES_DB' already exists"
    read -p "  Do you want to drop and recreate it? (yes/no): " -r
    echo
    if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo -e "${YELLOW}→${NC} Dropping existing database..."
        psql -h "$POSTGRES_HOST" -p "${POSTGRES_PORT:-5432}" -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS $POSTGRES_DB;"
        echo -e "${GREEN}✓${NC} Database dropped"

        echo -e "${YELLOW}→${NC} Creating database '$POSTGRES_DB'..."
        psql -h "$POSTGRES_HOST" -p "${POSTGRES_PORT:-5432}" -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE $POSTGRES_DB;"
        echo -e "${GREEN}✓${NC} Database created"
    else
        echo -e "${BLUE}→${NC} Skipping database creation, will use existing database"
    fi
else
    echo -e "${YELLOW}→${NC} Creating database '$POSTGRES_DB'..."
    psql -h "$POSTGRES_HOST" -p "${POSTGRES_PORT:-5432}" -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE $POSTGRES_DB;"
    echo -e "${GREEN}✓${NC} Database created"
fi

# Step 3: Run migrations
echo ""
echo -e "${YELLOW}→${NC} Step 3: Running migrations..."

MIGRATIONS_DIR="migrations"
if [ ! -d "$MIGRATIONS_DIR" ]; then
    echo -e "${RED}✗${NC} Migrations directory not found: $MIGRATIONS_DIR"
    exit 1
fi

# Get all .sql files in order
MIGRATION_FILES=$(ls -1 $MIGRATIONS_DIR/*.sql 2>/dev/null | sort)

if [ -z "$MIGRATION_FILES" ]; then
    echo -e "${YELLOW}⚠${NC}  No migration files found in $MIGRATIONS_DIR"
else
    for migration in $MIGRATION_FILES; do
        filename=$(basename "$migration")
        echo -e "${BLUE}  →${NC} Applying $filename..."

        if psql -h "$POSTGRES_HOST" -p "${POSTGRES_PORT:-5432}" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$migration" > /dev/null 2>&1; then
            echo -e "${GREEN}    ✓${NC} $filename applied"
        else
            echo -e "${RED}    ✗${NC} Failed to apply $filename"
            echo "    Review the migration file and database logs"
            exit 1
        fi
    done
    echo -e "${GREEN}✓${NC} All migrations applied successfully"
fi

# Step 4: Verify tables
echo ""
echo -e "${YELLOW}→${NC} Step 4: Verifying database schema..."

TABLES=$(psql -h "$POSTGRES_HOST" -p "${POSTGRES_PORT:-5432}" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "
    SELECT COUNT(*)
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_type = 'BASE TABLE'
")

echo -e "${GREEN}✓${NC} Found $TABLES tables in database"

# List main tables
echo ""
echo -e "${BLUE}Main Tables:${NC}"
psql -h "$POSTGRES_HOST" -p "${POSTGRES_PORT:-5432}" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
    SELECT
        schemaname as schema,
        tablename as table_name,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
    FROM pg_tables
    WHERE schemaname = 'public'
    ORDER BY tablename;
"

# Step 5: Summary
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Database initialization completed successfully!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Load data with ETL:"
echo "     → python -m bankadvisor.etl_loader"
echo ""
echo "  2. Start the BankAdvisor server:"
echo "     → python -m src.main"
echo ""
echo "  3. Test the connection:"
echo "     → python scripts/test_postgres_connection.py"
echo ""

# Cleanup
unset PGPASSWORD
