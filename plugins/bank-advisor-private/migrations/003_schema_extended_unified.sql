-- ============================================================================
-- MIGRATION 003: Extended Schema for Unified ETL
-- ============================================================================
-- This migration extends the database schema to support the unified ETL pipeline
-- that consolidates both Legacy and Normalized data sources.
--
-- New tables:
--   - monthly_kpis: Legacy-compatible table for historical KPIs
--
-- Extended columns on metricas_financieras:
--   - ICAP (capitalización)
--   - TDA (deterioro ajustado)
--   - Tasas efectivas (sistema, INVEX consumo)
--   - Tasas corporativas (MN, ME)
--   - Etapas IFRS9 (ct_etapa_1/2/3)
--   - Reservas y quebrantos
--
-- Run with: psql -f migrations/003_schema_extended_unified.sql
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. EXTEND metricas_financieras TABLE
-- ============================================================================

-- Add ICAP (Índice de Capitalización)
ALTER TABLE metricas_financieras
ADD COLUMN IF NOT EXISTS icap_total NUMERIC(10, 4);
COMMENT ON COLUMN metricas_financieras.icap_total IS 'Índice de Capitalización Total (ICAP) - fuente: ICAP_Bancos.xlsx';

-- Add TDA (Tasa de Deterioro Ajustada)
ALTER TABLE metricas_financieras
ADD COLUMN IF NOT EXISTS tda_cartera_total NUMERIC(10, 4);
COMMENT ON COLUMN metricas_financieras.tda_cartera_total IS 'Tasa de Deterioro Ajustada de Cartera Total - fuente: TDA.xlsx';

-- Add Tasas Efectivas
ALTER TABLE metricas_financieras
ADD COLUMN IF NOT EXISTS tasa_sistema NUMERIC(10, 4);
COMMENT ON COLUMN metricas_financieras.tasa_sistema IS 'Tasa efectiva promedio del sistema bancario - fuente: TE_Invex_Sistema.xlsx';

ALTER TABLE metricas_financieras
ADD COLUMN IF NOT EXISTS tasa_invex_consumo NUMERIC(10, 4);
COMMENT ON COLUMN metricas_financieras.tasa_invex_consumo IS 'Tasa efectiva INVEX consumo - fuente: TE_Invex_Sistema.xlsx';

-- Add Tasas Corporativas (de CorporateLoan_CNBVDB.csv)
ALTER TABLE metricas_financieras
ADD COLUMN IF NOT EXISTS tasa_mn NUMERIC(10, 4);
COMMENT ON COLUMN metricas_financieras.tasa_mn IS 'Tasa corporativa promedio Moneda Nacional - fuente: CorporateLoan_CNBVDB.csv';

ALTER TABLE metricas_financieras
ADD COLUMN IF NOT EXISTS tasa_me NUMERIC(10, 4);
COMMENT ON COLUMN metricas_financieras.tasa_me IS 'Tasa corporativa promedio Moneda Extranjera - fuente: CorporateLoan_CNBVDB.csv';

-- Add Etapas IFRS9 (de CNBV_Cartera_Bancos_V2.xlsx)
ALTER TABLE metricas_financieras
ADD COLUMN IF NOT EXISTS ct_etapa_1 NUMERIC(10, 4);
COMMENT ON COLUMN metricas_financieras.ct_etapa_1 IS 'Cartera Total Etapa 1 IFRS9 (sin deterioro significativo)';

ALTER TABLE metricas_financieras
ADD COLUMN IF NOT EXISTS ct_etapa_2 NUMERIC(10, 4);
COMMENT ON COLUMN metricas_financieras.ct_etapa_2 IS 'Cartera Total Etapa 2 IFRS9 (deterioro significativo)';

ALTER TABLE metricas_financieras
ADD COLUMN IF NOT EXISTS ct_etapa_3 NUMERIC(10, 4);
COMMENT ON COLUMN metricas_financieras.ct_etapa_3 IS 'Cartera Total Etapa 3 IFRS9 (deterioro crediticio)';

-- Add Reservas
ALTER TABLE metricas_financieras
ADD COLUMN IF NOT EXISTS reservas_etapa_todas NUMERIC(20, 2);
COMMENT ON COLUMN metricas_financieras.reservas_etapa_todas IS 'Reservas totales (todas las etapas) en MDP';

ALTER TABLE metricas_financieras
ADD COLUMN IF NOT EXISTS reservas_variacion_mm NUMERIC(20, 2);
COMMENT ON COLUMN metricas_financieras.reservas_variacion_mm IS 'Variación mensual de reservas en MDP';

-- Add Quebrantos
ALTER TABLE metricas_financieras
ADD COLUMN IF NOT EXISTS quebrantos_cc NUMERIC(20, 2);
COMMENT ON COLUMN metricas_financieras.quebrantos_cc IS 'Quebrantos cartera comercial en MDP - fuente: CASTIGOS.xlsx';

ALTER TABLE metricas_financieras
ADD COLUMN IF NOT EXISTS quebrantos_vs_cartera_cc NUMERIC(10, 4);
COMMENT ON COLUMN metricas_financieras.quebrantos_vs_cartera_cc IS 'Ratio quebrantos / cartera comercial';


