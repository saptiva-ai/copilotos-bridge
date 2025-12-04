#!/usr/bin/env python3
"""
DEPRECATED: This module is deprecated and will be removed in a future release.
Use the unified ETL instead: bankadvisor.etl.etl_unified

Migration guide:
    # Old way (pandas-based, generates SQL file)
    python etl_processor.py

    # New way (polars-based, loads directly to PostgreSQL)
    from bankadvisor.etl.etl_unified import UnifiedETL
    etl = UnifiedETL()
    etl.run()

Deprecated since: 2025-12-03
Reason: Consolidated into unified Polars-based ETL for better performance

---
Original docstring:
ETL para BE_BM_202509.xlsx -> carga_inicial_bancos.sql

Requiere: pandas (y openpyxl como backend de Excel).
Lee las hojas Pm2, Indicadores y CCT, limpia valores, hace unpivot a largo,
normaliza nombres de instituciones y genera statements SQL de insercion.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

# Directorios base
ETL_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = ETL_DIR.parent
REPO_ROOT = PLUGIN_ROOT.parent.parent

EXCEL_PATH = PLUGIN_ROOT / "data" / "raw" / "BE_BM_202509.xlsx"
OUTPUT_SQL = ETL_DIR / "carga_inicial_bancos.sql"


def clean_numeric(value):
    """Normaliza valores numericos y devuelve float o None."""
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().lower()
    if text in {"n.d.", "n.d", "n.a.", "n.a", "-", "", "nan"}:
        return None
    text = text.replace(",", "")
    try:
        return float(text)
    except ValueError:
        return None


def normalize_bank_name(name: str | float | int | None) -> str:
    """Limpia pies de pagina o caracteres residuales en el nombre de institucion."""
    if name is None or pd.isna(name):
        return ""
    text = str(name).strip()
    text = text.replace("*/", "").replace("*", "").strip()
    text = re.sub(r"\s{2,}", " ", text)
    return text


def excel_serial_to_date(serial_val) -> str | None:
    """Convierte un serial/fecha de Excel a ISO date (YYYY-MM-DD)."""
    if pd.isna(serial_val):
        return None
    # Si ya viene como datetime/timestamp, solo normalizamos
    if isinstance(serial_val, (pd.Timestamp, datetime)):
        return pd.to_datetime(serial_val).date().isoformat()
    try:
        serial_float = float(serial_val)
    except (TypeError, ValueError):
        return None
    # Excel usa 1899-12-30 como origen (evita el bug de 1900)
    base = pd.to_datetime("1899-12-30")
    return (base + pd.to_timedelta(serial_float, unit="D")).date().isoformat()


def find_header_row(df: pd.DataFrame, marker: str) -> int:
    """Detecta la fila que contiene el marcador de cabecera."""
    marker_lower = marker.lower()
    for idx in range(min(len(df), 25)):
        row_vals = df.iloc[idx].astype(str).str.lower()
        if row_vals.str.contains(marker_lower, na=False).any():
            return idx
    raise ValueError(f"No se encontro la fila de cabecera que contenga '{marker}'.")


def parse_sheet(
    df: pd.DataFrame,
    bank_col: int,
    header_marker: str,
    metrics: List[Tuple[str, int, int, int]],
) -> pd.DataFrame:
    """
    Extrae filas en formato largo para una hoja.

    metrics: lista de tuplas (field_name, start_col, step, num_dates)
             start_col y step son indices de columna basados en header row.
    """
    header_idx = find_header_row(df, header_marker)
    date_row = df.iloc[header_idx + 1]
    data_rows = df.iloc[header_idx + 2 :]

    # Determinar fechas base usando el primer bloque de metricas
    first_metric = metrics[0]
    _, start_col_first, step_first, num_dates_first = first_metric
    dates = []
    for i in range(num_dates_first):
        col_idx = start_col_first + step_first * i
        dates.append(excel_serial_to_date(date_row.iloc[col_idx]))

    records: List[Dict[str, object]] = []
    for _, row in data_rows.iterrows():
        bank_raw = row.iloc[bank_col]
        bank = normalize_bank_name(bank_raw)
        if not bank:
            continue
        for date_idx, fecha in enumerate(dates):
            if not fecha:
                continue
            rec: Dict[str, object] = {"institucion": bank, "fecha_corte": fecha}
            for field, start_col, step, num_dates in metrics:
                if date_idx >= num_dates:
                    continue
                col_idx = start_col + step * date_idx
                rec[field] = clean_numeric(row.iloc[col_idx])
            records.append(rec)

    return pd.DataFrame.from_records(records)


def find_date_row(df: pd.DataFrame, date_cols: List[int]) -> Tuple[int, List[str]]:
    """Localiza la fila con fechas (datetime o serial) y devuelve fechas ISO."""
    for idx in range(min(len(df), 12)):
        row = df.iloc[idx]
        dates = [excel_serial_to_date(row.iloc[c]) for c in date_cols if c < len(row)]
        if all(dates):
            return idx, dates
    raise ValueError("No se encontro fila de fechas.")


def parse_segment_sheet(df: pd.DataFrame, segment_code: str, segment_name: str) -> pd.DataFrame:
    """
    Parsea hojas de cartera segmentada (CCE, CCEF, CCCT, etc.).

    Estructura esperada:
    - Col 1: Banco
    - Cols 2-4: cartera total (tres cortes)
    - Cols 5-7: IMOR
    - Cols 8-10: ICOR
    - Cols 11-13: Perdida esperada (cuando exista)
    """
    date_row_idx, fechas = find_date_row(df, [2, 3, 4])
    data_rows = df.iloc[date_row_idx + 1 :]

    records: List[Dict[str, object]] = []
    for _, row in data_rows.iterrows():
        bank = normalize_bank_name(row.iloc[1] if len(row) > 1 else None)
        if not bank:
            continue
        for i, fecha in enumerate(fechas):
            if not fecha:
                continue

            def get_val(idx: int):
                if idx >= len(row):
                    return None
                return clean_numeric(row.iloc[idx])

            records.append(
                {
                    "segmento_codigo": segment_code,
                    "segmento_nombre": segment_name,
                    "institucion": bank,
                    "fecha_corte": fecha,
                    "cartera_total": get_val(2 + i),
                    "imor": get_val(5 + i),
                    "icor": get_val(8 + i),
                    "perdida_esperada": get_val(11 + i),
                }
            )

    return pd.DataFrame.from_records(records)


def load_all_sheets(excel_path: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Orquesta la lectura de Pm2, Indicadores, CCT y cartera segmentada."""
    if not excel_path.exists():
        raise FileNotFoundError(f"No se encontro el archivo {excel_path}")

    print(f"Leyendo Excel: {excel_path}")
    pm2_raw = pd.read_excel(excel_path, sheet_name="Pm2", header=None, dtype=object, engine="openpyxl")
    ind_raw = pd.read_excel(excel_path, sheet_name="Indicadores", header=None, dtype=object, engine="openpyxl")
    cct_raw = pd.read_excel(excel_path, sheet_name="CCT", header=None, dtype=object, engine="openpyxl")

    pm2 = parse_sheet(
        pm2_raw,
        bank_col=1,
        header_marker="Activo total",
        metrics=[
            ("activo_total", 2, 2, 3),
            ("inversiones_financieras", 8, 2, 3),
            ("cartera_total", 14, 2, 3),
            ("captacion_total", 20, 2, 3),
            ("capital_contable", 26, 2, 3),
            ("resultado_neto", 32, 2, 3),
        ],
    )

    indicadores = parse_sheet(
        ind_raw,
        bank_col=1,
        header_marker="ROA",
        metrics=[
            ("roa_12m", 2, 1, 3),
            ("roe_12m", 5, 1, 3),
        ],
    )

    cct = parse_sheet(
        cct_raw,
        bank_col=1,
        header_marker="IMOR",
        metrics=[
            # cartera_total se ignora en merge si es redundante
            ("cartera_total_cct", 2, 1, 3),
            ("imor", 5, 1, 3),
            ("icor", 8, 1, 3),
            ("perdida_esperada", 11, 1, 3),
        ],
    )

    print("Combinando hojas...")
    master = pm2.merge(indicadores, on=["institucion", "fecha_corte"], how="outer")
    master = master.merge(cct, on=["institucion", "fecha_corte"], how="outer")

    if "cartera_total_cct" in master.columns:
        master = master.drop(columns=["cartera_total_cct"])

    # Elimina duplicados exactos
    master = master.drop_duplicates(subset=["institucion", "fecha_corte"])

    # Normalizacion final de nombres
    master["institucion"] = master["institucion"].apply(normalize_bank_name)

    # ---------------- Cartera segmentada (hojas adicionales) ----------------
    segment_map: Dict[str, Tuple[str, str]] = {
        "CCE": ("EMPRESAS", "Crédito a empresas"),
        "CCEF": ("ENTIDADES_FINANCIERAS", "Crédito a entidades financieras"),
        "CCGT": ("GUBERNAMENTAL_TOTAL", "Crédito gubernamental total"),
        "CCG EyM": ("GUB_ESTADOS_MUN", "Gobiernos estatales y municipales"),
        "CCG OG": ("GUB_OTRAS", "Otras entidades gubernamentales"),
        "CCCT": ("CONSUMO_TOTAL", "Consumo total"),
        "CCCTC": ("CONSUMO_TARJETA", "Tarjetas de crédito"),
        "CCCN": ("CONSUMO_NOMINA", "Crédito de nómina"),
        "CCCnrP": ("CONSUMO_PERSONALES", "Préstamos personales"),
        "CCCAut": ("CONSUMO_AUTOMOTRIZ", "Crédito automotriz"),
        "CCCAdq BiMu": ("CONSUMO_BIENES_MUEBLES", "Bienes muebles"),
        "CCOAC": ("CONSUMO_ARRENDAMIENTO", "Arrendamiento"),
        "CCCMicro": ("CONSUMO_MICROCREDITOS", "Microcréditos"),
        "CCCnrO": ("CONSUMO_OTROS", "Otros créditos de consumo"),
        "CCV": ("VIVIENDA", "Crédito a la vivienda"),
    }

    segment_frames: List[pd.DataFrame] = []
    for sheet_name, (seg_code, seg_name) in segment_map.items():
        try:
            seg_raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=None, dtype=object, engine="openpyxl")
            df_seg = parse_segment_sheet(seg_raw, segment_code=seg_code, segment_name=seg_name)
            if not df_seg.empty:
                segment_frames.append(df_seg)
        except Exception as exc:  # pragma: no cover - defensive
            print(f"[WARN] No se pudo parsear hoja {sheet_name}: {exc}")

    segment_df = pd.concat(segment_frames, ignore_index=True) if segment_frames else pd.DataFrame()

    return master, segment_df


