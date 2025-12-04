"""
Unified Data Transformations using Polars.

Consolidates transformations from both Legacy and Normalized ETL pipelines:
- CNBV portfolio aggregations (etapas IFRS9)
- Castigos (write-offs) enrichment
- ICAP/TDA weighted averages
- Corporate rates merging
- BE_BM metrics merging

All transformations use Polars for maximum performance.
"""
from __future__ import annotations

import polars as pl
from typing import Dict, Optional, List
import structlog

logger = structlog.get_logger(__name__)


def get_cols(df: pl.LazyFrame) -> List[str]:
    """Get column names from LazyFrame without performance warning."""
    return df.collect_schema().names()


# =============================================================================
# BANK NAME NORMALIZATION
# =============================================================================

BANK_NAME_MAPPING = {
    # Normalize common variations
    "BBVA MÉXICO": "BBVA",  # With accent (from Instituciones.xlsx)
    "BBVA MEXICO": "BBVA",
    "BBVA BANCOMER": "BBVA",
    "SANTANDER MEXICO": "SANTANDER",
    "BANCO SANTANDER": "SANTANDER",
    "HSBC MEXICO": "HSBC",
    "SCOTIABANK": "SCOTIABANK",
    "BANCO AZTECA": "AZTECA",
    "BANORTE": "BANORTE",
    "CITIBANAMEX": "CITIBANAMEX",
    "BANAMEX": "CITIBANAMEX",
    "INVEX BANCO": "INVEX",
    "BANCO INVEX": "INVEX",
    "SISTEMA BANCARIO": "SISTEMA",
    "SISTEMA NACIONAL": "SISTEMA",
    "TOTAL SISTEMA": "SISTEMA",
}


def normalize_bank_name(name: str) -> str:
    """Normalize bank name to standard form."""
    if not name:
        return ""

    # Clean up
    name = str(name).strip().upper()
    name = name.replace("*", "").replace("  ", " ").strip()

    # Check mapping
    for pattern, normalized in BANK_NAME_MAPPING.items():
        if pattern in name:
            return normalized

    return name


def add_banco_norm_column(df: pl.LazyFrame, source_col: str = "institucion") -> pl.LazyFrame:
    """Add normalized bank name column."""
    # Get unique values to create mapping
    unique_banks = df.select(pl.col(source_col).unique()).collect()[source_col].to_list()
    mapping = {bank: normalize_bank_name(bank) for bank in unique_banks if bank}

    return df.with_columns([
        pl.col(source_col).replace(mapping).alias("banco_norm")
    ])


# =============================================================================
# CNBV PORTFOLIO TRANSFORMATIONS
# =============================================================================

def enrich_with_instituciones(
    df: pl.LazyFrame,
    instituciones: pl.LazyFrame
) -> pl.LazyFrame:
    """
    Enrich data with bank names from instituciones catalog.

    Args:
        df: DataFrame with institucion column (codes like '040059')
        instituciones: Instituciones catalog with institucion_code -> banco mapping

    Returns:
        DataFrame with banco column added and banco_norm created from it
    """
    logger.info("Enriching with instituciones catalog...")

    # Ensure both have compatible key column
    existing_cols = get_cols(df)

    if "institucion" not in existing_cols:
        logger.warning("No 'institucion' column found, skipping instituciones enrichment")
        return df

    # Join with instituciones
    inst_cols = get_cols(instituciones)
    logger.info(f"Instituciones columns: {inst_cols}")

    # Select relevant columns from instituciones
    inst_subset = instituciones.select([
        pl.col("institucion_code"),
        pl.col("banco")
    ])

    # Join
    df = df.join(
        inst_subset,
        left_on="institucion",
        right_on="institucion_code",
        how="left"
    )

    # Create banco_norm from banco (bank name)
    df = add_banco_norm_column(df, "banco")

    # Log join results
    collected = df.select([pl.col("banco").is_not_null().sum().alias("matched")]).collect()
    matched_count = collected["matched"][0]
    logger.info(f"Instituciones join: {matched_count} records matched")

    return df


