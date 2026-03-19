#!/bin/bash
# Script to verify PostgreSQL data is correct
# Credentials referenced from envs/.env

set -e

export PGPASSWORD="${POSTGRES_PASSWORD}"

echo "===== Verifying data range in PostgreSQL ====="

psql -h ${POSTGRES_HOST} -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "
SELECT
  COUNT(*) as total_rows,
  MIN(EXTRACT(YEAR FROM fecha)) as min_year,
  MAX(EXTRACT(YEAR FROM fecha)) as max_year,
  MAX(fecha) as latest_period,
  COUNT(DISTINCT banco_norm) as num_banks
FROM monthly_kpis;
"

echo ""
echo "===== Checking IMOR values for 2024 (should NOT be 2024%) ====="

psql -h ${POSTGRES_HOST} -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "
SELECT
  banco_norm,
  fecha as period,
  imor,
  ROUND((imor * 100)::numeric, 2) || '%' as imor_formatted,
  icap_total,
  ROUND(icap_total::numeric, 2) || '%' as icap_formatted
FROM monthly_kpis
WHERE banco_norm IN ('SISTEMA', 'BANORTE', 'BBVA', 'SANTANDER')
  AND EXTRACT(YEAR FROM fecha) = 2024
  AND fecha >= '2024-12-01'
ORDER BY fecha DESC, banco_norm
LIMIT 10;
"

echo ""
echo "===== Checking for impossible values (none should exist) ====="

psql -h ${POSTGRES_HOST} -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "
SELECT
  banco_norm,
  fecha,
  imor,
  icap_total,
  CASE
    WHEN imor > 100 THEN 'IMOR > 100 (impossible)'
    WHEN icap_total > 100 THEN 'ICAP > 100 (unusual)'
    WHEN imor = EXTRACT(YEAR FROM fecha) THEN 'IMOR = YEAR (bug)'
    WHEN icap_total = EXTRACT(YEAR FROM fecha) THEN 'ICAP = YEAR (bug)'
    ELSE 'OK'
  END as validation
FROM monthly_kpis
WHERE fecha >= '2023-01-01'
  AND (
    imor > 100 OR
    icap_total > 100 OR
    imor = EXTRACT(YEAR FROM fecha) OR
    icap_total = EXTRACT(YEAR FROM fecha)
  )
LIMIT 20;
"

echo ""
echo "===== Checking CARTERA_VIVIENDA_TOTAL availability ====="

psql -h ${POSTGRES_HOST} -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "
SELECT
  banco_norm,
  fecha,
  cartera_vivienda_total,
  CASE
    WHEN cartera_vivienda_total = 0 THEN 'Zero (no data)'
    WHEN cartera_vivienda_total IS NULL THEN 'NULL'
    ELSE 'Has data'
  END as status
FROM monthly_kpis
WHERE banco_norm IN ('SISTEMA', 'BANORTE', 'BBVA')
  AND fecha >= '2024-01-01'
ORDER BY fecha DESC, banco_norm
LIMIT 15;
"
