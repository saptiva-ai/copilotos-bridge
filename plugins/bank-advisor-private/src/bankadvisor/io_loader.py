"""
DEPRECATED: This module is deprecated and will be removed in a future release.
Use the unified loaders instead: bankadvisor.etl.loaders_polars

Migration guide:
    # Old way (pandas-based)
    from bankadvisor.io_loader import load_all, get_data_paths
    paths = get_data_paths(data_root)
    dfs = load_all(paths)

    # New way (polars-based, 10x faster)
    from bankadvisor.etl.loaders_polars import get_data_paths, load_all_sources
    paths = get_data_paths(data_root)
    sources = load_all_sources(paths)

Deprecated since: 2025-12-03
Reason: Consolidated into unified Polars-based ETL for better performance

---
Original docstring:
Utilities for loading the raw spreadsheets that powered the Tableau workbook.

Each loader:
  * reads the appropriate sheet / file,
  * enforces basic dtypes (dates, institution codes),
  * returns a pandas DataFrame ready for downstream transformations.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import pandas as pd


# -----------------------------------------------------------------------------
# Core helpers
# -----------------------------------------------------------------------------

def _normalize_code(series: pd.Series, width: int = 6) -> pd.Series:
    """
    Cast institution codes to zero-padded strings.

    Tableau frequently joins on strings such as '040059'; the Excel sources,
    however, store the same codes as integers.  Normalising here saves us from
    repeating the conversion down the pipeline.
    """
    numeric = pd.to_numeric(series, errors="coerce").astype("Int64")
    formatted = numeric.astype(str)
    formatted = formatted.where(
        numeric.isna(),
        formatted.str.zfill(width),
    )
    return formatted


def _coerce_datetime(series: pd.Series) -> pd.Series:
    """Standardise date parsing with pandas' tolerant conversion."""
    return pd.to_datetime(series, errors="coerce")


# -----------------------------------------------------------------------------
# Data configuration
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class DataPaths:
    base_dir: Path

    def file(self, relative: str) -> Path:
        return self.base_dir / relative


def get_data_paths(data_root: Path | str) -> DataPaths:
    """Factory that ensures the directory exists and wraps it in DataPaths."""
    if isinstance(data_root, str):
        data_root = Path(data_root)
    root = data_root.expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Data directory not found: {root}")
    return DataPaths(base_dir=root)


# -----------------------------------------------------------------------------
# Loaders
# -----------------------------------------------------------------------------

def load_cnbv(paths: DataPaths) -> pd.DataFrame:
    path = paths.file("CNBV_Cartera_Bancos_V2.xlsx")
    df = pd.read_excel(path, sheet_name="Sheet1")
    df["Institucion"] = _normalize_code(df["Institucion"])
    df["Fecha"] = _coerce_datetime(df["Fecha"])
    return df


def load_instituciones(paths: DataPaths) -> pd.DataFrame:
    path = paths.file("Instituciones.xlsx")
    df = pd.read_excel(path, sheet_name="Instituciones")
    df = df.rename(columns={"CLAVE": "institucion_code", "DESCRIPCION": "banco"})
    df["institucion_code"] = _normalize_code(df["institucion_code"])
    return df


def load_castigos(paths: DataPaths) -> pd.DataFrame:
    path = paths.file("CASTIGOS.xlsx")
    df = pd.read_excel(path, sheet_name="CASTIGOS")
    df["institucion"] = _normalize_code(df["institucion"])
    df["FECHA"] = _coerce_datetime(df["FECHA"])

    # Drop Tableau artefact columns that only contain NaNs.
    junk_cols = [col for col in df.columns if col.startswith("Unnamed")]
    if junk_cols:
        df = df.drop(columns=junk_cols)
    return df


def load_castigos_comerciales(paths: DataPaths) -> pd.DataFrame:
    path = paths.file("Castigos Comerciales.xlsx")
    df = pd.read_excel(path, sheet_name="Sheet 1")
    df = df.rename(
        columns={
            "Institucion1": "institucion",
            "CASTIGOS ACMULUADOS COMERCIAL": "castigos_acumulados_comercial",
        }
    )
    df["institucion"] = _normalize_code(df["institucion"])
    df["Fecha"] = _coerce_datetime(df["Fecha"])
    return df


def load_icap(paths: DataPaths) -> pd.DataFrame:
    path = paths.file("ICAP_Bancos.xlsx")
    df = pd.read_excel(path, sheet_name="ICAP Bancos")
    df = df.rename(columns={"Cve_Inst": "institucion", "Banco": "banco"})
    df["institucion"] = _normalize_code(df["institucion"])
    df["FECHA"] = _coerce_datetime(df["FECHA"])
    return df


def load_tda(paths: DataPaths) -> pd.DataFrame:
    path = paths.file("TDA.xlsx")
    df = pd.read_excel(path, sheet_name="Sheet1")
    df = df.rename(
        columns={
            "cve_institucion": "institucion",
            " TDA Cartera total": "tda_cartera_total",
        }
    )
    df["institucion"] = _normalize_code(df["institucion"])
    df["Fecha"] = _coerce_datetime(df["Fecha"])
    return df


def load_te(paths: DataPaths) -> pd.DataFrame:
    path = paths.file("TE_Invex_Sistema.xlsx")
    df = pd.read_excel(path)
    df = df.rename(
        columns={
            "Fecha1": "Fecha",
            "Sistema": "tasa_sistema",
            "Invex Consumo": "tasa_invex_consumo",
        }
    )
    df["Fecha"] = _coerce_datetime(df["Fecha"])
    return df


def load_corporate_loan(paths: DataPaths, *, encoding: str = "latin-1") -> pd.DataFrame:
    """
    Load corporate loan data from CSV if available.

    Note: This file (CorporateLoan_CNBVDB.csv) is 218MB and excluded from git.
    Returns empty DataFrame if file doesn't exist.
    """
    path = paths.file("CorporateLoan_CNBVDB.csv")
    if not path.exists():
        # Return empty DataFrame with expected columns if file not present
        return pd.DataFrame(columns=[
            "institution_code", "institution", "monitoring_term",
            "funded", "draw_down_amount"
        ])

    df = pd.read_csv(path, encoding=encoding, low_memory=False)
    # Normalise header spacing for downstream use.
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
    if "institution_code" in df.columns:
        df["institution_code"] = df["institution_code"].astype(str).str.zfill(6)
    if "institution" in df.columns:
        df["institution"] = df["institution"].str.strip()
    if "monitoring_term" in df.columns:
        df["monitoring_term"] = df["monitoring_term"].astype(str).str.strip()
    if "funded" in df.columns:
        df["funded"] = df["funded"].str.strip()
    if "draw_down_amount" in df.columns:
        df["draw_down_amount"] = pd.to_numeric(df["draw_down_amount"], errors="coerce")
    return df


def load_all(paths: DataPaths) -> Dict[str, pd.DataFrame]:
    """Convenience wrapper used by the orchestrator."""
    return {
        "cnbv": load_cnbv(paths),
        "instituciones": load_instituciones(paths),
        "castigos": load_castigos(paths),
        "castigos_comerciales": load_castigos_comerciales(paths),
        "icap": load_icap(paths),
        "tda": load_tda(paths),
        "te": load_te(paths),
        "corporate_loan": load_corporate_loan(paths),
    }


__all__ = [
    "DataPaths",
    "get_data_paths",
    "load_all",
    "load_cnbv",
    "load_instituciones",
    "load_castigos",
    "load_castigos_comerciales",
    "load_icap",
    "load_tda",
    "load_te",
    "load_corporate_loan",
]