def prepare_cnbv(df: pl.LazyFrame, instituciones: Optional[pl.LazyFrame] = None) -> pl.LazyFrame:
    """
    Prepare CNBV cartera data with calculated aggregations.

    Calculates:
    - empresarial_total: Sum of 4 etapas for empresarial
    - entidades_financieras_total: Sum of 4 etapas
    - entidades_gubernamentales_total: Sum of 4 etapas
    - cartera_comercial_total: empresarial + fin + gob
    - cartera_consumo_total: Sum of 4 etapas
    - cartera_vivienda_total: Sum of 4 etapas
    - cartera_total: comercial + consumo + vivienda
    """
    logger.info("Preparing CNBV cartera data...")

    # Column groups for etapa aggregations
    empresarial_cols = [
        "actividad_empresarial_etapa_1",
        "actividad_empresarial_etapa_2",
        "actividad_empresarial_etapa_3",
        "actividad_empresarial_etapa_vr"
    ]

    entidades_fin_cols = [
        "entidades_financieras_etapa_1",
        "entidades_financieras_etapa_2",
        "entidades_financieras_etapa_3",
        "entidades_financieras_etapa_vr"
    ]

    entidades_gob_cols = [
        "entidades_gubernamentales_etapa_1",
        "entidades_gubernamentales_etapa_2",
        "entidades_gubernamentales_etapa_3",
        "entidades_gubernamentales_etapa_vr"
    ]

    consumo_cols = [
        "consumo_etapa_1",
        "consumo_etapa_2",
        "consumo_etapa_3",
        "consumo_etapa_vr"
    ]

    vivienda_cols = [
        "vivienda_etapa_1",
        "vivienda_etapa_2",
        "vivienda_etapa_3",
        "vivienda_etapa_vr"
    ]

    # Check which columns exist
    existing_cols = get_cols(df)

    def safe_sum(cols: List[str]) -> pl.Expr:
        """Sum columns that exist, treating missing as 0."""
        valid_cols = [c for c in cols if c in existing_cols]
        if not valid_cols:
            return pl.lit(0.0)
        return sum(pl.col(c).fill_null(0) for c in valid_cols)

    # Calculate totals
    df = df.with_columns([
        safe_sum(empresarial_cols).alias("empresarial_total"),
        safe_sum(entidades_fin_cols).alias("entidades_financieras_total"),
        safe_sum(entidades_gob_cols).alias("entidades_gubernamentales_total"),
        safe_sum(consumo_cols).alias("cartera_consumo_total"),
        safe_sum(vivienda_cols).alias("cartera_vivienda_total"),
    ])

    # Calculate cartera_comercial_total
    df = df.with_columns([
        (
            pl.col("empresarial_total") +
            pl.col("entidades_financieras_total") +
            pl.col("entidades_gubernamentales_total")
        ).alias("cartera_comercial_total")
    ])

    # Calculate cartera_total
    df = df.with_columns([
        (
            pl.col("cartera_comercial_total") +
            pl.col("cartera_consumo_total") +
            pl.col("cartera_vivienda_total")
        ).alias("cartera_total")
    ])

    # Calculate cartera_vencida (sum of all etapa_3 columns = IFRS9 credit-impaired)
    etapa_3_cols = [c for c in existing_cols if "etapa_3" in c]
    df = df.with_columns([
        safe_sum(etapa_3_cols).alias("cartera_vencida")
    ])

    # Calculate etapa ratios (% of total)
    df = df.with_columns([
        # Etapa 1 ratio
        pl.when(pl.col("cartera_total") > 0)
        .then(
            safe_sum([c for c in existing_cols if "etapa_1" in c]) / pl.col("cartera_total")
        )
        .otherwise(None)
        .alias("ct_etapa_1"),

        # Etapa 2 ratio
        pl.when(pl.col("cartera_total") > 0)
        .then(
            safe_sum([c for c in existing_cols if "etapa_2" in c]) / pl.col("cartera_total")
        )
        .otherwise(None)
        .alias("ct_etapa_2"),

        # Etapa 3 ratio
        pl.when(pl.col("cartera_total") > 0)
        .then(
            safe_sum([c for c in existing_cols if "etapa_3" in c]) / pl.col("cartera_total")
        )
        .otherwise(None)
        .alias("ct_etapa_3"),
    ])

    # Add banco_norm via instituciones enrichment (code -> name mapping)
    if instituciones is not None:
        df = enrich_with_instituciones(df, instituciones)
    elif "institucion" in existing_cols:
        # Fallback to direct normalization (only works if institucion has names)
        df = add_banco_norm_column(df, "institucion")

    return df


