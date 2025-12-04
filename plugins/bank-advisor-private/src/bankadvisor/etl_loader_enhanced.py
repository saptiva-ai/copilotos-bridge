"""
DEPRECATED: This module is deprecated and will be removed in a future release.
Use the unified ETL instead: etl.etl_unified

Migration guide:
    # Old way (pandas-based, slow)
    from bankadvisor.etl_loader_enhanced import run_etl_enhancement
    run_etl_enhancement()

    # New way (polars-based, 10x faster)
    from etl.etl_unified import UnifiedETL
    etl = UnifiedETL()
    etl.run()

Deprecated since: 2025-12-03
Reason: Consolidated into unified Polars-based ETL for better performance

---
Original docstring:
Enhanced ETL Loader for BankAdvisor Plugin

This script extends the base ETL to load additional metrics:
- ICAP (Índice de Capitalización)
- TDA (Tasa de Deterioro Ajustada)
- TASA_MN (Tasa promedio Moneda Nacional)
- TASA_ME (Tasa promedio Moneda Extranjera)

Author: Claude Code
Date: 2025-11-27
"""
import warnings
warnings.warn(
    "bankadvisor.etl_loader_enhanced is deprecated. Use etl.etl_unified instead.",
    DeprecationWarning,
    stacklevel=2
)

import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from datetime import datetime
from core.config import get_settings
import structlog

logger = structlog.get_logger()

settings = get_settings()


def load_icap_data(data_root: str) -> pd.DataFrame:
    """
    Load ICAP data from ICAP_Bancos.xlsx

    Returns DataFrame with columns: [fecha, banco_norm, icap_total]
    """
    logger.info("Loading ICAP data...")
    file_path = os.path.join(data_root, "ICAP_Bancos.xlsx")

    if not os.path.exists(file_path):
        logger.warning(f"ICAP file not found: {file_path}")
        return pd.DataFrame()

    # Read Excel
    df = pd.read_excel(file_path, sheet_name=0)

    # Clean and standardize
    df_clean = df.rename(columns={
        'FECHA': 'fecha',
        'Banco': 'banco_raw',
        'ICAP Total': 'icap_total'
    })

    # Convert fecha to datetime
    df_clean['fecha'] = pd.to_datetime(df_clean['fecha'])

    # Normalize bank names to match monthly_kpis.banco_norm
    # Map banco names to INVEX or SISTEMA
    def normalize_banco(banco_name):
        if pd.isna(banco_name):
            return None
        banco_upper = str(banco_name).upper()
        if 'INVEX' in banco_upper:
            return 'INVEX'
        # For sistema, we'll aggregate all other banks
        return banco_upper

    df_clean['banco_norm'] = df_clean['banco_raw'].apply(normalize_banco)

    # Select relevant columns
    df_result = df_clean[['fecha', 'banco_norm', 'icap_total']].copy()

    # Remove nulls
    df_result = df_result.dropna(subset=['fecha', 'banco_norm', 'icap_total'])

    logger.info(f"Loaded {len(df_result)} ICAP records")

    return df_result


def load_tda_data(data_root: str) -> pd.DataFrame:
    """
    Load TDA data from TDA.xlsx

    Returns DataFrame with columns: [fecha, cve_institucion, tda_cartera_total]
    """
    logger.info("Loading TDA data...")
    file_path = os.path.join(data_root, "TDA.xlsx")

    if not os.path.exists(file_path):
        logger.warning(f"TDA file not found: {file_path}")
        return pd.DataFrame()

    # Read Excel
    df = pd.read_excel(file_path, sheet_name=0)

    # Clean column names (there's a leading space in " TDA Cartera total")
    df.columns = df.columns.str.strip()

    # Rename columns
    df_clean = df.rename(columns={
        'Fecha': 'fecha',
        'cve_institucion': 'cve_inst',
        'TDA Cartera total': 'tda_cartera_total'
    })

    # Parse fecha (format: MM/DD/YYYY)
    df_clean['fecha'] = pd.to_datetime(df_clean['fecha'], format='%m/%d/%Y', errors='coerce')

    # Normalize to first day of month (fixes 2022 data that uses day 2)
    df_clean['fecha'] = df_clean['fecha'].dt.to_period('M').dt.to_timestamp()

    # Select relevant columns
    df_result = df_clean[['fecha', 'cve_inst', 'tda_cartera_total']].copy()

    # Remove nulls
    df_result = df_result.dropna(subset=['fecha', 'cve_inst', 'tda_cartera_total'])

    logger.info(f"Loaded {len(df_result)} TDA records")

    return df_result