def generate_sql(df: pd.DataFrame, segment_df: pd.DataFrame | None = None) -> str:
    """Genera statements SQL para catalogo, métricas principales y segmentadas."""
    statements: List[str] = []

    # Catalogo de segmentos
    segment_catalog: List[Tuple[str, str, str]] = []
    if segment_df is not None and not segment_df.empty:
        segment_catalog = sorted(
            {
                (row["segmento_codigo"], row["segmento_nombre"], "")
                for _, row in segment_df[["segmento_codigo", "segmento_nombre"]].drop_duplicates().iterrows()
            }
        )

    statements.append("-- Catalogo de instituciones")
    bancos_unicos = sorted(b for b in df["institucion"].dropna().unique() if str(b).strip())
    for banco in bancos_unicos:
        nombre = str(banco).replace("'", "''")
        nombre_corto = nombre.split(" (")[0]
        es_sistema = "TRUE" if nombre.lower().startswith("sistema") else "FALSE"
        statements.append(
            f"INSERT INTO instituciones (nombre_oficial, nombre_corto, es_sistema)\n"
            f"VALUES ('{nombre}', '{nombre_corto}', {es_sistema})\n"
            f"ON CONFLICT (nombre_oficial) DO NOTHING;"
        )

    if segment_catalog:
        statements.append("\n-- Catalogo de segmentos de cartera")
        for code, name, desc in segment_catalog:
            code_sql = code.replace("'", "''")
            name_sql = name.replace("'", "''")
            desc_sql = desc.replace("'", "''") if desc else ""
            statements.append(
                "INSERT INTO segmentos_cartera (codigo, nombre, descripcion)\n"
                f"VALUES ('{code_sql}', '{name_sql}', '{desc_sql}')\n"
                "ON CONFLICT (codigo) DO NOTHING;"
            )

    statements.append("\n-- Metricas financieras")
    for _, row in df.iterrows():
        banco = str(row["institucion"]).replace("'", "''")
        if not banco or banco.lower() == "nan":
            continue

        def fmt(val):
            return "NULL" if pd.isna(val) else str(val)

        statements.append(
            "INSERT INTO metricas_financieras (\n"
            "    institucion_id, fecha_corte,\n"
            "    activo_total, inversiones_financieras, cartera_total,\n"
            "    captacion_total, capital_contable, resultado_neto,\n"
            "    roa_12m, roe_12m, imor, icor, perdida_esperada\n"
            ")\n"
            "VALUES (\n"
            f"    (SELECT id FROM instituciones WHERE nombre_oficial = '{banco}' LIMIT 1),\n"
            f"    '{row['fecha_corte']}',\n"
            f"    {fmt(row.get('activo_total'))}, {fmt(row.get('inversiones_financieras'))}, {fmt(row.get('cartera_total'))},\n"
            f"    {fmt(row.get('captacion_total'))}, {fmt(row.get('capital_contable'))}, {fmt(row.get('resultado_neto'))},\n"
            f"    {fmt(row.get('roa_12m'))}, {fmt(row.get('roe_12m'))},\n"
            f"    {fmt(row.get('imor'))}, {fmt(row.get('icor'))}, {fmt(row.get('perdida_esperada'))}\n"
            ")\n"
            "ON CONFLICT (institucion_id, fecha_corte) DO UPDATE SET\n"
            "    activo_total = EXCLUDED.activo_total,\n"
            "    inversiones_financieras = EXCLUDED.inversiones_financieras,\n"
            "    cartera_total = EXCLUDED.cartera_total,\n"
            "    captacion_total = EXCLUDED.captacion_total,\n"
            "    capital_contable = EXCLUDED.capital_contable,\n"
            "    resultado_neto = EXCLUDED.resultado_neto,\n"
            "    roa_12m = EXCLUDED.roa_12m,\n"
            "    roe_12m = EXCLUDED.roe_12m,\n"
            "    imor = EXCLUDED.imor,\n"
            "    icor = EXCLUDED.icor,\n"
            "    perdida_esperada = EXCLUDED.perdida_esperada;"
        )

    # ---------------- Inserts para cartera segmentada ----------------
    if segment_df is not None and not segment_df.empty:
        statements.append("\n-- Cartera segmentada (IMOR/ICOR por segmento)")
        for _, row in segment_df.iterrows():
            banco = str(row["institucion"]).replace("'", "''")
            if not banco or banco.lower() == "nan":
                continue

            def fmt(val):
                return "NULL" if pd.isna(val) else str(val)

            seg_code = str(row.get("segmento_codigo", "")).replace("'", "''")

            statements.append(
                "INSERT INTO metricas_cartera_segmentada (\n"
                "    institucion_id, segmento_id, fecha_corte,\n"
                "    cartera_total, imor, icor, perdida_esperada\n"
                ")\n"
                "VALUES (\n"
                f"    (SELECT id FROM instituciones WHERE nombre_oficial = '{banco}' LIMIT 1),\n"
                f"    (SELECT id FROM segmentos_cartera WHERE codigo = '{seg_code}' LIMIT 1),\n"
                f"    '{row['fecha_corte']}',\n"
                f"    {fmt(row.get('cartera_total'))}, {fmt(row.get('imor'))}, {fmt(row.get('icor'))}, {fmt(row.get('perdida_esperada'))}\n"
                ")\n"
                "ON CONFLICT (institucion_id, segmento_id, fecha_corte) DO UPDATE SET\n"
                "    cartera_total = EXCLUDED.cartera_total,\n"
                "    imor = EXCLUDED.imor,\n"
                "    icor = EXCLUDED.icor,\n"
                "    perdida_esperada = EXCLUDED.perdida_esperada;"
            )

    return "\n\n".join(statements)


def main():
    df_main, df_segment = load_all_sheets(EXCEL_PATH)
    print(f"Registros totales (métricas principales): {len(df_main)}")
    print(f"Registros totales (cartera segmentada): {len(df_segment)}")
    sql_script = generate_sql(df_main, df_segment)
    OUTPUT_SQL.write_text(sql_script, encoding="utf-8")
    print(f"Archivo generado: {OUTPUT_SQL}")


if __name__ == "__main__":
    main()
