"""
Helpers para gestión de herramientas (tools) en prompts.
Genera descripciones markdown y schemas JSON para function-calling.
"""

from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


def describe_tools_markdown(tools: Optional[List[Dict[str, Any]]]) -> Optional[str]:
    """
    Generar descripción en markdown de herramientas disponibles.

    Args:
        tools: Lista de definiciones de herramientas con formato:
            [
                {"name": "web_search", "description": "Buscar información en la web"},
                {"name": "calculator", "description": "Realizar cálculos matemáticos"}
            ]

    Returns:
        String markdown con lista de herramientas, o None si no hay herramientas

    Example:
        >>> tools = [{"name": "search", "description": "Search the web"}]
        >>> describe_tools_markdown(tools)
        '* **search** — Search the web'
    """
    if not tools or len(tools) == 0:
        return None

    try:
        lines = []
        for tool in tools:
            # Validar estructura básica
            if not isinstance(tool, dict):
                logger.warning("Invalid tool format, skipping", tool=tool)
                continue

            name = tool.get("name", "unknown")
            description = tool.get("description", "No description available")

            # Formato: * **nombre** — descripción
            lines.append(f"* **{name}** — {description}")

        if not lines:
            return None

        return "\n".join(lines)

    except Exception as e:
        logger.error("Error generating tools markdown", error=str(e), tools=tools)
        return None


def tool_schemas_json(tools: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
    """
    Convertir herramientas a formato JSON Schema para function-calling.

    Args:
        tools: Lista de definiciones de herramientas con formato expandido:
            [
                {
                    "name": "web_search",
                    "description": "Buscar información en la web",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Query de búsqueda"}
                        },
                        "required": ["query"]
                    }
                }
            ]

    Returns:
        Lista de schemas JSON compatibles con function-calling de OpenAI/Saptiva,
        o None si no hay herramientas o falta información

    Example:
        >>> tools = [{
        ...     "name": "search",
        ...     "description": "Search",
        ...     "parameters": {"type": "object", "properties": {"q": {"type": "string"}}}
        ... }]
        >>> schemas = tool_schemas_json(tools)
        >>> schemas[0]["type"]
        'function'
    """
    if not tools or len(tools) == 0:
        return None

    try:
        schemas = []

        for tool in tools:
            # Validar estructura básica
            if not isinstance(tool, dict):
                logger.warning("Invalid tool format for schema, skipping", tool=tool)
                continue

            name = tool.get("name")
            description = tool.get("description", "")
            parameters = tool.get("parameters")

            # Function-calling requiere nombre y parámetros
            if not name:
                logger.warning("Tool missing name, skipping", tool=tool)
                continue

            # Si no hay parameters, usar schema vacío básico
            if not parameters:
                parameters = {
                    "type": "object",
                    "properties": {},
                    "required": []
                }

            # Formato OpenAI/Saptiva function-calling
            schema = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": parameters
                }
            }

            schemas.append(schema)

        if not schemas:
            return None

        logger.debug("Generated tool schemas", count=len(schemas))
        return schemas

    except Exception as e:
        logger.error("Error generating tool schemas", error=str(e), tools=tools)
        return None