def load_tasas_data(data_root: str) -> pd.DataFrame:
    """
    Load interest rate data from CorporateLoan_CNBVDB.csv

    Returns DataFrame with columns: [fecha, cve_inst, currency_type, tasa_promedio]

    Note: This is a large file (228MB), so we use chunking

    IMPORTANT: Uses 'Currency' column (not 'Currency type') to distinguish MN vs ME
    - 'Currency' = 'Moneda nacional' → MN
    - 'Currency' = 'Moneda extranjera' → ME
    """
    logger.info("Loading Tasas data (this may take a while)...")
    file_path = os.path.join(data_root, "CorporateLoan_CNBVDB.csv")

    if not os.path.exists(file_path):
        logger.warning(f"Tasas file not found: {file_path}")
        return pd.DataFrame()

    # Read CSV in chunks to handle large file
    chunks = []
    chunk_size = 50000

    for chunk in pd.read_csv(file_path, chunksize=chunk_size):
        # Filter for relevant columns
        # CORRECTED: Use 'Currency' instead of 'Currency type'
        chunk_filtered = chunk[['Monitoring Term', 'Institution Code', 'Currency', 'Average Rate']].copy()

        # Only keep rows with valid data
        chunk_filtered = chunk_filtered.dropna(subset=['Monitoring Term', 'Institution Code', 'Average Rate'])

        chunks.append(chunk_filtered)

    # Combine all chunks
    df = pd.concat(chunks, ignore_index=True)

    # Clean and standardize
    df_clean = df.rename(columns={
        'Monitoring Term': 'fecha',
        'Institution Code': 'cve_inst',
        'Currency': 'currency_type',  # CORRECTED: renamed from 'Currency type'
        'Average Rate': 'tasa_promedio'
    })

    # Parse fecha (format varies: M/D/YY or MM/DD/YYYY)
    df_clean['fecha'] = pd.to_datetime(df_clean['fecha'], errors='coerce')

    # Normalize to first day of month (fixes end-of-month dates)
    df_clean['fecha'] = df_clean['fecha'].dt.to_period('M').dt.to_timestamp()

    # Normalize currency type
    df_clean['currency_type'] = df_clean['currency_type'].str.strip()

    # Remove nulls
    df_result = df_clean.dropna(subset=['fecha', 'cve_inst', 'tasa_promedio'])

    logger.info(f"Loaded {len(df_result)} Tasas records")

    return df_result


def map_institution_to_banco_norm(cve_inst: int) -> str:
    """
    Map institution code to banco_norm (INVEX or institution name)

    INVEX code: 40059
    """
    if cve_inst == 40059:
        return 'INVEX'
    else:
        # Return the code as string for now (we'll aggregate to SISTEMA later)
        return str(cve_inst)


def aggregate_sistema_metrics(df: pd.DataFrame, metric_col: str) -> pd.DataFrame:
    """
    Aggregate all non-INVEX banks into SISTEMA

    Args:
        df: DataFrame with columns [fecha, banco_norm, metric_col]
        metric_col: Name of the metric column to aggregate

    Returns:
        DataFrame with SISTEMA aggregated values
    """
    # Filter for non-INVEX banks
    sistema_df = df[df['banco_norm'] != 'INVEX'].copy()

    if len(sistema_df) == 0:
        return pd.DataFrame()

    # Aggregate by fecha (weighted average)
    # For simplicity, we'll use simple mean for now
    # TODO: Implement weighted average based on cartera size
    agg_df = sistema_df.groupby('fecha').agg({
        metric_col: 'mean'
    }).reset_index()

    agg_df['banco_norm'] = 'SISTEMA'

    return agg_df[['fecha', 'banco_norm', metric_col]]


