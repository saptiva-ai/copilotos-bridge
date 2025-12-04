"""
DEPRECATED: This module is deprecated and will be removed in a future release.
Use the unified transforms instead: bankadvisor.etl.transforms_polars

Migration guide:
    # Old way (pandas-based)
    from bankadvisor.transforms import prepare_cnbv, enrich_with_castigos
    cnbv_clean = prepare_cnbv(dfs["cnbv"])
    full_data = enrich_with_castigos(cnbv_clean, castigos_agg)

    # New way (polars-based, 10x faster)
    from bankadvisor.etl.transforms_polars import prepare_cnbv, enrich_with_castigos
    cnbv_clean = prepare_cnbv(sources["cnbv"])
    full_data = enrich_with_castigos(cnbv_clean, sources["castigos"])

Deprecated since: 2025-12-03
Reason: Consolidated into unified Polars-based ETL for better performance

---
Original docstring:
Calculated fields replicated from the Tableau workbook.

The functions in this module expect the raw tables already loaded with
`io_loader` and return DataFrames enriched with the metrics used across the
report.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Iterable

import pandas as pd


CNBV_RENAME = {
    "Institucion": "institucion",
    "Cve_Periodo": "cve_periodo",
    "Año": "anio",
    "Mes": "mes",
    "Fecha": "fecha",
    "Cartera Total Etapa 2": "cartera_total_etapa_2",
    "Cartera Total Etapa VR": "cartera_total_etapa_vr",
    "Créditos Comerciales Etapa 2": "creditos_comerciales_etapa_2",
    "Créditos de Consumo Etapa 2": "creditos_consumo_etapa_2",
    "Créditos a la Vivienda Etapa 2": "creditos_vivienda_etapa_2",
    "Créditos Comerciales Etapa VR": "creditos_comerciales_etapa_vr",
    "Créditos de Consumo Etapa VR": "creditos_consumo_etapa_vr",
    "Créditos a la Vivienda Etapa VR": "creditos_vivienda_etapa_vr",
    "Actividad Empresarial o Comercial Etapa 2": "actividad_empresarial_etapa_2",
    "Entidades Financieras Etapa 2": "entidades_financieras_etapa_2",
    "Entidades Gubernamentales Etapa 2": "entidades_gubernamentales_etapa_2",
    "Actividad Empresarial o Comercial Etapa VR": "actividad_empresarial_etapa_vr",
    "Entidades Financieras Etapa VR": "entidades_financieras_etapa_vr",
    "Entidades Gubernamentales Etapa VR": "entidades_gubernamentales_etapa_vr",
    "Cartera Total Etapa 1": "cartera_total_etapa_1",
    "Créditos Comerciales Etapa 1": "creditos_comerciales_etapa_1",
    "Actividad Empresarial o Comercial Etapa 1": "actividad_empresarial_etapa_1",
    "Entidades Financieras Etapa 1": "entidades_financieras_etapa_1",
    "Entidades Gubernamentales Etapa 1": "entidades_gubernamentales_etapa_1",
    "Créditos de Consumo Etapa 1": "creditos_consumo_etapa_1",
    "Créditos a la Vivienda Etapa 1": "creditos_vivienda_etapa_1",
    "Cartera de Crédito Total Etapa todas": "cartera_total_etapa_todas",
    "Cartera Total Etapa 3": "cartera_total_etapa_3",
    "Créditos Comerciales Etapa 3": "creditos_comerciales_etapa_3",
    "Actividad Empresarial o Comercial Etapa 3": "actividad_empresarial_etapa_3",
    "Entidades Financieras Etapa 3": "entidades_financieras_etapa_3",
    "Entidades Gubernamentales Etapa 3": "entidades_gubernamentales_etapa_3",
    "Créditos de Consumo Etapa 3": "creditos_consumo_etapa_3",
    "Créditos a la Vivienda Etapa 3": "creditos_vivienda_etapa_3",
    "Reservas Etapa todas": "reservas_etapa_todas",
    "Res Actividad Empresarial o Comercial Etapa todas": "res_actividad_empresarial_etapa_todas",
    "Res Entidades Financieras Etapa todas": "res_entidades_financieras_etapa_todas",
    "Res Entidades Gubernamentales Etapa todas": "res_entidades_gubernamentales_etapa_todas",
    "Res Créditos de Consumo Etapa todas": "res_creditos_consumo_etapa_todas",
    "Res Créditos a la Vivienda Etapa todas": "res_creditos_vivienda_etapa_todas",
}


def ensure_columns(df: pd.DataFrame, required: Iterable[str]) -> None:
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise KeyError(f"Missing expected columns: {missing}")


def normalize_bank_name(series: pd.Series) -> pd.Series:
    """Remove diacritics, punctuation and force uppercase for consistent joins."""
    def _norm(value: object) -> str:
        if value is None:
            return ""
        text = str(value)
        text = unicodedata.normalize("NFKD", text)
        text = text.encode("ASCII", "ignore").decode("ASCII")
        text = text.upper()
        text = re.sub(r"[^A-Z0-9 ]+", "", text)
        return text.strip()

    return series.fillna("").map(_norm)


def prepare_cnbv(df: pd.DataFrame) -> pd.DataFrame:
    ensure_columns(df, CNBV_RENAME.keys())
    data = df.rename(columns=CNBV_RENAME).copy()

    # Category aggregates (replicates Tableau calculated fields).
    empresarial_cols = [
        "actividad_empresarial_etapa_1",
        "actividad_empresarial_etapa_2",
        "actividad_empresarial_etapa_3",
        "actividad_empresarial_etapa_vr",
    ]
    entidades_fin_cols = [
        "entidades_financieras_etapa_1",
        "entidades_financieras_etapa_2",
        "entidades_financieras_etapa_3",
        "entidades_financieras_etapa_vr",
    ]
    entidades_gob_cols = [
        "entidades_gubernamentales_etapa_1",
        "entidades_gubernamentales_etapa_2",
        "entidades_gubernamentales_etapa_3",
        "entidades_gubernamentales_etapa_vr",
    ]
    consumo_cols = [
        "creditos_consumo_etapa_1",
        "creditos_consumo_etapa_2",
        "creditos_consumo_etapa_3",
        "creditos_consumo_etapa_vr",
    ]
    vivienda_cols = [
        "creditos_vivienda_etapa_1",
        "creditos_vivienda_etapa_2",
        "creditos_vivienda_etapa_3",
        "creditos_vivienda_etapa_vr",
    ]

    data["empresarial_total"] = data[empresarial_cols].sum(axis=1)
    data["entidades_financieras_total"] = data[entidades_fin_cols].sum(axis=1)
    data["entidades_gubernamentales_total"] = data[entidades_gob_cols].sum(axis=1)
    data["cartera_comercial_total"] = (
        data["empresarial_total"]
        + data["entidades_financieras_total"]
        + data["entidades_gubernamentales_total"]
    )
    data["cartera_comercial_sin_gob"] = (
        data["cartera_comercial_total"] - data["entidades_gubernamentales_total"]
    )
    data["cartera_consumo_total"] = data[consumo_cols].sum(axis=1)
    data["cartera_vivienda_total"] = data[vivienda_cols].sum(axis=1)
    data["cartera_total"] = (
        data["cartera_comercial_total"]
        + data["cartera_consumo_total"]
        + data["cartera_vivienda_total"]
    )

    # Stage specific aggregates (Comercial Etapa N).
    data["comercial_etapa_1"] = (
        data["actividad_empresarial_etapa_1"]
        + data["entidades_financieras_etapa_1"]
        + data["entidades_gubernamentales_etapa_1"]
    )
    data["comercial_etapa_2"] = (
        data["actividad_empresarial_etapa_2"]
        + data["entidades_financieras_etapa_2"]
        + data["entidades_gubernamentales_etapa_2"]
    )
    data["comercial_etapa_3"] = (
        data["actividad_empresarial_etapa_3"]
        + data["entidades_financieras_etapa_3"]
        + data["entidades_gubernamentales_etapa_3"]
    )
    data["comercial_etapa_vr"] = (
        data["actividad_empresarial_etapa_vr"]
        + data["entidades_financieras_etapa_vr"]
        + data["entidades_gubernamentales_etapa_vr"]
    )

    # Stage ratios vs cartera total (Tableau fields CT_Etapa N).
    with pd.option_context("mode.use_inf_as_na", True):
        data["ct_etapa_1"] = (
            data["comercial_etapa_1"]
            + data["creditos_consumo_etapa_1"]
            + data["creditos_vivienda_etapa_1"]
        ) / data["cartera_total"]
        data["ct_etapa_2"] = (
            data["comercial_etapa_2"]
            + data["creditos_consumo_etapa_2"]
            + data["creditos_vivienda_etapa_2"]
        ) / data["cartera_total"]
        data["ct_etapa_3"] = (
            data["comercial_etapa_3"]
            + data["creditos_consumo_etapa_3"]
            + data["creditos_vivienda_etapa_3"]
        ) / data["cartera_total"]
        data["ct_etapa_vr"] = (
            data["comercial_etapa_vr"]
            + data["creditos_consumo_etapa_vr"]
            + data["creditos_vivienda_etapa_vr"]
        ) / data["cartera_total"]

    data["cartera_vencida"] = (
        data["comercial_etapa_3"] + data["creditos_vivienda_etapa_3"]
    )

    # Pérdida esperada por segmento replicating Tableau sign convention.
    data["pe_total"] = (-data["reservas_etapa_todas"]) / data["cartera_total"]
    data["pe_empresarial"] = -data["res_actividad_empresarial_etapa_todas"] / data[
        "empresarial_total"
    ].replace(0, pd.NA)
    data["pe_entidades_financieras"] = -data[
        "res_entidades_financieras_etapa_todas"
    ] / data["entidades_financieras_total"].replace(0, pd.NA)
    data["pe_entidades_gubernamentales"] = -data[
        "res_entidades_gubernamentales_etapa_todas"
    ] / data["entidades_gubernamentales_total"].replace(0, pd.NA)
    data["pe_consumo"] = -data["res_creditos_consumo_etapa_todas"] / data[
        "cartera_consumo_total"
    ].replace(0, pd.NA)
    data["pe_vivienda"] = -data["res_creditos_vivienda_etapa_todas"] / data[
        "cartera_vivienda_total"
    ].replace(0, pd.NA)

    return data


def prepare_castigos(df: pd.DataFrame) -> pd.DataFrame:
    ensure_columns(
        df,
        [
            "institucion",
            "FECHA",
            "LIB_CASTIGOS_COMERC",
            "LIB_CASTIGOS_ACT_EMP",
            "LIB_CASTIGOS_ENT_FIN",
            "LIB_CASTIGOS_CONSUMO",
            "LIB_CASTIGOS_VIVIENDA",
            "QUITAS_COMER",
        ],
    )
    aggregated = (
        df.rename(columns={"FECHA": "fecha"})
        .sort_values(["institucion", "fecha"])
        .groupby(["institucion", "fecha"], as_index=False)
        .agg(
            {
                "LIB_CASTIGOS_COMERC": "sum",
                "QUITAS_COMER": "sum",
            }
        )
    )
    aggregated["castigos_acumulados_comercial"] = (
        aggregated.groupby("institucion")["LIB_CASTIGOS_COMERC"].cumsum()
    )
    aggregated["quebrantos_cc"] = (
        aggregated["LIB_CASTIGOS_COMERC"] + aggregated["QUITAS_COMER"]
    )
    aggregated = aggregated.rename(
        columns={
            "LIB_CASTIGOS_COMERC": "castigos_corrientes_comercial",
            "QUITAS_COMER": "quitas_comercial",
        }
    )
    return aggregated


def enrich_with_castigos(
    cartera_df: pd.DataFrame,
    castigos_df: pd.DataFrame,
) -> pd.DataFrame:
    merged = cartera_df.merge(
        castigos_df,
        on=["institucion", "fecha"],
        how="left",
        suffixes=("", "_castigos"),
    )
    merged = merged.sort_values(["institucion", "fecha"])
    merged["castigos_acumulados_comercial"] = merged[
        "castigos_acumulados_comercial"
    ].fillna(0)
    merged["quebrantos_cc"] = merged["quebrantos_cc"].fillna(0)
    merged["castigos_corrientes_comercial"] = merged[
        "castigos_corrientes_comercial"
    ].fillna(0)
    merged["quitas_comercial"] = merged["quitas_comercial"].fillna(0)
    merged["imor"] = (
        merged["comercial_etapa_3"] + merged["castigos_acumulados_comercial"]
    ) / merged["cartera_comercial_total"]
    reservas_pos = merged["reservas_etapa_todas"].abs()
    merged["icor"] = reservas_pos / merged["cartera_vencida"].replace(0, pd.NA)
    return merged


__all__ = [
    "prepare_cnbv",
    "prepare_castigos",
    "enrich_with_castigos",
    "normalize_bank_name",
]
