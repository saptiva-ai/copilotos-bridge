from typing import Dict, Any, List
import pandas as pd

# Colores oficiales (Hardcoded para eficiencia, extraídos de legacy_styles.py)
COLOR_INVEX = "#E45756"
COLOR_SISTEMA = "#AAB0B3"
COLOR_ETAPA_1 = "#2E8B57"
COLOR_ETAPA_2 = "#FFD700"
COLOR_ETAPA_3 = "#DC143C"

class VisualizationService:
    
    @staticmethod
    def build_plotly_config(
        data: List[Dict[str, Any]],
        section_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Convierte datos planos a configuración de Plotly.js.

        Args:
            data: Lista de diccionarios [{'month_label': '...', 'data': [{'category': 'INVEX', 'value': 100}, ...]}, ...]
            section_config: Configuración de la sección desde YAML.
        """
        mode = section_config.get("mode", "dashboard_month_comparison")
        title = section_config.get("title", "Gráfico")
        unit = section_config.get("unit", "")
        is_ratio = section_config.get("type") == "ratio"

        if mode == "variation_chart":
            return VisualizationService._build_variation_chart(data, title, unit)
        elif mode == "dashboard_month_comparison":
            return VisualizationService._build_comparison_chart(data, title, unit, is_ratio)
        elif mode == "timeline_with_summary":
            return VisualizationService._build_timeline_chart(data, title, unit, is_ratio)
        elif mode == "ranking_bar_chart":
            return VisualizationService._build_ranking_chart(data, title, unit)

        # Default fallback
        return VisualizationService._build_timeline_chart(data, title, unit, is_ratio)

    @staticmethod
    def build_plotly_config_enhanced(
        data: List[Dict[str, Any]],
        section_config: Dict[str, Any],
        intent: str = "evolution"
    ) -> Dict[str, Any]:
        """
        Versión mejorada que soporta selección dinámica según intent del usuario.

        Args:
            data: Datos formateados
            section_config: Config desde YAML
            intent: Intent detectado por NlpIntentService (evolution, comparison, ranking, point_value)

        Returns:
            Plotly config adaptado al intent
        """
        mode = section_config.get("mode", "dashboard_month_comparison")
        title = section_config.get("title", "Gráfico")
        unit = section_config.get("unit", "")
        is_ratio = section_config.get("type") == "ratio"

        # Para métricas "dual_mode", seleccionar según intent
        if mode == "dual_mode":
            if intent in ["evolution", "point_value"]:
                mode = "timeline_with_summary"
            else:  # comparison, ranking
                mode = "dashboard_month_comparison"

        # Dispatch a función específica
        if mode == "variation_chart":
            return VisualizationService._build_variation_chart(data, title, unit)
        elif mode == "dashboard_month_comparison":
            return VisualizationService._build_comparison_chart(data, title, unit, is_ratio)
        elif mode == "timeline_with_summary":
            return VisualizationService._build_timeline_chart(data, title, unit, is_ratio)

        # Fallback
        return VisualizationService._build_timeline_chart(data, title, unit, is_ratio)

    @staticmethod
    def _build_comparison_chart(data: List[Dict], title: str, unit: str, is_ratio: bool) -> Dict[str, Any]:
        """Gráfico de barras agrupadas para comparar Invex vs Sistema en el último mes."""
        if not data:
            return {}
            
        # Usamos el último mes disponible
        latest_month = data[-1]
        month_label = latest_month["month_label"]
        values = latest_month["data"]
        
        categories = [item["category"] for item in values]
        # Handle NULL values: replace None with 0 for display
        vals = [item["value"] if item["value"] is not None else 0 for item in values]
        colors = [COLOR_INVEX if "INVEX" in c.upper() else COLOR_SISTEMA for c in categories]

        # Format text labels, handling None values
        def format_value(v, is_ratio):
            if v is None or v == 0:
                return "N/A"
            return f"{v:.2f}%" if is_ratio else f"{v:,.0f} MDP"

        # Build hovertemplate with units
        hover_template = (
            "<b>%{x}</b><br>" +
            ("Valor: %{y:.2f}%<extra></extra>" if is_ratio else "Valor: %{y:,.2f} MDP<extra></extra>")
        )

        return {
            "data": [
                {
                    "type": "bar",
                    "x": categories,
                    "y": vals,
                    "marker": {"color": colors},
                    "text": [format_value(v, is_ratio) for v in vals],
                    "textposition": "auto",
                    "hovertemplate": hover_template
                }
            ],
            "layout": {
                "title": {
                    "text": f"{title} - {month_label}",
                    "y": 0.95,
                    "x": 0.5,
                    "xanchor": "center",
                    "yanchor": "top"
                },
                "yaxis": {
                    "title": "%" if is_ratio else "MDP (Millones de Pesos)"
                },
                "hoverlabel": {
                    "bgcolor": "white",
                    "font_size": 13,
                    "font_family": "Arial",
                    "align": "left"
                },
                "hovermode": "closest",
                "margin": {"l": 60, "r": 50, "t": 80, "b": 50},
                "autosize": True
            }
        }

    @staticmethod
    def _build_timeline_chart(data: List[Dict], title: str, unit: str, is_ratio: bool) -> Dict[str, Any]:
        """Gráfico de líneas para evolución histórica."""
        
        months = [d["month_label"] for d in data]
        
        # Separar series
        invex_data = []
        sistema_data = []
        
        for month in data:
            for item in month["data"]:
                # Handle NULL values: use None for gaps in line charts
                value = item["value"] if item["value"] is not None else None
                if "INVEX" in item["category"].upper():
                    invex_data.append(value)
                elif "SISTEMA" in item["category"].upper():
                    sistema_data.append(value)
        
        # Build hovertemplate with units
        hover_template = (
            "<b>%{fullData.name}</b><br>" +
            "Fecha: %{x}<br>" +
            ("Valor: %{y:.2f}%<extra></extra>" if is_ratio else "Valor: %{y:,.2f} MDP<extra></extra>")
        )

        traces = []
        if invex_data:
            traces.append({
                "type": "scatter",
                "mode": "lines+markers",
                "name": "INVEX",
                "x": months,
                "y": invex_data,
                "line": {"color": COLOR_INVEX, "width": 3},
                "hovertemplate": hover_template
            })

        if sistema_data:
            traces.append({
                "type": "scatter",
                "mode": "lines+markers",
                "name": "Sistema",
                "x": months,
                "y": sistema_data,
                "line": {"color": COLOR_SISTEMA, "width": 2, "dash": "dot"},
                "hovertemplate": hover_template
            })

        return {
            "data": traces,
            "layout": {
                "title": {
                    "text": f"Evolución {title}",
                    "y": 0.95,
                    "x": 0.5,
                    "xanchor": "center",
                    "yanchor": "top"
                },
                "hovermode": "x unified",
                "xaxis": {
                    "type": "category",  # Treat month labels as categories for proper ordering
                    "title": "Período"
                },
                "yaxis": {
                    "title": "%" if is_ratio else "MDP (Millones de Pesos)"
                },
                "hoverlabel": {
                    "bgcolor": "white",
                    "font_size": 13,
                    "font_family": "Arial",
                    "align": "left"
                },
                "legend": {"orientation": "h", "y": -0.15, "yanchor": "top"},
                "margin": {"l": 60, "r": 50, "t": 80, "b": 80},
                "autosize": True
            }
        }

    @staticmethod
    def _build_variation_chart(data: List[Dict], title: str, unit: str) -> Dict[str, Any]:
        """
        Gráfico de variación porcentual mes a mes.
        Calcula (mes_actual - mes_anterior) / mes_anterior * 100

        Args:
            data: Lista de meses con datos INVEX/SISTEMA
            title: Título de la gráfica
            unit: Unidad (debe ser "%")

        Returns:
            Plotly config con barras agrupadas mostrando variación %
        """
        if len(data) < 2:
            # Necesitamos al menos 2 meses para calcular variación
            return {
                "data": [],
                "layout": {
                    "title": f"{title} - Datos insuficientes",
                    "annotations": [{
                        "text": "Se requieren al menos 2 meses de datos para calcular variación",
                        "xref": "paper",
                        "yref": "paper",
                        "showarrow": False,
                        "font": {"size": 14}
                    }]
                }
            }

        months = [d["month_label"] for d in data]
        variations_invex = []
        variations_sistema = []

        # Calcular variaciones mes a mes
        for i in range(1, len(data)):
            prev_month = data[i-1]
            curr_month = data[i]

            # Variación INVEX
            prev_invex = next((item["value"] for item in prev_month["data"] if "INVEX" in item["category"].upper()), None)
            curr_invex = next((item["value"] for item in curr_month["data"] if "INVEX" in item["category"].upper()), None)

            if prev_invex and curr_invex and prev_invex != 0:
                var_invex = ((curr_invex - prev_invex) / prev_invex) * 100
                variations_invex.append(var_invex)
            else:
                variations_invex.append(None)

            # Variación SISTEMA
            prev_sistema = next((item["value"] for item in prev_month["data"] if "SISTEMA" in item["category"].upper()), None)
            curr_sistema = next((item["value"] for item in curr_month["data"] if "SISTEMA" in item["category"].upper()), None)

            if prev_sistema and curr_sistema and prev_sistema != 0:
                var_sistema = ((curr_sistema - prev_sistema) / prev_sistema) * 100
                variations_sistema.append(var_sistema)
            else:
                variations_sistema.append(None)

        # Los labels empiezan desde el segundo mes (ya que es variación vs anterior)
        variation_months = months[1:]

        # Colores dinámicos: verde si positivo, rojo si negativo
        colors_invex = [COLOR_INVEX if v and v >= 0 else "#8B0000" for v in variations_invex]
        colors_sistema = [COLOR_SISTEMA if v and v >= 0 else "#696969" for v in variations_sistema]

        return {
            "data": [
                {
                    "type": "bar",
                    "name": "INVEX",
                    "x": variation_months,
                    "y": variations_invex,
                    "marker": {"color": colors_invex},
                    "text": [f"{v:.2f}%" if v is not None else "N/A" for v in variations_invex],
                    "textposition": "outside",
                    "hovertemplate": "<b>INVEX</b><br>Período: %{x}<br>Variación: %{y:.2f}%<extra></extra>"
                },
                {
                    "type": "bar",
                    "name": "Sistema",
                    "x": variation_months,
                    "y": variations_sistema,
                    "marker": {"color": colors_sistema},
                    "text": [f"{v:.2f}%" if v is not None else "N/A" for v in variations_sistema],
                    "textposition": "outside",
                    "hovertemplate": "<b>Sistema</b><br>Período: %{x}<br>Variación: %{y:.2f}%<extra></extra>"
                }
            ],
            "layout": {
                "title": {
                    "text": title,
                    "y": 0.95,
                    "x": 0.5,
                    "xanchor": "center",
                    "yanchor": "top"
                },
                "barmode": "group",
                "yaxis": {
                    "title": "Variación %",
                    "tickformat": ".1f",
                    "zeroline": True,
                    "zerolinewidth": 2,
                    "zerolinecolor": "black"
                },
                "xaxis": {
                    "title": "Período"
                },
                "hoverlabel": {
                    "bgcolor": "white",
                    "font_size": 13,
                    "font_family": "Arial",
                    "align": "left"
                },
                "hovermode": "closest",
                "legend": {"orientation": "h", "y": -0.15, "yanchor": "top"},
                "margin": {"l": 60, "r": 50, "t": 80, "b": 100},
                "autosize": True
            }
        }

    @staticmethod
    def _build_ranking_chart(data: List[Dict], title: str, unit: str) -> Dict[str, Any]:
        """
        Gráfico de barras horizontales para ranking de bancos.

        Args:
            data: Lista con un solo elemento "Ranking" conteniendo la lista de bancos
            title: Título de la gráfica
            unit: Unidad (MDP, %, etc.)

        Returns:
            Plotly config con barras horizontales ordenadas por valor descendente
        """
        if not data or not data[0].get("data"):
            return {}

        # Extract ranking data from the single "Ranking" month entry
        ranking_data = data[0]["data"]

        # Sort by value descending and take top 15 for readability
        sorted_data = sorted(
            [d for d in ranking_data if d.get("value") is not None],
            key=lambda x: x["value"],
            reverse=True
        )[:15]

        # Extract categories (bank names) and values
        categories = [item["category"] for item in sorted_data]
        values = [item["value"] for item in sorted_data]
        pct_totals = [item.get("pct_total") for item in sorted_data]

        # Color scale: use gradient from dark to light
        # Highlight INVEX if present
        colors = []
        for cat in categories:
            if "INVEX" in cat.upper():
                colors.append(COLOR_INVEX)
            else:
                colors.append("#4682B4")  # Steel blue for other banks

        # Format values for display (convert to billions if > 1M)
        def format_value(v):
            if v is None:
                return "N/A"
            if v >= 1_000_000:
                return f"{v/1_000_000:,.1f}B"
            elif v >= 1_000:
                return f"{v/1_000:,.1f}K"
            else:
                return f"{v:,.0f}"

        # Add percentage to text if available
        text_values = []
        for i, v in enumerate(values):
            pct = pct_totals[i] if pct_totals else None
            if pct is not None:
                text_values.append(f"{format_value(v)} ({pct:.1f}%)")
            else:
                text_values.append(format_value(v))

        # Build hovertemplate
        hover_template = (
            "<b>%{y}</b><br>" +
            "Valor: %{x:,.2f} MDP<extra></extra>"
        )

        return {
            "data": [
                {
                    "type": "bar",
                    "orientation": "h",
                    "y": categories[::-1],  # Reverse for top-to-bottom ordering
                    "x": values[::-1],
                    "marker": {"color": colors[::-1]},
                    "text": text_values[::-1],
                    "textposition": "outside",
                    "hovertemplate": hover_template
                }
            ],
            "layout": {
                "title": {
                    "text": title,
                    "y": 0.97,
                    "x": 0.5,
                    "xanchor": "center",
                    "yanchor": "top"
                },
                "xaxis": {
                    "title": "MDP (Millones de Pesos)",
                    "tickformat": ",.0f"
                },
                "yaxis": {
                    "title": "",
                    "automargin": True
                },
                "hoverlabel": {
                    "bgcolor": "white",
                    "font_size": 13,
                    "font_family": "Arial",
                    "align": "left"
                },
                "hovermode": "closest",
                "margin": {"l": 150, "r": 100, "t": 80, "b": 50},
                "autosize": True,
                "height": max(400, len(categories) * 30)  # Dynamic height based on # of banks
            }
        }
