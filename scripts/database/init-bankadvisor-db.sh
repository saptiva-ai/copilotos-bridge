#!/bin/bash
set -e

# ============================================================================
# BANK ADVISOR - DATABASE INITIALIZATION & ETL SCRIPT
# ============================================================================
# Este script:
# 1. Crea todas las tablas necesarias (monthly_kpis, etl_runs)
# 2. Instala dependencias faltantes en el contenedor
# 3. Ejecuta el ETL completo para poblar datos
# ============================================================================

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     Bank Advisor - Inicialización de Base de Datos         ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# ============================================================================
# PRE-CHECKS
# ============================================================================

echo "🔍 Verificando pre-requisitos..."

# Check if we're in the right directory
if [ ! -f "infra/docker-compose.yml" ]; then
    log_error "No se encuentra infra/docker-compose.yml"
    echo "Ejecuta este script desde el directorio raíz del proyecto"
    exit 1
fi

# Detect docker compose command
if docker compose version > /dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# Check if bank-advisor container is running
if ! $DOCKER_COMPOSE -f infra/docker-compose.yml ps bank-advisor | grep -q "Up"; then
    log_error "Contenedor bank-advisor no está corriendo"
    echo "Inicia los servicios con: $DOCKER_COMPOSE -f infra/docker-compose.yml up -d"
    exit 1
fi

# Check if postgres container is running
if ! $DOCKER_COMPOSE -f infra/docker-compose.yml ps postgres | grep -q "Up"; then
    log_error "Contenedor postgres no está corriendo"
    echo "Inicia los servicios con: $DOCKER_COMPOSE -f infra/docker-compose.yml up -d"
    exit 1
fi

log_success "Pre-checks completados"
echo ""

# ============================================================================
# CREAR TABLAS DE BASE DE DATOS
# ============================================================================

echo "🗄️  Creando tablas de base de datos..."

