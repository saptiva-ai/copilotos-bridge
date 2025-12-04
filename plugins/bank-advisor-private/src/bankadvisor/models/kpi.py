from sqlalchemy import Column, Integer, Float, String, Date, DateTime
from sqlalchemy.orm import declarative_base

# Use local Base to avoid circular import with db.py
Base = declarative_base()

class MonthlyKPI(Base):
    __tablename__ = "monthly_kpis"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, index=True)
    institucion = Column(String, index=True)
    
    # Carteras
    cartera_total = Column(Float)
    cartera_comercial_total = Column(Float)
    cartera_comercial_sin_gob = Column(Float, nullable=True)  # Comercial - Gobierno
    cartera_consumo_total = Column(Float)
    cartera_vivienda_total = Column(Float)
    entidades_gubernamentales_total = Column(Float)
    entidades_financieras_total = Column(Float)
    empresarial_total = Column(Float)

    # Etapas de Cartera Total (montos absolutos IFRS9)
    cartera_total_etapa_1 = Column(Float, nullable=True)
    cartera_total_etapa_2 = Column(Float, nullable=True)
    cartera_total_etapa_3 = Column(Float, nullable=True)

    # Calidad de Cartera
    cartera_vencida = Column(Float)
    imor = Column(Float)
    icor = Column(Float)
    
    # Reservas
    reservas_etapa_todas = Column(Float)
    reservas_variacion_mm = Column(Float, nullable=True)  # Variación mes a mes (%)

    # Pérdida Esperada (PE)
    pe_total = Column(Float, nullable=True)
    pe_empresarial = Column(Float, nullable=True)
    pe_consumo = Column(Float, nullable=True)
    pe_vivienda = Column(Float, nullable=True)

    # Etapas de Deterioro (ratios sobre cartera total)
    ct_etapa_1 = Column(Float, nullable=True)
    ct_etapa_2 = Column(Float, nullable=True)
    ct_etapa_3 = Column(Float, nullable=True)

    # Porcentaje de Etapas (% sobre cartera total)
    pct_etapa_1 = Column(Float, nullable=True)
    pct_etapa_2 = Column(Float, nullable=True)
    pct_etapa_3 = Column(Float, nullable=True)

    # Quebrantos Comerciales
    quebrantos_comerciales = Column(Float, nullable=True)  # Renamed from quebrantos_cc
    quebrantos_vs_cartera_cc = Column(Float, nullable=True)  # Ratio quebrantos / cartera comercial

    # Tasas
    tasa_mn = Column(Float, nullable=True)
    tasa_me = Column(Float, nullable=True)
    icap_total = Column(Float, nullable=True)
    tda_cartera_total = Column(Float, nullable=True)
    tasa_sistema = Column(Float, nullable=True)  # Tasa Efectiva Sistema
    tasa_invex_consumo = Column(Float, nullable=True)  # Tasa Efectiva INVEX Consumo

    # Market Share
    market_share_pct = Column(Float, nullable=True)  # % de cartera sobre sistema total

    # Metadata
    banco_norm = Column(String, index=True)  # Nombre normalizado (ej: INVEX, BBVA)


class MetricasCarteraSegmentada(Base):
    """
    Métricas de cartera segmentadas por tipo de crédito.

    Segmentos disponibles:
    - Credito Automotriz
    - Credito de Nomina
    - Tarjeta de Credito
    - Prestamos Personales
    - Credito a la Vivienda
    - Credito a Empresas
    - etc.
    """
    __tablename__ = "metricas_cartera_segmentada"

    id = Column(Integer, primary_key=True, index=True)
    institucion = Column(String, index=True)
    fecha_corte = Column(String, index=True)  # Format: YYYY-MM-DD
    segmento_codigo = Column(String)
    segmento_nombre = Column(String, index=True)
    cartera_total = Column(Float)
    imor = Column(Float, nullable=True)
    icor = Column(Float, nullable=True)
    perdida_esperada = Column(Float, nullable=True)


class MetricasFinancierasExt(Base):
    """
    Métricas financieras extendidas incluyendo activos totales y rentabilidad.

    Contiene datos de ~54 instituciones bancarias.
    """
    __tablename__ = "metricas_financieras_ext"

    id = Column(Integer, primary_key=True, index=True)
    institucion = Column(String, index=True)
    fecha_corte = Column(String, index=True)  # Format: YYYY-MM-DD
    activo_total = Column(Float, nullable=True)
    inversiones_financieras = Column(Float, nullable=True)
    cartera_total_pm2 = Column(Float, nullable=True)
    captacion_total = Column(Float, nullable=True)
    capital_contable = Column(Float, nullable=True)
    resultado_neto = Column(Float, nullable=True)
    roa_12m = Column(Float, nullable=True)
    roe_12m = Column(Float, nullable=True)
    banco_norm = Column(String, index=True)