-- ============================================================================
-- 2. CREATE monthly_kpis TABLE (Legacy-compatible)
-- ============================================================================

CREATE TABLE IF NOT EXISTS monthly_kpis (
    id SERIAL PRIMARY KEY,
    fecha DATE NOT NULL,
    institucion VARCHAR(100) NOT NULL,
    banco_norm VARCHAR(50) NOT NULL,

    -- Carteras (MDP)
    cartera_total NUMERIC(20, 2),
    cartera_comercial_total NUMERIC(20, 2),
    cartera_consumo_total NUMERIC(20, 2),
    cartera_vivienda_total NUMERIC(20, 2),
    entidades_gubernamentales_total NUMERIC(20, 2),
    entidades_financieras_total NUMERIC(20, 2),
    empresarial_total NUMERIC(20, 2),

    -- Calidad de Cartera
    cartera_vencida NUMERIC(20, 2),
    imor NUMERIC(10, 4),
    icor NUMERIC(10, 4),

    -- Reservas
    reservas_etapa_todas NUMERIC(20, 2),
    reservas_variacion_mm NUMERIC(20, 2),

    -- Pérdida Esperada (ratios)
    pe_total NUMERIC(10, 4),
    pe_empresarial NUMERIC(10, 4),
    pe_consumo NUMERIC(10, 4),
    pe_vivienda NUMERIC(10, 4),

    -- Etapas de Deterioro IFRS9 (ratios)
    ct_etapa_1 NUMERIC(10, 4),
    ct_etapa_2 NUMERIC(10, 4),
    ct_etapa_3 NUMERIC(10, 4),

    -- Quebrantos
    quebrantos_cc NUMERIC(20, 2),
    quebrantos_vs_cartera_cc NUMERIC(10, 4),

    -- Índices y Tasas
    icap_total NUMERIC(10, 4),
    tda_cartera_total NUMERIC(10, 4),
    tasa_sistema NUMERIC(10, 4),
    tasa_invex_consumo NUMERIC(10, 4),
    tasa_mn NUMERIC(10, 4),
    tasa_me NUMERIC(10, 4),

    CONSTRAINT uk_monthly_kpis_fecha_banco UNIQUE (fecha, banco_norm)
);

COMMENT ON TABLE monthly_kpis IS 'KPIs mensuales agregados por banco. Compatible con ETL legacy. Fuente unificada: etl_unified.py';
COMMENT ON COLUMN monthly_kpis.banco_norm IS 'Nombre normalizado del banco (INVEX, BBVA, SISTEMA, etc.)';
COMMENT ON COLUMN monthly_kpis.imor IS 'Índice de Morosidad = cartera_vencida / cartera_total';
COMMENT ON COLUMN monthly_kpis.icor IS 'Índice de Cobertura = reservas / cartera_vencida';


-- ============================================================================
-- 3. CREATE metricas_financieras_ext TABLE (Extended metrics)
-- ============================================================================
-- This table stores extended financial metrics from the unified ETL.
-- It mirrors metricas_financieras but without FK constraints for simpler loading.

CREATE TABLE IF NOT EXISTS metricas_financieras_ext (
    id SERIAL PRIMARY KEY,
    institucion VARCHAR(100) NOT NULL,
    banco_norm VARCHAR(50),
    fecha_corte DATE NOT NULL,

    -- Balance general (MDP)
    activo_total NUMERIC(20, 2),
    inversiones_financieras NUMERIC(20, 2),
    cartera_total NUMERIC(20, 2),
    captacion_total NUMERIC(20, 2),
    capital_contable NUMERIC(20, 2),
    resultado_neto NUMERIC(20, 2),

    -- Rentabilidad (%)
    roa_12m NUMERIC(10, 4),
    roe_12m NUMERIC(10, 4),

    -- Calidad de cartera (%)
    imor NUMERIC(10, 4),
    icor NUMERIC(10, 4),
    perdida_esperada NUMERIC(10, 4),

    -- Extended: ICAP y TDA
    icap_total NUMERIC(10, 4),
    tda_cartera_total NUMERIC(10, 4),

    -- Extended: Tasas
    tasa_sistema NUMERIC(10, 4),
    tasa_invex_consumo NUMERIC(10, 4),
    tasa_mn NUMERIC(10, 4),
    tasa_me NUMERIC(10, 4),

    -- Extended: Etapas IFRS9
    ct_etapa_1 NUMERIC(10, 4),
    ct_etapa_2 NUMERIC(10, 4),
    ct_etapa_3 NUMERIC(10, 4),

    -- Extended: Reservas y quebrantos
    reservas_etapa_todas NUMERIC(20, 2),
    quebrantos_cc NUMERIC(20, 2),

    CONSTRAINT uk_metricas_ext_fecha_banco UNIQUE (fecha_corte, institucion)
);

COMMENT ON TABLE metricas_financieras_ext IS 'Métricas financieras extendidas sin FKs. Fuente: etl_unified.py';


