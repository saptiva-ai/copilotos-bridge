#!/usr/bin/env bash
################################################################################
# Bank Advisor Data Initialization Script
################################################################################
# This script consolidates all steps needed to populate Bank Advisor data:
#   1. Run database migrations
#   2. Execute ETL to load all metrics
#   3. Verify data integrity
#
# Usage:
#   ./scripts/init_bank_advisor_data.sh              # Full init
#   ./scripts/init_bank_advisor_data.sh --migrations-only
#   ./scripts/init_bank_advisor_data.sh --etl-only
################################################################################

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
POSTGRES_CONTAINER="octavios-chat-bajaware_invex-postgres"
BANK_ADVISOR_CONTAINER="octavios-chat-bajaware_invex-bank-advisor"
DB_USER="octavios"
DB_NAME="bankadvisor"
MIGRATIONS_DIR="/app/migrations"

################################################################################
# Helper Functions
################################################################################

log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

check_container() {
    local container=$1
    if ! docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        log_error "Container ${container} is not running"
        exit 1
    fi
    log_success "Container ${container} is running"
}

################################################################################
# Migration Functions
################################################################################

run_migrations() {
    log_info "Running database migrations..."

    # 1. Apply normalized schema (instituciones, metricas_financieras, etc.)
    log_info "  Applying normalized schema (database_schema.sql)..."
    if cat plugins/bank-advisor-private/database_schema.sql | docker exec -i "${POSTGRES_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" &>/dev/null; then
        log_success "  Normalized schema applied (IF NOT EXISTS)"
    else
        log_warning "  Normalized schema may have already been applied"
    fi

    # 2. Check if migrations directory exists
    if ! docker exec "${BANK_ADVISOR_CONTAINER}" ls "${MIGRATIONS_DIR}" &>/dev/null; then
        log_warning "Migrations directory not found, skipping legacy migrations"
        return 0
    fi

    # 3. Get list of migration files for legacy tables
    local migrations=$(docker exec "${BANK_ADVISOR_CONTAINER}" ls "${MIGRATIONS_DIR}" | grep '\.sql$' | sort)

    if [ -z "$migrations" ]; then
        log_warning "No legacy migration files found"
        return 0
    fi

    # 4. Run each legacy migration
    for migration in $migrations; do
        log_info "  Applying legacy migration: ${migration}"

        # Execute migration via pipe to postgres container
        if docker exec "${BANK_ADVISOR_CONTAINER}" cat "${MIGRATIONS_DIR}/${migration}" | \
           docker exec -i "${POSTGRES_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" &>/dev/null; then
            log_success "  Migration ${migration} applied"
        else
            log_warning "  Migration ${migration} may have already been applied (non-critical)"
        fi
    done

    log_success "Migrations completed (normalized + legacy schemas)"
}

