"""
Unified Data Loaders using Polars for high-performance data loading.

Consolidates all data sources from both Legacy and Normalized ETL pipelines:
- Legacy sources: CNBV, Castigos, ICAP, TDA, TE, CorporateLoan, Instituciones
- Normalized source: BE_BM_202509.xlsx (16 sheets)

Performance: 10-15x faster than Pandas for large files (CorporateLoan: 219MB)
"""
from __future__ import annotations

import polars as pl
import pandas as pd
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Optional, List, Any
import structlog

logger = structlog.get_logger(__name__)


# =============================================================================
# DATA PATHS CONFIGURATION
# =============================================================================

@dataclass(frozen=True)
class DataPaths:
    """Configuration for all data source paths."""
    base_dir: Path

    def file(self, relative: str) -> Path:
        return self.base_dir / relative

    # Legacy sources
    @property
    def cnbv_cartera(self) -> Path:
        return self.file("CNBV_Cartera_Bancos_V2.xlsx")

    @property
    def castigos(self) -> Path:
        return self.file("CASTIGOS.xlsx")

    @property
    def castigos_comerciales(self) -> Path:
        return self.file("Castigos Comerciales.xlsx")

    @property
    def icap_bancos(self) -> Path:
        return self.file("ICAP_Bancos.xlsx")

    @property
    def tda(self) -> Path:
        return self.file("TDA.xlsx")

    @property
    def te_invex(self) -> Path:
        return self.file("TE_Invex_Sistema.xlsx")

    @property
    def corporate_loan(self) -> Path:
        return self.file("CorporateLoan_CNBVDB.csv")

    @property
    def instituciones(self) -> Path:
        return self.file("Instituciones.xlsx")

    # Normalized source
    @property
    def be_bm(self) -> Path:
        return self.file("BE_BM_202509.xlsx")


def get_data_paths(data_root: Path | str) -> DataPaths:
    """Factory that ensures the directory exists and wraps it in DataPaths."""
    if isinstance(data_root, str):
        data_root = Path(data_root)
    root = data_root.expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Data directory not found: {root}")
    return DataPaths(base_dir=root)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def normalize_institution_code(df: pl.LazyFrame, col: str = "institucion") -> pl.LazyFrame:
    """Normalize institution codes to 6-digit zero-padded strings."""
    # FIX: Cast to Int64 first to handle float types (40131.0 -> 40131)
    # before converting to string, otherwise zfill doesn't work correctly
    return df.with_columns([
        pl.col(col).cast(pl.Int64).cast(pl.Utf8).str.zfill(6).alias(col)
    ])


def normalize_date_to_month_start(df: pl.LazyFrame, col: str = "fecha") -> pl.LazyFrame:
    """Normalize dates to first day of month for consistent joins."""
    return df.with_columns([
        pl.col(col).dt.truncate("1mo").alias(f"{col}_normalized")
    ])


