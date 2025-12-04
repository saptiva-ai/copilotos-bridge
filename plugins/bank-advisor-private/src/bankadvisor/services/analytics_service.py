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
            - "variation": Month-over-month variation chart
            - "single_series": Single series chart (SISTEMA only)
            - "table": Multi-month table view
            - None: Use standard intent-based routing
        """
        query_lower = user_query.lower()

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

        # Check for variation keywords
        variation_keywords = [
            "variación", "variacion", "cambio", "diferencia",
            "mes a mes", "mensual", "delta", "incremento", "decremento"
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

        return None

    @staticmethod
    def _format_evolution(rows, metric_id: str, config, metric_type: str) -> Dict[str, Any]:
        """Format data for evolution/trend view with Plotly config."""
        import pandas as pd

        df = pd.DataFrame(rows, columns=['fecha', 'banco', 'value'])

        # Convert ratio metrics to percentage, currency to millions
        is_ratio = metric_type == "ratio"

        # DEBUG: Log original values
        import structlog
        logger = structlog.get_logger(__name__)
        logger.info("analytics_service._format_evolution.values_before_conversion",
                   metric_id=metric_id,
                   metric_type=metric_type,
                   is_ratio=is_ratio,
                   sample_values=df['value'].head(10).tolist() if len(df) > 0 else [],
                   all_unique_values=sorted(df['value'].unique().tolist()) if len(df) > 0 else [])

        if is_ratio:
            df['value'] = df['value'] * 100
        else:
            # IMPORTANT: Database values are ALREADY in millions (MDP)
            # DO NOT divide by 1,000,000 as it would make them too small
            # df['value'] = df['value'] / 1_000_000
            pass  # Values are already in correct scale

        # DEBUG: Log converted values
        logger.info("analytics_service._format_evolution.values_after_conversion",
                   metric_id=metric_id,
                   is_ratio=is_ratio,
                   sample_values=df['value'].head(10).tolist() if len(df) > 0 else [])

        # Build hovertemplate with units
        hover_template = (
            "<b>%{fullData.name}</b><br>" +
            "Fecha: %{x}<br>" +
            ("Valor: %{y:.2f}%<extra></extra>" if is_ratio else "Valor: %{y:,.2f} MDP<extra></extra>")
        )

        # Group by bank for multi-line chart with distinctive colors
        traces = []
        for banco in df['banco'].unique():
            bank_data = df[df['banco'] == banco].sort_values('fecha')
            bank_color = get_bank_color(banco)

            # INVEX gets thicker line, SISTEMA gets dashed, others solid
            line_config = {"color": bank_color, "width": 2}
            if banco.upper() == "INVEX":
                line_config["width"] = 3  # Thicker for emphasis
            elif banco.upper() == "SISTEMA":
                line_config["dash"] = "dot"  # Dashed for reference

            traces.append({
                "x": bank_data['fecha'].astype(str).tolist(),
                "y": bank_data['value'].tolist(),
                "type": "scatter",
                "mode": "lines+markers",
                "name": banco,
                "line": line_config,
                "hovertemplate": hover_template
            })

        display_name = config.get_metric_display_name(metric_id)

        # Calculate time range and metadata from data
        time_range = {}
        bank_names = []
        data_as_of = None
        summary = None

        if len(df) > 0:
            df_sorted = df.sort_values('fecha')
            min_date = df_sorted['fecha'].min()
            max_date = df_sorted['fecha'].max()
            time_range = {
                "start": str(min_date),
                "end": str(max_date)
            }
            bank_names = df['banco'].unique().tolist()
            data_as_of = str(max_date)

            # Calculate summary statistics for the primary bank (first in list)
            primary_bank = bank_names[0] if bank_names else None
            if primary_bank:
                bank_df = df[df['banco'] == primary_bank].sort_values('fecha')
                if len(bank_df) >= 2:
                    current_value = bank_df.iloc[-1]['value']
                    previous_value = bank_df.iloc[-2]['value']

                    # Calculate percentage change
                    change_pct = None
                    if previous_value and previous_value != 0:
                        change_pct = ((current_value - previous_value) / previous_value) * 100

                    summary = {
                        "current_value": float(current_value) if current_value else None,
                        "previous_value": float(previous_value) if previous_value else None,
                        "change_pct": round(change_pct, 2) if change_pct is not None else None,
                        "period_end": str(max_date),
                        "bank": primary_bank
                    }

        return {
            "type": "data",
            "visualization": "line_chart",
            "metric_name": display_name,
            "metric_type": metric_type,  # Include type for context
            "bank_names": bank_names,  # List of banks in chart
            "time_range": time_range,  # Add time range for UI header
            "data_as_of": data_as_of,  # Last data update
            "summary": summary,  # Summary stats for LLM/UI alignment
            "plotly_config": {
                "data": traces,
                "layout": {
                    "title": f"Evolución de {display_name}",
                    "xaxis": {"title": "Fecha"},
                    "yaxis": {
                        "title": "%" if is_ratio else "MDP (Millones de Pesos)"
                    }
                }
            },
            "summary": f"Mostrando evolución de {display_name}"
        }

    @staticmethod
    def _format_comparison(rows, metric_id: str, config, metric_type: str) -> Dict[str, Any]:
        """Format data for bank comparison with Plotly config."""
        import pandas as pd

        df = pd.DataFrame(rows, columns=['fecha', 'banco', 'value'])

        # Convert ratio metrics to percentage, currency to millions
        is_ratio = metric_type == "ratio"
        if is_ratio:
            df['value'] = df['value'] * 100
        # else: Database values are ALREADY in millions (MDP), no conversion needed

        # Get latest value per bank
        latest = df.sort_values('fecha').groupby('banco').last().reset_index()

        display_name = config.get_metric_display_name(metric_id)

        # Build hovertemplate with units
        hover_template = (
            "<b>%{x}</b><br>" +
            ("Valor: %{y:.2f}%<extra></extra>" if is_ratio else "Valor: %{y:,.2f} MDP<extra></extra>")
        )

        # Calculate metadata from data
        time_range = {}
        bank_names = []
        data_as_of = None
        summary = None

        if len(df) > 0:
            df_sorted = df.sort_values('fecha')
            max_date = df_sorted['fecha'].max()
            time_range = {
                "start": str(df_sorted['fecha'].min()),
                "end": str(max_date)
            }
            bank_names = latest['banco'].tolist()
            data_as_of = str(max_date)

            # For comparison, summary shows the highest value bank
            if len(latest) > 0:
                top_bank = latest.iloc[0]
                summary = {
                    "current_value": float(top_bank['value']) if top_bank['value'] else None,
                    "period_end": str(max_date),
                    "bank": top_bank['banco']
                }

        # Assign distinctive colors to each bank
        bank_colors = [get_bank_color(banco) for banco in latest['banco'].tolist()]

        return {
            "type": "data",
            "visualization": "bar_chart",
            "metric_name": display_name,
            "metric_type": metric_type,
            "bank_names": bank_names,  # List of banks in chart
            "time_range": time_range,  # Add time range for UI header
            "data_as_of": data_as_of,  # Last data update
            "summary": summary,  # Summary stats for LLM/UI alignment
            "plotly_config": {
                "data": [{
                    "x": latest['banco'].tolist(),
                    "y": latest['value'].tolist(),
                    "type": "bar",
                    "marker": {"color": bank_colors},  # Use distinctive colors per bank
                    "hovertemplate": hover_template,
                    "text": [f"{v:.2f}%" if is_ratio else f"{v:,.0f} MDP" for v in latest['value'].tolist()],
                    "textposition": "auto"
                }],
                "layout": {
                    "title": f"Comparación de {display_name}",
                    "xaxis": {"title": "Banco"},
                    "yaxis": {
                        "title": "%" if is_ratio else "MDP (Millones de Pesos)"
                    }
                }
            },
            "summary": f"Comparando {display_name} entre bancos"
        }

    @staticmethod
    def _format_ranking(rows, metric_id: str, config, metric_type: str) -> Dict[str, Any]:
        """Format data for ranking view."""
        import pandas as pd

        df = pd.DataFrame(rows, columns=['fecha', 'banco', 'value'])

        # Convert ratio metrics to percentage, currency to millions
        is_ratio = metric_type == "ratio"
        if is_ratio:
            df['value'] = df['value'] * 100
        # else: Database values are ALREADY in millions (MDP), no conversion needed

        # Get latest value per bank, sorted
        latest = df.sort_values('fecha').groupby('banco').last().reset_index()
        latest = latest.sort_values('value', ascending=False)

        display_name = config.get_metric_display_name(metric_id)

        # Build hovertemplate with units
        hover_template = (
            "<b>%{y}</b><br>" +
            ("Valor: %{x:.2f}%<extra></extra>" if is_ratio else "Valor: %{x:,.2f} MDP<extra></extra>")
        )

        # Assign distinctive colors to each bank in ranking
        bank_colors = [get_bank_color(banco) for banco in latest['banco'].tolist()]

        return {
            "type": "data",
            "visualization": "ranking",
            "metric_name": display_name,
            "metric_type": metric_type,
            "ranking": [
                {
                    "position": i + 1,
                    "banco": row['banco'],
                    "value": round(row['value'], 2),
                    "unit": "%" if is_ratio else "MDP"
                }
                for i, (_, row) in enumerate(latest.iterrows())
            ],
            "plotly_config": {
                "data": [{
                    "x": latest['value'].tolist(),
                    "y": latest['banco'].tolist(),
                    "type": "bar",
                    "orientation": "h",
                    "marker": {"color": bank_colors},  # Use distinctive colors per bank
                    "hovertemplate": hover_template,
                    "text": [f"{v:.2f}%" if is_ratio else f"{v:,.0f} MDP" for v in latest['value'].tolist()],
                    "textposition": "auto"
                }],
                "layout": {
                    "title": f"Ranking de {display_name}",
                    "xaxis": {
                        "title": "%" if is_ratio else "MDP (Millones de Pesos)",
                        "tickformat": ".0f",
                        "ticksuffix": "%" if is_ratio else " MDP"
                    },
                    "yaxis": {"title": "Banco", "autorange": "reversed"}
                }
            },
            "summary": f"Ranking de {display_name}"
        }

    @staticmethod
    def _format_point_value(rows, metric_id: str, config, metric_type: str) -> Dict[str, Any]:
        """Format data for single point value."""
        import pandas as pd

        df = pd.DataFrame(rows, columns=['fecha', 'banco', 'value'])

        # Convert ratio metrics to percentage, currency to millions
        is_ratio = metric_type == "ratio"
        if is_ratio:
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
        if is_ratio:
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

        # Convert ratio metrics to percentage
        is_ratio = metric_type == "ratio"
        if is_ratio:
            df['value'] = df['value'] * 100

        df = df.sort_values('fecha')
        display_name = config.get_metric_display_name(metric_id)

        # Build simple line chart
        hover_template = (
            "<b>SISTEMA</b><br>" +
            "Fecha: %{x}<br>" +
            ("Valor: %{y:.2f}%<extra></extra>" if is_ratio else "Valor: %{y:,.2f} MDP<extra></extra>")
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
                        "title": "%" if is_ratio else "MDP (Millones de Pesos)"
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
        if is_ratio:
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
        if is_ratio:
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
            is_ratio = metric_column in ['imor', 'icor', 'roa_12m', 'roe_12m', 'perdida_esperada']
            # Ensure Decimal is converted to float
            df['value'] = df['value'].astype(float)
            if is_ratio:
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
