"""
DEPRECATED: This module is deprecated and will be removed in a future release.
Use the unified transforms instead: bankadvisor.etl.transforms_polars

Migration guide:
    # Old way (pandas-based)
    from bankadvisor.metrics import monthly_kpis
    kpis = monthly_kpis(full_data, banco="INVEX")

    # New way (polars-based)
    from bankadvisor.etl.transforms_polars import aggregate_monthly_kpis
    kpis = aggregate_monthly_kpis(full_data, banco_filter="INVEX")

Deprecated since: 2025-12-03
Reason: Consolidated into unified Polars-based ETL for better performance

---
Original docstring:
Aggregations aligned with Tableau KPI tables.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from .transforms import normalize_bank_name


def _filter_institucion(df: pd.DataFrame, banco: Optional[str]) -> pd.DataFrame:
    if banco is None:
        return df
    working = df.copy()
    if "banco_norm" not in working.columns:
        working["banco_norm"] = normalize_bank_name(working.get("banco", ""))
    target_norm = normalize_bank_name(pd.Series([banco])).iloc[0]
    institucion_norm = working["institucion"].astype(str).str.zfill(6)
    mask = working["banco_norm"].eq(target_norm) | institucion_norm.eq(target_norm)
    return working[mask]


def monthly_kpis(
    df: pd.DataFrame,
    *,
    banco: Optional[str] = None,
    months: Optional[int] = None,
    include_rollups: bool = True,
) -> pd.DataFrame:
    data = _filter_institucion(df, banco).copy()
    if data.empty:
        return pd.DataFrame()

    period_index = pd.PeriodIndex(data["fecha"], freq="M", name="periodo")
    grouped = data.groupby(period_index)

    summed = grouped.agg(
        {
            "cartera_total": "sum",
            "cartera_comercial_total": "sum",
            "cartera_comercial_sin_gob": "sum",
            "cartera_consumo_total": "sum",
            "cartera_vivienda_total": "sum",
            "reservas_etapa_todas": "sum",
            "comercial_etapa_1": "sum",
            "comercial_etapa_2": "sum",
            "comercial_etapa_3": "sum",
            "comercial_etapa_vr": "sum",
            "creditos_consumo_etapa_1": "sum",
            "creditos_consumo_etapa_2": "sum",
            "creditos_consumo_etapa_3": "sum",
            "creditos_consumo_etapa_vr": "sum",
            "creditos_vivienda_etapa_1": "sum",
            "creditos_vivienda_etapa_2": "sum",
            "creditos_vivienda_etapa_3": "sum",
            "creditos_vivienda_etapa_vr": "sum",
            "empresarial_total": "sum",
            "entidades_financieras_total": "sum",
            "entidades_gubernamentales_total": "sum",
            "res_actividad_empresarial_etapa_todas": "sum",
            "res_entidades_financieras_etapa_todas": "sum",
            "res_entidades_gubernamentales_etapa_todas": "sum",
            "res_creditos_consumo_etapa_todas": "sum",
            "res_creditos_vivienda_etapa_todas": "sum",
            "cartera_vencida": "sum",
            "castigos_acumulados_comercial": "sum",
            "castigos_corrientes_comercial": "sum",
            "quebrantos_cc": "sum",
            "quitas_comercial": "sum",
        }
    )

    metrics = summed.copy()

    # S0-02: Calcular ICAP (promedio ponderado por cartera o valor directo)
    if "icap_total" in data.columns:
        # Crear columna ponderada: cartera * icap
        data_with_icap = data[data["icap_total"].notna()].copy()

        # ICAP viene en porcentaje (ej: 19.36%), convertir a ratio 0-1
        data_with_icap["icap_ratio"] = data_with_icap["icap_total"] / 100.0

        data_with_icap["icap_weighted"] = (
            data_with_icap["cartera_total"] * data_with_icap["icap_ratio"]
        )

        # Crear period index para los datos con ICAP
        icap_period_index = pd.PeriodIndex(data_with_icap["fecha"], freq="M", name="periodo")

        # Agrupar por periodo
        icap_grouped = data_with_icap.groupby(icap_period_index).agg({
            "icap_weighted": "sum",
            "cartera_total": "sum",
        })

        # Calcular promedio ponderado (ya en escala 0-1)
        metrics["icap_total"] = icap_grouped["icap_weighted"] / icap_grouped["cartera_total"]

    # S0-05: Calcular TDA (promedio ponderado por cartera)
    if "tda_cartera_total" in data.columns:
        # Crear columna ponderada: cartera * tda
        data_with_tda = data[data["tda_cartera_total"].notna()].copy()

        # TDA viene en porcentaje (ej: 3.27%), convertir a ratio 0-1
        data_with_tda["tda_ratio"] = data_with_tda["tda_cartera_total"] / 100.0

        data_with_tda["tda_weighted"] = (
            data_with_tda["cartera_total"] * data_with_tda["tda_ratio"]
        )

        # Crear period index para los datos con TDA
        tda_period_index = pd.PeriodIndex(data_with_tda["fecha"], freq="M", name="periodo")

        # Agrupar por periodo
        tda_grouped = data_with_tda.groupby(tda_period_index).agg({
            "tda_weighted": "sum",
            "cartera_total": "sum",
        })

        # Calcular promedio ponderado (ya en escala 0-1)
        metrics["tda_cartera_total"] = tda_grouped["tda_weighted"] / tda_grouped["cartera_total"]

    # S0-04: Calcular TE (Tasa de Interés Efectiva)
    # TE viene agregado por fecha (mismo valor para todas las instituciones del periodo)
    if "tasa_sistema" in data.columns:
        # Crear period index
        te_period_index = pd.PeriodIndex(data["fecha"], freq="M", name="periodo")

        # Agrupar y tomar el primer valor no nulo (todos son iguales en el periodo)
        te_grouped = data.groupby(te_period_index).agg({
            "tasa_sistema": "first",
            "tasa_invex_consumo": "first" if "tasa_invex_consumo" in data.columns else lambda x: pd.NA,
        })

        # TE viene en porcentaje, convertir a ratio 0-1
        # S1-05: Interpolar NaN (TE es bimestral, falta Nov)
        metrics["tasa_sistema"] = (te_grouped["tasa_sistema"] / 100.0).interpolate(method='linear', limit_direction='both')

        if "tasa_invex_consumo" in data.columns:
            metrics["tasa_invex_consumo"] = (te_grouped["tasa_invex_consumo"] / 100.0).interpolate(method='linear', limit_direction='both')

    # S0-03: Calcular Tasas MN y ME (Corporate Loan)
    # Tasas vienen por institución-fecha-moneda, calcular promedio ponderado
    if "tasa_mn" in data.columns:
        data_with_tasa_mn = data[data["tasa_mn"].notna()].copy()

        # Tasa MN viene en porcentaje, convertir a ratio 0-1
        data_with_tasa_mn["tasa_mn_ratio"] = data_with_tasa_mn["tasa_mn"] / 100.0

        # Ponderar por cartera
        data_with_tasa_mn["tasa_mn_weighted"] = (
            data_with_tasa_mn["cartera_total"] * data_with_tasa_mn["tasa_mn_ratio"]
        )

        # Crear period index
        tasa_mn_period_index = pd.PeriodIndex(data_with_tasa_mn["fecha"], freq="M", name="periodo")

        # Agrupar por periodo
        tasa_mn_grouped = data_with_tasa_mn.groupby(tasa_mn_period_index).agg({
            "tasa_mn_weighted": "sum",
            "cartera_total": "sum",
        })

        # Calcular promedio ponderado (ya en escala 0-1)
        tasa_mn_avg = tasa_mn_grouped["tasa_mn_weighted"] / tasa_mn_grouped["cartera_total"]
        metrics["tasa_mn"] = tasa_mn_avg.apply(lambda x: round(x, 6) if pd.notna(x) else x)

    if "tasa_me" in data.columns:
        data_with_tasa_me = data[data["tasa_me"].notna()].copy()

        # Tasa ME viene en porcentaje, convertir a ratio 0-1
        data_with_tasa_me["tasa_me_ratio"] = data_with_tasa_me["tasa_me"] / 100.0

        # Ponderar por cartera
        data_with_tasa_me["tasa_me_weighted"] = (
            data_with_tasa_me["cartera_total"] * data_with_tasa_me["tasa_me_ratio"]
        )

        # Crear period index
        tasa_me_period_index = pd.PeriodIndex(data_with_tasa_me["fecha"], freq="M", name="periodo")

        # Agrupar por periodo
        tasa_me_grouped = data_with_tasa_me.groupby(tasa_me_period_index).agg({
            "tasa_me_weighted": "sum",
            "cartera_total": "sum",
        })

        # Calcular promedio ponderado (ya en escala 0-1)
        tasa_me_avg = tasa_me_grouped["tasa_me_weighted"] / tasa_me_grouped["cartera_total"]
        metrics["tasa_me"] = tasa_me_avg.apply(lambda x: round(x, 6) if pd.notna(x) else x)

    with pd.option_context("mode.use_inf_as_na", True):
        metrics["pe_total"] = -metrics["reservas_etapa_todas"] / metrics[
            "cartera_total"
        ]
        metrics["pe_empresarial"] = -metrics[
            "res_actividad_empresarial_etapa_todas"
        ] / metrics["empresarial_total"].replace(0, pd.NA)
        metrics["pe_entidades_financieras"] = -metrics[
            "res_entidades_financieras_etapa_todas"
        ] / metrics["entidades_financieras_total"].replace(0, pd.NA)
        metrics["pe_entidades_gubernamentales"] = -metrics[
            "res_entidades_gubernamentales_etapa_todas"
        ] / metrics["entidades_gubernamentales_total"].replace(0, pd.NA)
        metrics["pe_consumo"] = -metrics[
            "res_creditos_consumo_etapa_todas"
        ] / metrics["cartera_consumo_total"].replace(0, pd.NA)
        metrics["pe_vivienda"] = -metrics[
            "res_creditos_vivienda_etapa_todas"
        ] / metrics["cartera_vivienda_total"].replace(0, pd.NA)
        metrics["imor"] = (
            metrics["comercial_etapa_3"] + metrics["castigos_acumulados_comercial"]
        ) / metrics["cartera_comercial_total"]
        reservas_pos = metrics["reservas_etapa_todas"].abs()
        metrics["icor"] = reservas_pos / metrics[
            "cartera_vencida"
        ].replace(0, pd.NA)
        metrics["ct_etapa_1"] = (
            metrics["comercial_etapa_1"]
            + metrics["creditos_consumo_etapa_1"]
            + metrics["creditos_vivienda_etapa_1"]
        ) / metrics["cartera_total"]
        metrics["ct_etapa_2"] = (
            metrics["comercial_etapa_2"]
            + metrics["creditos_consumo_etapa_2"]
            + metrics["creditos_vivienda_etapa_2"]
        ) / metrics["cartera_total"]
        metrics["ct_etapa_3"] = (
            metrics["comercial_etapa_3"]
            + metrics["creditos_consumo_etapa_3"]
            + metrics["creditos_vivienda_etapa_3"]
        ) / metrics["cartera_total"]
        metrics["ct_etapa_vr"] = (
            metrics["comercial_etapa_vr"]
            + metrics["creditos_consumo_etapa_vr"]
            + metrics["creditos_vivienda_etapa_vr"]
        ) / metrics["cartera_total"]
        metrics["quebrantos_vs_cartera_cc"] = metrics["quebrantos_cc"] / metrics[
            "cartera_comercial_total"
        ]

        # S0-01: Reservas totales Variación (m/m)
        metrics["reservas_variacion_mm"] = metrics["reservas_etapa_todas"].pct_change() * 100

    if include_rollups:
        metrics["pe_total_prom_3m"] = (
            metrics["pe_total"].rolling(window=3).mean().shift(1)
        )
        metrics["imor_prom_3m"] = (
            metrics["imor"].rolling(window=3).mean().shift(1)
        )
        metrics["icor_prom_3m"] = (
            metrics["icor"].rolling(window=3).mean().shift(1)
        )

    metrics = metrics.sort_index()
    if months:
        metrics = metrics.tail(months)

    metrics.index = metrics.index.to_timestamp()
    return metrics


__all__ = ["monthly_kpis"]