def prepare_castigos(df: pl.LazyFrame) -> pl.LazyFrame:
    """Prepare castigos data for merging."""
    logger.info("Preparing castigos data...")

    # Normalize column names
    rename_map = {
        "castigos_acumulados": "castigos_acumulados_total",
        "castigos_corrientes": "castigos_corrientes_total",
    }

    for old, new in rename_map.items():
        if old in get_cols(df):
            df = df.rename({old: new})

    # Normalize institution code
    if "institucion" in get_cols(df):
        df = df.with_columns([
            pl.col("institucion").cast(pl.Utf8).str.zfill(6).alias("institucion")
        ])

    return df


def enrich_with_castigos(
    cartera_df: pl.LazyFrame,
    castigos_df: pl.LazyFrame
) -> pl.LazyFrame:
    """Merge castigos data into cartera data."""
    logger.info("Enriching with castigos data...")

    # Normalize dates for both
    cartera_df = cartera_df.with_columns([
        pl.col("fecha").dt.truncate("1mo").alias("fecha_month")
    ])
    castigos_df = castigos_df.with_columns([
        pl.col("fecha").dt.truncate("1mo").alias("fecha_month")
    ])

    # Select relevant columns from castigos
    castigos_cols = ["fecha_month", "institucion"]
    for col in get_cols(castigos_df):
        if "castigos" in col.lower() or "quebrantos" in col.lower():
            castigos_cols.append(col)

    castigos_subset = castigos_df.select([c for c in castigos_cols if c in get_cols(castigos_df)])

    # Merge
    merged = cartera_df.join(
        castigos_subset,
        on=["fecha_month", "institucion"],
        how="left"
    )

    # Fill nulls for castigos columns
    castigos_fill_cols = [c for c in get_cols(merged) if "castigos" in c.lower() or "quebrantos" in c.lower()]
    for col in castigos_fill_cols:
        merged = merged.with_columns([pl.col(col).fill_null(0)])

    # Drop temporary column
    merged = merged.drop("fecha_month")

    return merged


# =============================================================================
# WEIGHTED AVERAGE CALCULATIONS
# =============================================================================

def calculate_weighted_average(
    df: pl.LazyFrame,
    value_col: str,
    weight_col: str = "cartera_total",
    group_cols: List[str] = None
) -> pl.LazyFrame:
    """
    Calculate weighted average of a metric.

    Formula: Σ(value * weight) / Σ(weight)

    Used for: ICAP, TDA, Tasas
    """
    if group_cols is None:
        group_cols = ["fecha"]

    # Filter out nulls
    df_valid = df.filter(
        pl.col(value_col).is_not_null() &
        pl.col(weight_col).is_not_null() &
        (pl.col(weight_col) > 0)
    )

    # Calculate weighted sum and total weight
    result = df_valid.group_by(group_cols).agg([
        (pl.col(value_col) * pl.col(weight_col)).sum().alias("_weighted_sum"),
        pl.col(weight_col).sum().alias("_total_weight")
    ])

    # Calculate weighted average
    result = result.with_columns([
        (pl.col("_weighted_sum") / pl.col("_total_weight")).alias(f"{value_col}_weighted_avg")
    ]).drop(["_weighted_sum", "_total_weight"])

    return result


def merge_icap(
    full_data: pl.LazyFrame,
    icap_df: pl.LazyFrame
) -> pl.LazyFrame:
    """Merge ICAP data with weighted average calculation."""
    logger.info("Merging ICAP data...")

    # Normalize dates
    full_data = full_data.with_columns([
        pl.col("fecha").dt.truncate("1mo").alias("fecha_month")
    ])
    icap_df = icap_df.with_columns([
        pl.col("fecha").dt.truncate("1mo").alias("fecha_month")
    ])

    # Select ICAP columns
    icap_subset = icap_df.select(["fecha_month", "institucion", "icap_total"])

    # Merge
    merged = full_data.join(
        icap_subset,
        on=["fecha_month", "institucion"],
        how="left"
    )

    merged = merged.drop("fecha_month")
    return merged


def merge_tda(
    full_data: pl.LazyFrame,
    tda_df: pl.LazyFrame
) -> pl.LazyFrame:
    """Merge TDA data."""
    logger.info("Merging TDA data...")

    full_data = full_data.with_columns([
        pl.col("fecha").dt.truncate("1mo").alias("fecha_month")
    ])
    tda_df = tda_df.with_columns([
        pl.col("fecha").dt.truncate("1mo").alias("fecha_month")
    ])

    tda_subset = tda_df.select(["fecha_month", "institucion", "tda_cartera_total"])

    merged = full_data.join(
        tda_subset,
        on=["fecha_month", "institucion"],
        how="left"
    )

    merged = merged.drop("fecha_month")
    return merged


