"""
AnalyticsService - Servicio de consultas de métricas bancarias

Cambios de Seguridad (24 Nov 2025):
- Whitelist explícita de columnas válidas (SAFE_METRIC_COLUMNS)
- Validación guard clause (_get_safe_column)
- Manejo de errores con HTTPException
- Logging estructurado de seguridad
"""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from bankadvisor.models.kpi import MonthlyKPI
from typing import Dict, Any, List, Optional
import difflib
import structlog

logger = structlog.get_logger(__name__)

# Bank color palette for consistent visualization across charts
# Uses distinctive colors optimized for dark and light themes
BANK_COLORS = {
    "INVEX": "#E45756",          # Red (brand color)
    "SISTEMA": "#AAB0B3",        # Grey (neutral benchmark)
    "BBVA": "#004481",           # BBVA Blue
    "SANTANDER": "#EC0000",      # Santander Red
    "BANORTE": "#D7282F",        # Banorte Red
    "HSBC": "#DB0011",           # HSBC Red
    "SCOTIABANK": "#EC1C24",     # Scotia Red
    "INBURSA": "#003DA5",        # Inbursa Blue
    "CITIBANAMEX": "#0065B3",    # Citi Blue
    "AZTECA": "#00A651",         # Azteca Green
    "BAJIO": "#00529B",          # Bajio Blue
    "BANREGIO": "#0033A0",       # Banregio Blue
    "MIFEL": "#8B0304",          # Mifel Dark Red
    "AFIRME": "#005EB8",         # Afirme Blue
    "MULTIVA": "#F58220",        # Multiva Orange
    "ACTINVER": "#006341",       # Actinver Green
    "INTERCAM": "#4A90E2",       # Intercam Light Blue
    "BANSI": "#FF6B35",          # Bansi Orange
    "BARCLAYS": "#00AEEF",       # Barclays Blue
    "MONEX": "#E94E1B",          # Monex Orange
    "VE POR MAS": "#FF8C00",     # Ve por Mas Orange
    "AMERICAN EXPRESS": "#006FCF", # Amex Blue
    "CONSUBANCO": "#7030A0",     # Consubanco Purple
    "BANCO WALMART": "#0071CE",  # Walmart Blue
    "CIBANCO": "#1B365D",        # Cibanco Navy
    "COMPARTAMOS": "#78BE20",    # Compartamos Green
    "BANBAJIO": "#003B5C",       # BanBajio Dark Blue
    "ICBC": "#C8102E",           # ICBC Red
    "INMOBILIARIO": "#6D2077",   # Inmobiliario Purple
    "JP MORGAN": "#117ACA",      # JP Morgan Blue
    "BANK OF AMERICA": "#E31837", # BofA Red
    "MUFG": "#D71920",           # MUFG Red
    "MIZUHO": "#004098",         # Mizuho Blue
    "DEFAULT": "#4F46E5",        # Indigo (fallback for unknown banks)
}


def get_bank_color(bank_name: str) -> str:
    """
    Get consistent color for a bank across all visualizations.

    Args:
        bank_name: Bank name (e.g., "INVEX", "BBVA", "SISTEMA")

    Returns:
        Hex color code
    """
    # Normalize bank name (uppercase, strip whitespace)
    normalized = bank_name.strip().upper()

    # Try exact match first
    if normalized in BANK_COLORS:
        return BANK_COLORS[normalized]

    # Try partial match (e.g., "BBVA BANCOMER" -> "BBVA")
    for bank_key in BANK_COLORS:
        if bank_key in normalized or normalized in bank_key:
            return BANK_COLORS[bank_key]

    # Fallback to default
    return BANK_COLORS["DEFAULT"]


