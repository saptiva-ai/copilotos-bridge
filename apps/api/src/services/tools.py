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

    markdown = describe_tools_markdown(enabled_tools)
    schemas = tool_schemas_json(enabled_tools)

    logger.debug(
        "Built tools context",
        enabled_count=len(enabled_tools),
        has_markdown=markdown is not None,
        has_schemas=schemas is not None
    )

    return markdown, schemas


# Catálogo de herramientas disponibles (ejemplo - puedes extenderlo)
DEFAULT_AVAILABLE_TOOLS = {
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
        "description": "Investigación profunda multi-paso con síntesis de información",
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
                    "description": "Profundidad de investigación",
                    "default": "medium"
                }
            },
            "required": ["query"]
        }
    },
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