def merge_te(
    full_data: pl.LazyFrame,
    te_df: pl.LazyFrame
) -> pl.LazyFrame:
    """Merge TE (Effective Rates) data."""
    logger.info("Merging TE data...")

    full_data = full_data.with_columns([
        pl.col("fecha").dt.truncate("1mo").alias("fecha_month")
    ])
    te_df = te_df.with_columns([
        pl.col("fecha").dt.truncate("1mo").alias("fecha_month")
    ])

    te_subset = te_df.select(["fecha_month", "tasa_sistema", "tasa_invex_consumo"])

    merged = full_data.join(
        te_subset,
        on="fecha_month",
        how="left"
    )

    merged = merged.drop("fecha_month")
    return merged


def merge_corporate_rates(
    full_data: pl.LazyFrame,
    corp_rates_df: pl.LazyFrame
) -> pl.LazyFrame:
    """Merge corporate rates (MN/ME) data."""
    logger.info("Merging corporate rates...")

    if corp_rates_df.collect().height == 0:
        logger.warning("No corporate rates data to merge")
        return full_data.with_columns([
            pl.lit(None).cast(pl.Float64).alias("tasa_mn"),
            pl.lit(None).cast(pl.Float64).alias("tasa_me"),
        ])

    full_data = full_data.with_columns([
        pl.col("fecha").dt.truncate("1mo").alias("fecha_month")
    ])

    corp_subset = corp_rates_df.select(["fecha", "institucion", "tasa_mn", "tasa_me"])
    corp_subset = corp_subset.rename({"fecha": "fecha_month"})

    merged = full_data.join(
        corp_subset,
        on=["fecha_month", "institucion"],
        how="left"
    )

    merged = merged.drop("fecha_month")
    return merged


# =============================================================================
# METRICS CALCULATIONS
# =============================================================================

def calculate_imor(df: pl.LazyFrame) -> pl.LazyFrame:
    """
    Calculate IMOR (Índice de Morosidad).

    Formula: cartera_vencida / cartera_total
    """
    return df.with_columns([
        pl.when(pl.col("cartera_total") > 0)
        .then(pl.col("cartera_vencida") / pl.col("cartera_total"))
        .otherwise(None)
        .alias("imor")
    ])


def calculate_icor(df: pl.LazyFrame) -> pl.LazyFrame:
    """
    Calculate ICOR (Índice de Cobertura).

    Formula: |reservas| / cartera_vencida

    Note: reservas_etapa_todas is stored as negative (liability convention),
    but ICOR should be positive (coverage ratio percentage).
    """
    return df.with_columns([
        pl.when(pl.col("cartera_vencida") > 0)
        .then(pl.col("reservas_etapa_todas").abs() / pl.col("cartera_vencida"))
        .otherwise(None)
        .alias("icor")
    ])


def calculate_pe(df: pl.LazyFrame) -> pl.LazyFrame:
    """
    Calculate Pérdida Esperada (Expected Loss) ratios.

    PE = -reservas / cartera
    """
    existing_cols = get_cols(df)
    pe_calculations = []

    # PE Total (only if reservas_etapa_todas exists)
    if "reservas_etapa_todas" in existing_cols and "cartera_total" in existing_cols:
        pe_calculations.append(
            pl.when(pl.col("cartera_total") > 0)
            .then(-pl.col("reservas_etapa_todas").fill_null(0) / pl.col("cartera_total"))
            .otherwise(None)
            .alias("pe_total")
        )

    # PE by segment (if BOTH cartera and reservas columns exist)
    # Column names may vary (e.g., "res_actividad_empresarial_o_comercial_etapa_todas")
    segment_mappings = [
        ("empresarial_total", "res_actividad_empresarial_o_comercial_etapa_todas", "pe_empresarial"),
        ("cartera_consumo_total", "res_créditos_de_consumo_etapa_todas", "pe_consumo"),
        ("cartera_vivienda_total", "res_créditos_a_la_vivienda_etapa_todas", "pe_vivienda"),
    ]

    for cartera_col, reservas_col, pe_col in segment_mappings:
        # Check BOTH columns exist before calculating
        if cartera_col in existing_cols and reservas_col in existing_cols:
            pe_calculations.append(
                pl.when(pl.col(cartera_col) > 0)
                .then(-pl.col(reservas_col).fill_null(0) / pl.col(cartera_col))
                .otherwise(None)
                .alias(pe_col)
            )

    if pe_calculations:
        return df.with_columns(pe_calculations)
    return df