def build_tools_context(
    tools_enabled: Optional[Dict[str, bool]],
    available_tools: Optional[Dict[str, Dict[str, Any]]] = None
) -> tuple[Optional[str], Optional[List[Dict[str, Any]]]]:
    """
    Construir contexto de herramientas para inyectar en prompts.

    Args:
        tools_enabled: Dict de herramientas habilitadas {tool_name: bool}
        available_tools: Dict de definiciones completas de herramientas disponibles

    Returns:
        Tupla de (markdown_description, json_schemas) para inyectar en system prompt
        y payload respectivamente

    Example:
        >>> tools_enabled = {"web_search": True, "calculator": False}
        >>> available = {
        ...     "web_search": {
        ...         "name": "web_search",
        ...         "description": "Search the web",
        ...         "parameters": {"type": "object", "properties": {}}
        ...     }
        ... }
        >>> markdown, schemas = build_tools_context(tools_enabled, available)
        >>> "web_search" in markdown
        True
    """
    if not tools_enabled:
        return None, None

    # Filtrar herramientas habilitadas
    enabled_tool_names = [name for name, enabled in tools_enabled.items() if enabled]

    if not enabled_tool_names:
        return None, None

    # Si no hay definiciones disponibles, solo retornar nombres
    if not available_tools:
        simple_tools = [{"name": name, "description": f"Tool: {name}"} for name in enabled_tool_names]
        markdown = describe_tools_markdown(simple_tools)
        return markdown, None

    # Construir lista de herramientas completas
    enabled_tools = []
    for tool_name in enabled_tool_names:
        if tool_name in available_tools:
            enabled_tools.append(available_tools[tool_name])
        else:
            # Fallback si no está en available_tools
            enabled_tools.append({
                "name": tool_name,
                "description": f"Tool: {tool_name}"
            })

    # BA-P0-004: Excluir bank_analytics porque se ejecuta proactivamente
    # bank_analytics se invoca ANTES del LLM en streaming_handler.py y sus resultados
    # se inyectan como contexto. No debe aparecer en el markdown NI en schemas porque
    # confunde al LLM y genera tool_calls que el backend no puede ejecutar.
    tools_without_bank_analytics = [t for t in enabled_tools if t.get("name") != "bank_analytics"]

    markdown = describe_tools_markdown(tools_without_bank_analytics)
    schemas = tool_schemas_json(tools_without_bank_analytics) if tools_without_bank_analytics else None

    logger.debug(
        "Built tools context",
        enabled_count=len(enabled_tools),
        has_markdown=markdown is not None,
        has_schemas=schemas is not None
    )

    return markdown, schemas


