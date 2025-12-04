"""
DEPRECATED: This module is deprecated and will be removed in a future release.
Use the unified ETL instead: bankadvisor.etl.etl_unified

Migration guide:
    # Old way (pandas-based, slow)
    from bankadvisor.etl_loader import run_etl
    run_etl()

    # New way (polars-based, 10x faster)
    from bankadvisor.etl.etl_unified import UnifiedETL
    etl = UnifiedETL()
    etl.run()

Deprecated since: 2025-12-03
Reason: Consolidated into unified Polars-based ETL for better performance
"""
import warnings
warnings.warn(
    "bankadvisor.etl_loader is deprecated. Use bankadvisor.etl.etl_unified instead.",
    DeprecationWarning,
    stacklevel=2
)

import os
import pandas as pd
from sqlalchemy import create_engine
from bankadvisor.io_loader import load_all, get_data_paths
from bankadvisor.transforms import prepare_cnbv, prepare_castigos, enrich_with_castigos
from bankadvisor.metrics import monthly_kpis
from bankadvisor.corporate_rates_processor import process_corporate_rates, merge_corporate_rates
from core.config import get_settings
from pathlib import Path

settings = get_settings()

def run_etl():
    print("🚀 Iniciando ETL de BankAdvisor...")
    
    # 1. Configurar rutas
    # Asumimos que los datos están en apps/api/data/raw (copiados anteriormente)
    data_root = "/app/data/raw"
    if not os.path.exists(data_root):
        # Fallback si se ejecuta desde root del proyecto (local dev)
        data_root = os.path.join(os.path.dirname(__file__), "../../../data/raw")
    
    print(f"📂 Leyendo datos desde: {os.path.abspath(data_root)}")
    paths = get_data_paths(data_root)

    # 2. Cargar fuentes raw
    print("📥 Cargando archivos Excel (esto puede tardar un poco)...")
    dfs = load_all(paths)
    
    # 3. Transformaciones Base
    print("🔄 Ejecutando transformaciones...")
    cnbv_clean = prepare_cnbv(dfs["cnbv"])
    castigos_agg = prepare_castigos(dfs["castigos"])
    
    # Unir Castigos con Cartera
    full_data = enrich_with_castigos(cnbv_clean, castigos_agg)
    
    # Cruzar con Catálogo de Instituciones para tener nombres limpios
    instituciones = dfs["instituciones"]
    full_data = full_data.merge(
        instituciones[["institucion_code", "banco"]],
        left_on="institucion",
        right_on="institucion_code",
        how="left"
    )

    # Agregar Tasas Efectivas (TE) - merge por fecha normalizada a mes
    print("🔗 Integrando datos de Tasas Efectivas...")
    te_data = dfs["te"]
    if not te_data.empty and "Fecha" in te_data.columns:
        # Normalize both dates to first day of month for accurate merge
        # TE data has end-of-month dates, full_data has start-of-month dates
        te_data = te_data.copy()
        te_data["fecha_normalized"] = pd.to_datetime(te_data["Fecha"]).dt.to_period('M').dt.to_timestamp()
        full_data["fecha_normalized"] = pd.to_datetime(full_data["fecha"]).dt.to_period('M').dt.to_timestamp()

        # Merge on normalized month
        full_data = full_data.merge(
            te_data[["fecha_normalized", "tasa_sistema", "tasa_invex_consumo"]],
            on="fecha_normalized",
            how="left"
        )
        # Drop temporary normalized column
        full_data = full_data.drop(columns=["fecha_normalized"])
        print(f"   ✓ Tasas integradas: {full_data['tasa_sistema'].notna().sum()} registros con tasa_sistema")

    # Agregar ICAP (Índice de Capitalización)
    print("🔗 Integrando datos de ICAP...")
    icap_data = dfs["icap"]
    if not icap_data.empty and "FECHA" in icap_data.columns:
        icap_data = icap_data.copy()
        icap_data["fecha_normalized"] = pd.to_datetime(icap_data["FECHA"]).dt.to_period('M').dt.to_timestamp()
        full_data["fecha_normalized"] = pd.to_datetime(full_data["fecha"]).dt.to_period('M').dt.to_timestamp()

        # Merge on fecha and institucion
        full_data = full_data.merge(
            icap_data[["fecha_normalized", "institucion", "ICAP Total"]].rename(columns={"ICAP Total": "icap_total"}),
            left_on=["fecha_normalized", "institucion"],
            right_on=["fecha_normalized", "institucion"],
            how="left"
        )
        full_data = full_data.drop(columns=["fecha_normalized"])
        print(f"   ✓ ICAP integrado: {full_data['icap_total'].notna().sum()} registros con icap_total")

    # Agregar TDA (Tasa de Deterioro Ajustada)
    print("🔗 Integrando datos de TDA...")
    tda_data = dfs["tda"]
    if not tda_data.empty and "Fecha" in tda_data.columns:
        tda_data = tda_data.copy()
        tda_data["fecha_normalized"] = pd.to_datetime(tda_data["Fecha"]).dt.to_period('M').dt.to_timestamp()
        full_data["fecha_normalized"] = pd.to_datetime(full_data["fecha"]).dt.to_period('M').dt.to_timestamp()

        # Merge on fecha and institucion
        full_data = full_data.merge(
            tda_data[["fecha_normalized", "institucion", "tda_cartera_total"]],
            left_on=["fecha_normalized", "institucion"],
            right_on=["fecha_normalized", "institucion"],
            how="left"
        )
        full_data = full_data.drop(columns=["fecha_normalized"])
        print(f"   ✓ TDA integrado: {full_data['tda_cartera_total'].notna().sum()} registros con tda_cartera_total")

    # Agregar Tasas Corporativas (MN/ME) con Polars (alto rendimiento)
    print("🔗 Integrando tasas corporativas MN/ME (procesando 1.3M+ registros con Polars)...")
    corp_csv_path = Path(data_root) / "CorporateLoan_CNBVDB.csv"
    if corp_csv_path.exists():
        try:
            # Process with Polars (much faster than pandas for large files)
            corp_rates = process_corporate_rates(corp_csv_path)

            if not corp_rates.empty:
                # Merge into full_data
                full_data = merge_corporate_rates(full_data, corp_rates)
                mn_count = full_data['tasa_mn'].notna().sum()
                me_count = full_data['tasa_me'].notna().sum()
                print(f"   ✓ Tasas corporativas integradas:")
                print(f"      • Tasa MN: {mn_count} registros")
                print(f"      • Tasa ME: {me_count} registros")
            else:
                print(f"   ⚠ No se pudieron extraer tasas corporativas del archivo")
        except Exception as e:
            print(f"   ⚠ Error procesando tasas corporativas: {str(e)[:100]}")
    else:
        print(f"   ⚠ Archivo Corporate Loan no encontrado: {corp_csv_path}")
    
    # 4. Generar KPIs Mensuales (Agrupados por Banco y Sistema)

    # Identificar bancos principales con suficientes datos
    banco_counts = full_data[full_data['banco'].notna()].groupby('banco').size()
    bancos_principales = banco_counts[banco_counts >= 50].index.tolist()  # Bancos con al menos 50 períodos

    print(f"📊 Calculando KPIs para {len(bancos_principales) + 2} entidades (INVEX, SISTEMA + {len(bancos_principales)} bancos principales)...")

    all_kpis = []

    # 1. INVEX
    print("   • INVEX...")
    kpi_invex = monthly_kpis(full_data, banco="INVEX")
    kpi_invex["banco_norm"] = "INVEX"
    kpi_invex = kpi_invex.reset_index()
    kpi_invex = kpi_invex.rename(columns={"periodo": "fecha"})
    all_kpis.append(kpi_invex)

    # 2. Sistema (Todos)
    print("   • SISTEMA...")
    kpi_sistema = monthly_kpis(full_data, banco=None)
    kpi_sistema["banco_norm"] = "SISTEMA"
    kpi_sistema = kpi_sistema.reset_index()
    kpi_sistema = kpi_sistema.rename(columns={"periodo": "fecha"})
    all_kpis.append(kpi_sistema)

    # 3. Otros bancos principales
    for banco in sorted(bancos_principales):
        if banco and banco not in ['INVEX', 'SISTEMA']:
            print(f"   • {banco}...")
            try:
                kpi_banco = monthly_kpis(full_data, banco=banco)
                kpi_banco["banco_norm"] = banco
                kpi_banco = kpi_banco.reset_index()
                kpi_banco = kpi_banco.rename(columns={"periodo": "fecha"})
                all_kpis.append(kpi_banco)
            except Exception as e:
                print(f"     ⚠ Error calculando KPIs para {banco}: {str(e)[:100]}")

    # Unir todos los KPIs
    final_kpis = pd.concat(all_kpis, ignore_index=True)
    print(f"   ✓ KPIs calculados para {len(all_kpis)} entidades, {len(final_kpis)} registros totales")

    # Limpieza final de columnas para coincidir con el Modelo SQL
    # Convertir PeriodIndex a datetime para compatibilidad con PostgreSQL
    if "fecha" in final_kpis.columns:
        final_kpis["fecha"] = final_kpis["fecha"].apply(lambda x: x.to_timestamp() if hasattr(x, "to_timestamp") else x)

    final_kpis["institucion"] = final_kpis["banco_norm"] # Para simplificar consultas por nombre
    
    # Seleccionar solo columnas que existen en el modelo
    target_columns = [
        "fecha", "institucion", "banco_norm",
        # Carteras
        "cartera_total", "cartera_comercial_total", "cartera_consumo_total",
        "cartera_vivienda_total", "entidades_gubernamentales_total",
        "entidades_financieras_total", "empresarial_total",
        # Calidad de Cartera
        "cartera_vencida", "imor", "icor",
        # Reservas
        "reservas_etapa_todas", "reservas_variacion_mm",
        # Pérdida Esperada
        "pe_total", "pe_empresarial", "pe_consumo", "pe_vivienda",
        # Etapas de Deterioro
        "ct_etapa_1", "ct_etapa_2", "ct_etapa_3",
        # Quebrantos
        "quebrantos_cc", "quebrantos_vs_cartera_cc",
        # Índices y Tasas
        "icap_total", "tda_cartera_total",
        # Tasas de Interés
        "tasa_sistema", "tasa_invex_consumo",
        # Tasas Corporativas
        "tasa_mn", "tasa_me",
    ]
    
    # Filtrar columnas existentes
    cols_to_save = [c for c in target_columns if c in final_kpis.columns]
    final_df = final_kpis[cols_to_save].copy()

    # 5. Cargar a Postgres
    print("💾 Guardando en PostgreSQL...")

    # Use sync database URL from settings
    db_url = settings.database_url_sync

    # Override host if running outside docker
    if not os.path.exists("/.dockerenv"):
        db_url = db_url.replace(f"@{settings.postgres_host}:", "@localhost:")

    engine = create_engine(db_url)
    
    # Guardar (reemplazar tabla completa para idempodencia en dev)
    final_df.to_sql("monthly_kpis", engine, if_exists="replace", index=False)
    
    print(f"✅ Carga completada! {len(final_df)} registros insertados.")

def main():
    """Entry point for ETL execution."""
    run_etl()


if __name__ == "__main__":
    main()