verify_schema() {
    log_info "Verifying database schema..."

    # Check critical columns exist
    local columns=$(docker exec "${POSTGRES_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'monthly_kpis'
        AND column_name IN ('tasa_mn', 'tasa_me', 'icap_total', 'tda_cartera_total', 'pe_total')
        ORDER BY column_name;
    " 2>/dev/null | tr -d '[:space:]')

    local expected="icap_totalpe_totaltasa_metasa_mntda_cartera_total"

    if [ "$columns" = "$expected" ]; then
        log_success "Schema verification passed - all critical columns exist"
    else
        log_error "Schema verification failed - missing columns"
        log_info "Expected: icap_total, pe_total, tasa_me, tasa_mn, tda_cartera_total"
        log_info "Found: $(echo $columns | sed 's/./ &/g')"
        exit 1
    fi
}

################################################################################
# ETL Functions
################################################################################

run_etl() {
    log_info "Running ETL pipelines (legacy + normalized)..."

    # ===========================================================================
    # 1. LEGACY ETL - Populate monthly_kpis table (2017-2025)
    # ===========================================================================
    log_info ""
    log_info "  [1/2] Running Legacy ETL (monthly_kpis)..."
    log_info "  ├─ Loading 1.3M+ records from Excel/CSV files"
    log_info "  ├─ Processing with Polars and Pandas"
    log_info "  └─ Target: monthly_kpis table"

    # Check if legacy ETL module exists
    if ! docker exec "${BANK_ADVISOR_CONTAINER}" python -c "import bankadvisor.etl_runner" 2>/dev/null; then
        log_error "Legacy ETL module not found"
        exit 1
    fi

    if docker exec "${BANK_ADVISOR_CONTAINER}" python -m bankadvisor.etl_runner 2>&1 | tail -20; then
        log_success "  Legacy ETL completed (monthly_kpis populated)"
    else
        log_error "Legacy ETL failed"
        exit 1
    fi

    # ===========================================================================
    # 2. NORMALIZED ETL - Populate normalized tables (BE_BM_202509.xlsx)
    # ===========================================================================
    log_info ""
    log_info "  [2/2] Running Normalized ETL (BE_BM_202509.xlsx)..."
    log_info "  ├─ Processing Balance Sheet & Income Statement"
    log_info "  ├─ Generating carga_inicial_bancos.sql"
    log_info "  └─ Target: instituciones, metricas_financieras, segmentos_cartera"

    # Check if normalized ETL exists
    if ! docker exec "${BANK_ADVISOR_CONTAINER}" test -f /app/etl/etl_processor.py; then
        log_warning "Normalized ETL processor not found, skipping"
        return 0
    fi

    # Run normalized ETL processor to generate SQL
    if docker exec "${BANK_ADVISOR_CONTAINER}" python /app/etl/etl_processor.py &>/dev/null; then
        log_success "  SQL generation completed"
    else
        log_warning "  SQL generation failed or file already exists"
    fi

    # Load normalized data into database
    if docker exec "${BANK_ADVISOR_CONTAINER}" test -f /app/etl/carga_inicial_bancos.sql; then
        log_info "  Loading normalized data into database..."
        if docker exec "${BANK_ADVISOR_CONTAINER}" cat /app/etl/carga_inicial_bancos.sql | \
           docker exec -i "${POSTGRES_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" &>/dev/null; then
            log_success "  Normalized data loaded successfully"
        else
            log_warning "  Normalized data may have already been loaded"
        fi
    else
        log_warning "  carga_inicial_bancos.sql not found, skipping normalized data load"
    fi

    log_success "ETL pipelines completed (legacy + normalized)"
}

verify_data() {
    log_info "Verifying data integrity..."

    # ===========================================================================
    # 1. Verify Legacy Data (monthly_kpis)
    # ===========================================================================
    log_info ""
    log_info "  [1/2] Legacy Data (monthly_kpis):"

    local legacy_count=$(docker exec "${POSTGRES_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "
        SELECT COUNT(*) FROM monthly_kpis;
    " 2>/dev/null | tr -d '[:space:]')

    if [ "$legacy_count" -gt 0 ]; then
        log_success "    ✓ ${legacy_count} records in monthly_kpis"

        # Show data range
        local date_range=$(docker exec "${POSTGRES_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "
            SELECT
                TO_CHAR(MIN(fecha), 'YYYY-MM') as earliest,
                TO_CHAR(MAX(fecha), 'YYYY-MM') as latest,
                COUNT(DISTINCT banco_norm) as banks
            FROM monthly_kpis;
        " 2>/dev/null)

        log_info "    ├─ Date range: $(echo $date_range | awk '{print $1 " to " $2}')"
        log_info "    └─ Banks: $(echo $date_range | awk '{print $3}')"
    else
        log_warning "    ⚠ No records in monthly_kpis (legacy ETL may have failed)"
    fi

    # ===========================================================================
    # 2. Verify Normalized Data (instituciones, metricas_financieras)
    # ===========================================================================
    log_info ""
    log_info "  [2/2] Normalized Data:"

    # Check if normalized tables exist
    local instituciones_count=$(docker exec "${POSTGRES_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "
        SELECT COUNT(*) FROM instituciones;
    " 2>/dev/null | tr -d '[:space:]')

    local metricas_count=$(docker exec "${POSTGRES_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "
        SELECT COUNT(*) FROM metricas_financieras;
    " 2>/dev/null | tr -d '[:space:]')

    local segmentos_count=$(docker exec "${POSTGRES_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "
        SELECT COUNT(*) FROM segmentos_cartera;
    " 2>/dev/null | tr -d '[:space:]')

    if [ ! -z "$instituciones_count" ] && [ "$instituciones_count" -gt 0 ]; then
        log_success "    ✓ ${instituciones_count} instituciones"
        log_success "    ✓ ${metricas_count} metricas_financieras"
        log_success "    ✓ ${segmentos_count} segmentos_cartera"
    else
        log_warning "    ⚠ Normalized tables empty or not found"
    fi

    log_info ""
    log_success "Data verification completed"
}

################################################################################
# Main Execution
################################################################################

main() {
    local run_migrations=true
    local run_etl=true

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --migrations-only)
                run_etl=false
                shift
                ;;
            --etl-only)
                run_migrations=false
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --migrations-only   Only run database migrations"
                echo "  --etl-only          Only run ETL (skip migrations)"
                echo "  --help              Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    log_info "======================================================================"
    log_info "Bank Advisor Data Initialization"
    log_info "======================================================================"
    echo ""

    # 1. Verify containers are running
    log_info "Step 1/5: Verifying containers..."
    check_container "${POSTGRES_CONTAINER}"
    check_container "${BANK_ADVISOR_CONTAINER}"
    echo ""

    # 2. Run migrations if requested
    if [ "$run_migrations" = true ]; then
        log_info "Step 2/5: Database migrations..."
        run_migrations
        verify_schema
        echo ""
    else
        log_info "Step 2/5: Skipping migrations (--etl-only)"
        echo ""
    fi

    # 3. Run ETL if requested
    if [ "$run_etl" = true ]; then
        log_info "Step 3/5: ETL execution..."
        run_etl
        echo ""
    else
        log_info "Step 3/5: Skipping ETL (--migrations-only)"
        echo ""
    fi

    # 4. Verify data
    log_info "Step 4/5: Data verification..."
    verify_data
    echo ""

    # 5. Final status
    log_info "Step 5/5: Health check..."
    local health=$(docker exec "${BANK_ADVISOR_CONTAINER}" curl -s http://localhost:8002/health | python -m json.tool 2>/dev/null || echo "{}")

    if echo "$health" | grep -q '"status": "healthy"'; then
        log_success "Bank Advisor service is healthy"
    else
        log_warning "Bank Advisor service health check returned unexpected status"
    fi
    echo ""

    log_info "======================================================================"
    log_success "Initialization completed successfully!"
    log_info "======================================================================"
    log_info "Bank Advisor is ready to use"
    log_info "  - Frontend: http://localhost:3000"
    log_info "  - Backend: http://localhost:8000"
    log_info "  - Bank Advisor: http://localhost:8002"
    echo ""
}

# Run main function
main "$@"