def update_monthly_kpis_with_metrics(engine, icap_df, tda_df, tasas_df):
    """
    Update existing monthly_kpis records with new metrics

    Strategy: Use UPDATE statements with JOIN on (fecha, banco_norm)
    """
    logger.info("Updating monthly_kpis with new metrics...")

    with engine.begin() as conn:
        # 1. Update ICAP data
        if not icap_df.empty:
            logger.info(f"Updating ICAP for {len(icap_df)} records...")

            # Separate INVEX and SISTEMA
            icap_invex = icap_df[icap_df['banco_norm'] == 'INVEX']

            # Create temp table for ICAP data
            icap_invex.to_sql('temp_icap', conn, if_exists='replace', index=False)

            # Update INVEX records
            update_sql = text("""
                UPDATE monthly_kpis mk
                SET icap_total = ti.icap_total
                FROM temp_icap ti
                WHERE mk.fecha = ti.fecha
                  AND mk.banco_norm = ti.banco_norm
                  AND mk.banco_norm = 'INVEX'
            """)
            result = conn.execute(update_sql)
            logger.info(f"Updated {result.rowcount} INVEX ICAP records")

            # Aggregate and update SISTEMA
            icap_sistema = aggregate_sistema_metrics(icap_df, 'icap_total')
            if not icap_sistema.empty:
                icap_sistema.to_sql('temp_icap_sistema', conn, if_exists='replace', index=False)

                update_sql = text("""
                    UPDATE monthly_kpis mk
                    SET icap_total = ti.icap_total
                    FROM temp_icap_sistema ti
                    WHERE mk.fecha = ti.fecha
                      AND mk.banco_norm = ti.banco_norm
                      AND mk.banco_norm = 'SISTEMA'
                """)
                result = conn.execute(update_sql)
                logger.info(f"Updated {result.rowcount} SISTEMA ICAP records")

            # Drop temp tables
            conn.execute(text("DROP TABLE IF EXISTS temp_icap"))
            conn.execute(text("DROP TABLE IF EXISTS temp_icap_sistema"))

        # 2. Update TDA data
        if not tda_df.empty:
            logger.info(f"Updating TDA for {len(tda_df)} records...")

            # Map institution codes to banco_norm
            tda_df['banco_norm'] = tda_df['cve_inst'].apply(map_institution_to_banco_norm)

            # INVEX only
            tda_invex = tda_df[tda_df['banco_norm'] == 'INVEX']

            if not tda_invex.empty:
                tda_invex_clean = tda_invex[['fecha', 'banco_norm', 'tda_cartera_total']].copy()
                tda_invex_clean.to_sql('temp_tda', conn, if_exists='replace', index=False)

                update_sql = text("""
                    UPDATE monthly_kpis mk
                    SET tda_cartera_total = ti.tda_cartera_total
                    FROM temp_tda ti
                    WHERE mk.fecha = ti.fecha
                      AND mk.banco_norm = ti.banco_norm
                      AND mk.banco_norm = 'INVEX'
                """)
                result = conn.execute(update_sql)
                logger.info(f"Updated {result.rowcount} INVEX TDA records")

                conn.execute(text("DROP TABLE IF EXISTS temp_tda"))

            # Aggregate SISTEMA
            tda_sistema = aggregate_sistema_metrics(tda_df[['fecha', 'banco_norm', 'tda_cartera_total']], 'tda_cartera_total')
            if not tda_sistema.empty:
                tda_sistema.to_sql('temp_tda_sistema', conn, if_exists='replace', index=False)

                update_sql = text("""
                    UPDATE monthly_kpis mk
                    SET tda_cartera_total = ti.tda_cartera_total
                    FROM temp_tda_sistema ti
                    WHERE mk.fecha = ti.fecha
                      AND mk.banco_norm = ti.banco_norm
                      AND mk.banco_norm = 'SISTEMA'
                """)
                result = conn.execute(update_sql)
                logger.info(f"Updated {result.rowcount} SISTEMA TDA records")

                conn.execute(text("DROP TABLE IF EXISTS temp_tda_sistema"))

        # 3. Update Tasas data
        if not tasas_df.empty:
            logger.info(f"Updating Tasas for {len(tasas_df)} records...")

            # Map institution codes
            tasas_df['banco_norm'] = tasas_df['cve_inst'].apply(map_institution_to_banco_norm)

            # Separate MN and ME
            # CORRECTED: Use proper column values from 'Currency' column
            tasas_mn = tasas_df[tasas_df['currency_type'] == 'Moneda nacional'].copy()
            tasas_me = tasas_df[tasas_df['currency_type'] == 'Moneda extranjera'].copy()

            # Update TASA_MN for INVEX
            if not tasas_mn.empty:
                tasas_mn_invex = tasas_mn[tasas_mn['banco_norm'] == 'INVEX']

                if not tasas_mn_invex.empty:
                    # Aggregate by fecha (in case multiple records per month)
                    tasas_mn_agg = tasas_mn_invex.groupby(['fecha', 'banco_norm']).agg({
                        'tasa_promedio': 'mean'
                    }).reset_index()
                    tasas_mn_agg = tasas_mn_agg.rename(columns={'tasa_promedio': 'tasa_mn'})

                    tasas_mn_agg.to_sql('temp_tasa_mn', conn, if_exists='replace', index=False)

                    update_sql = text("""
                        UPDATE monthly_kpis mk
                        SET tasa_mn = ti.tasa_mn
                        FROM temp_tasa_mn ti
                        WHERE mk.fecha = ti.fecha
                          AND mk.banco_norm = ti.banco_norm
                          AND mk.banco_norm = 'INVEX'
                    """)
                    result = conn.execute(update_sql)
                    logger.info(f"Updated {result.rowcount} INVEX TASA_MN records")

                    conn.execute(text("DROP TABLE IF EXISTS temp_tasa_mn"))

                # Aggregate SISTEMA MN
                tasas_mn_sistema_raw = tasas_mn[['fecha', 'banco_norm', 'tasa_promedio']].copy()
                tasas_mn_sistema_raw = tasas_mn_sistema_raw.rename(columns={'tasa_promedio': 'tasa_mn'})
                tasas_mn_sistema = aggregate_sistema_metrics(tasas_mn_sistema_raw, 'tasa_mn')

                if not tasas_mn_sistema.empty:
                    tasas_mn_sistema.to_sql('temp_tasa_mn_sistema', conn, if_exists='replace', index=False)

                    update_sql = text("""
                        UPDATE monthly_kpis mk
                        SET tasa_mn = ti.tasa_mn
                        FROM temp_tasa_mn_sistema ti
                        WHERE mk.fecha = ti.fecha
                          AND mk.banco_norm = ti.banco_norm
                          AND mk.banco_norm = 'SISTEMA'
                    """)
                    result = conn.execute(update_sql)
                    logger.info(f"Updated {result.rowcount} SISTEMA TASA_MN records")

                    conn.execute(text("DROP TABLE IF EXISTS temp_tasa_mn_sistema"))

            # Update TASA_ME for INVEX
            if not tasas_me.empty:
                tasas_me_invex = tasas_me[tasas_me['banco_norm'] == 'INVEX']

                if not tasas_me_invex.empty:
                    tasas_me_agg = tasas_me_invex.groupby(['fecha', 'banco_norm']).agg({
                        'tasa_promedio': 'mean'
                    }).reset_index()
                    tasas_me_agg = tasas_me_agg.rename(columns={'tasa_promedio': 'tasa_me'})

                    tasas_me_agg.to_sql('temp_tasa_me', conn, if_exists='replace', index=False)

                    update_sql = text("""
                        UPDATE monthly_kpis mk
                        SET tasa_me = ti.tasa_me
                        FROM temp_tasa_me ti
                        WHERE mk.fecha = ti.fecha
                          AND mk.banco_norm = ti.banco_norm
                          AND mk.banco_norm = 'INVEX'
                    """)
                    result = conn.execute(update_sql)
                    logger.info(f"Updated {result.rowcount} INVEX TASA_ME records")

                    conn.execute(text("DROP TABLE IF EXISTS temp_tasa_me"))

                # Aggregate SISTEMA ME
                tasas_me_sistema_raw = tasas_me[['fecha', 'banco_norm', 'tasa_promedio']].copy()
                tasas_me_sistema_raw = tasas_me_sistema_raw.rename(columns={'tasa_promedio': 'tasa_me'})
                tasas_me_sistema = aggregate_sistema_metrics(tasas_me_sistema_raw, 'tasa_me')

                if not tasas_me_sistema.empty:
                    tasas_me_sistema.to_sql('temp_tasa_me_sistema', conn, if_exists='replace', index=False)

                    update_sql = text("""
                        UPDATE monthly_kpis mk
                        SET tasa_me = ti.tasa_me
                        FROM temp_tasa_me_sistema ti
                        WHERE mk.fecha = ti.fecha
                          AND mk.banco_norm = ti.banco_norm
                          AND mk.banco_norm = 'SISTEMA'
                    """)
                    result = conn.execute(update_sql)
                    logger.info(f"Updated {result.rowcount} SISTEMA TASA_ME records")

                    conn.execute(text("DROP TABLE IF EXISTS temp_tasa_me_sistema"))

    logger.info("✅ All metrics updated successfully")