def clean_numeric(value: Any) -> Optional[float]:
    """Clean numeric values, handling n.d., n.a., etc."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().lower()
    if s in ('n.d.', 'n.a.', 'n/d', 'n/a', '-', '', 'nan', 'none'):
        return None
    try:
        # Remove commas and convert
        return float(s.replace(',', ''))
    except (ValueError, TypeError):
        return None


def load_excel_to_polars(path: Path, sheet_name: str = "Sheet1") -> pl.LazyFrame:
    """
    Helper to load Excel file to Polars LazyFrame with proper datetime handling.

    Converts datetime columns to string format before passing to Polars
    to avoid conversion issues. Excel files often have mixed types in columns
    (some strings, some datetime objects), so we need to check ALL values.
    """
    import pandas as pd
    from datetime import datetime as dt
    from datetime import date

    pdf = pd.read_excel(path, sheet_name=sheet_name)

    # Convert all potential datetime columns to string before passing to Polars
    for col in pdf.columns:
        col_dtype = str(pdf[col].dtype)

        # Check for datetime64 types
        if 'datetime' in col_dtype:
            pdf[col] = pd.to_datetime(pdf[col], errors='coerce').dt.strftime('%Y-%m-%d')
            continue

        # Check for object dtype that might contain datetime objects
        # Excel often has MIXED types - some strings, some datetime objects in same column
        if pdf[col].dtype == 'object' and len(pdf) > 0:
            # Check if ANY value in the column is a datetime object
            has_datetime = False
            for val in pdf[col].dropna():
                if isinstance(val, (dt, date)):
                    has_datetime = True
                    break

            if has_datetime:
                # Convert ALL values - datetime objects to string, keep strings as is
                def convert_to_str(x):
                    if pd.isna(x):
                        return None
                    if isinstance(x, (dt, date)):
                        return x.strftime('%Y-%m-%d')
                    return str(x)

                pdf[col] = pdf[col].apply(convert_to_str)

    return pl.from_pandas(pdf).lazy()


def get_schema_names(df: pl.LazyFrame) -> List[str]:
    """Get column names from LazyFrame without triggering full schema resolution warning."""
    return df.collect_schema().names()


# =============================================================================
# LEGACY SOURCE LOADERS (from src/bankadvisor/io_loader.py)
# =============================================================================

def load_cnbv_cartera(paths: DataPaths) -> pl.LazyFrame:
    """
    Load CNBV Cartera data (main portfolio data with IFRS9 stages).

    Source: CNBV_Cartera_Bancos_V2.xlsx
    Contains: ~40K records with portfolio by stage (etapa 1/2/3/VR)
    """
    path = paths.cnbv_cartera
    if not path.exists():
        logger.warning(f"CNBV Cartera file not found: {path}")
        return pl.LazyFrame()

    logger.info(f"Loading CNBV Cartera from {path}")

    df = load_excel_to_polars(path, "Sheet1")

    # Normalize column names
    col_names = get_schema_names(df)
    df = df.rename({col: col.strip().lower().replace(" ", "_") for col in col_names})

    # Re-fetch schema after rename
    col_names = get_schema_names(df)

    # Normalize institution code
    if "institucion" in col_names:
        df = normalize_institution_code(df, "institucion")

    # Parse date (now as string, convert back)
    if "fecha" in col_names:
        df = df.with_columns([
            pl.col("fecha").str.to_date("%Y-%m-%d").alias("fecha")
        ])

    logger.info(f"Loaded CNBV Cartera: {df.collect().height} records")
    return df


def load_instituciones(paths: DataPaths) -> pl.LazyFrame:
    """
    Load institutions catalog.

    Source: Instituciones.xlsx
    Contains: 37 institutions with code -> name mapping
    """
    path = paths.instituciones
    if not path.exists():
        logger.warning(f"Instituciones file not found: {path}")
        return pl.LazyFrame()

    logger.info(f"Loading Instituciones from {path}")

    import pandas as pd
    pdf = pd.read_excel(path, sheet_name="Instituciones")
    df = pl.from_pandas(pdf).lazy()

    # Rename and normalize
    df = df.rename({
        "CLAVE": "institucion_code",
        "DESCRIPCION": "banco"
    })
    df = normalize_institution_code(df, "institucion_code")

    logger.info(f"Loaded {df.collect().height} institutions")
    return df


def load_castigos(paths: DataPaths) -> pl.LazyFrame:
    """
    Load castigos (write-offs) data.

    Source: CASTIGOS.xlsx
    """
    path = paths.castigos
    if not path.exists():
        logger.warning(f"Castigos file not found: {path}")
        return pl.LazyFrame()

    logger.info(f"Loading Castigos from {path}")

    df = load_excel_to_polars(path, "CASTIGOS")

    # Normalize column names
    col_names = get_schema_names(df)
    df = df.rename({col: col.strip().lower().replace(" ", "_") for col in col_names})

    # Re-fetch schema
    col_names = get_schema_names(df)

    if "institucion" in col_names:
        df = normalize_institution_code(df, "institucion")

    if "fecha" in col_names:
        # CASTIGOS has MIXED date formats:
        # - Most: "DD/MM/YYYY" (e.g., "01/01/2022")
        # - Some: "YYYY-MM-DD HH:MM:SS" (e.g., "2024-01-10 00:00:00")
        # Use coalesce with strict=False to try both formats
        df = df.with_columns([
            pl.coalesce([
                pl.col("fecha").str.to_date("%d/%m/%Y", strict=False),
                pl.col("fecha").str.slice(0, 10).str.to_date("%Y-%m-%d", strict=False),
            ]).alias("fecha")
        ])

    # Drop junk columns
    junk_cols = [col for col in col_names if col.startswith("unnamed")]
    if junk_cols:
        df = df.drop(junk_cols)

    return df


def load_castigos_comerciales(paths: DataPaths) -> pl.LazyFrame:
    """
    Load commercial write-offs data.

    Source: Castigos Comerciales.xlsx
    """
    path = paths.castigos_comerciales
    if not path.exists():
        logger.warning(f"Castigos Comerciales file not found: {path}")
        return pl.LazyFrame()

    logger.info(f"Loading Castigos Comerciales from {path}")

    df = load_excel_to_polars(path, "Sheet 1")

    # Get column names
    col_names = get_schema_names(df)

    # Rename columns
    rename_map = {
        "Institucion1": "institucion",
        "CASTIGOS ACMULUADOS COMERCIAL": "castigos_acumulados_comercial",
        "Fecha": "fecha"
    }
    df = df.rename({k: v for k, v in rename_map.items() if k in col_names})

    col_names = get_schema_names(df)

    if "institucion" in col_names:
        df = normalize_institution_code(df, "institucion")

    if "fecha" in col_names:
        # Handle multiple date formats (2022/1/01 or 2022-01-01)
        df = df.with_columns([
            pl.when(pl.col("fecha").str.contains("/"))
            .then(pl.col("fecha").str.to_date("%Y/%m/%d", strict=False))
            .otherwise(pl.col("fecha").str.to_date("%Y-%m-%d", strict=False))
            .alias("fecha")
        ])

    return df


def load_icap(paths: DataPaths) -> pl.LazyFrame:
    """
    Load ICAP (Capital Adequacy Index) data.

    Source: ICAP_Bancos.xlsx
    Contains: Monthly ICAP by institution
    """
    path = paths.icap_bancos
    if not path.exists():
        logger.warning(f"ICAP file not found: {path}")
        return pl.LazyFrame()

    logger.info(f"Loading ICAP from {path}")

    df = load_excel_to_polars(path, "ICAP Bancos")

    col_names = get_schema_names(df)

    # Rename columns
    rename_map = {
        "Cve_Inst": "institucion",
        "Banco": "banco",
        "FECHA": "fecha",
        "ICAP Total": "icap_total"
    }
    df = df.rename({k: v for k, v in rename_map.items() if k in col_names})

    col_names = get_schema_names(df)

    if "institucion" in col_names:
        # FIX 2025-12-05: Map INVEX code from 40059 (ICAP file) to 40131 (CNBV standard)
        # This must be done BEFORE normalization (while code is still numeric)
        # Root cause: ICAP uses old code 40059, CNBV uses 40131
        df = df.with_columns([
            pl.when(pl.col("institucion") == 40059.0)
            .then(pl.lit(40131.0))
            .otherwise(pl.col("institucion"))
            .alias("institucion")
        ])
        df = normalize_institution_code(df, "institucion")

    if "fecha" in col_names:
        df = df.with_columns([pl.col("fecha").str.to_date("%Y-%m-%d").alias("fecha")])

    # FIX 2025-12-05: Normalize ICAP from percentage (0-100) to ratio (0-1) scale
    # Root cause: Raw data is in percentages, but analytics_service expects ratios
    if "icap_total" in get_schema_names(df):
        df = df.with_columns([
            (pl.col("icap_total") / 100.0).alias("icap_total")
        ])

    return df


def load_tda(paths: DataPaths) -> pl.LazyFrame:
    """
    Load TDA (Adjusted Default Rate) data.

    Source: TDA.xlsx
    """
    path = paths.tda
    if not path.exists():
        logger.warning(f"TDA file not found: {path}")
        return pl.LazyFrame()

    logger.info(f"Loading TDA from {path}")

    df = load_excel_to_polars(path, "Sheet1")

    col_names = get_schema_names(df)

    # Rename columns
    rename_map = {
        "cve_institucion": "institucion",
        " TDA Cartera total": "tda_cartera_total",
        "Fecha": "fecha"
    }
    df = df.rename({k: v for k, v in rename_map.items() if k in col_names})

    col_names = get_schema_names(df)

    if "institucion" in col_names:
        df = normalize_institution_code(df, "institucion")

    if "fecha" in col_names:
        # TDA has dates in DD/MM/YYYY format (e.g., "12/01/2021")
        df = df.with_columns([pl.col("fecha").str.to_date("%d/%m/%Y").alias("fecha")])

    # FIX 2025-12-05: Normalize TDA from percentage (0-100) to ratio (0-1) scale
    # Root cause: Raw data is in percentages, but analytics_service expects ratios
    if "tda_cartera_total" in get_schema_names(df):
        df = df.with_columns([
            (pl.col("tda_cartera_total") / 100.0).alias("tda_cartera_total")
        ])

    return df


def load_te_invex(paths: DataPaths) -> pl.LazyFrame:
    """
    Load TE (Effective Rate) data for INVEX and Sistema.

    Source: TE_Invex_Sistema.xlsx
    """
    path = paths.te_invex
    if not path.exists():
        logger.warning(f"TE file not found: {path}")
        return pl.LazyFrame()

    logger.info(f"Loading TE from {path}")

    df = load_excel_to_polars(path, "Tasa efectiva considerando prom")

    col_names = get_schema_names(df)

    # Rename columns
    rename_map = {
        "Fecha1": "fecha",
        "Sistema": "tasa_sistema",
        "Invex Consumo": "tasa_invex_consumo"
    }
    df = df.rename({k: v for k, v in rename_map.items() if k in col_names})

    col_names = get_schema_names(df)

    if "fecha" in col_names:
        df = df.with_columns([pl.col("fecha").str.to_date("%Y-%m-%d").alias("fecha")])

    return df


def load_corporate_loan(paths: DataPaths) -> pl.LazyFrame:
    """
    Load Corporate Loan data using pure Polars (high performance).

    Source: CorporateLoan_CNBVDB.csv (219MB, 1.3M+ records)
    Performance: ~4 seconds vs ~45 seconds with Pandas chunks

    Returns aggregated rates by institution and month:
    - tasa_mn: Average rate for MN (Moneda Nacional)
    - tasa_me: Average rate for ME (Moneda Extranjera)
    """
    path = paths.corporate_loan
    if not path.exists():
        logger.warning(f"Corporate Loan file not found: {path}")
        return pl.LazyFrame(schema={
            "fecha": pl.Date,
            "institucion": pl.Utf8,
            "tasa_mn": pl.Float64,
            "tasa_me": pl.Float64
        })

    logger.info(f"Loading Corporate Loan from {path} (219MB, using Polars)")

    # Pure Polars - much faster than Pandas
    # Use utf8-lossy to handle non-UTF8 characters gracefully
    df = pl.scan_csv(
        path,
        encoding="utf8-lossy",
        ignore_errors=True,
        low_memory=False,
    )

    # Normalize column names
    col_names = get_schema_names(df)
    df = df.rename({col: col.strip().lower().replace(" ", "_") for col in col_names})

    # Parse monitoring_term to date (format: M/D/YY)
    df = df.with_columns([
        pl.col("monitoring_term").str.strptime(pl.Date, "%m/%d/%y", strict=False).alias("fecha")
    ])

    # Normalize institution code
    df = df.with_columns([
        pl.col("institution_code").cast(pl.Utf8).str.zfill(6).alias("institucion")
    ])

    # Convert average_rate to float
    df = df.with_columns([
        pl.col("average_rate").cast(pl.Float64, strict=False).alias("average_rate"),
        pl.col("currency").cast(pl.Utf8).alias("currency")
    ])

    # Filter invalid data
    df = df.filter(
        (pl.col("fecha").is_not_null()) &
        (pl.col("institucion").is_not_null()) &
        (pl.col("average_rate").is_not_null()) &
        (pl.col("average_rate") > 0) &
        (pl.col("average_rate") < 100) &
        (pl.col("currency").is_not_null())
    )

    # Extract month for grouping
    df = df.with_columns([
        pl.col("fecha").dt.truncate("1mo").alias("periodo")
    ])

    # Separate MN and ME
    df_mn = df.filter(pl.col("currency").str.to_lowercase().str.contains("nacional"))
    df_me = df.filter(pl.col("currency").str.to_lowercase().str.contains("extranjera"))

    # Aggregate MN by institution and month
    df_mn_agg = df_mn.group_by(["periodo", "institucion"]).agg([
        pl.col("average_rate").mean().alias("tasa_mn"),
        pl.col("average_rate").count().alias("n_mn")
    ])

    # Aggregate ME by institution and month
    df_me_agg = df_me.group_by(["periodo", "institucion"]).agg([
        pl.col("average_rate").mean().alias("tasa_me"),
        pl.col("average_rate").count().alias("n_me")
    ])

    # Join MN and ME
    df_agg = df_mn_agg.join(
        df_me_agg,
        on=["periodo", "institucion"],
        how="outer"
    )

    # Fill nulls and filter unreliable groups
    df_agg = df_agg.with_columns([
        pl.col("n_mn").fill_null(0),
        pl.col("n_me").fill_null(0),
    ])
    df_agg = df_agg.with_columns([
        (pl.col("n_mn") + pl.col("n_me")).alias("n_total")
    ])
    df_agg = df_agg.filter(pl.col("n_total") >= 5)

    # Rename periodo to fecha
    df_agg = df_agg.rename({"periodo": "fecha"})

    # Select final columns
    df_final = df_agg.select(["fecha", "institucion", "tasa_mn", "tasa_me"])

    # FIX 2025-12-05: Normalize tasa_mn/tasa_me from percentage (0-100) to ratio (0-1) scale
    # Root cause: Raw data is in percentages, but analytics_service expects ratios
    df_final = df_final.with_columns([
        (pl.col("tasa_mn") / 100.0).alias("tasa_mn"),
        (pl.col("tasa_me") / 100.0).alias("tasa_me")
    ])

    logger.info("Corporate Loan processing complete")
    return df_final


# =============================================================================
# NORMALIZED SOURCE LOADERS (from etl/etl_processor.py)
# =============================================================================

def _find_header_row(pdf, marker: str, max_rows: int = 20) -> Optional[int]:
    """Find the row containing the header marker."""
    import pandas as pd
    for i in range(min(max_rows, len(pdf))):
        row_values = [str(v).strip().lower() for v in pdf.iloc[i].values if pd.notna(v)]
        if any(marker.lower() in v for v in row_values):
            return i
    return None


def _excel_serial_to_date(serial: Any) -> Optional[str]:
    """Convert Excel serial date to ISO date string."""
    import pandas as pd
    try:
        if isinstance(serial, (int, float)) and serial > 40000:
            # Excel serial date
            date = pd.Timestamp('1899-12-30') + pd.Timedelta(days=int(serial))
            return date.strftime('%Y-%m-%d')
        elif isinstance(serial, str):
            # Try parsing as date string
            parsed = pd.to_datetime(serial, errors='coerce')
            if pd.notna(parsed):
                return parsed.strftime('%Y-%m-%d')
        elif hasattr(serial, 'strftime'):
            return serial.strftime('%Y-%m-%d')
    except Exception:
        pass
    return None


def load_be_bm_sheet(
    paths: DataPaths,
    sheet_name: str,
    metrics: List[str],
    header_marker: str,
    bank_col: int = 1,
    start_col: int = 2,
    step: int = 2,
    num_dates: int = 3
) -> pl.LazyFrame:
    """
    Load a sheet from BE_BM_202509.xlsx with configurable structure.

    Args:
        paths: DataPaths configuration
        sheet_name: Name of the Excel sheet
        metrics: List of metric names to extract
        header_marker: String to find header row
        bank_col: Column index for bank names (0-indexed)
        start_col: Starting column for first date
        step: Step between date columns
        num_dates: Number of date columns

    Returns:
        LazyFrame with columns: institucion, fecha_corte, metric1, metric2, ...
    """
    import pandas as pd

    path = paths.be_bm
    if not path.exists():
        logger.warning(f"BE_BM file not found: {path}")
        return pl.LazyFrame()

    try:
        # Read raw (no header)
        pdf = pd.read_excel(path, sheet_name=sheet_name, header=None)

        # Find header row
        header_row = _find_header_row(pdf, header_marker)
        if header_row is None:
            logger.warning(f"Header not found in sheet {sheet_name}")
            return pl.LazyFrame()

        # Extract dates from header row
        dates = []
        for i in range(num_dates):
            col_idx = start_col + (i * step)
            if col_idx < len(pdf.columns):
                date_val = pdf.iloc[header_row - 1, col_idx] if header_row > 0 else None
                date_str = _excel_serial_to_date(date_val)
                if date_str:
                    dates.append(date_str)

        if not dates:
            logger.warning(f"No dates found in sheet {sheet_name}")
            return pl.LazyFrame()

        # Process data rows
        data_rows = []
        for row_idx in range(header_row + 1, len(pdf)):
            bank_name = pdf.iloc[row_idx, bank_col]
            if pd.isna(bank_name) or str(bank_name).strip() == '':
                continue

            bank_name = str(bank_name).strip()

            # Skip summary rows (but keep Sistema for aggregated data)
            if bank_name.lower() in ('total', 'subtotal'):
                continue

            # Normalize "Sistema  */" to "SISTEMA"
            if 'sistema' in bank_name.lower():
                bank_name = 'SISTEMA'

            # Extract values for each date and metric
            for date_idx, date_str in enumerate(dates):
                row_data = {
                    'institucion': bank_name,
                    'fecha_corte': date_str
                }

                for metric_idx, metric_name in enumerate(metrics):
                    col_idx = start_col + (date_idx * step) + metric_idx
                    if col_idx < len(pdf.columns):
                        value = pdf.iloc[row_idx, col_idx]
                        row_data[metric_name] = clean_numeric(value)
                    else:
                        row_data[metric_name] = None

                data_rows.append(row_data)

        if not data_rows:
            logger.warning(f"No data rows found in sheet {sheet_name}")
            return pl.LazyFrame()

        df = pl.LazyFrame(data_rows)
        logger.info(f"Loaded {len(data_rows)} records from sheet {sheet_name}")
        return df

    except Exception as e:
        logger.error(f"Error loading sheet {sheet_name}: {e}")
        return pl.LazyFrame()


def load_be_bm_pm2(paths: DataPaths) -> pl.LazyFrame:
    """
    Load Pm2 sheet (Balance sheet metrics) with custom parser.

    PM2 structure:
    - Row 4: Metric headers at cols 2, 8, 14, 20, 26, 32 (6 cols apart)
    - Row 5: Dates at cols 2,4,6 for each metric (Sept24, Aug25, Sept25)
    - Rows 6+: Bank data
    """
    path = paths.be_bm
    if not path.exists():
        logger.warning(f"BE_BM file not found: {path}")
        return pl.LazyFrame()

    try:
        pdf = pd.read_excel(path, sheet_name="Pm2", header=None)

        # PM2 structure: each metric is 6 columns apart, with 3 dates per metric
        metric_config = [
            (2, "activo_total"),      # Col 2, 4, 6
            (8, "inversiones_financieras"),  # Col 8, 10, 12
            (14, "cartera_total_pm2"),  # Col 14, 16, 18
            (20, "captacion_total"),   # Col 20, 22, 24
            (26, "capital_contable"),  # Col 26, 28, 30
            (32, "resultado_neto"),    # Col 32, 34, 36
        ]

        # Extract dates from row 5 (using first metric as reference)
        dates = []
        for offset in [0, 2, 4]:  # Columns 2, 4, 6
            date_val = pdf.iloc[5, 2 + offset]
            date_str = _excel_serial_to_date(date_val)
            if date_str:
                dates.append(date_str)

        if not dates:
            logger.warning("No dates found in PM2 sheet")
            return pl.LazyFrame()

        # Process data rows (start from row 6)
        data_rows = []
        for row_idx in range(6, len(pdf)):
            bank_name = pdf.iloc[row_idx, 1]
            if pd.isna(bank_name) or str(bank_name).strip() == '':
                continue

            bank_name = str(bank_name).strip()
            if bank_name.lower() in ('total', 'subtotal'):
                continue

            # Normalize Sistema
            if 'sistema' in bank_name.lower():
                bank_name = 'SISTEMA'

            # For each date
            for date_idx, date_str in enumerate(dates):
                row_data = {
                    'institucion': bank_name,
                    'fecha_corte': date_str
                }

                # For each metric, get value at appropriate column
                for base_col, metric_name in metric_config:
                    col_idx = base_col + (date_idx * 2)  # Dates are 2 cols apart within group
                    if col_idx < len(pdf.columns):
                        value = pdf.iloc[row_idx, col_idx]
                        row_data[metric_name] = clean_numeric(value)
                    else:
                        row_data[metric_name] = None

                data_rows.append(row_data)

        if not data_rows:
            logger.warning("No data rows found in PM2 sheet")
            return pl.LazyFrame()

        df = pl.LazyFrame(data_rows)
        logger.info(f"Loaded {len(data_rows)} records from PM2 (Balance)")
        return df

    except Exception as e:
        logger.error(f"Error loading PM2 sheet: {e}")
        return pl.LazyFrame()


def load_be_bm_indicadores(paths: DataPaths) -> pl.LazyFrame:
    """
    Load Indicadores sheet (ROA, ROE) with custom parser.

    Indicadores structure:
    - Row 4: Col 2=ROA header, Col 5=ROE header
    - Row 5: Dates (3 per metric)
    - Rows 6+: Bank data
    """
    path = paths.be_bm
    if not path.exists():
        logger.warning(f"BE_BM file not found: {path}")
        return pl.LazyFrame()

    try:
        pdf = pd.read_excel(path, sheet_name="Indicadores", header=None)

        # Indicadores structure: ROA at cols 2,3,4; ROE at cols 5,6,7
        # Each metric has 3 dates
        metric_config = [
            (2, "roa_12m"),   # Cols 2, 3, 4
            (5, "roe_12m"),   # Cols 5, 6, 7
        ]

        # Extract dates from row 5
        dates = []
        for col in [3, 4]:  # Aug 2025, Sept 2025 (skip Sept 2024)
            date_val = pdf.iloc[5, col]
            date_str = _excel_serial_to_date(date_val)
            if date_str:
                dates.append(date_str)

        if not dates:
            logger.warning("No dates found in Indicadores sheet")
            return pl.LazyFrame()

        # Process data rows
        data_rows = []
        for row_idx in range(6, len(pdf)):
            bank_name = pdf.iloc[row_idx, 1]
            if pd.isna(bank_name) or str(bank_name).strip() == '':
                continue

            bank_name = str(bank_name).strip()
            if bank_name.lower() in ('total', 'subtotal'):
                continue

            # Normalize Sistema
            if 'sistema' in bank_name.lower():
                bank_name = 'SISTEMA'

            # For each date (using last 2 dates: Aug and Sept 2025)
            for date_idx, date_str in enumerate(dates):
                row_data = {
                    'institucion': bank_name,
                    'fecha_corte': date_str
                }

                # For each metric
                for base_col, metric_name in metric_config:
                    col_idx = base_col + date_idx + 1  # +1 to skip first date
                    if col_idx < len(pdf.columns):
                        value = pdf.iloc[row_idx, col_idx]
                        row_data[metric_name] = clean_numeric(value)
                    else:
                        row_data[metric_name] = None

                data_rows.append(row_data)

        if not data_rows:
            logger.warning("No data rows found in Indicadores sheet")
            return pl.LazyFrame()

        df = pl.LazyFrame(data_rows)
        logger.info(f"Loaded {len(data_rows)} records from Indicadores (ROA, ROE)")
        return df

    except Exception as e:
        logger.error(f"Error loading Indicadores sheet: {e}")
        return pl.LazyFrame()


def load_be_bm_cct(paths: DataPaths) -> pl.LazyFrame:
    """Load CCT sheet (Portfolio quality: IMOR, ICOR, PE)."""
    return load_be_bm_sheet(
        paths,
        sheet_name="CCT",
        metrics=["imor", "icor", "perdida_esperada"],
        header_marker="IMOR",
        bank_col=1,
        start_col=2,
        step=1,
        num_dates=3
    )


def load_be_bm_segment(
    paths: DataPaths,
    sheet_name: str,
    segment_code: str,
    segment_name: str
) -> pl.LazyFrame:
    """
    Load a segment sheet from BE_BM (CCE, CCEF, CCGT, CCCT, CCV, etc.).

    Structure:
    - Col 1: Bank name
    - Cols 2-4: cartera_total (3 dates)
    - Cols 5-7: IMOR
    - Cols 8-10: ICOR
    - Cols 11-13: Perdida Esperada
    """
    import pandas as pd

    path = paths.be_bm
    if not path.exists():
        return pl.LazyFrame()

    try:
        pdf = pd.read_excel(path, sheet_name=sheet_name, header=None)

        # Find header row
        header_row = _find_header_row(pdf, "IMOR")
        if header_row is None:
            header_row = _find_header_row(pdf, "Cartera")
        if header_row is None:
            logger.warning(f"Header not found in segment sheet {sheet_name}")
            return pl.LazyFrame()

        # Extract dates (usually 3)
        dates = []
        for col_idx in [2, 3, 4]:  # Cartera columns
            if col_idx < len(pdf.columns) and header_row > 0:
                date_val = pdf.iloc[header_row - 1, col_idx]
                date_str = _excel_serial_to_date(date_val)
                if date_str:
                    dates.append(date_str)

        if not dates:
            # Try alternative date positions
            dates = ['2024-09-30', '2025-08-31', '2025-09-30']  # Default dates

        # Process data rows
        data_rows = []
        for row_idx in range(header_row + 1, len(pdf)):
            bank_name = pdf.iloc[row_idx, 1]
            if pd.isna(bank_name) or str(bank_name).strip() == '':
                continue

            bank_name = str(bank_name).strip()
            if bank_name.lower() in ('total', 'subtotal'):
                continue

            for date_idx, date_str in enumerate(dates):
                row_data = {
                    'institucion': bank_name,
                    'fecha_corte': date_str,
                    'segmento_codigo': segment_code,
                    'segmento_nombre': segment_name,
                    'cartera_total': clean_numeric(pdf.iloc[row_idx, 2 + date_idx]) if 2 + date_idx < len(pdf.columns) else None,
                    'imor': clean_numeric(pdf.iloc[row_idx, 5 + date_idx]) if 5 + date_idx < len(pdf.columns) else None,
                    'icor': clean_numeric(pdf.iloc[row_idx, 8 + date_idx]) if 8 + date_idx < len(pdf.columns) else None,
                    'perdida_esperada': clean_numeric(pdf.iloc[row_idx, 11 + date_idx]) if 11 + date_idx < len(pdf.columns) else None,
                }
                data_rows.append(row_data)

        if not data_rows:
            return pl.LazyFrame()

        df = pl.LazyFrame(data_rows)
        logger.info(f"Loaded {len(data_rows)} records from segment {sheet_name}")
        return df

    except Exception as e:
        logger.error(f"Error loading segment {sheet_name}: {e}")
        return pl.LazyFrame()


# Segment mapping: sheet_name -> (segment_code, segment_name)
SEGMENT_MAP = {
    "CCE": ("EMPRESAS", "Credito a Empresas"),
    "CCEF": ("ENTIDADES_FINANCIERAS", "Entidades Financieras"),
    "CCGT": ("GUBERNAMENTAL_TOTAL", "Gubernamental Total"),
    "CCG EyM": ("GUB_ESTADOS_MUN", "Estados y Municipios"),
    "CCG OG": ("GUB_OTRAS", "Otras Gubernamentales"),
    "CCCT": ("CONSUMO_TOTAL", "Consumo Total"),
    "CCCTC": ("CONSUMO_TARJETA", "Tarjeta de Credito"),
    "CCCN": ("CONSUMO_NOMINA", "Credito de Nomina"),
    "CCCnrP": ("CONSUMO_PERSONALES", "Prestamos Personales"),
    "CCCAut": ("CONSUMO_AUTOMOTRIZ", "Credito Automotriz"),
    "CCCAdq BiMu": ("CONSUMO_BIENES_MUEBLES", "Bienes Muebles"),
    "CCOAC": ("CONSUMO_ARRENDAMIENTO", "Arrendamiento"),
    "CCCMicro": ("CONSUMO_MICROCREDITOS", "Microcreditos"),
    "CCCnrO": ("CONSUMO_OTROS", "Otros Consumo"),
    "CCV": ("VIVIENDA", "Credito a la Vivienda"),
}


def load_all_segments(paths: DataPaths) -> pl.LazyFrame:
    """Load all segment sheets and concatenate."""
    all_segments = []

    for sheet_name, (code, name) in SEGMENT_MAP.items():
        try:
            df = load_be_bm_segment(paths, sheet_name, code, name)
            if df.collect().height > 0:
                all_segments.append(df)
        except Exception as e:
            logger.warning(f"Could not load segment {sheet_name}: {e}")
            continue

    if not all_segments:
        return pl.LazyFrame()

    return pl.concat(all_segments)


# =============================================================================
# UNIFIED LOADER
# =============================================================================

def load_all_sources(paths: DataPaths) -> Dict[str, pl.LazyFrame]:
    """
    Load all data sources for the unified ETL.

    Returns a dictionary with all loaded DataFrames:
    - Legacy sources: cnbv, instituciones, castigos, icap, tda, te, corporate_rates
    - Normalized sources: pm2, indicadores, cct, segments
    """
    logger.info("="*60)
    logger.info("LOADING ALL DATA SOURCES")
    logger.info("="*60)

    sources = {}

    # Legacy sources
    logger.info("\n--- LEGACY SOURCES ---")
    sources["cnbv"] = load_cnbv_cartera(paths)
    sources["instituciones"] = load_instituciones(paths)
    sources["castigos"] = load_castigos(paths)
    sources["castigos_comerciales"] = load_castigos_comerciales(paths)
    sources["icap"] = load_icap(paths)
    sources["tda"] = load_tda(paths)
    sources["te"] = load_te_invex(paths)
    sources["corporate_rates"] = load_corporate_loan(paths)

    # Normalized sources (BE_BM)
    logger.info("\n--- NORMALIZED SOURCES (BE_BM) ---")
    sources["pm2"] = load_be_bm_pm2(paths)
    sources["indicadores"] = load_be_bm_indicadores(paths)
    sources["cct"] = load_be_bm_cct(paths)
    sources["segments"] = load_all_segments(paths)

    # Summary
    logger.info("\n--- LOADING SUMMARY ---")
    for name, df in sources.items():
        try:
            count = df.collect().height
            logger.info(f"  {name}: {count:,} records")
        except Exception:
            logger.info(f"  {name}: (lazy, not materialized)")

    return sources


__all__ = [
    "DataPaths",
    "get_data_paths",
    "load_all_sources",
    # Legacy loaders
    "load_cnbv_cartera",
    "load_instituciones",
    "load_castigos",
    "load_castigos_comerciales",
    "load_icap",
    "load_tda",
    "load_te_invex",
    "load_corporate_loan",
    # Normalized loaders
    "load_be_bm_pm2",
    "load_be_bm_indicadores",
    "load_be_bm_cct",
    "load_all_segments",
    "SEGMENT_MAP",
]