def calculate_quebrantos_ratio(df: pl.LazyFrame) -> pl.LazyFrame:
    """Calculate quebrantos vs cartera ratio."""
    cols = get_cols(df)

    # Check for either column name (quebrantos_comerciales or legacy quebrantos_cc)
    quebrantos_col = None
    if "quebrantos_comerciales" in cols:
        quebrantos_col = "quebrantos_comerciales"
    elif "quebrantos_cc" in cols:
        quebrantos_col = "quebrantos_cc"

    if quebrantos_col is None:
        return df

    return df.with_columns([
        pl.when(pl.col("cartera_comercial_total") > 0)
        .then(pl.col(quebrantos_col) / pl.col("cartera_comercial_total"))
        .otherwise(None)
        .alias("quebrantos_vs_cartera_cc")
    ])


def calculate_reservas_variacion(df: pl.LazyFrame) -> pl.LazyFrame:
    """Calculate month-over-month variation in reserves."""
    if "reservas_etapa_todas" not in get_cols(df):
        return df

    return df.with_columns([
        (
            pl.col("reservas_etapa_todas") -
            pl.col("reservas_etapa_todas").shift(1).over("institucion")
        ).alias("reservas_variacion_mm")
    ])


# =============================================================================
# MONTHLY AGGREGATIONS
# =============================================================================

def aggregate_monthly_kpis(
    df: pl.LazyFrame,
    banco_filter: Optional[str] = None
) -> pl.LazyFrame:
    """
    Aggregate data to monthly KPIs by institution.

    Args:
        df: Full data with all metrics
        banco_filter: Optional filter for specific bank (e.g., "INVEX", "SISTEMA")

    Returns:
        Monthly aggregated KPIs
    """
    logger.info(f"Aggregating monthly KPIs (filter: {banco_filter or 'ALL'})")

    # Apply filter if specified
    if banco_filter:
        if banco_filter.upper() == "SISTEMA":
            # SISTEMA = all banks aggregated
            pass  # No filter, aggregate all
        else:
            df = df.filter(pl.col("banco_norm") == banco_filter.upper())

    # Extract month from fecha
    df = df.with_columns([
        pl.col("fecha").dt.truncate("1mo").alias("periodo")
    ])

    # Define aggregations - sum columns
    sum_cols = [
        # Carteras
        "cartera_total", "cartera_comercial_total", "cartera_consumo_total",
        "cartera_vivienda_total", "empresarial_total", "entidades_financieras_total",
        "entidades_gubernamentales_total", "cartera_vencida",
        # Reservas
        "reservas_etapa_todas", "reservas_variacion_mm",
        # Etapas de Deterioro (IFRS9)
        "ct_etapa_1", "ct_etapa_2", "ct_etapa_3",
        "cartera_total_etapa_1", "cartera_total_etapa_2", "cartera_total_etapa_3",
        # Quebrantos
        "quebrantos_cc", "lib_castigos_comerc",
    ]

    # Filter to existing columns
    existing_sum_cols = [c for c in sum_cols if c in get_cols(df)]

    # Build aggregation expressions
    agg_exprs = [pl.col(c).sum().alias(c) for c in existing_sum_cols]

    # Weighted averages for rates
    weighted_cols = ["icap_total", "tda_cartera_total", "tasa_mn", "tasa_me"]
    for col in weighted_cols:
        if col in get_cols(df):
            agg_exprs.append(
                (
                    (pl.col(col) * pl.col("cartera_total")).sum() /
                    pl.col("cartera_total").sum()
                ).alias(col)
            )

    # First values for system-wide rates
    first_cols = ["tasa_sistema", "tasa_invex_consumo"]
    for col in first_cols:
        if col in get_cols(df):
            agg_exprs.append(pl.col(col).first().alias(col))

    # Aggregate
    result = df.group_by("periodo").agg(agg_exprs)

    # Rename periodo to fecha
    result = result.rename({"periodo": "fecha"})

    # Add banco_norm to identify the entity
    entity_name = banco_filter.upper() if banco_filter else "SISTEMA"
    result = result.with_columns([
        pl.lit(entity_name).alias("banco_norm")
    ])

    # Recalculate ratios after aggregation
    result = calculate_imor(result)
    result = calculate_icor(result)
    result = calculate_pe(result)
    result = calculate_quebrantos_ratio(result)

    # Calculate derived metrics
    result_cols = get_cols(result)

    # Cartera Comercial Sin Gobierno
    if "cartera_comercial_total" in result_cols and "entidades_gubernamentales_total" in result_cols:
        result = result.with_columns([
            (pl.col("cartera_comercial_total") - pl.col("entidades_gubernamentales_total"))
            .alias("cartera_comercial_sin_gob")
        ])

    # Rename lib_castigos_comerc to quebrantos_comerciales
    if "lib_castigos_comerc" in result_cols:
        result = result.rename({"lib_castigos_comerc": "quebrantos_comerciales"})

    # Calculate etapa ratios (% of total portfolio in each stage)
    for etapa in [1, 2, 3]:
        etapa_col = f"cartera_total_etapa_{etapa}"
        ratio_col = f"pct_etapa_{etapa}"
        if etapa_col in result_cols and "cartera_total" in result_cols:
            result = result.with_columns([
                (pl.col(etapa_col) / pl.col("cartera_total") * 100).alias(ratio_col)
            ])

    # Add banco_norm
    if banco_filter:
        result = result.with_columns([pl.lit(banco_filter.upper()).alias("banco_norm")])
    else:
        result = result.with_columns([pl.lit("SISTEMA").alias("banco_norm")])

    return result