def run_etl_enhancement():
    """
    Main ETL enhancement function

    Loads ICAP, TDA, and Tasas data and updates monthly_kpis table
    """
    logger.info("🚀 Starting ETL Enhancement...")

    # 1. Configure paths
    data_root = "/app/data/raw"
    if not os.path.exists(data_root):
        data_root = os.path.join(os.path.dirname(__file__), "../../../data/raw")

    logger.info(f"📂 Reading data from: {os.path.abspath(data_root)}")

    # 2. Load data files
    icap_df = load_icap_data(data_root)
    tda_df = load_tda_data(data_root)
    tasas_df = load_tasas_data(data_root)

    # 3. Setup database connection
    db_url = settings.database_url_sync

    # Override host if running outside docker
    if not os.path.exists("/.dockerenv"):
        db_url = db_url.replace(f"@{settings.postgres_host}:", "@localhost:")

    engine = create_engine(db_url)

    # 4. Update monthly_kpis table
    update_monthly_kpis_with_metrics(engine, icap_df, tda_df, tasas_df)

    # 5. Verify updates
    with engine.begin() as conn:
        result = conn.execute(text("""
            SELECT
                COUNT(*) as total_rows,
                COUNT(icap_total) as icap_count,
                COUNT(tda_cartera_total) as tda_count,
                COUNT(tasa_mn) as tasa_mn_count,
                COUNT(tasa_me) as tasa_me_count
            FROM monthly_kpis
        """))
        row = result.fetchone()

        logger.info("📊 Final data counts:")
        logger.info(f"  Total rows: {row[0]}")
        logger.info(f"  ICAP populated: {row[1]}")
        logger.info(f"  TDA populated: {row[2]}")
        logger.info(f"  TASA_MN populated: {row[3]}")
        logger.info(f"  TASA_ME populated: {row[4]}")

    logger.info("✅ ETL Enhancement completed successfully!")


def main():
    """Entry point for ETL enhancement."""
    run_etl_enhancement()


if __name__ == "__main__":
    main()