class AnalyticsService:

    # =========================================================================
    # SECURITY: WHITELIST DE COLUMNAS VÁLIDAS
    # =========================================================================
    # Mapeo explícito de nombres de métricas a objetos Column de SQLAlchemy.
    # Previene inyección de atributos vía getattr().
    # Cualquier métrica no listada aquí será rechazada con error 400.

    SAFE_METRIC_COLUMNS = {
        # Carteras
        "cartera_total": MonthlyKPI.cartera_total,
        "cartera_comercial_total": MonthlyKPI.cartera_comercial_total,
        "cartera_comercial_sin_gob": MonthlyKPI.cartera_comercial_sin_gob,
        "cartera_consumo_total": MonthlyKPI.cartera_consumo_total,
        "cartera_vivienda_total": MonthlyKPI.cartera_vivienda_total,
        "entidades_gubernamentales_total": MonthlyKPI.entidades_gubernamentales_total,
        "entidades_financieras_total": MonthlyKPI.entidades_financieras_total,
        "empresarial_total": MonthlyKPI.empresarial_total,

        # Etapas de Cartera Total (montos absolutos IFRS9)
        "cartera_total_etapa_1": MonthlyKPI.cartera_total_etapa_1,
        "cartera_total_etapa_2": MonthlyKPI.cartera_total_etapa_2,
        "cartera_total_etapa_3": MonthlyKPI.cartera_total_etapa_3,

        # Calidad de Cartera
        "cartera_vencida": MonthlyKPI.cartera_vencida,
        "imor": MonthlyKPI.imor,
        "icor": MonthlyKPI.icor,

        # Reservas
        "reservas_etapa_todas": MonthlyKPI.reservas_etapa_todas,
        "reservas_variacion_mm": MonthlyKPI.reservas_variacion_mm,

        # Pérdida Esperada (PE)
        "pe_total": MonthlyKPI.pe_total,
        "pe_empresarial": MonthlyKPI.pe_empresarial,
        "pe_consumo": MonthlyKPI.pe_consumo,
        "pe_vivienda": MonthlyKPI.pe_vivienda,

        # Etapas de Deterioro (ratios)
        "ct_etapa_1": MonthlyKPI.ct_etapa_1,
        "ct_etapa_2": MonthlyKPI.ct_etapa_2,
        "ct_etapa_3": MonthlyKPI.ct_etapa_3,

        # Porcentaje de Etapas (% sobre cartera total)
        "pct_etapa_1": MonthlyKPI.pct_etapa_1,
        "pct_etapa_2": MonthlyKPI.pct_etapa_2,
        "pct_etapa_3": MonthlyKPI.pct_etapa_3,

        # Quebrantos Comerciales
        "quebrantos_comerciales": MonthlyKPI.quebrantos_comerciales,
        "quebrantos_vs_cartera_cc": MonthlyKPI.quebrantos_vs_cartera_cc,

        # Tasas (nullable)
        "tasa_mn": MonthlyKPI.tasa_mn,
        "tasa_me": MonthlyKPI.tasa_me,
        "icap_total": MonthlyKPI.icap_total,
        "tda_cartera_total": MonthlyKPI.tda_cartera_total,
        "tasa_sistema": MonthlyKPI.tasa_sistema,
        "tasa_invex_consumo": MonthlyKPI.tasa_invex_consumo,

        # Market Share
        "market_share_pct": MonthlyKPI.market_share_pct,

        # =========================================================================
        # Métricas Financieras (BE_BM) - from metricas_financieras_ext table
        # Note: These require special handling via get_financial_metric_data()
        # =========================================================================
        # "activo_total": <requires metricas_financieras_ext>,
        # "inversiones_financieras": <requires metricas_financieras_ext>,
        # "captacion_total": <requires metricas_financieras_ext>,
        # "capital_contable": <requires metricas_financieras_ext>,
        # "resultado_neto": <requires metricas_financieras_ext>,
        # "roa_12m": <requires metricas_financieras_ext>,
        # "roe_12m": <requires metricas_financieras_ext>,
    }

    # =========================================================================
    # NLP TOPIC MAP (sin cambios)
    # =========================================================================
    # Mapa de "Frases de Usuario" -> "Columna Real en monthly_kpis"

    TOPIC_MAP = {
        "cartera total": "cartera_total",
        "cartera": "cartera_total",
        "total": "cartera_total",

        "cartera comercial": "cartera_comercial_total",
        "comercial": "cartera_comercial_total",

        "cartera comercial sin gobierno": "cartera_comercial_sin_gob",
        "comercial sin gob": "cartera_comercial_sin_gob",
        "cartera comercial privada": "cartera_comercial_sin_gob",

        "cartera gobierno": "entidades_gubernamentales_total",
        "gobierno": "entidades_gubernamentales_total",

        "cartera consumo": "cartera_consumo_total",
        "consumo": "cartera_consumo_total",

        "cartera vivienda": "cartera_vivienda_total",
        "vivienda": "cartera_vivienda_total",

        "empresarial": "empresarial_total",
        "entidades financieras": "entidades_financieras_total",

        "imor": "imor",
        "morosidad": "imor",

        "icor": "icor",
        "cobertura": "icor",

        "reservas": "reservas_etapa_todas",
        "cartera vencida": "cartera_vencida",
        "vencida": "cartera_vencida",

        # Capitalización y Tasas (agregadas Phase 4)
        "icap": "icap_total",
        "icap_total": "icap_total",  # Direct mapping for legacy flow
        "capitalización": "icap_total",
        "capitalizacion": "icap_total",
        "capital": "icap_total",

        "tda": "tda_cartera_total",
        "tda_cartera_total": "tda_cartera_total",  # Direct mapping for legacy flow
        "deterioro": "tda_cartera_total",
        "tasa deterioro": "tda_cartera_total",

        "tasa_mn": "tasa_mn",
        "tasa mn": "tasa_mn",
        "tasa pesos": "tasa_mn",
        "tasa corporativa moneda nacional": "tasa_mn",
        "tasa corporativa mn": "tasa_mn",
        "tasa moneda nacional": "tasa_mn",
        "credito corporativo mn": "tasa_mn",

        "tasa_me": "tasa_me",
        "tasa me": "tasa_me",
        "tasa dolares": "tasa_me",
        "tasa corporativa moneda extranjera": "tasa_me",
        "tasa corporativa me": "tasa_me",
        "tasa moneda extranjera": "tasa_me",
        "credito corporativo me": "tasa_me",

        # Pérdida Esperada (PE)
        "pe": "pe_total",
        "pe total": "pe_total",
        "perdida esperada": "pe_total",
        "pérdida esperada": "pe_total",
        "pe empresarial": "pe_empresarial",
        "pe consumo": "pe_consumo",
        "pe vivienda": "pe_vivienda",

        # Variación de Reservas
        "reservas variacion": "reservas_variacion_mm",
        "variación reservas": "reservas_variacion_mm",
        "variacion reservas": "reservas_variacion_mm",
        "reservas mes a mes": "reservas_variacion_mm",

        # Etapas de Deterioro
        "etapa 1": "ct_etapa_1",
        "etapa 2": "ct_etapa_2",
        "etapa 3": "ct_etapa_3",
        "ct etapa 1": "ct_etapa_1",
        "ct etapa 2": "ct_etapa_2",
        "ct etapa 3": "ct_etapa_3",
        "deterioro etapa 1": "ct_etapa_1",
        "deterioro etapa 2": "ct_etapa_2",
        "deterioro etapa 3": "ct_etapa_3",
        "cartera etapa 1": "ct_etapa_1",
        "cartera etapa 2": "ct_etapa_2",
        "cartera etapa 3": "ct_etapa_3",
        "etapas de deterioro": "ct_etapa_1",  # Default to etapa 1 for general queries
        "etapas deterioro": "ct_etapa_1",
        "ifrs9": "ct_etapa_1",

        # Quebrantos Comerciales
        "quebrantos": "quebrantos_comerciales",
        "quebrantos comerciales": "quebrantos_comerciales",
        "castigos comerciales": "quebrantos_comerciales",
        "write-offs": "quebrantos_comerciales",
        "castigos": "quebrantos_comerciales",
        "quebrantos vs cartera": "quebrantos_vs_cartera_cc",
        "ratio quebrantos": "quebrantos_vs_cartera_cc",

        # Tasas de Interés Efectiva
        "te sistema": "tasa_sistema",
        "tasa efectiva sistema": "tasa_sistema",
        "tasa sistema": "tasa_sistema",
        "te invex": "tasa_invex_consumo",
        "tasa efectiva invex": "tasa_invex_consumo",
        "tasa invex consumo": "tasa_invex_consumo",
        "te invex consumo": "tasa_invex_consumo",

        # Market Share (PDM)
        "market share": "market_share_pct",
        "participacion de mercado": "market_share_pct",
        "participación de mercado": "market_share_pct",
        "pdm": "market_share_pct",
        "cuota de mercado": "market_share_pct",
        "porcentaje de mercado": "market_share_pct",
    }

    # Priority metric names - match these as WHOLE WORDS first before other logic
    PRIORITY_METRICS = {
        "imor": "imor",
        "icor": "icor",
        "icap": "icap_total",
        "tda": "tda_cartera_total",
        "roa": "roa",
        "roe": "roe",
        "variación": "reservas_variacion_mm",  # "Variación de reservas"
        "variacion": "reservas_variacion_mm",  # Without accent
    }

    @staticmethod
    def resolve_metric_id(user_query: str) -> Optional[str]:
        """
        Resuelve una query de usuario a un nombre de columna válido.

        Estrategia:
        1. Match exacto en TOPIC_MAP
        2. Match de métricas prioritarias (IMOR, ICOR, etc.) como palabras completas
        3. Match de keywords largos primero (para evitar matches espurios)
        4. Fuzzy matching (cutoff 0.6)

        Args:
            user_query: Query del usuario (ej: "cartera comercial de INVEX")

        Returns:
            Nombre de columna o None si no hay match
        """
        query_lower = user_query.lower()

        # 1. Match exacto
        if query_lower in AnalyticsService.TOPIC_MAP:
            return AnalyticsService.TOPIC_MAP[query_lower]

        # 2. Match de métricas prioritarias como PALABRAS COMPLETAS
        # Esto evita que "INVEX" matchee antes de "IMOR" en "IMOR de INVEX"
        import re
        for metric, column in AnalyticsService.PRIORITY_METRICS.items():
            # Match as whole word (not part of another word)
            if re.search(rf'\b{metric}\b', query_lower):
                return column

        # 3. Match parcial - Buscar keywords ORDENADOS por longitud (longest first)
        # Esto evita que "tda" matchee antes de "tda cartera total"
        sorted_keys = sorted(
            AnalyticsService.TOPIC_MAP.keys(),
            key=len,
            reverse=True
        )

        # Skip keys that contain bank names to avoid "invex" matching
        bank_keywords = {'invex', 'bbva', 'santander', 'banorte', 'hsbc', 'sistema'}

        for key in sorted_keys:
            # Skip if key is or contains a bank name
            key_words = set(key.split())
            if key_words & bank_keywords:
                continue

            if key in query_lower:
                # Security: Keyword must be at least 2 words or 6 chars
                if len(key) >= 6 or ' ' in key:
                    return AnalyticsService.TOPIC_MAP[key]

        # 4. Now check bank-specific metrics (like "tasa invex consumo")
        for key in sorted_keys:
            if key in query_lower:
                if len(key) >= 6 or ' ' in key:
                    return AnalyticsService.TOPIC_MAP[key]

        # 5. Fuzzy matching - SECURITY: Cutoff más estricto (0.6)
        # Only use fuzzy for short queries (< 30 chars) to avoid performance issues
        if len(query_lower) < 30:
            matches = difflib.get_close_matches(
                query_lower,
                AnalyticsService.TOPIC_MAP.keys(),
                n=1,
                cutoff=0.6
            )
            if matches:
                return AnalyticsService.TOPIC_MAP[matches[0]]

        return None

    @staticmethod
    def _get_safe_column(metric_name: str):
        """
        SECURITY GUARD: Valida que la métrica esté en la whitelist.

        Pattern: Guard Clause / Whitelist Validation

        Previene:
        - Inyección de atributos vía getattr()
        - Acceso a metadatos internos de SQLAlchemy (__class__, metadata, etc.)
        - DoS por atributos inexistentes

        Args:
            metric_name: Nombre de columna (ej: "cartera_total")

        Returns:
            Column object de SQLAlchemy

        Raises:
            ValueError: Si la métrica no está en la whitelist

        Example:
            >>> _get_safe_column("cartera_total")  # OK
            >>> _get_safe_column("__class__")  # ValueError
        """
        if metric_name not in AnalyticsService.SAFE_METRIC_COLUMNS:
            # Security logging - alerta de intento de acceso no autorizado
            logger.warning(
                "security.metric_validation_failed",
                metric=metric_name,
                valid_metrics_sample=list(AnalyticsService.SAFE_METRIC_COLUMNS.keys())[:5],
                total_valid_metrics=len(AnalyticsService.SAFE_METRIC_COLUMNS)
            )

            # Error amigable al usuario con sugerencias
            valid_sample = list(AnalyticsService.SAFE_METRIC_COLUMNS.keys())[:5]
            raise ValueError(
                f"Métrica '{metric_name}' no está autorizada. "
                f"Métricas válidas incluyen: {', '.join(valid_sample)}, etc. "
                f"Total de métricas disponibles: {len(AnalyticsService.SAFE_METRIC_COLUMNS)}"
            )

        return AnalyticsService.SAFE_METRIC_COLUMNS[metric_name]

    @staticmethod
    async def get_dashboard_data(
        session: AsyncSession,
        metric_or_query: str,
        mode: str = "dashboard"
    ) -> Dict[str, Any]:
        """
        Obtiene datos de dashboard con validación de seguridad.

        Security Improvements (24 Nov 2025):
        - Whitelist validation antes de acceder a columnas
        - Try/except con manejo granular de errores (400/503/500)
        - Logging estructurado para auditoría
        - Mensajes de error user-friendly

        Args:
            session: Sesión async de SQLAlchemy
            metric_or_query: Nombre de métrica o query de usuario
            mode: Modo de visualización (dashboard/timeline)

        Returns:
            Dict con datos formateados para Plotly

        Raises:
            HTTPException(400): Métrica no válida
            HTTPException(503): Error de base de datos
            HTTPException(500): Error inesperado

        Example:
            >>> data = await get_dashboard_data(session, "cartera comercial")
            >>> data["title"]
            "Cartera Comercial Total"
        """
        try:
            # 1. Resolver ID con NLP
            metric_column = AnalyticsService.resolve_metric_id(metric_or_query)

            # SECURITY: Si el NLP no puede resolver, rechazar directamente
            # No permitir fallback a metric_or_query sin validación NLP
            if metric_column is None:
                logger.warning(
                    "security.nlp_resolution_failed",
                    query=metric_or_query,
                    reason="No match in TOPIC_MAP"
                )
                raise ValueError(
                    f"No se pudo identificar la métrica '{metric_or_query}'. "
                    f"Por favor, usa términos como: 'cartera comercial', 'IMOR', 'ICOR', etc."
                )

            final_column_name = metric_column

            # 2. SECURITY: Validación de whitelist (reemplaza getattr vulnerable)
            safe_column = AnalyticsService._get_safe_column(final_column_name)

            logger.info(
                "analytics.query_started",
                metric=final_column_name,
                original_query=metric_or_query,
                mode=mode
            )

            # 3. Obtener fecha de corte (Data As Of)
            date_query = select(func.max(MonthlyKPI.fecha))
            date_result = await session.execute(date_query)
            max_date = date_result.scalar()
            data_as_of = max_date.strftime("%d/%m/%Y") if max_date else "N/A"

            # 4. Consulta SQL con columna validada
            query = (
                select(MonthlyKPI.fecha, MonthlyKPI.banco_norm, safe_column)
                .order_by(MonthlyKPI.fecha.asc())
            )

            result = await session.execute(query)
            rows = result.fetchall()

            logger.info(
                "analytics.query_completed",
                metric=final_column_name,
                rows_returned=len(rows),
                data_as_of=data_as_of
            )

            # 5. Procesar resultados
            data_by_month = {}

            for row in rows:
                date_str = row.fecha.strftime("%Y-%m") if row.fecha else "N/A"
                banco = row.banco_norm
                val = row[2]

                if date_str not in data_by_month:
                    data_by_month[date_str] = []

                # Handle NULL values: skip records with NULL metric values
                # This prevents "unsupported format string passed to NoneType" errors
                if val is None:
                    continue

                # Normalizar ratios a porcentaje
                if final_column_name in ["imor", "icor"]:
                    val = val * 100 if val else 0

                data_by_month[date_str].append({
                    "category": banco,
                    "value": val
                })

            chart_data = [
                {"month_label": k, "data": v}
                for k, v in data_by_month.items()
            ]

            return {
                "title": final_column_name.replace("_", " ").title(),
                "layout_type": "dashboard_month_comparison",
                "period": "Historico",
                "data_as_of": data_as_of,
                "chart_props": {
                    "colors": ["rose", "slate"],
                    "valueFormatter": (
                        "(number) => `${number.toFixed(2)}%`"
                        if final_column_name in ["imor", "icor"]
                        else "(number) => `$${Intl.NumberFormat('us', {notation: 'compact'}).format(number)}`"
                    )
                },
                "data": {
                    "months": chart_data
                }
            }

        except ValueError as ve:
            # Error de validación de negocio (400 Bad Request)
            # Incluye: métrica no válida, parámetros incorrectos
            logger.info(
                "analytics.validation_error",
                metric=metric_or_query,
                error=str(ve),
                error_type="ValueError"
            )
            raise HTTPException(
                status_code=400,
                detail=str(ve)
            )

        except SQLAlchemyError as db_err:
            # Error de base de datos (503 Service Unavailable)
            # Incluye: conexión perdida, timeout, constraint violations
            logger.error(
                "analytics.database_error",
                metric=metric_or_query,
                error=str(db_err),
                error_type=type(db_err).__name__
            )
            raise HTTPException(
                status_code=503,
                detail=(
                    "El servicio de datos bancarios no está disponible temporalmente. "
                    "Por favor, intente nuevamente en unos momentos."
                )
            )

        except Exception as e:
            # Catch-all para errores inesperados (500 Internal Server Error)
            # Esto NO debería ocurrir en operación normal
            logger.error(
                "analytics.unexpected_error",
                metric=metric_or_query,
                error=str(e),
                error_type=type(e).__name__
            )
            raise HTTPException(
                status_code=500,
                detail=(
                    "Error interno procesando el análisis. "
                    "El equipo técnico ha sido notificado."
                )
            )

    # =========================================================================
    # HU3: NLP QUERY FILTERING AND FORMATTING
    # =========================================================================

    @staticmethod
    async def get_filtered_data(
        session: AsyncSession,
        metric_id: str,
        banks: List[str] = None,
        date_start=None,
        date_end=None,
        intent: str = "evolution",
        user_query: str = None
    ) -> Dict[str, Any]:
        """
        Get metric data with filters for HU3 NLP pipeline.
        Production-grade: parameterized queries, proper error handling.

        Args:
            session: AsyncSession for database queries
            metric_id: Metric identifier (e.g., 'imor', 'cartera_total')
            banks: List of bank names to filter (or None for all)
            date_start: Start date for filtering
            date_end: End date for filtering
            intent: Query intent for response formatting

        Returns:
            Dict with data, visualization config, and metadata
        """
        from bankadvisor.config_service import get_config
        config = get_config()

        column_name = config.get_metric_column(metric_id)

        if not column_name:
            return {
                "type": "error",
                "message": f"Métrica desconocida: {metric_id}",
                "available_metrics": [m["label"] for m in config.get_all_metric_options()[:5]]
            }

        # Validate column exists in whitelist
        if column_name not in AnalyticsService.SAFE_METRIC_COLUMNS:
            logger.warning(
                "analytics.filtered_data.invalid_column",
                metric_id=metric_id,
                column_name=column_name
            )
            return {
                "type": "error",
                "message": f"Métrica '{metric_id}' no está autorizada"
            }

        metric_column = AnalyticsService.SAFE_METRIC_COLUMNS[column_name]

        try:
            # Build query - handle calculated fields
            if column_name == "cartera_comercial_sin_gob":
                # Special case: Cartera Comercial - Entidades Gubernamentales
                calculated_value = (
                    MonthlyKPI.cartera_comercial_total -
                    func.coalesce(MonthlyKPI.entidades_gubernamentales_total, 0)
                ).label('value')
                query = select(
                    MonthlyKPI.fecha,
                    MonthlyKPI.banco_norm,
                    calculated_value
                )
            else:
                # Standard column query
                query = select(
                    MonthlyKPI.fecha,
                    MonthlyKPI.banco_norm,
                    metric_column.label('value')
                )

            # Apply filters
            if banks and len(banks) > 0:
                query = query.where(MonthlyKPI.banco_norm.in_(banks))

            if date_start:
                query = query.where(MonthlyKPI.fecha >= date_start)

            if date_end:
                query = query.where(MonthlyKPI.fecha <= date_end)

            # Order by date
            query = query.order_by(MonthlyKPI.fecha.asc())

            # Execute
            result = await session.execute(query)
            rows = result.fetchall()

            if not rows:
                return {
                    "type": "empty",
                    "message": f"No hay datos para {config.get_metric_display_name(metric_id)}",
                    "filters": {
                        "banks": banks,
                        "date_start": str(date_start) if date_start else None,
                        "date_end": str(date_end) if date_end else None
                    }
                }

            # Format based on intent
            metric_type = config.get_metric_type(metric_id)

            # Check for special visualization modes based on metric or query
            viz_mode = AnalyticsService._detect_visualization_mode(metric_id, intent, user_query, config)

            if viz_mode == "table":
                return AnalyticsService._format_multi_month_table(rows, metric_id, config, metric_type)
            elif viz_mode == "yoy":
                return AnalyticsService._format_yoy_comparison(rows, metric_id, config, metric_type)
            elif viz_mode == "variation":
                return AnalyticsService._format_variation(rows, metric_id, config, metric_type)
            elif viz_mode == "single_series":
                return AnalyticsService._format_single_series(rows, metric_id, config, metric_type)
            elif intent == "evolution":
                return AnalyticsService._format_evolution(rows, metric_id, config, metric_type)
            elif intent == "comparison":
                return AnalyticsService._format_comparison(rows, metric_id, config, metric_type)
            elif intent == "ranking":
                return AnalyticsService._format_ranking(rows, metric_id, config, metric_type)
            else:  # point_value or unknown
                # SMART DEFAULT: If we have multiple data points, show as evolution
                # This ensures visualizations are always generated
                if len(rows) > 3:
                    logger.debug(
                        "analytics.auto_evolution",
                        metric=metric_id,
                        original_intent=intent,
                        rows=len(rows),
                        reason="Multiple data points available - showing as evolution"
                    )
                    return AnalyticsService._format_evolution(rows, metric_id, config, metric_type)
                else:
                    return AnalyticsService._format_point_value(rows, metric_id, config, metric_type)

        except SQLAlchemyError as e:
            logger.error(
                "analytics.filtered_data.db_error",
                metric_id=metric_id,
                error=str(e)
            )
            return {
                "type": "error",
                "message": "Error de base de datos. Por favor intente nuevamente."
            }

    async def get_multi_metric_data(
        session: AsyncSession,
        metric_ids: List[str],
        banks: List[str] = None,
        date_start=None,
        date_end=None,
        user_query: str = ""
    ) -> Dict[str, Any]:
        """
        Query multiple metrics simultaneously for stacked visualizations.

        Used for queries like "etapas de deterioro" which need ct_etapa_1, ct_etapa_2, ct_etapa_3.

        Args:
            session: AsyncSession for database queries
            metric_ids: List of metric identifiers (e.g., ['ct_etapa_1', 'ct_etapa_2', 'ct_etapa_3'])
            banks: List of bank names to filter
            date_start: Start date filter
            date_end: End date filter
            user_query: Original user query for context

        Returns:
            Dict with stacked bar visualization or error
        """
        from bankadvisor.config_service import get_config
        config = get_config()

        # Validate all metrics exist
        validated_metrics = []
        for metric_id in metric_ids:
            column_name = config.get_metric_column(metric_id)
            if not column_name or column_name not in AnalyticsService.SAFE_METRIC_COLUMNS:
                logger.warning(
                    "analytics.multi_metric.invalid_metric",
                    metric_id=metric_id
                )
                continue
            validated_metrics.append((metric_id, column_name))

        if not validated_metrics:
            return {
                "type": "error",
                "message": "No se encontraron métricas válidas para visualizar"
            }

        try:
            # Query all metrics - using UNION ALL to combine results
            all_rows = []

            for metric_id, column_name in validated_metrics:
                metric_column = AnalyticsService.SAFE_METRIC_COLUMNS[column_name]

                query = select(
                    MonthlyKPI.fecha,
                    MonthlyKPI.banco_norm,
                    metric_column.label('value')
                )

                # Apply filters
                if banks and len(banks) > 0:
                    query = query.where(MonthlyKPI.banco_norm.in_(banks))

                if date_start:
                    query = query.where(MonthlyKPI.fecha >= date_start)

                if date_end:
                    query = query.where(MonthlyKPI.fecha <= date_end)

                query = query.order_by(MonthlyKPI.fecha.desc()).limit(1000)

                result = await session.execute(query)
                rows = result.fetchall()

                # Add field_name to each row
                for row in rows:
                    all_rows.append({
                        'fecha': row[0],
                        'banco': row[1],
                        'field_name': column_name,  # e.g., 'ct_etapa_1'
                        'value': row[2]
                    })

            if not all_rows:
                return {
                    "type": "empty",
                    "message": "No hay datos disponibles para las métricas solicitadas"
                }

            # Convert to format expected by _format_stacked_bar
            # Need: fecha, banco, field_name, value
            formatted_rows = [
                (row['fecha'], row['banco'], row['field_name'], row['value'])
                for row in all_rows
            ]

            # Get metric type (should be ratio for stacked percentages)
            metric_type = config.get_metric_type(validated_metrics[0][0])

            # Use _format_stacked_bar
            return AnalyticsService._format_stacked_bar(
                formatted_rows,
                [m[1] for m in validated_metrics],  # field names
                config,
                metric_type
            )

        except SQLAlchemyError as e:
            logger.error(
                "analytics.multi_metric.db_error",
                metrics=metric_ids,
                error=str(e)
            )
            return {
                "type": "error",
                "message": "Error consultando múltiples métricas"
            }

    @staticmethod
    def _detect_visualization_mode(metric_id: str, intent: str, user_query: str, config) -> Optional[str]:
        """
        Detect special visualization modes based on metric type and query keywords.

        Returns:
            - "yoy": Year-over-year comparison chart
            - "variation": Month-over-month variation chart
            - "single_series": Single series chart (SISTEMA only)
            - "table": Multi-month table view
            - None: Use standard intent-based routing
        """
        query_lower = user_query.lower()

        # Check for YoY (year-over-year) keywords - HIGHEST PRIORITY
        yoy_keywords = [
            "año contra año", "año vs año", "yoy", "year over year",
            "año anterior", "vs año pasado", "comparado con el año",
            "interanual", "anual", "variación anual", "variacion anual",
            "crecimiento anual", "cambio anual"
        ]
        if any(keyword in query_lower for keyword in yoy_keywords):
            return "yoy"

        # Check for table/tabular view keywords
        table_keywords = [
            "tabla", "tabular", "table",
            "últimos", "ultimos",
            "últimos 3 meses", "últimos 6 meses", "últimos 12 meses",
            "last 3 months", "last 6 months"
        ]
        if any(keyword in query_lower for keyword in table_keywords):
            # Only use table for specific metrics or if explicitly requested
            if "tabla" in query_lower or "table" in query_lower:
                return "table"

        # Check for variation keywords (month-over-month)
        variation_keywords = [
            "variación mensual", "variacion mensual",
            "mes a mes", "mensual", "delta mensual",
            "mom", "month over month"
        ]
        if any(keyword in query_lower for keyword in variation_keywords):
            return "variation"

        # Check if metric is explicitly a variation metric
        if "variacion" in metric_id or "_mm" in metric_id:
            return "variation"

        # Check for single-series metrics (SISTEMA only)
        single_series_metrics = ["tasa_sistema", "tasa_invex_consumo"]
        if metric_id in single_series_metrics:
            return "single_series"

        # Check visualization config from sections.yaml
        viz_config = config.visualizations.get(metric_id, {})
        viz_mode = viz_config.get("mode")

        if viz_mode == "single_sistema":
            return "single_series"
        elif viz_mode == "multi_month_table_b":
            return "table"
        elif viz_mode == "yoy":
            return "yoy"

        return None

    @staticmethod
    def _format_evolution(rows, metric_id: str, config, metric_type: str) -> Dict[str, Any]:
        """
        Format data for evolution/trend view with enhanced WOW visualization.

        Features:
        - INVEX prominently displayed with thick line and markers
        - SISTEMA as dashed reference line
        - Other banks with thinner lines
        - Smart legend ordering (INVEX first, then SISTEMA, then alphabetical)
        - Last value annotations
        - Trend indicators
        """
        import pandas as pd
        import numpy as np

        df = pd.DataFrame(rows, columns=['fecha', 'banco', 'value'])

        # Convert ratio metrics to percentage, currency to millions
        # FIX 2025-12-05: ICOR is already in percentage scale (0-100+) in DB, don't multiply
        is_ratio = metric_type == "ratio"
        is_icor = metric_id.lower() == "icor"

        if is_ratio and not is_icor:
            df['value'] = df['value'] * 100
        # else: Database values are ALREADY in correct scale

        display_name = config.get_metric_display_name(metric_id)

        # Determine if lower is better for trend indicators
        lower_is_better = metric_id.lower() in ['imor', 'icor', 'cartera_vencida', 'pe_total',
                                                  'pe_empresarial', 'pe_consumo', 'pe_vivienda',
                                                  'quebrantos_comerciales', 'ct_etapa_3']

        # Build hovertemplate with units
        hover_template = (
            "<b>%{fullData.name}</b><br>" +
            "Fecha: %{x}<br>" +
            ("Valor: %{y:.2f}%<extra></extra>" if is_ratio else "Valor: %{y:,.2f} MDP<extra></extra>")
        )

        # Order banks: INVEX first, SISTEMA second, then alphabetical
        unique_banks = df['banco'].unique().tolist()
        ordered_banks = []

        # Add INVEX first if present
        for bank in unique_banks:
            if bank.upper() == 'INVEX':
                ordered_banks.append(bank)
                break

        # Add SISTEMA second if present
        for bank in unique_banks:
            if bank.upper() == 'SISTEMA':
                ordered_banks.append(bank)
                break

        # Add remaining banks alphabetically
        remaining = sorted([b for b in unique_banks if b.upper() not in ['INVEX', 'SISTEMA']])
        ordered_banks.extend(remaining)

        # Group by bank for multi-line chart with distinctive styling
        traces = []
        annotations = []

        for banco in ordered_banks:
            bank_data = df[df['banco'] == banco].sort_values('fecha')
            bank_color = get_bank_color(banco)
            banco_upper = banco.upper()

            # Configure line style based on bank importance
            if banco_upper == "INVEX":
                line_config = {
                    "color": "#E45756",  # INVEX brand red
                    "width": 4
                }
                marker_config = {"size": 8, "symbol": "circle", "color": "#E45756"}
                mode = "lines+markers"
            elif banco_upper == "SISTEMA":
                line_config = {
                    "color": "#6B7280",  # Gray
                    "width": 3,
                    "dash": "dash"
                }
                marker_config = {"size": 6, "symbol": "diamond", "color": "#6B7280"}
                mode = "lines+markers"
            else:
                line_config = {
                    "color": bank_color,
                    "width": 2
                }
                marker_config = {"size": 4, "color": bank_color}
                mode = "lines"

            traces.append({
                "x": bank_data['fecha'].astype(str).tolist(),
                "y": bank_data['value'].tolist(),
                "type": "scatter",
                "mode": mode,
                "name": banco,
                "line": line_config,
                "marker": marker_config,
                "hovertemplate": hover_template
            })

            # Add last value annotation for INVEX and SISTEMA
            if banco_upper in ['INVEX', 'SISTEMA'] and len(bank_data) > 0:
                last_date = bank_data['fecha'].iloc[-1]
                last_value = bank_data['value'].iloc[-1]

                annotations.append({
                    "x": str(last_date),
                    "y": last_value,
                    "xref": "x",
                    "yref": "y",
                    "text": f"<b>{banco}</b><br>{last_value:.2f}%" if is_ratio else f"<b>{banco}</b><br>${last_value:,.0f}M",
                    "showarrow": True,
                    "arrowhead": 2,
                    "arrowsize": 1,
                    "arrowwidth": 1,
                    "arrowcolor": line_config['color'],
                    "ax": 40 if banco_upper == 'INVEX' else -40,
                    "ay": -30 if banco_upper == 'INVEX' else 30,
                    "bordercolor": line_config['color'],
                    "borderwidth": 1,
                    "borderpad": 4,
                    "bgcolor": "rgba(255,255,255,0.9)",
                    "font": {"size": 10, "color": line_config['color']}
                })

        # Calculate time range and metadata from data
        time_range = {}
        bank_names = ordered_banks
        data_as_of = None
        summary_data = None

        if len(df) > 0:
            df_sorted = df.sort_values('fecha')
            min_date = df_sorted['fecha'].min()
            max_date = df_sorted['fecha'].max()
            time_range = {
                "start": str(min_date),
                "end": str(max_date)
            }
            data_as_of = str(max_date)

            # Calculate summary statistics for INVEX (primary focus)
            invex_df = df[df['banco'].str.upper() == 'INVEX'].sort_values('fecha')
            if len(invex_df) >= 2:
                current_value = invex_df.iloc[-1]['value']
                previous_value = invex_df.iloc[-2]['value']
                first_value = invex_df.iloc[0]['value']

                # Calculate percentage change
                change_pct = None
                if previous_value and previous_value != 0:
                    change_pct = ((current_value - previous_value) / abs(previous_value)) * 100

                # Calculate trend from beginning
                total_change = None
                if first_value and first_value != 0:
                    total_change = ((current_value - first_value) / abs(first_value)) * 100

                # Determine if trend is positive (based on lower_is_better)
                if change_pct is not None:
                    if lower_is_better:
                        trend_direction = "mejorando" if change_pct < 0 else "empeorando"
                    else:
                        trend_direction = "mejorando" if change_pct > 0 else "empeorando"
                else:
                    trend_direction = None

                summary_data = {
                    "current_value": float(current_value) if current_value else None,
                    "previous_value": float(previous_value) if previous_value else None,
                    "change_pct": round(change_pct, 2) if change_pct is not None else None,
                    "total_change_pct": round(total_change, 2) if total_change is not None else None,
                    "trend_direction": trend_direction,
                    "period_end": str(max_date),
                    "period_start": str(min_date),
                    "bank": "INVEX"
                }

        return {
            "type": "data",
            "visualization": "line_chart",
            "metric_name": display_name,
            "metric_type": metric_type,
            "bank_names": bank_names,
            "time_range": time_range,
            "data_as_of": data_as_of,
            "summary_stats": summary_data,
            "lower_is_better": lower_is_better,
            "plotly_config": {
                "data": traces,
                "layout": {
                    "title": {
                        "text": f"<b>Evolución de {display_name}</b>",
                        "font": {"size": 16, "color": "#1F2937"}
                    },
                    "xaxis": {
                        "title": "Fecha",
                        "gridcolor": "#E5E7EB",
                        "tickformat": "%b %Y"
                    },
                    "yaxis": {
                        "title": "%" if is_ratio else "MDP (Millones de Pesos)",
                        "gridcolor": "#E5E7EB",
                        "tickformat": ".1f" if is_ratio else ",.0f",
                        "ticksuffix": "%" if is_ratio else ""
                    },
                    "legend": {
                        "orientation": "h",
                        "yanchor": "bottom",
                        "y": 1.02,
                        "xanchor": "center",
                        "x": 0.5,
                        "bgcolor": "rgba(255,255,255,0.8)"
                    },
                    "margin": {"l": 80, "r": 40, "t": 80, "b": 60},
                    "plot_bgcolor": "rgba(0,0,0,0)",
                    "paper_bgcolor": "rgba(0,0,0,0)",
                    "hovermode": "x unified",
                    "annotations": annotations
                }
            },
            "summary": f"Evolución de {display_name}" + (f" - INVEX {summary_data['trend_direction']}" if summary_data and summary_data.get('trend_direction') else "")
        }

    @staticmethod
    def _format_comparison(rows, metric_id: str, config, metric_type: str) -> Dict[str, Any]:
        """
        Format data for bank comparison with time evolution (line chart).

        Shows evolution of metric over time for multiple banks (comparison).
        Different from ranking which shows latest values only.
        """
        import pandas as pd

        logger.info("analytics._format_comparison", metric_id=metric_id, rows_count=len(rows), metric_type=metric_type)

        df = pd.DataFrame(rows, columns=['fecha', 'banco', 'value'])

        # Convert ratio metrics to percentage
        # FIX 2025-12-05: ICOR is already in percentage scale (0-100+) in DB, don't multiply
        is_ratio = metric_type == "ratio"
        is_percentage = metric_type == "percentage"
        is_icor = metric_id.lower() == "icor"

        if is_ratio and not is_icor:
            df['value'] = df['value'] * 100
        # else: Database values are ALREADY in millions (MDP) or percentage, no conversion needed

        display_name = config.get_metric_display_name(metric_id)

        # Build hovertemplate with units
        hover_template = (
            "<b>%{fullData.name}</b><br>" +
            "Fecha: %{x|%Y-%m-%d}<br>" +
            ("Valor: %{y:.2f}%<extra></extra>" if (is_ratio or is_percentage) else "Valor: %{y:,.2f} MDP<extra></extra>")
        )

        # Calculate metadata from data
        time_range = {}
        bank_names = []
        data_as_of = None

        if len(df) > 0:
            df_sorted = df.sort_values('fecha')
            max_date = df_sorted['fecha'].max()
            min_date = df_sorted['fecha'].min()
            time_range = {
                "start": str(min_date),
                "end": str(max_date)
            }
            bank_names = df['banco'].unique().tolist()
            data_as_of = str(max_date)

        # Create one trace per bank (line chart)
        traces = []
        for banco in sorted(df['banco'].unique()):
            bank_data = df[df['banco'] == banco].sort_values('fecha')

            traces.append({
                "x": bank_data['fecha'].dt.strftime('%Y-%m-%d').tolist(),
                "y": bank_data['value'].tolist(),
                "type": "scatter",
                "mode": "lines+markers",
                "name": banco,
                "line": {"color": get_bank_color(banco), "width": 2},
                "marker": {"size": 6},
                "hovertemplate": hover_template
            })

        logger.info("analytics._format_comparison.result", traces_count=len(traces), visualization="line_chart")

        return {
            "type": "data",
            "visualization": "line_chart",
            "metric_name": display_name,
            "metric_type": metric_type,
            "bank_names": bank_names,  # List of banks in chart
            "time_range": time_range,  # Add time range for UI header
            "data_as_of": data_as_of,  # Last data update
            "plotly_config": {
                "data": traces,
                "layout": {
                    "title": f"Comparación de {display_name}",
                    "xaxis": {"title": "Fecha"},
                    "yaxis": {
                        "title": "%" if (is_ratio or is_percentage) else "MDP (Millones de Pesos)"
                    },
                    "hovermode": "closest"
                }
            },
            "summary": f"Comparando evolución de {display_name} entre bancos"
        }

    @staticmethod
    def _format_ranking(rows, metric_id: str, config, metric_type: str) -> Dict[str, Any]:
        """
        Format data for ranking view with enhanced WOW visualization.

        Features:
        - Horizontal bar chart sorted by value
        - Average (promedio) reference line
        - INVEX highlighted with special color and border
        - Semantic colors: green for good, red for bad (context-aware)
        - Value annotations on bars
        """
        import pandas as pd
        import numpy as np

        df = pd.DataFrame(rows, columns=['fecha', 'banco', 'value'])

        # Convert ratio metrics to percentage, currency to millions
        # FIX 2025-12-05: ICOR is already in percentage scale (0-100+) in DB, don't multiply
        is_ratio = metric_type == "ratio"
        is_icor = metric_id.lower() == "icor"
        if is_ratio and not is_icor:
            df['value'] = df['value'] * 100
        # else: Database values are ALREADY in millions (MDP), no conversion needed

        # Get latest value per bank, sorted
        latest = df.sort_values('fecha').groupby('banco').last().reset_index()

        # Exclude SISTEMA from ranking (it's an aggregate, not a competitor)
        latest = latest[latest['banco'].str.upper() != 'SISTEMA']

        # Determine if lower is better (IMOR, ICOR = lower is better)
        lower_is_better = metric_id.lower() in ['imor', 'icor', 'cartera_vencida', 'pe_total',
                                                  'pe_empresarial', 'pe_consumo', 'pe_vivienda',
                                                  'quebrantos_comerciales', 'ct_etapa_3']

        # Sort: if lower is better, ascending (best at top), else descending (best at top)
        latest = latest.sort_values('value', ascending=lower_is_better)

        display_name = config.get_metric_display_name(metric_id)

        # Calculate average (excluding SISTEMA for meaningful comparison)
        non_sistema = latest[latest['banco'].str.upper() != 'SISTEMA']
        avg_value = non_sistema['value'].mean() if len(non_sistema) > 0 else latest['value'].mean()

        # Build colors with semantic meaning and INVEX highlight
        bar_colors = []
        bar_borders = []
        for _, row in latest.iterrows():
            banco = row['banco'].upper()
            value = row['value']

            if banco == 'INVEX':
                # INVEX always highlighted in brand red with gold border
                bar_colors.append('#E45756')  # INVEX Red
                bar_borders.append({'width': 3, 'color': '#FFD700'})  # Gold border
            elif banco == 'SISTEMA':
                # SISTEMA in neutral gray
                bar_colors.append('#AAB0B3')
                bar_borders.append({'width': 0, 'color': 'rgba(0,0,0,0)'})
            else:
                # Other banks: semantic color based on performance vs average
                if lower_is_better:
                    # Lower is better: green if below avg, red if above
                    if value < avg_value:
                        bar_colors.append('#10B981')  # Green - good
                    else:
                        bar_colors.append('#6B7280')  # Gray - neutral
                else:
                    # Higher is better: green if above avg, red if below
                    if value > avg_value:
                        bar_colors.append('#10B981')  # Green - good
                    else:
                        bar_colors.append('#6B7280')  # Gray - neutral
                bar_borders.append({'width': 0, 'color': 'rgba(0,0,0,0)'})

        # Build hovertemplate with units
        hover_template = (
            "<b>%{y}</b><br>" +
            ("Valor: %{x:.2f}%<extra></extra>" if is_ratio else "Valor: %{x:,.2f} MDP<extra></extra>")
        )

        # Main bar trace
        bar_trace = {
            "x": latest['value'].tolist(),
            "y": latest['banco'].tolist(),
            "type": "bar",
            "orientation": "h",
            "marker": {
                "color": bar_colors,
                "line": {
                    "width": [b['width'] for b in bar_borders],
                    "color": [b['color'] for b in bar_borders]
                }
            },
            "hovertemplate": hover_template,
            "text": [f"{v:.2f}%" if is_ratio else f"${v:,.0f}M" for v in latest['value'].tolist()],
            "textposition": "outside",
            "textfont": {"size": 11, "color": "#374151"},
            "name": display_name
        }

        # Average reference line (vertical line)
        avg_line = {
            "type": "scatter",
            "x": [avg_value, avg_value],
            "y": [latest['banco'].iloc[0], latest['banco'].iloc[-1]],
            "mode": "lines",
            "line": {
                "color": "#F59E0B",  # Amber/Orange
                "width": 3,
                "dash": "dash"
            },
            "name": f"Promedio: {avg_value:.2f}%" if is_ratio else f"Promedio: ${avg_value:,.0f}M",
            "hovertemplate": f"<b>Promedio</b><br>{avg_value:.2f}%<extra></extra>" if is_ratio else f"<b>Promedio</b><br>${avg_value:,.0f}M<extra></extra>",
            "showlegend": True
        }

        # Get time info for metadata
        max_date = df['fecha'].max()

        # Find INVEX position in ranking
        invex_position = None
        for i, (_, row) in enumerate(latest.iterrows()):
            if row['banco'].upper() == 'INVEX':
                invex_position = i + 1
                invex_value = row['value']
                break

        return {
            "type": "data",
            "visualization": "ranking",
            "metric_name": display_name,
            "metric_type": metric_type,
            "bank_names": latest['banco'].tolist(),
            "time_range": {"start": str(max_date), "end": str(max_date)},
            "data_as_of": str(max_date),
            "ranking": [
                {
                    "position": i + 1,
                    "banco": row['banco'],
                    "value": round(row['value'], 2),
                    "unit": "%" if is_ratio else "MDP",
                    "vs_avg": round(row['value'] - avg_value, 2),
                    "is_invex": row['banco'].upper() == 'INVEX'
                }
                for i, (_, row) in enumerate(latest.iterrows())
            ],
            "summary_stats": {
                "average": round(avg_value, 2),
                "invex_position": invex_position,
                "invex_value": round(invex_value, 2) if invex_position else None,
                "invex_vs_avg": round(invex_value - avg_value, 2) if invex_position else None,
                "total_banks": len(latest),
                "lower_is_better": lower_is_better
            },
            "plotly_config": {
                "data": [bar_trace, avg_line],
                "layout": {
                    "title": {
                        "text": f"<b>Ranking de {display_name}</b>",
                        "font": {"size": 16, "color": "#1F2937"}
                    },
                    "xaxis": {
                        "title": "%" if is_ratio else "MDP (Millones de Pesos)",
                        "tickformat": ".1f" if is_ratio else ",.0f",
                        "ticksuffix": "%" if is_ratio else "",
                        "gridcolor": "#E5E7EB",
                        "zeroline": True,
                        "zerolinecolor": "#9CA3AF"
                    },
                    "yaxis": {
                        "title": "",
                        "tickfont": {"size": 11}
                    },
                    "legend": {
                        "orientation": "h",
                        "yanchor": "bottom",
                        "y": 1.02,
                        "xanchor": "right",
                        "x": 1
                    },
                    "margin": {"l": 120, "r": 80, "t": 60, "b": 40},
                    "plot_bgcolor": "rgba(0,0,0,0)",
                    "paper_bgcolor": "rgba(0,0,0,0)",
                    "hovermode": "closest",
                    "annotations": [
                        {
                            "x": avg_value,
                            "y": 1.05,
                            "xref": "x",
                            "yref": "paper",
                            "text": f"Promedio: {avg_value:.2f}%" if is_ratio else f"Promedio: ${avg_value:,.0f}M",
                            "showarrow": False,
                            "font": {"size": 10, "color": "#F59E0B"},
                            "bgcolor": "rgba(255,255,255,0.8)"
                        }
                    ]
                }
            },
            "summary": f"Ranking de {display_name} - INVEX en posición {invex_position} de {len(latest)}" if invex_position else f"Ranking de {display_name}"
        }

    @staticmethod
    def _format_point_value(rows, metric_id: str, config, metric_type: str) -> Dict[str, Any]:
        """Format data for single point value."""
        import pandas as pd

        df = pd.DataFrame(rows, columns=['fecha', 'banco', 'value'])

        # Convert ratio metrics to percentage, currency to millions
        # FIX 2025-12-05: ICOR is already in percentage scale (0-100+) in DB, don't multiply
        is_ratio = metric_type == "ratio"
        is_icor = metric_id.lower() == "icor"
        if is_ratio and not is_icor:
            df['value'] = df['value'] * 100
        # else: Database values are ALREADY in millions (MDP), no conversion needed

        # Get latest values
        latest = df.sort_values('fecha').groupby('banco').last().reset_index()

        display_name = config.get_metric_display_name(metric_id)

        return {
            "type": "data",
            "visualization": "value",
            "metric_name": display_name,
            "metric_type": metric_type,
            "values": [
                {
                    "banco": row['banco'],
                    "value": round(row['value'], 2),
                    "fecha": str(row['fecha']),
                    "unit": "%" if is_ratio else "MDP"
                }
                for _, row in latest.iterrows()
            ],
            "summary": f"Valor actual de {display_name}"
        }

    @staticmethod
    def _format_variation(rows, metric_id: str, config, metric_type: str) -> Dict[str, Any]:
        """
        Format data for month-over-month variation view.

        Shows percentage change between consecutive months with color coding:
        - Green bars for positive changes
        - Red bars for negative changes
        - Reference line at 0%
        """
        import pandas as pd

        df = pd.DataFrame(rows, columns=['fecha', 'banco', 'value'])

        # Convert ratio metrics to percentage, currency already in millions
        is_ratio = metric_type == "ratio"
        if is_ratio and not is_icor:
            df['value'] = df['value'] * 100

        display_name = config.get_metric_display_name(metric_id)

        # Calculate month-over-month variation for each bank
        traces = []
        for banco in df['banco'].unique():
            bank_data = df[df['banco'] == banco].sort_values('fecha')

            if len(bank_data) < 2:
                continue  # Need at least 2 points to calculate variation

            # Calculate percentage change
            variations = []
            dates = []
            for i in range(1, len(bank_data)):
                prev_value = bank_data.iloc[i-1]['value']
                curr_value = bank_data.iloc[i]['value']

                if prev_value and prev_value != 0:
                    variation_pct = ((curr_value - prev_value) / prev_value) * 100
                    variations.append(variation_pct)
                    dates.append(str(bank_data.iloc[i]['fecha']))

            if not variations:
                continue

            # Color bars based on positive/negative
            colors = ['#10B981' if v >= 0 else '#EF4444' for v in variations]
            bank_color = get_bank_color(banco)

            traces.append({
                "x": dates,
                "y": variations,
                "type": "bar",
                "name": banco,
                "marker": {"color": colors if banco.upper() == "INVEX" else bank_color},
                "hovertemplate": f"<b>{banco}</b><br>Fecha: %{{x}}<br>Variación: %{{y:.2f}}%<extra></extra>",
                "text": [f"{v:+.2f}%" for v in variations],
                "textposition": "outside"
            })

        return {
            "type": "data",
            "visualization": "variation_chart",
            "metric_name": display_name,
            "metric_type": metric_type,
            "plotly_config": {
                "data": traces,
                "layout": {
                    "title": f"Variación Mensual de {display_name}",
                    "xaxis": {"title": "Período"},
                    "yaxis": {
                        "title": "Variación %",
                        "zeroline": True,
                        "zerolinewidth": 2,
                        "zerolinecolor": "#374151"
                    },
                    "barmode": "group",
                    "hovermode": "x unified"
                }
            },
            "summary": f"Variación mes a mes de {display_name}"
        }

    @staticmethod
    def _format_yoy_comparison(rows, metric_id: str, config, metric_type: str) -> Dict[str, Any]:
        """
        Format data for Year-over-Year (YoY) comparison visualization.

        Shows horizontal bar chart with percentage change from same period last year.
        Features:
        - Green bars for positive growth (or negative for metrics where lower is better)
        - Red bars for negative growth (or positive for metrics where lower is better)
        - INVEX highlighted with special styling
        - Average line reference
        - Period comparison annotation

        Based on PDF reference pages 1-2, 3-4, 5-6, 8-9.
        """
        import pandas as pd
        import numpy as np
        from datetime import timedelta

        df = pd.DataFrame(rows, columns=['fecha', 'banco', 'value'])

        # Convert ratio metrics to percentage
        is_ratio = metric_type == "ratio"
        if is_ratio and not is_icor:
            df['value'] = df['value'] * 100

        # Determine if lower is better
        lower_is_better = metric_id.lower() in ['imor', 'icor', 'cartera_vencida', 'pe_total',
                                                  'pe_empresarial', 'pe_consumo', 'pe_vivienda',
                                                  'quebrantos_comerciales', 'ct_etapa_3']

        display_name = config.get_metric_display_name(metric_id)

        # Get the most recent period and same period last year
        df['fecha'] = pd.to_datetime(df['fecha'])
        latest_date = df['fecha'].max()
        one_year_ago = latest_date - pd.DateOffset(years=1)

        # Find closest dates to latest and one year ago
        unique_dates = df['fecha'].unique()
        latest_data = df[df['fecha'] == latest_date]

        # Find the closest date to one year ago (within 45 days tolerance)
        one_year_ago_data = None
        for days_delta in range(0, 45):
            target_date = one_year_ago + pd.Timedelta(days=days_delta)
            target_date_neg = one_year_ago - pd.Timedelta(days=days_delta)

            if target_date in unique_dates:
                one_year_ago_data = df[df['fecha'] == target_date]
                one_year_ago_actual = target_date
                break
            elif target_date_neg in unique_dates:
                one_year_ago_data = df[df['fecha'] == target_date_neg]
                one_year_ago_actual = target_date_neg
                break

        if one_year_ago_data is None or one_year_ago_data.empty:
            # Fallback: use earliest available date
            earliest_date = df['fecha'].min()
            one_year_ago_data = df[df['fecha'] == earliest_date]
            one_year_ago_actual = earliest_date

        # Calculate YoY change for each bank
        yoy_data = []
        for _, current_row in latest_data.iterrows():
            banco = current_row['banco']
            current_value = current_row['value']

            # Find matching bank in previous period
            prev_row = one_year_ago_data[one_year_ago_data['banco'] == banco]
            if not prev_row.empty:
                prev_value = prev_row.iloc[0]['value']
                if prev_value and prev_value != 0:
                    yoy_pct = ((current_value - prev_value) / abs(prev_value)) * 100
                else:
                    yoy_pct = 0
            else:
                yoy_pct = None

            if yoy_pct is not None:
                yoy_data.append({
                    'banco': banco,
                    'current_value': current_value,
                    'prev_value': prev_value if not prev_row.empty else None,
                    'yoy_pct': yoy_pct
                })

        if not yoy_data:
            return {
                "type": "empty",
                "message": f"No hay datos suficientes para calcular variación YoY de {display_name}"
            }

        yoy_df = pd.DataFrame(yoy_data)

        # Exclude SISTEMA from YoY ranking (it's an aggregate, not a competitor)
        yoy_df = yoy_df[yoy_df['banco'].str.upper() != 'SISTEMA']

        if len(yoy_df) == 0:
            return {
                "type": "empty",
                "message": f"No hay bancos con datos suficientes para variación YoY de {display_name}"
            }

        # Sort by YoY change
        # For lower_is_better metrics: negative YoY (decrease) is GOOD -> sort ascending
        # For higher_is_better metrics: positive YoY (increase) is GOOD -> sort descending
        yoy_df = yoy_df.sort_values('yoy_pct', ascending=lower_is_better)

        # Calculate average YoY (excluding SISTEMA)
        non_sistema = yoy_df[yoy_df['banco'].str.upper() != 'SISTEMA']
        avg_yoy = non_sistema['yoy_pct'].mean() if len(non_sistema) > 0 else yoy_df['yoy_pct'].mean()

        # Build colors based on performance
        bar_colors = []
        bar_borders = []
        for _, row in yoy_df.iterrows():
            banco = row['banco'].upper()
            yoy = row['yoy_pct']

            if banco == 'INVEX':
                # INVEX highlighted with gold border
                if lower_is_better:
                    color = '#10B981' if yoy < 0 else '#EF4444'  # Green if decreased, red if increased
                else:
                    color = '#10B981' if yoy > 0 else '#EF4444'  # Green if increased, red if decreased
                bar_colors.append(color)
                bar_borders.append({'width': 3, 'color': '#FFD700'})
            else:
                # Semantic coloring for other banks
                if lower_is_better:
                    color = '#10B981' if yoy < 0 else '#EF4444'  # Green if decreased
                else:
                    color = '#10B981' if yoy > 0 else '#EF4444'  # Green if increased
                bar_colors.append(color)
                bar_borders.append({'width': 0, 'color': 'rgba(0,0,0,0)'})

        # Main bar trace
        bar_trace = {
            "x": yoy_df['yoy_pct'].tolist(),
            "y": yoy_df['banco'].tolist(),
            "type": "bar",
            "orientation": "h",
            "marker": {
                "color": bar_colors,
                "line": {
                    "width": [b['width'] for b in bar_borders],
                    "color": [b['color'] for b in bar_borders]
                }
            },
            "hovertemplate": "<b>%{y}</b><br>Variación YoY: %{x:+.2f}%<br>Actual: %{customdata[0]:.2f}<br>Anterior: %{customdata[1]:.2f}<extra></extra>",
            "customdata": [[row['current_value'], row['prev_value']] for _, row in yoy_df.iterrows()],
            "text": [f"{v:+.1f}%" for v in yoy_df['yoy_pct'].tolist()],
            "textposition": "outside",
            "textfont": {"size": 10, "color": "#374151"},
            "name": "Variación YoY"
        }

        # Zero reference line
        zero_line = {
            "type": "scatter",
            "x": [0, 0],
            "y": [yoy_df['banco'].iloc[0], yoy_df['banco'].iloc[-1]],
            "mode": "lines",
            "line": {"color": "#9CA3AF", "width": 2},
            "showlegend": False,
            "hoverinfo": "skip"
        }

        # Average reference line
        avg_line = {
            "type": "scatter",
            "x": [avg_yoy, avg_yoy],
            "y": [yoy_df['banco'].iloc[0], yoy_df['banco'].iloc[-1]],
            "mode": "lines",
            "line": {"color": "#F59E0B", "width": 2, "dash": "dash"},
            "name": f"Promedio: {avg_yoy:+.1f}%",
            "hovertemplate": f"<b>Promedio</b><br>{avg_yoy:+.2f}%<extra></extra>"
        }

        # Find INVEX position
        invex_row = yoy_df[yoy_df['banco'].str.upper() == 'INVEX']
        invex_yoy = invex_row.iloc[0]['yoy_pct'] if not invex_row.empty else None
        invex_position = yoy_df[yoy_df['banco'].str.upper() == 'INVEX'].index.tolist()
        invex_position = list(yoy_df['banco']).index(invex_row.iloc[0]['banco']) + 1 if not invex_row.empty else None

        # Period labels
        current_period = latest_date.strftime('%b %Y')
        prev_period = one_year_ago_actual.strftime('%b %Y')

        return {
            "type": "data",
            "visualization": "yoy_comparison",
            "metric_name": display_name,
            "metric_type": metric_type,
            "bank_names": yoy_df['banco'].tolist(),
            "time_range": {
                "start": str(one_year_ago_actual.date()),
                "end": str(latest_date.date())
            },
            "data_as_of": str(latest_date.date()),
            "yoy_data": [
                {
                    "banco": row['banco'],
                    "current_value": round(row['current_value'], 2),
                    "prev_value": round(row['prev_value'], 2) if row['prev_value'] else None,
                    "yoy_pct": round(row['yoy_pct'], 2),
                    "is_invex": row['banco'].upper() == 'INVEX'
                }
                for _, row in yoy_df.iterrows()
            ],
            "summary_stats": {
                "average_yoy": round(avg_yoy, 2),
                "invex_yoy": round(invex_yoy, 2) if invex_yoy else None,
                "invex_position": invex_position,
                "total_banks": len(yoy_df),
                "current_period": current_period,
                "comparison_period": prev_period,
                "lower_is_better": lower_is_better
            },
            "plotly_config": {
                "data": [bar_trace, zero_line, avg_line],
                "layout": {
                    "title": {
                        "text": f"<b>Variación YoY de {display_name}</b><br><sub>{prev_period} → {current_period}</sub>",
                        "font": {"size": 14, "color": "#1F2937"}
                    },
                    "xaxis": {
                        "title": "Variación %",
                        "tickformat": "+.0f",
                        "ticksuffix": "%",
                        "zeroline": True,
                        "zerolinewidth": 2,
                        "zerolinecolor": "#374151",
                        "gridcolor": "#E5E7EB"
                    },
                    "yaxis": {
                        "title": "",
                        "tickfont": {"size": 11}
                    },
                    "legend": {
                        "orientation": "h",
                        "yanchor": "bottom",
                        "y": 1.02,
                        "xanchor": "right",
                        "x": 1
                    },
                    "margin": {"l": 120, "r": 80, "t": 80, "b": 40},
                    "plot_bgcolor": "rgba(0,0,0,0)",
                    "paper_bgcolor": "rgba(0,0,0,0)",
                    "hovermode": "closest",
                    "annotations": [
                        {
                            "x": avg_yoy,
                            "y": 1.05,
                            "xref": "x",
                            "yref": "paper",
                            "text": f"Promedio: {avg_yoy:+.1f}%",
                            "showarrow": False,
                            "font": {"size": 10, "color": "#F59E0B"},
                            "bgcolor": "rgba(255,255,255,0.8)"
                        }
                    ]
                }
            },
            "summary": f"Variación YoY de {display_name}: INVEX {invex_yoy:+.1f}% (#{invex_position} de {len(yoy_df)})" if invex_yoy else f"Variación YoY de {display_name}"
        }

    @staticmethod
    def _format_single_series(rows, metric_id: str, config, metric_type: str) -> Dict[str, Any]:
        """
        Format data for single series view (typically SISTEMA only).

        Used for metrics that exist only at system level without bank breakdown.
        Examples: Tasa Efectiva Sistema, benchmarks globales.
        """
        import pandas as pd

        df = pd.DataFrame(rows, columns=['fecha', 'banco', 'value'])

        # Filter for SISTEMA only
        df = df[df['banco'].str.upper() == 'SISTEMA']

        if df.empty:
            # Fallback: use first bank if SISTEMA not available
            df = pd.DataFrame(rows, columns=['fecha', 'banco', 'value'])
            df = df[df['banco'] == df['banco'].iloc[0]]

        # Drop rows with NULL/NaN values - these metrics may have sparse data
        # (e.g., tasa_sistema is reported bimonthly, not monthly)
        df = df.dropna(subset=['value'])

        if df.empty:
            return {
                "type": "empty",
                "message": f"No hay datos válidos para {config.get_metric_display_name(metric_id)}",
                "visualization": "none"
            }

        # Convert ratio metrics to percentage (ratios are 0-1, percentages are already 0-100)
        is_ratio = metric_type == "ratio"
        is_percentage = metric_type == "percentage"
        if is_ratio and not is_icor:
            df['value'] = df['value'] * 100

        df = df.sort_values('fecha')
        display_name = config.get_metric_display_name(metric_id)

        # Build simple line chart - show % for both ratio and percentage types
        show_as_percent = is_ratio or is_percentage
        hover_template = (
            "<b>SISTEMA</b><br>" +
            "Fecha: %{x}<br>" +
            ("Valor: %{y:.2f}%<extra></extra>" if show_as_percent else "Valor: %{y:,.2f} MDP<extra></extra>")
        )

        return {
            "type": "data",
            "visualization": "single_series",
            "metric_name": display_name,
            "metric_type": metric_type,
            "plotly_config": {
                "data": [{
                    "x": df['fecha'].astype(str).tolist(),
                    "y": df['value'].tolist(),
                    "type": "scatter",
                    "mode": "lines+markers",
                    "name": "SISTEMA",
                    "line": {"color": BANK_COLORS["SISTEMA"], "width": 3},
                    "marker": {"size": 6},
                    "hovertemplate": hover_template
                }],
                "layout": {
                    "title": f"Evolución de {display_name}",
                    "xaxis": {"title": "Período"},
                    "yaxis": {
                        "title": "%" if show_as_percent else "MDP (Millones de Pesos)"
                    },
                    "showlegend": False
                }
            },
            "summary": f"Evolución de {display_name} del sistema bancario"
        }

    @staticmethod
    def _format_stacked_bar(rows, fields: List[str], config, metric_type: str) -> Dict[str, Any]:
        """
        Format data for stacked bar chart (100%).

        Used for showing portfolio distribution across categories.
        Examples: IFRS 9 stages (Etapa 1/2/3), Portfolio composition.

        Args:
            rows: Query results with multiple metric columns
            fields: List of field names to stack (e.g., ['ct_etapa_1', 'ct_etapa_2', 'ct_etapa_3'])
            config: Config service
            metric_type: Should be 'ratio' for percentage-based stacking
        """
        import pandas as pd

        # Rows should contain: fecha, banco, field_name, value
        # Need to pivot to get each field as a separate column
        df = pd.DataFrame(rows, columns=['fecha', 'banco', 'field_name', 'value'])

        # Convert ratio to percentage
        is_ratio = metric_type == "ratio"
        if is_ratio and not is_icor:
            df['value'] = df['value'] * 100

        # Get latest date data
        latest_date = df['fecha'].max()
        latest = df[df['fecha'] == latest_date]

        # Pivot: rows = bancos, columns = fields
        pivot = latest.pivot(index='banco', columns='field_name', values='value').fillna(0)

        # Define colors for stages (if IFRS 9 etapas)
        STAGE_COLORS = {
            'ct_etapa_1': '#2E8B57',  # Green - Performing
            'ct_etapa_2': '#FFD700',  # Yellow - Watchlist
            'ct_etapa_3': '#DC143C',  # Red - Non-performing
        }

        # Create stacked bar traces
        traces = []
        for field in fields:
            if field not in pivot.columns:
                continue

            field_display = config.get_metric_display_name(field) if hasattr(config, 'get_metric_display_name') else field.replace('_', ' ').title()
            field_color = STAGE_COLORS.get(field, BANK_COLORS["DEFAULT"])

            traces.append({
                "x": pivot.index.tolist(),
                "y": pivot[field].tolist(),
                "type": "bar",
                "name": field_display,
                "marker": {"color": field_color},
                "hovertemplate": f"<b>{field_display}</b><br>Banco: %{{x}}<br>Valor: %{{y:.2f}}%<extra></extra>",
                "text": [f"{v:.1f}%" if v > 5 else "" for v in pivot[field].tolist()],
                "textposition": "inside"
            })

        return {
            "type": "data",
            "visualization": "stacked_bar",
            "metric_name": "Distribución de Cartera",
            "metric_type": metric_type,
            "plotly_config": {
                "data": traces,
                "layout": {
                    "title": "Distribución de Cartera por Etapas",
                    "xaxis": {"title": "Banco"},
                    "yaxis": {
                        "title": "% de Cartera Total",
                        "range": [0, 100]
                    },
                    "barmode": "stack",
                    "hovermode": "x unified"
                }
            },
            "summary": "Distribución de cartera por etapas de deterioro (IFRS 9)"
        }

    @staticmethod
    def _format_multi_month_table(rows, metric_id: str, config, metric_type: str, months: int = 6) -> Dict[str, Any]:
        """
        Format data as multi-month table view.

        Shows last N months in tabular format with color coding.
        Useful for variation metrics where tabular view is clearer.
        """
        import pandas as pd

        df = pd.DataFrame(rows, columns=['fecha', 'banco', 'value'])

        # Convert ratio to percentage
        is_ratio = metric_type == "ratio"
        if is_ratio and not is_icor:
            df['value'] = df['value'] * 100

        # Get last N months
        df = df.sort_values('fecha', ascending=False)
        unique_dates = df['fecha'].unique()[:months]
        df = df[df['fecha'].isin(unique_dates)]

        # Pivot: rows = bancos, columns = dates
        pivot = df.pivot(index='banco', columns='fecha', values='value')
        pivot = pivot[sorted(pivot.columns, reverse=True)]  # Most recent first

        display_name = config.get_metric_display_name(metric_id)

        # Convert to table format
        table_data = []
        for banco in pivot.index:
            row_data = {"banco": banco}
            for date in pivot.columns:
                value = pivot.loc[banco, date]
                row_data[str(date)] = round(value, 2) if pd.notna(value) else None
            table_data.append(row_data)

        return {
            "type": "data",
            "visualization": "table",
            "metric_name": display_name,
            "metric_type": metric_type,
            "table_data": table_data,
            "columns": ["banco"] + [str(d) for d in pivot.columns],
            "summary": f"Últimos {months} meses de {display_name}"
        }

    # =========================================================================
    # NEW METHODS FOR 5 BUSINESS QUESTIONS INTEGRATION
    # =========================================================================

    @staticmethod
    async def get_comparative_ratio_data(
        session: AsyncSession,
        metric_column: str,
        primary_bank: str = "INVEX",
        comparison_bank: str = "SISTEMA",
        date_start: Optional[str] = None,
        date_end: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get comparative ratio data for IMOR, ICOR, etc.

        Used for questions like:
        - "IMOR de INVEX vs Sistema"
        - "Compara ICOR de INVEX contra el promedio del mercado"

        Args:
            session: AsyncSession for database queries
            metric_column: Column name (e.g., 'imor', 'icor')
            primary_bank: Primary bank to compare (default: INVEX)
            comparison_bank: Comparison bank (default: SISTEMA)
            date_start: Optional start date filter (YYYY-MM-DD)
            date_end: Optional end date filter (YYYY-MM-DD)

        Returns:
            Dict with comparative evolution data and Plotly config
        """
        from bankadvisor.config_service import get_config
        from datetime import datetime

        config = get_config()

        # Validate metric column
        if metric_column not in AnalyticsService.SAFE_METRIC_COLUMNS:
            logger.warning(
                "analytics.comparative_ratio.invalid_metric",
                metric=metric_column
            )
            return {
                "type": "error",
                "message": f"Métrica '{metric_column}' no válida"
            }

        safe_column = AnalyticsService.SAFE_METRIC_COLUMNS[metric_column]

        try:
            # Build query for both banks
            query = select(
                MonthlyKPI.fecha,
                MonthlyKPI.banco_norm,
                (safe_column * 100).label('value')  # Convert to percentage
            ).where(
                MonthlyKPI.banco_norm.in_([primary_bank, comparison_bank])
            )

            # Apply date filters
            if date_start:
                query = query.where(MonthlyKPI.fecha >= datetime.strptime(date_start, '%Y-%m-%d').date())
            if date_end:
                query = query.where(MonthlyKPI.fecha <= datetime.strptime(date_end, '%Y-%m-%d').date())

            query = query.order_by(MonthlyKPI.fecha.asc())

            result = await session.execute(query)
            rows = result.fetchall()

            if not rows:
                return {
                    "type": "empty",
                    "message": f"No hay datos de {metric_column} para comparar"
                }

            # Format as evolution with 2 traces
            import pandas as pd
            df = pd.DataFrame(rows, columns=['fecha', 'banco', 'value'])

            traces = []
            for banco in [primary_bank, comparison_bank]:
                bank_data = df[df['banco'] == banco].sort_values('fecha')
                bank_color = get_bank_color(banco)

                line_config = {"color": bank_color, "width": 3 if banco == primary_bank else 2}
                if banco.upper() == "SISTEMA":
                    line_config["dash"] = "dot"

                traces.append({
                    "x": bank_data['fecha'].astype(str).tolist(),
                    "y": bank_data['value'].tolist(),
                    "type": "scatter",
                    "mode": "lines+markers",
                    "name": banco,
                    "line": line_config,
                    "hovertemplate": f"<b>{banco}</b><br>Fecha: %{{x}}<br>Valor: %{{y:.2f}}%<extra></extra>"
                })

            # Calculate difference (spread)
            primary_data = df[df['banco'] == primary_bank].sort_values('fecha')
            comparison_data = df[df['banco'] == comparison_bank].sort_values('fecha')

            if len(primary_data) > 0 and len(comparison_data) > 0:
                latest_primary = primary_data.iloc[-1]['value']
                latest_comparison = comparison_data.iloc[-1]['value']
                spread = latest_primary - latest_comparison
            else:
                spread = None

            display_name = config.get_metric_display_name(metric_column)

            # Extract bank names and time range for frontend compatibility
            unique_banks = [str(b) for b in df['banco'].unique().tolist()]
            min_date = str(df['fecha'].min())
            max_date = str(df['fecha'].max())

            return {
                "type": "data",
                "visualization": "comparative_line",
                "metric_name": display_name,
                "metric_type": "ratio",
                "bank_names": unique_banks,  # Required by frontend BankChartData interface
                "time_range": {  # Required by frontend BankChartData interface
                    "start": min_date,
                    "end": max_date
                },
                "plotly_config": {
                    "data": traces,
                    "layout": {
                        "title": f"Comparación de {display_name}: {primary_bank} vs {comparison_bank}",
                        "xaxis": {"title": "Fecha"},
                        "yaxis": {"title": "%", "tickformat": ".2f"}
                    }
                },
                "summary": {
                    "primary_bank": primary_bank,
                    "comparison_bank": comparison_bank,
                    "latest_primary": float(latest_primary) if len(primary_data) > 0 else None,
                    "latest_comparison": float(latest_comparison) if len(comparison_data) > 0 else None,
                    "spread": float(spread) if spread is not None else None,
                    "spread_description": f"{primary_bank} {'mejor' if spread < 0 else 'peor'} que {comparison_bank} por {abs(spread):.2f}pp" if spread is not None else None
                }
            }

        except Exception as e:
            logger.error(
                "analytics.comparative_ratio.error",
                metric=metric_column,
                error=str(e)
            )
            return {
                "type": "error",
                "message": f"Error al comparar {metric_column}"
            }

    @staticmethod
    async def get_market_share_data(
        session: AsyncSession,
        primary_bank: str = "INVEX",
        years: int = 3
    ) -> Dict[str, Any]:
        """
        Get market share evolution for a bank over time.

        Used for questions like:
        - "Market share de INVEX en los últimos 3 años"
        - "Participación de mercado de INVEX"

        Args:
            session: AsyncSession for database queries
            primary_bank: Bank to analyze (default: INVEX)
            years: Number of years to analyze (default: 3)

        Returns:
            Dict with market share evolution and Plotly config
        """
        from bankadvisor.config_service import get_config
        from datetime import datetime, timedelta

        config = get_config()

        try:
            # Calculate date range
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=years * 365)

            # Query cartera_total for bank and total system
            query = select(
                MonthlyKPI.fecha,
                MonthlyKPI.banco_norm,
                MonthlyKPI.cartera_total
            ).where(
                MonthlyKPI.fecha >= start_date,
                MonthlyKPI.fecha <= end_date
            ).order_by(MonthlyKPI.fecha.asc())

            result = await session.execute(query)
            rows = result.fetchall()

            if not rows:
                return {
                    "type": "empty",
                    "message": f"No hay datos de market share para {primary_bank}"
                }

            # Calculate market share
            import pandas as pd
            df = pd.DataFrame(rows, columns=['fecha', 'banco', 'cartera_total'])

            # Group by month and calculate total
            monthly_totals = df.groupby('fecha')['cartera_total'].sum().reset_index()
            monthly_totals.columns = ['fecha', 'total_sistema']

            # Get bank data
            bank_data = df[df['banco'] == primary_bank].copy()

            # Merge and calculate share
            bank_data = bank_data.merge(monthly_totals, on='fecha')
            bank_data['market_share'] = (bank_data['cartera_total'] / bank_data['total_sistema']) * 100

            if len(bank_data) == 0:
                return {
                    "type": "empty",
                    "message": f"No hay datos de {primary_bank}"
                }

            # Build Plotly line chart
            traces = [{
                "x": bank_data['fecha'].astype(str).tolist(),
                "y": bank_data['market_share'].tolist(),
                "type": "scatter",
                "mode": "lines+markers",
                "name": f"Market Share {primary_bank}",
                "line": {"color": get_bank_color(primary_bank), "width": 3},
                "hovertemplate": f"<b>{primary_bank}</b><br>Fecha: %{{x}}<br>Market Share: %{{y:.2f}}%<extra></extra>"
            }]

            # Extract bank names and time range for frontend compatibility
            min_date = str(bank_data['fecha'].min())
            max_date = str(bank_data['fecha'].max())

            return {
                "type": "data",
                "visualization": "market_share_evolution",
                "metric_name": f"Market Share {primary_bank}",
                "metric_type": "ratio",
                "bank_names": [primary_bank],  # Required by frontend BankChartData interface
                "time_range": {  # Required by frontend BankChartData interface
                    "start": min_date,
                    "end": max_date
                },
                "plotly_config": {
                    "data": traces,
                    "layout": {
                        "title": f"Evolución de Market Share - {primary_bank}",
                        "xaxis": {"title": "Fecha"},
                        "yaxis": {"title": "% del Sistema", "tickformat": ".2f"}
                    }
                },
                "summary": {
                    "bank": primary_bank,
                    "latest_share": float(bank_data.iloc[-1]['market_share']),
                    "avg_share": float(bank_data['market_share'].mean()),
                    "period_start": str(bank_data.iloc[0]['fecha']),
                    "period_end": str(bank_data.iloc[-1]['fecha'])
                }
            }

        except Exception as e:
            logger.error(
                "analytics.market_share.error",
                bank=primary_bank,
                error=str(e)
            )
            return {
                "type": "error",
                "message": f"Error al calcular market share de {primary_bank}"
            }

    # Mapping from segment codes to actual segment names in DB
    SEGMENT_CODE_MAP = {
        "AUTOMOTRIZ": "Credito Automotriz",
        "CONSUMO_AUTOMOTRIZ": "Credito Automotriz",
        "NOMINA": "Credito de Nomina",
        "TDC": "Tarjeta de Credito",
        "TARJETA": "Tarjeta de Credito",
        "PERSONALES": "Prestamos Personales",
        "VIVIENDA": "Credito a la Vivienda",
        "EMPRESAS": "Credito a Empresas",
        "CONSUMO": "Consumo Total",
        "EMPRESARIAL": "Credito a Empresas",
    }

    @staticmethod
    async def get_segment_evolution(
        session: AsyncSession,
        segment_code: str,
        metric_column: str = "imor",
        years: int = 3,
        bank_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get evolution of a specific metric for a portfolio segment.

        Uses metricas_cartera_segmentada table directly (simplified schema).

        Used for questions like:
        - "IMOR automotriz últimos 3 años"
        - "Evolución de ICOR en consumo"

        Args:
            session: AsyncSession for database queries
            segment_code: Segment code (e.g., 'AUTOMOTRIZ', 'EMPRESAS', 'CONSUMO')
            metric_column: Metric to analyze (default: 'imor')
            years: Number of years to analyze (default: 3)
            bank_filter: Optional bank name filter

        Returns:
            Dict with segment evolution data and Plotly config
        """
        from bankadvisor.config_service import get_config
        from bankadvisor.models.kpi import MetricasCarteraSegmentada
        from datetime import datetime, timedelta
        from sqlalchemy import text

        config = get_config()

        try:
            # Calculate date range
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=years * 365)

            # Map segment code to actual segment name
            segment_name = AnalyticsService.SEGMENT_CODE_MAP.get(
                segment_code.upper(),
                segment_code  # Fallback to provided code
            )

            # Build raw SQL query (simpler and more reliable)
            sql = text("""
                SELECT
                    fecha_corte::date as fecha,
                    institucion as banco,
                    {metric}
                FROM metricas_cartera_segmentada
                WHERE segmento_nombre = :segment_name
                  AND fecha_corte::date >= :start_date
                  AND fecha_corte::date <= :end_date
                  AND {metric} IS NOT NULL
                ORDER BY fecha_corte ASC
            """.format(metric=metric_column))

            result = await session.execute(
                sql,
                {"segment_name": segment_name, "start_date": start_date, "end_date": end_date}
            )
            rows = result.fetchall()

            if not rows:
                return {
                    "type": "empty",
                    "message": f"No hay datos de {metric_column} para el segmento {segment_code}"
                }

            # Format as evolution chart
            import pandas as pd
            df = pd.DataFrame(rows, columns=['fecha', 'banco', 'value'])

            # Ensure Decimal is converted to float
            # NOTE: Values in metricas_cartera_segmentada are ALREADY in percentage form (3.77 = 3.77%)
            # Unlike monthly_kpis where they're decimals (0.0377 = 3.77%)
            df['value'] = df['value'].astype(float)

            traces = []
            for banco in df['banco'].unique():
                bank_data = df[df['banco'] == banco].sort_values('fecha')
                bank_color = get_bank_color(banco)

                traces.append({
                    "x": bank_data['fecha'].astype(str).tolist(),
                    "y": [float(v) for v in bank_data['value'].tolist()],
                    "type": "scatter",
                    "mode": "lines+markers",
                    "name": str(banco),
                    "line": {"color": bank_color, "width": 2},
                    "hovertemplate": f"<b>{banco}</b><br>Fecha: %{{x}}<br>{metric_column.upper()}: %{{y:.2f}}%<extra></extra>"
                })

            # Extract bank names and time range for frontend compatibility
            unique_banks = [str(b) for b in df['banco'].unique().tolist()]
            min_date = str(df['fecha'].min())
            max_date = str(df['fecha'].max())

            return {
                "type": "data",
                "visualization": "segment_evolution",
                "metric_name": f"{metric_column.upper()} - {segment_code.title()}",
                "metric_type": "ratio",
                "bank_names": unique_banks,  # Required by frontend BankChartData interface
                "time_range": {  # Required by frontend BankChartData interface
                    "start": min_date,
                    "end": max_date
                },
                "plotly_config": {
                    "data": traces,
                    "layout": {
                        "title": f"Evolución de {metric_column.upper()} - Segmento {segment_code.title()}",
                        "xaxis": {"title": "Fecha"},
                        "yaxis": {"title": "%", "tickformat": ".2f"},
                        "autosize": True,
                        "margin": {"l": 80, "r": 20, "t": 60, "b": 60}
                    }
                },
                "summary": {
                    "segment": segment_code,
                    "metric": metric_column,
                    "banks_count": len(df['banco'].unique()),
                    "period_start": min_date,
                    "period_end": max_date
                },
                "metadata": {
                    "sql_generated": f"SELECT mcs.fecha_corte, i.nombre_corto, mcs.{metric_column}\nFROM metricas_cartera_segmentada mcs\nJOIN segmentos_cartera sc ON mcs.segmento_id = sc.id\nJOIN instituciones i ON mcs.institucion_id = i.id\nWHERE sc.codigo = '{segment_code}'\n  AND mcs.fecha_corte >= '{start_date}'\n  AND mcs.fecha_corte <= '{end_date}'\nORDER BY mcs.fecha_corte ASC;",
                    "pipeline": "segment_evolution",
                    "data_source": "metricas_cartera_segmentada"
                }
            }

        except Exception as e:
            logger.error(
                "analytics.segment_evolution.error",
                segment=segment_code,
                metric=metric_column,
                error=str(e)
            )
            return {
                "type": "error",
                "message": f"Error al consultar evolución de {segment_code}"
            }

    @staticmethod
    async def get_segment_ranking(
        session: AsyncSession,
        segment_code: str,
        metric_column: str = "imor",
        top_n: int = 5
    ) -> Dict[str, Any]:
        """
        Get ranking of institutions by metric for a specific segment.

        Uses metricas_cartera_segmentada table directly (simplified schema).

        Used for questions like:
        - "IMOR automotriz por banco (Top 5)"
        - "Top 10 bancos con mejor ICOR en consumo"

        Args:
            session: AsyncSession for database queries
            segment_code: Segment code (e.g., 'AUTOMOTRIZ', 'EMPRESAS')
            metric_column: Metric to rank by (default: 'imor')
            top_n: Number of top institutions to return (default: 5)

        Returns:
            Dict with ranking data and Plotly config
        """
        from bankadvisor.config_service import get_config
        from sqlalchemy import text

        config = get_config()

        try:
            # Map segment code to actual segment name
            segment_name = AnalyticsService.SEGMENT_CODE_MAP.get(
                segment_code.upper(),
                segment_code  # Fallback to provided code
            )

            # Get latest date and ranking using raw SQL
            sql = text("""
                WITH latest AS (
                    SELECT MAX(fecha_corte) as max_fecha
                    FROM metricas_cartera_segmentada
                    WHERE segmento_nombre = :segment_name
                )
                SELECT
                    institucion as banco,
                    {metric}
                FROM metricas_cartera_segmentada, latest
                WHERE segmento_nombre = :segment_name
                  AND fecha_corte = latest.max_fecha
                  AND {metric} IS NOT NULL
                  AND institucion NOT ILIKE '%Sistema%'
                  AND institucion NOT ILIKE '%n.a.%'
                ORDER BY {metric} ASC
                LIMIT :top_n
            """.format(metric=metric_column))

            result = await session.execute(
                sql,
                {"segment_name": segment_name, "top_n": top_n}
            )
            rows = result.fetchall()

            if not rows:
                return {
                    "type": "empty",
                    "message": f"No hay datos de {metric_column} para el segmento {segment_code}"
                }

            # Format as ranking
            import pandas as pd
            df = pd.DataFrame(rows, columns=['banco', 'value'])
            # Ensure Decimal is converted to float
            # NOTE: Values in metricas_cartera_segmentada are ALREADY in percentage form
            df['value'] = df['value'].astype(float)

            # Assign colors to each bank
            bank_colors = [get_bank_color(banco) for banco in df['banco'].tolist()]

            # Get smart visualization recommendation
            from bankadvisor.services.viz_recommender import VizRecommender
            viz_rec = VizRecommender.recommend(
                data={},
                intent="ranking",
                metric_type="ratio",
                banks_count=len(df),
                time_points=0,
                is_ranking=True,
                is_comparison=False
            )

            # Build base layout
            base_layout = {
                "title": f"Top {top_n} - {metric_column.upper()} en {segment_code.title()}",
                "xaxis": {"title": "%", "tickformat": ".2f"},
                "yaxis": {"title": "Banco"}
            }

            # Enhance layout with smart recommendations
            enhanced_layout = VizRecommender.enhance_layout(
                base_layout,
                chart_type=viz_rec["chart_type"],
                banks_count=len(df),
                metric_type="ratio"
            )

            # Extract bank names and time range for frontend compatibility
            unique_banks = [str(b) for b in df['banco'].tolist()]

            return {
                "type": "data",
                "visualization": "segment_ranking",
                "metric_name": f"{metric_column.upper()} - {segment_code.title()}",
                "metric_type": "ratio",
                "bank_names": unique_banks,  # Required by frontend BankChartData interface
                "time_range": {  # Required by frontend BankChartData interface
                    "start": str(latest_date),
                    "end": str(latest_date)
                },
                "ranking": [
                    {
                        "position": i + 1,
                        "banco": str(row['banco']),
                        "value": float(round(row['value'], 2)),
                        "unit": "%"
                    }
                    for i, (_, row) in enumerate(df.iterrows())
                ],
                "plotly_config": {
                    "data": [{
                        "x": [float(v) for v in df['value'].tolist()],
                        "y": [str(b) for b in df['banco'].tolist()],
                        "type": viz_rec["chart_type"],
                        "orientation": viz_rec.get("orientation"),
                        "marker": {"color": bank_colors},
                        "hovertemplate": "<b>%{y}</b><br>Valor: %{x:.2f}%<extra></extra>",
                        "text": [f"{float(v):.2f}%" for v in df['value'].tolist()],
                        "textposition": "auto"
                    }],
                    "layout": enhanced_layout
                },
                "viz_recommendation": viz_rec,  # Include recommendation for debugging/transparency
                "summary": {
                    "segment": segment_code,
                    "metric": metric_column,
                    "top_n": top_n,
                    "data_as_of": str(latest_date)
                },
                "metadata": {
                    "sql_generated": f"SELECT i.nombre_corto, mcs.{metric_column}\nFROM metricas_cartera_segmentada mcs\nJOIN segmentos_cartera sc ON mcs.segmento_id = sc.id\nJOIN instituciones i ON mcs.institucion_id = i.id\nWHERE sc.codigo = '{segment_code}'\n  AND mcs.fecha_corte = '{latest_date}'\n  AND i.es_sistema = FALSE\nORDER BY mcs.{metric_column} ASC\nLIMIT {top_n};",
                    "pipeline": "segment_ranking",
                    "data_source": "metricas_cartera_segmentada"
                }
            }

        except Exception as e:
            logger.error(
                "analytics.segment_ranking.error",
                segment=segment_code,
                metric=metric_column,
                error=str(e)
            )
            return {
                "type": "error",
                "message": f"Error al generar ranking de {segment_code}"
            }

    @staticmethod
    async def get_institution_ranking(
        session: AsyncSession,
        metric_column: str = "activo_total",
        top_n: int = 10,
        ascending: bool = False
    ) -> Dict[str, Any]:
        """
        Get ranking of institutions by financial metric.

        Used for questions like:
        - "Ranking de bancos por activo total"
        - "Top 10 bancos más grandes"
        - "Bancos con mayor ROE"

        Args:
            session: AsyncSession for database queries
            metric_column: Metric to rank by (default: 'activo_total')
            top_n: Number of top institutions to return (default: 10)
            ascending: Sort order (False = descending/largest first)

        Returns:
            Dict with ranking data and Plotly config
        """
        from bankadvisor.config_service import get_config
        from bankadvisor.models.normalized import MetricaFinanciera, Institucion

        config = get_config()

        try:
            # Get latest date
            latest_date_query = select(func.max(MetricaFinanciera.fecha_corte))
            result = await session.execute(latest_date_query)
            latest_date = result.scalar()

            if not latest_date:
                return {
                    "type": "empty",
                    "message": "No hay datos financieros disponibles"
                }

            # Query latest values
            order_column = getattr(MetricaFinanciera, metric_column)
            if ascending:
                order_clause = order_column.asc()
            else:
                order_clause = order_column.desc()

            query = select(
                Institucion.nombre_corto,
                getattr(MetricaFinanciera, metric_column)
            ).join(
                Institucion,
                MetricaFinanciera.institucion_id == Institucion.id
            ).where(
                MetricaFinanciera.fecha_corte == latest_date,
                Institucion.es_sistema == False  # Exclude SISTEMA aggregate
            ).order_by(order_clause).limit(top_n)

            result = await session.execute(query)
            rows = result.fetchall()

            if not rows:
                return {
                    "type": "empty",
                    "message": f"No hay datos de {metric_column}"
                }

            # Format as ranking
            import pandas as pd
            df = pd.DataFrame(rows, columns=['banco', 'value'])

            # Determine if ratio or currency
            # FIX 2025-12-05: ICOR is already in percentage scale (0-100+) in DB, don't multiply
            is_ratio = metric_column in ['imor', 'icor', 'roa_12m', 'roe_12m', 'perdida_esperada']
            is_icor = metric_column == 'icor'
            # Ensure Decimal is converted to float
            df['value'] = df['value'].astype(float)
            if is_ratio and not is_icor:
                df['value'] = df['value'] * 100  # Convert to percentage

            # Assign colors to each bank
            bank_colors = [get_bank_color(banco) for banco in df['banco'].tolist()]

            metric_display = config.get_metric_display_name(metric_column) if hasattr(config, 'get_metric_display_name') else metric_column.replace('_', ' ').title()

            # Extract bank names and time range for frontend compatibility
            unique_banks = [str(b) for b in df['banco'].tolist()]

            return {
                "type": "data",
                "visualization": "institution_ranking",
                "metric_name": metric_display,
                "metric_type": "ratio" if is_ratio else "currency",
                "bank_names": unique_banks,  # Required by frontend BankChartData interface
                "time_range": {  # Required by frontend BankChartData interface
                    "start": str(latest_date),
                    "end": str(latest_date)
                },
                "ranking": [
                    {
                        "position": i + 1,
                        "banco": str(row['banco']),
                        "value": float(round(row['value'], 2)),
                        "unit": "%" if is_ratio else "MDP"
                    }
                    for i, (_, row) in enumerate(df.iterrows())
                ],
                "plotly_config": {
                    "data": [{
                        "x": [float(v) for v in df['value'].tolist()],
                        "y": [str(b) for b in df['banco'].tolist()],
                        "type": "bar",
                        "orientation": "h",
                        "marker": {"color": bank_colors},
                        "hovertemplate": "<b>%{y}</b><br>Valor: " + ("%{x:.2f}%<extra></extra>" if is_ratio else "%{x:,.0f} MDP<extra></extra>"),
                        "text": [f"{float(v):.2f}%" if is_ratio else f"{float(v):,.0f} MDP" for v in df['value'].tolist()],
                        "textposition": "auto"
                    }],
                    "layout": {
                        "title": f"Ranking - {metric_display}",
                        "xaxis": {"title": "%" if is_ratio else "MDP (Millones de Pesos)", "tickformat": ".0f"},
                        "yaxis": {"title": "Institución", "autorange": "reversed"}
                    }
                },
                "summary": {
                    "metric": metric_column,
                    "top_n": top_n,
                    "data_as_of": str(latest_date),
                    "leader": df.iloc[0]['banco'],
                    "leader_value": float(df.iloc[0]['value'])
                }
            }

        except Exception as e:
            logger.error(
                "analytics.institution_ranking.error",
                metric=metric_column,
                error=str(e)
            )
            return {
                "type": "error",
                "message": f"Error al generar ranking por {metric_column}"
            }

    # =========================================================================
    # MÉTRICAS FINANCIERAS (BE_BM) - Balance y Estado de Resultados
    # =========================================================================

    # Metrics available in metricas_financieras_ext
    FINANCIAL_METRICS = {
        "activo_total": {"column": "activo_total", "type": "currency", "display": "Activo Total"},
        "inversiones_financieras": {"column": "inversiones_financieras", "type": "currency", "display": "Inversiones Financieras"},
        "captacion_total": {"column": "captacion_total", "type": "currency", "display": "Captación Total"},
        "capital_contable": {"column": "capital_contable", "type": "currency", "display": "Capital Contable"},
        "resultado_neto": {"column": "resultado_neto", "type": "currency", "display": "Resultado Neto"},
        "roa_12m": {"column": "roa_12m", "type": "ratio", "display": "ROA (12m)"},
        "roe_12m": {"column": "roe_12m", "type": "ratio", "display": "ROE (12m)"},
    }

    @staticmethod
    async def get_financial_metric_data(
        session: AsyncSession,
        metric_id: str,
        banks: List[str] = None,
        intent: str = "ranking",
        top_n: int = 15
    ) -> Dict[str, Any]:
        """
        Get financial metrics from metricas_financieras_ext table.

        Used for BE_BM metrics like:
        - Activo Total, Capital Contable, Resultado Neto
        - ROA, ROE

        Args:
            session: AsyncSession for database queries
            metric_id: Metric identifier (e.g., 'roa_12m', 'activo_total')
            banks: Optional list of banks to filter
            intent: Visualization intent (ranking, evolution, comparison)
            top_n: Number of top institutions for ranking

        Returns:
            Dict with data and Plotly visualization config
        """
        from sqlalchemy import text
        import pandas as pd

        # Validate metric
        metric_info = AnalyticsService.FINANCIAL_METRICS.get(metric_id)
        if not metric_info:
            return {
                "type": "error",
                "message": f"Métrica financiera '{metric_id}' no reconocida",
                "available_metrics": list(AnalyticsService.FINANCIAL_METRICS.keys())
            }

        column_name = metric_info["column"]
        metric_type = metric_info["type"]
        display_name = metric_info["display"]

        try:
            # Build query - get latest data with ranking
            sql = text(f"""
                WITH latest AS (
                    SELECT MAX(fecha_corte::date) as max_fecha
                    FROM metricas_financieras_ext
                )
                SELECT
                    banco_norm as banco,
                    fecha_corte::date as fecha,
                    {column_name} as value
                FROM metricas_financieras_ext, latest
                WHERE fecha_corte::date = latest.max_fecha
                  AND {column_name} IS NOT NULL
                  AND banco_norm IS NOT NULL
                  AND banco_norm NOT ILIKE '%sistema%'
                ORDER BY {column_name} DESC
                LIMIT :top_n
            """)

            result = await session.execute(sql, {"top_n": top_n})
            rows = result.fetchall()

            if not rows:
                return {
                    "type": "empty",
                    "message": f"No hay datos de {display_name} disponibles"
                }

            df = pd.DataFrame(rows, columns=['banco', 'fecha', 'value'])

            # Convert to float
            df['value'] = df['value'].astype(float)

            # For ratio metrics, convert to percentage if needed
            # FIX 2025-12-05: ICOR is already in percentage scale (0-100+) in DB, don't multiply
            is_ratio = metric_type == "ratio"
            is_icor = metric_id.lower() == "icor"
            if is_ratio and not is_icor:
                # All ratios (except ICOR) are now stored in 0-1 scale, convert to percentage
                df['value'] = df['value'] * 100

            # Calculate statistics
            avg_value = df['value'].mean()

            # Find INVEX position
            invex_row = df[df['banco'].str.upper() == 'INVEX']
            invex_position = None
            invex_value = None
            if not invex_row.empty:
                invex_position = df[df['banco'].str.upper() == 'INVEX'].index.tolist()[0] + 1
                invex_value = invex_row.iloc[0]['value']

            # Determine if higher is better
            higher_is_better = metric_id in ['activo_total', 'capital_contable', 'resultado_neto',
                                              'roa_12m', 'roe_12m', 'captacion_total']

            # Build colors with semantic meaning
            bar_colors = []
            bar_borders = []
            for _, row in df.iterrows():
                banco = row['banco'].upper()
                value = row['value']

                if banco == 'INVEX':
                    bar_colors.append('#E45756')  # INVEX Red
                    bar_borders.append({'width': 3, 'color': '#FFD700'})
                else:
                    # Semantic: above average = green, below = gray
                    if higher_is_better:
                        color = '#10B981' if value > avg_value else '#6B7280'
                    else:
                        color = '#10B981' if value < avg_value else '#6B7280'
                    bar_colors.append(color)
                    bar_borders.append({'width': 0, 'color': 'rgba(0,0,0,0)'})

            # Build hovertemplate
            hover_template = (
                "<b>%{y}</b><br>" +
                (f"{display_name}: %{{x:.2f}}%<extra></extra>" if is_ratio else f"{display_name}: $%{{x:,.0f}}M<extra></extra>")
            )

            max_date = df['fecha'].max()

            return {
                "type": "data",
                "visualization": "financial_ranking",
                "metric_name": display_name,
                "metric_type": metric_type,
                "bank_names": df['banco'].tolist(),
                "time_range": {"start": str(max_date), "end": str(max_date)},
                "data_as_of": str(max_date),
                "ranking": [
                    {
                        "position": i + 1,
                        "banco": row['banco'],
                        "value": round(row['value'], 2),
                        "unit": "%" if is_ratio else "MDP",
                        "vs_avg": round(row['value'] - avg_value, 2),
                        "is_invex": row['banco'].upper() == 'INVEX'
                    }
                    for i, (_, row) in enumerate(df.iterrows())
                ],
                "summary_stats": {
                    "average": round(avg_value, 2),
                    "invex_position": invex_position,
                    "invex_value": round(invex_value, 2) if invex_value else None,
                    "invex_vs_avg": round(invex_value - avg_value, 2) if invex_value else None,
                    "total_banks": len(df),
                    "higher_is_better": higher_is_better
                },
                "plotly_config": {
                    "data": [
                        {
                            "x": df['value'].tolist(),
                            "y": df['banco'].tolist(),
                            "type": "bar",
                            "orientation": "h",
                            "marker": {
                                "color": bar_colors,
                                "line": {
                                    "width": [b['width'] for b in bar_borders],
                                    "color": [b['color'] for b in bar_borders]
                                }
                            },
                            "hovertemplate": hover_template,
                            "text": [f"{v:.2f}%" if is_ratio else f"${v:,.0f}M" for v in df['value'].tolist()],
                            "textposition": "outside",
                            "textfont": {"size": 10, "color": "#374151"},
                            "name": display_name
                        },
                        # Average reference line
                        {
                            "type": "scatter",
                            "x": [avg_value, avg_value],
                            "y": [df['banco'].iloc[0], df['banco'].iloc[-1]],
                            "mode": "lines",
                            "line": {"color": "#F59E0B", "width": 3, "dash": "dash"},
                            "name": f"Promedio: {avg_value:.2f}%" if is_ratio else f"Promedio: ${avg_value:,.0f}M",
                            "showlegend": True
                        }
                    ],
                    "layout": {
                        "title": {
                            "text": f"<b>Ranking de {display_name}</b>",
                            "font": {"size": 16, "color": "#1F2937"}
                        },
                        "xaxis": {
                            "title": "%" if is_ratio else "MDP (Millones de Pesos)",
                            "tickformat": ".1f" if is_ratio else ",.0f",
                            "gridcolor": "#E5E7EB"
                        },
                        "yaxis": {
                            "title": "",
                            "tickfont": {"size": 10}
                        },
                        "legend": {
                            "orientation": "h",
                            "yanchor": "bottom",
                            "y": 1.02,
                            "xanchor": "right",
                            "x": 1
                        },
                        "margin": {"l": 150, "r": 80, "t": 60, "b": 40},
                        "plot_bgcolor": "rgba(0,0,0,0)",
                        "paper_bgcolor": "rgba(0,0,0,0)",
                        "hovermode": "closest",
                        "annotations": [
                            {
                                "x": avg_value,
                                "y": 1.05,
                                "xref": "x",
                                "yref": "paper",
                                "text": f"Promedio: {avg_value:.2f}%" if is_ratio else f"Promedio: ${avg_value:,.0f}M",
                                "showarrow": False,
                                "font": {"size": 10, "color": "#F59E0B"},
                                "bgcolor": "rgba(255,255,255,0.8)"
                            }
                        ]
                    }
                },
                "summary": f"Ranking de {display_name}" + (f" - INVEX en posición {invex_position} de {len(df)}" if invex_position else "")
            }

        except Exception as e:
            logger.error(
                "analytics.financial_metric.error",
                metric=metric_id,
                error=str(e)
            )
            return {
                "type": "error",
                "message": f"Error al consultar {display_name}"
            }