-- ============================================================================
-- 4. CREATE monthly_kpis_v2 VIEW (Compatibility layer)
-- ============================================================================
-- This view provides a unified interface to query both old and new data.

CREATE OR REPLACE VIEW monthly_kpis_v2 AS
SELECT
    m.fecha,
    m.banco_norm as institucion,
    m.banco_norm,
    -- Carteras
    m.cartera_total,
    m.cartera_comercial_total,
    m.cartera_consumo_total,
    m.cartera_vivienda_total,
    m.empresarial_total,
    m.entidades_financieras_total,
    m.entidades_gubernamentales_total,
    -- Calidad
    m.cartera_vencida,
    m.imor,
    m.icor,
    -- Reservas
    m.reservas_etapa_todas,
    m.reservas_variacion_mm,
    -- Pérdida Esperada
    m.pe_total,
    m.pe_empresarial,
    m.pe_consumo,
    m.pe_vivienda,
    -- Etapas IFRS9
    m.ct_etapa_1,
    m.ct_etapa_2,
    m.ct_etapa_3,
    -- Índices
    m.icap_total,
    m.tda_cartera_total,
    -- Tasas
    m.tasa_sistema,
    m.tasa_invex_consumo,
    m.tasa_mn,
    m.tasa_me,
    -- Quebrantos
    m.quebrantos_cc,
    m.quebrantos_vs_cartera_cc
FROM monthly_kpis m;

COMMENT ON VIEW monthly_kpis_v2 IS 'Vista de compatibilidad para queries legacy. Fuente: monthly_kpis';


-- ============================================================================
-- 5. CREATE INDEXES FOR PERFORMANCE
-- ============================================================================

-- Monthly KPIs indexes
CREATE INDEX IF NOT EXISTS idx_monthly_kpis_fecha ON monthly_kpis(fecha);
CREATE INDEX IF NOT EXISTS idx_monthly_kpis_banco ON monthly_kpis(banco_norm);
CREATE INDEX IF NOT EXISTS idx_monthly_kpis_fecha_banco ON monthly_kpis(fecha, banco_norm);

-- Extended metrics indexes
CREATE INDEX IF NOT EXISTS idx_metricas_ext_fecha ON metricas_financieras_ext(fecha_corte);
CREATE INDEX IF NOT EXISTS idx_metricas_ext_banco ON metricas_financieras_ext(institucion);
CREATE INDEX IF NOT EXISTS idx_metricas_ext_banco_norm ON metricas_financieras_ext(banco_norm);


-- ============================================================================
-- 6. POPULATE segmentos_cartera CATALOG (if empty)
-- ============================================================================

INSERT INTO segmentos_cartera (codigo, nombre, descripcion)
VALUES
    ('EMPRESAS', 'Crédito a Empresas', 'Actividad empresarial y comercial'),
    ('ENTIDADES_FINANCIERAS', 'Entidades Financieras', 'Créditos interbancarios'),
    ('GUBERNAMENTAL_TOTAL', 'Gubernamental Total', 'Gobierno federal, estatal y municipal'),
    ('GUB_ESTADOS_MUN', 'Estados y Municipios', 'Gobiernos estatales y municipales'),
    ('GUB_OTRAS', 'Otras Gubernamentales', 'Otras entidades de gobierno'),
    ('CONSUMO_TOTAL', 'Consumo Total', 'Todos los segmentos de consumo'),
    ('CONSUMO_TARJETA', 'Tarjeta de Crédito', 'Crédito revolvente tarjetas'),
    ('CONSUMO_NOMINA', 'Crédito de Nómina', 'Préstamos con descuento de nómina'),
    ('CONSUMO_PERSONALES', 'Préstamos Personales', 'Créditos personales sin garantía'),
    ('CONSUMO_AUTOMOTRIZ', 'Crédito Automotriz', 'Financiamiento de vehículos'),
    ('CONSUMO_BIENES_MUEBLES', 'Bienes Muebles', 'Adquisición de bienes muebles'),
    ('CONSUMO_ARRENDAMIENTO', 'Arrendamiento Capitalizable', 'Leasing'),
    ('CONSUMO_MICROCREDITOS', 'Microcréditos', 'Créditos de bajo monto'),
    ('CONSUMO_OTROS', 'Otros Consumo', 'Otros créditos al consumo'),
    ('VIVIENDA', 'Crédito a la Vivienda', 'Hipotecarios y mejora de vivienda')
ON CONFLICT (codigo) DO NOTHING;


COMMIT;

-- ============================================================================
-- VERIFICATION QUERIES (run manually)
-- ============================================================================

-- Check new columns exist:
-- SELECT column_name, data_type
-- FROM information_schema.columns
-- WHERE table_name = 'metricas_financieras' AND column_name LIKE 'icap%';

-- Check tables created:
-- SELECT table_name FROM information_schema.tables
-- WHERE table_schema = 'public' AND table_name IN ('monthly_kpis', 'metricas_financieras_ext');

-- Check view:
-- SELECT * FROM monthly_kpis_v2 LIMIT 5;