# Catálogo de herramientas disponibles (incluye MCP tools integradas)
DEFAULT_AVAILABLE_TOOLS = {
    # === Web & Research Tools ===
    "web_search": {
        "name": "web_search",
        "description": "Buscar información actualizada en la web mediante motor de búsqueda",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Consulta de búsqueda"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Número de resultados (default: 5)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    },
    "deep_research": {
        "name": "deep_research",
        "description": "Investigación profunda multi-paso con síntesis de información usando Aletheia",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Pregunta o tema de investigación"
                },
                "depth": {
                    "type": "string",
                    "enum": ["shallow", "medium", "deep"],
                    "description": "Profundidad de investigación (shallow: 1-2 iteraciones, medium: 3-4, deep: 5+)",
                    "default": "medium"
                },
                "focus_areas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Áreas específicas en las que enfocarse (opcional)"
                }
            },
            "required": ["query"]
        }
    },

    # === Document Tools (MCP) ===
    "create_artifact": {
        "name": "create_artifact",
        "description": "Guardar un artefacto (markdown, código o grafo) asociado al chat y devolver su ID",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Título corto para el artefacto"
                },
                "type": {
                    "type": "string",
                    "enum": ["markdown", "code", "graph"],
                    "description": "Tipo de artefacto a crear"
                },
                "content": {
                    "type": "string",
                    "description": "Contenido del artefacto en formato markdown, código o grafo serializado"
                }
            },
            "required": ["title", "type", "content"]
        }
    },
    "extract_document_text": {
        "name": "extract_document_text",
        "description": "Extraer texto de documentos PDF e imágenes usando estrategia multi-tier (pypdf → Saptiva PDF SDK → OCR)",
        "parameters": {
            "type": "object",
            "properties": {
                "doc_id": {
                    "type": "string",
                    "description": "ID del documento del cual extraer texto"
                },
                "method": {
                    "type": "string",
                    "enum": ["auto", "pypdf", "saptiva_sdk", "ocr"],
                    "default": "auto",
                    "description": "Método de extracción"
                },
                "include_metadata": {
                    "type": "boolean",
                    "default": True,
                    "description": "Incluir metadatos del documento en la respuesta"
                }
            },
            "required": ["doc_id"]
        }
    },

    # === Data Analytics Tools (MCP) ===
    "excel_analyzer": {
        "name": "excel_analyzer",
        "description": "Analizar archivos Excel: estadísticas, agregaciones, validación de datos, preview",
        "parameters": {
            "type": "object",
            "properties": {
                "doc_id": {
                    "type": "string",
                    "description": "ID del documento Excel"
                },
                "sheet_name": {
                    "type": "string",
                    "description": "Nombre de la hoja (default: primera hoja)"
                },
                "operations": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["stats", "aggregate", "validate", "preview"]
                    },
                    "description": "Operaciones a realizar",
                    "default": ["stats", "preview"]
                },
                "aggregate_columns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Columnas para agregar (para operación 'aggregate')"
                }
            },
            "required": ["doc_id"]
        }
    },
    "viz_tool": {
        "name": "viz_tool",
        "description": "Generar especificaciones de gráficos interactivos (Plotly/ECharts) a partir de datos",
        "parameters": {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "pie", "scatter", "heatmap", "histogram"],
                    "description": "Tipo de gráfico"
                },
                "data_source": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["inline", "excel", "sql"]
                        },
                        "doc_id": {"type": "string"},
                        "data": {"type": "array"}
                    },
                    "required": ["type"]
                },
                "x_column": {
                    "type": "string",
                    "description": "Nombre de la columna para eje X"
                },
                "y_column": {
                    "type": "string",
                    "description": "Nombre de la columna para eje Y"
                },
                "title": {
                    "type": "string",
                    "description": "Título del gráfico"
                }
            },
            "required": ["chart_type", "data_source"]
        }
    },

    # === Banking Analytics Tools (MCP) - BA-P0-001 ===
    "bank_analytics": {
        "name": "bank_analytics",
        "description": "Consultar y visualizar métricas bancarias CNBV (IMOR, ROE, ROA, Morosidad, Liquidez, CAP) con NL2SQL. Soporta consultas en lenguaje natural sobre datos históricos bancarios mexicanos 2017-2025.",
        "parameters": {
            "type": "object",
            "properties": {
                "metric_or_query": {
                    "type": "string",
                    "description": "Consulta en lenguaje natural o métrica bancaria (ej: 'IMOR de INVEX en 2024', 'ROE de Santander vs BBVA 2023', 'bancos con mayor morosidad')"
                },
                "mode": {
                    "type": "string",
                    "enum": ["dashboard", "comparison", "trend", "ranking"],
                    "default": "dashboard",
                    "description": "Tipo de visualización: dashboard (métrica única), comparison (varios bancos), trend (evolución temporal), ranking (top/bottom bancos)"
                }
            },
            "required": ["metric_or_query"]
        }
    },

    # === Utility Tools ===
    "calculator": {
        "name": "calculator",
        "description": "Realizar cálculos matemáticos precisos",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Expresión matemática a evaluar (e.g., '2 + 2 * 10')"
                }
            },
            "required": ["expression"]
        }
    },
    "code_executor": {
        "name": "code_executor",
        "description": "Ejecutar código Python en entorno aislado",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Código Python a ejecutar"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout en segundos (default: 30)",
                    "default": 30
                }
            },
            "required": ["code"]
        }
    }
}


def normalize_tools_state(tools: Optional[Dict[str, Any]]) -> Dict[str, bool]:
    """Normalize raw tools-enabled mapping to boolean map with defaults."""

    # Default map from known tools (all tools disabled by default)
    normalized: Dict[str, bool] = {name: False for name in DEFAULT_AVAILABLE_TOOLS.keys()}

    # BA-P0-004: bank_analytics enabled by default for SAPTIVA models
    # The system prompt instructs the LLM when to use this tool for banking queries
    normalized["bank_analytics"] = True

    if tools:
        for name, value in tools.items():
            try:
                # Allow any tool name, not just defaults (supports dynamic/new tools)
                normalized[name] = bool(value)
            except Exception:
                normalized[name] = False

    return normalized