def calculate_market_share(df: pl.LazyFrame) -> pl.LazyFrame:
    """
    Calculate market share for each bank based on cartera_total.

    Market Share = (bank_cartera_total / sistema_cartera_total) * 100

    Args:
        df: Monthly KPIs with banco_norm and cartera_total columns

    Returns:
        DataFrame with market_share_pct column added
    """
    logger.info("Calculating market share...")

    # Extract SISTEMA totals per period
    sistema = df.filter(pl.col("banco_norm") == "SISTEMA").select([
        pl.col("fecha"),
        pl.col("cartera_total").alias("cartera_sistema")
    ])

    # Join with all banks
    df = df.join(sistema, on="fecha", how="left")

    # Calculate market share
    df = df.with_columns([
        pl.when(pl.col("cartera_sistema") > 0)
        .then((pl.col("cartera_total") / pl.col("cartera_sistema") * 100))
        .otherwise(None)
        .alias("market_share_pct")
    ])

    # Drop temporary column
    df = df.drop("cartera_sistema")

    logger.info("Market share calculated")
    return df


# =============================================================================
# BE_BM MERGING (NORMALIZED)
# =============================================================================

def merge_be_bm_metrics(
    pm2_df: pl.LazyFrame,
    indicadores_df: pl.LazyFrame,
    cct_df: pl.LazyFrame
) -> pl.LazyFrame:
    """
    Merge BE_BM sheets into unified metrics.

    Combines:
    - Pm2: activo_total, cartera_total, capital, resultado
    - Indicadores: ROA, ROE
    - CCT: IMOR, ICOR, PE
    """
    logger.info("Merging BE_BM metrics...")

    # Check if all inputs are empty
    pm2_height = pm2_df.collect().height
    indicadores_height = indicadores_df.collect().height
    cct_height = cct_df.collect().height

    if pm2_height == 0 and indicadores_height == 0 and cct_height == 0:
        logger.warning("All BE_BM inputs are empty, returning empty LazyFrame")
        return pl.LazyFrame()

    # Start with Pm2
    result = pm2_df

    # Merge Indicadores
    if indicadores_height > 0:
        if pm2_height > 0:
            result = result.join(
                indicadores_df,
                on=["institucion", "fecha_corte"],
                how="outer"
            )
        else:
            result = indicadores_df

    # Merge CCT
    if cct_height > 0:
        if result.collect().height > 0:
            result = result.join(
                cct_df,
                on=["institucion", "fecha_corte"],
                how="outer"
            )
        else:
            result = cct_df

    # Add banco_norm only if we have data and institucion column exists
    if result.collect().height > 0 and "institucion" in result.collect_schema().names():
        result = add_banco_norm_column(result, "institucion")

    return result


# =============================================================================
# FULL TRANSFORMATION PIPELINE
# =============================================================================