$DOCKER_COMPOSE -f infra/docker-compose.yml exec -T postgres psql -U octavios -d bankadvisor <<EOF
-- Tabla principal de KPIs mensuales
CREATE TABLE IF NOT EXISTS monthly_kpis (
    id SERIAL PRIMARY KEY,
    fecha TIMESTAMP,
    institucion VARCHAR(100),
    banco_norm VARCHAR(100),
    cartera_total NUMERIC,
    cartera_comercial_total NUMERIC,
    cartera_consumo_total NUMERIC,
    cartera_vivienda_total NUMERIC,
    entidades_gubernamentales_total NUMERIC,
    entidades_financieras_total NUMERIC,
    empresarial_total NUMERIC,
    cartera_vencida NUMERIC,
    imor NUMERIC,
    icor NUMERIC,
    reservas_etapa_todas NUMERIC,
    -- Campos adicionales del ETL enhanced
    icap_total NUMERIC,
    tda_cartera_total NUMERIC,
    tda_cartera_vencida NUMERIC,
    tda_vigente_total NUMERIC,
    tasa_sistema NUMERIC,
    tasa_mn_corp NUMERIC,
    tasa_me_corp NUMERIC,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de seguimiento de ETL runs
CREATE TABLE IF NOT EXISTS etl_runs (
    id SERIAL PRIMARY KEY,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    duration_seconds FLOAT,
    status VARCHAR(20) NOT NULL,
    error_message TEXT,
    rows_processed_base INTEGER,
    rows_processed_icap INTEGER,
    rows_processed_tda INTEGER,
    rows_processed_tasas INTEGER,
    etl_version VARCHAR(50),
    triggered_by VARCHAR(50) DEFAULT 'manual'
);

-- Índices para mejorar performance
CREATE INDEX IF NOT EXISTS idx_monthly_kpis_fecha ON monthly_kpis(fecha);
CREATE INDEX IF NOT EXISTS idx_monthly_kpis_banco_norm ON monthly_kpis(banco_norm);
CREATE INDEX IF NOT EXISTS idx_monthly_kpis_institucion ON monthly_kpis(institucion);
CREATE INDEX IF NOT EXISTS idx_etl_runs_started_at ON etl_runs(started_at);
CREATE INDEX IF NOT EXISTS idx_etl_runs_status ON etl_runs(status);
EOF

log_success "Tablas creadas correctamente"
echo ""

# ============================================================================
# VERIFICAR Y INSTALAR DEPENDENCIAS
# ============================================================================

echo "📦 Verificando dependencias en el contenedor..."

# Check if polars is installed
if ! $DOCKER_COMPOSE -f infra/docker-compose.yml exec bank-advisor pip show polars > /dev/null 2>&1; then
    log_warning "Polars no está instalado, instalando..."
    $DOCKER_COMPOSE -f infra/docker-compose.yml exec bank-advisor pip install polars openpyxl pyarrow
    log_success "Dependencias instaladas"
else
    log_info "Polars ya está instalado"
fi

echo ""

# ============================================================================
# VERIFICAR ARCHIVOS DE DATOS
# ============================================================================

echo "📂 Verificando archivos de datos..."

# Check if data files exist
DATA_DIR="plugins/bank-advisor-private/data/raw"

if [ ! -d "$DATA_DIR" ]; then
    log_error "Directorio de datos no encontrado: $DATA_DIR"
    echo "Asegúrate de que los archivos de datos estén en: $DATA_DIR"
    exit 1
fi

REQUIRED_FILES=(
    "CNBV_Cartera_Bancos_V2.xlsx"
    "Instituciones.xlsx"
    "CorporateLoan_CNBVDB.csv"
)

MISSING_FILES=0
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$DATA_DIR/$file" ]; then
        log_error "Archivo faltante: $file"
        MISSING_FILES=$((MISSING_FILES + 1))
    else
        log_info "Encontrado: $file"
    fi
done

if [ $MISSING_FILES -gt 0 ]; then
    log_error "$MISSING_FILES archivos de datos faltantes"
    echo "Sube los archivos necesarios a: $DATA_DIR"
    exit 1
fi

log_success "Todos los archivos de datos presentes"
echo ""

# ============================================================================
# EJECUTAR ETL
# ============================================================================

echo "🔄 Ejecutando ETL (esto puede tardar varios minutos)..."
echo ""
log_info "Procesando aproximadamente 1.3M+ registros..."
log_info "Esto incluye:"
log_info "  - Cartera bancaria (CNBV)"
log_info "  - ICAP"
log_info "  - TDA"
log_info "  - Tasas efectivas"
log_info "  - Tasas corporativas MN/ME"
echo ""

# Execute ETL with output streaming
$DOCKER_COMPOSE -f infra/docker-compose.yml exec bank-advisor python <<'PYTHON_EOF'
import sys
sys.path.insert(0, '/app/src')

from datetime import datetime
from bankadvisor.etl_loader import run_etl
from bankadvisor.db import engine
from sqlalchemy import text

print("🚀 Iniciando ETL...")
start_time = datetime.now()

# Record ETL start
etl_run_id = None
with engine.connect() as conn:
    result = conn.execute(text("""
        INSERT INTO etl_runs (started_at, status, triggered_by)
        VALUES (NOW(), 'running', 'init_script')
        RETURNING id
    """))
    conn.commit()
    etl_run_id = result.fetchone()[0]
    print(f"   ETL Run ID: {etl_run_id}")

try:
    # Run ETL
    run_etl()

    # Record success
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    with engine.connect() as conn:
        # Get row count
        result = conn.execute(text("SELECT COUNT(*) FROM monthly_kpis"))
        row_count = result.fetchone()[0]

        # Update ETL run
        conn.execute(text("""
            UPDATE etl_runs
            SET completed_at = NOW(),
                status = 'success',
                duration_seconds = :duration,
                rows_processed_base = :rows
            WHERE id = :id
        """), {"duration": duration, "rows": row_count, "id": etl_run_id})
        conn.commit()

    print(f"\n✅ ETL completado exitosamente")
    print(f"   Duración: {duration:.1f} segundos")
    print(f"   Registros procesados: {row_count:,}")

except Exception as e:
    # Record failure
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE etl_runs
            SET completed_at = NOW(),
                status = 'failure',
                error_message = :error
            WHERE id = :id
        """), {"error": str(e), "id": etl_run_id})
        conn.commit()

    print(f"\n❌ ETL falló: {str(e)}")
    sys.exit(1)
PYTHON_EOF

ETL_EXIT_CODE=$?

if [ $ETL_EXIT_CODE -ne 0 ]; then
    log_error "ETL falló con código de salida: $ETL_EXIT_CODE"
    echo ""
    echo "Revisa los logs con:"
    echo "  $DOCKER_COMPOSE -f infra/docker-compose.yml logs bank-advisor"
    exit 1
fi

echo ""
log_success "ETL completado exitosamente"
echo ""

# ============================================================================
# VERIFICACIÓN FINAL
# ============================================================================

echo "🔍 Verificación final de datos..."
echo ""

# Check row count by bank
$DOCKER_COMPOSE -f infra/docker-compose.yml exec -T postgres psql -U octavios -d bankadvisor <<EOF
SELECT
    banco_norm,
    COUNT(*) as registros,
    MIN(fecha)::date as desde,
    MAX(fecha)::date as hasta
FROM monthly_kpis
GROUP BY banco_norm
ORDER BY registros DESC
LIMIT 10;
EOF

echo ""

# Get total stats
TOTAL_ROWS=$($DOCKER_COMPOSE -f infra/docker-compose.yml exec -T postgres psql -U octavios -d bankadvisor -t -c "SELECT COUNT(*) FROM monthly_kpis;" | xargs)
TOTAL_BANKS=$($DOCKER_COMPOSE -f infra/docker-compose.yml exec -T postgres psql -U octavios -d bankadvisor -t -c "SELECT COUNT(DISTINCT banco_norm) FROM monthly_kpis;" | xargs)

echo ""
log_success "Total de registros: $TOTAL_ROWS"
log_success "Total de bancos: $TOTAL_BANKS"
echo ""

# ============================================================================
# RESUMEN FINAL
# ============================================================================

echo "╔════════════════════════════════════════════════════════════╗"
echo "║                 INICIALIZACIÓN COMPLETADA                   ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║  ✅ Tablas creadas (monthly_kpis, etl_runs)                ║"
echo "║  ✅ Dependencias instaladas (polars, openpyxl)              ║"
echo "║  ✅ ETL ejecutado exitosamente                              ║"
echo "║  ✅ $TOTAL_ROWS registros cargados                          "
echo "║  ✅ $TOTAL_BANKS bancos en la base de datos                 "
echo "╠════════════════════════════════════════════════════════════╣"
echo "║  Próximos pasos:                                            ║"
echo "║  1. Reiniciar bank-advisor:                                 ║"
echo "║     $DOCKER_COMPOSE -f infra/docker-compose.yml restart bank-advisor"
echo "║                                                            ║"
echo "║  2. Verificar health check:                                 ║"
echo "║     curl http://localhost:8002/health                       ║"
echo "║                                                            ║"
echo "║  3. Probar una consulta:                                    ║"
echo "║     curl -X POST http://localhost:8000/rpc \\               ║"
echo "║       -H 'Content-Type: application/json' \\                ║"
echo "║       -d '{\"jsonrpc\":\"2.0\",\"id\":\"1\",              ║"
echo "║            \"method\":\"bank_advisor.query\",              ║"
echo "║            \"params\":{\"query\":\"IMOR de INVEX\"}}'      ║"
echo "╚════════════════════════════════════════════════════════════╝"