def transform_all(sources: Dict[str, pl.LazyFrame]) -> Dict[str, pl.LazyFrame]:
    """
    Execute full transformation pipeline on all sources.

    Args:
        sources: Dictionary of loaded DataFrames from loaders_polars.load_all_sources()

    Returns:
        Dictionary with transformed DataFrames:
        - metricas_financieras: Unified financial metrics
        - metricas_segmentadas: Segmented portfolio metrics
        - monthly_kpis: Legacy-compatible monthly KPIs
    """
    logger.info("="*60)
    logger.info("TRANSFORMING ALL DATA")
    logger.info("="*60)

    result = {}

    # 1. Transform Legacy CNBV pipeline
    logger.info("\n--- LEGACY PIPELINE ---")

    if "cnbv" in sources and sources["cnbv"].collect().height > 0:
        # Get instituciones catalog for code -> name mapping
        instituciones = sources.get("instituciones")
        cnbv_prepared = prepare_cnbv(sources["cnbv"], instituciones)

        # Enrich with castigos
        if "castigos" in sources:
            cnbv_prepared = enrich_with_castigos(cnbv_prepared, sources["castigos"])

        # Merge additional sources
        if "icap" in sources:
            cnbv_prepared = merge_icap(cnbv_prepared, sources["icap"])

        if "tda" in sources:
            cnbv_prepared = merge_tda(cnbv_prepared, sources["tda"])

        if "te" in sources:
            cnbv_prepared = merge_te(cnbv_prepared, sources["te"])

        if "corporate_rates" in sources:
            cnbv_prepared = merge_corporate_rates(cnbv_prepared, sources["corporate_rates"])

        # Calculate metrics
        cnbv_prepared = calculate_reservas_variacion(cnbv_prepared)

        result["cnbv_enriched"] = cnbv_prepared

        # Generate monthly KPIs for key entities
        monthly_kpis_list = []

        # INVEX
        kpis_invex = aggregate_monthly_kpis(cnbv_prepared, "INVEX")
        monthly_kpis_list.append(kpis_invex)

        # SISTEMA
        kpis_sistema = aggregate_monthly_kpis(cnbv_prepared, None)  # All banks
        monthly_kpis_list.append(kpis_sistema)

        # Other major banks
        for banco in ["BBVA", "SANTANDER", "BANORTE", "HSBC", "CITIBANAMEX"]:
            try:
                kpis_banco = aggregate_monthly_kpis(cnbv_prepared, banco)
                if kpis_banco.collect().height > 0:
                    monthly_kpis_list.append(kpis_banco)
            except Exception:
                continue

        if monthly_kpis_list:
            monthly_kpis = pl.concat(monthly_kpis_list)
            # Calculate market share for all banks
            monthly_kpis = calculate_market_share(monthly_kpis)
            result["monthly_kpis"] = monthly_kpis

    # 2. Transform Normalized BE_BM pipeline
    logger.info("\n--- NORMALIZED PIPELINE ---")

    if all(k in sources for k in ["pm2", "indicadores", "cct"]):
        metricas_financieras = merge_be_bm_metrics(
            sources["pm2"],
            sources["indicadores"],
            sources["cct"]
        )
        result["metricas_financieras"] = metricas_financieras

    # 3. Segments (already prepared by loader)
    if "segments" in sources and sources["segments"].collect().height > 0:
        result["metricas_segmentadas"] = sources["segments"]

    # Summary
    logger.info("\n--- TRANSFORMATION SUMMARY ---")
    for name, df in result.items():
        try:
            count = df.collect().height
            logger.info(f"  {name}: {count:,} records")
        except Exception:
            logger.info(f"  {name}: (lazy)")

    return result


__all__ = [
    # Bank normalization
    "normalize_bank_name",
    "add_banco_norm_column",
    # CNBV transformations
    "prepare_cnbv",
    "prepare_castigos",
    "enrich_with_castigos",
    # Merging functions
    "merge_icap",
    "merge_tda",
    "merge_te",
    "merge_corporate_rates",
    "merge_be_bm_metrics",
    # Calculations
    "calculate_weighted_average",
    "calculate_imor",
    "calculate_icor",
    "calculate_pe",
    "calculate_quebrantos_ratio",
    "calculate_reservas_variacion",
    # Aggregations
    "aggregate_monthly_kpis",
    # Full pipeline
    "transform_all",
]
