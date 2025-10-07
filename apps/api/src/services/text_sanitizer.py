"""
Sanitizador de texto para respuestas del modelo.

Este módulo provee funciones para limpiar rótulos y encabezados no deseados
de las respuestas generadas por los modelos de lenguaje.
"""

import re
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)


# Lista de palabras clave de secciones (sin decoración)
SECTION_KEYWORDS_ES = [
    'resumen', 'respuesta', 'desarrollo', 'supuestos', 'suposiciones',
    'consideraciones', 'fuentes', 'referencias', 'siguientes pasos',
    'próximos pasos', 'pasos siguientes'
]

SECTION_KEYWORDS_EN = [
    'summary', 'response', 'answer', 'development', 'assumptions',
    'considerations', 'sources', 'references', 'next steps'
]

ALL_SECTION_KEYWORDS = SECTION_KEYWORDS_ES + SECTION_KEYWORDS_EN


def is_section_heading(line: str) -> bool:
    """
    Determina si una línea es un encabezado de sección.

    Reconoce patrones como:
    - **Resumen:**
    - **Resumen**:
    - Resumen:
    - ## Resumen
    - ## Resumen:
    - **Summary:**
    - Summary:

    Args:
        line: Línea a evaluar

    Returns:
        True si la línea es un encabezado de sección
    """
    # Limpiar la línea de espacios
    stripped = line.strip()
    if not stripped:
        return False

    # Remover markdown headers (##) del inicio
    working_line = re.sub(r'^#{1,6}\s*', '', stripped)

    # Remover negritas de markdown (**texto** o **texto:**)
    # Patrones: **Palabra:** o **Palabra**:
    working_line = re.sub(r'^\*\*(.*?)\*\*:?', r'\1', working_line)
    working_line = re.sub(r'^\*\*(.*?):?\*\*', r'\1', working_line)

    # Remover dos puntos finales
    working_line = working_line.rstrip(':').strip()

    # Convertir a minúsculas para comparación case-insensitive
    normalized = working_line.lower().strip()

    # Verificar si coincide con alguna palabra clave
    return normalized in ALL_SECTION_KEYWORDS


def strip_section_headings(text: str, debug: bool = False) -> str:
    """
    Elimina encabezados de sección del texto manteniendo el contenido.

    Esta función remueve líneas que contengan únicamente rótulos de sección
    como "Resumen:", "**Respuesta:**", "## Fuentes", etc., tanto en español
    como en inglés.

    Args:
        text: Texto a sanitizar
        debug: Si True, agrega comentarios HTML invisibles con información de debug

    Returns:
        Texto sanitizado sin encabezados de sección

    Examples:
        >>> strip_section_headings("**Resumen:**\\nContenido importante\\n\\n**Fuentes:**\\nFuente 1")
        'Contenido importante\\n\\nFuente 1'

        >>> strip_section_headings("## Resumen\\nTexto\\n\\nSiguientes pasos:\\nAcción 1")
        'Texto\\n\\nAcción 1'
    """
    if not text:
        return text

    original_text = text
    removed_headings = []

    # Procesar línea por línea
    lines = text.split('\n')
    cleaned_lines = []

    for i, line in enumerate(lines):
        # Verificar si la línea es un encabezado de sección
        if is_section_heading(line):
            if debug:
                removed_headings.append((i, line.strip()))
            logger.debug(
                "Stripped section heading",
                line_number=i,
                heading=line.strip()
            )
            # No agregar esta línea
        else:
            # Agregar líneas que no son encabezados
            cleaned_lines.append(line)

    # Unir líneas limpiadas
    cleaned_text = '\n'.join(cleaned_lines)

    # Eliminar múltiples líneas vacías consecutivas (más de 2)
    cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)

    # Eliminar espacios en blanco al inicio y final
    cleaned_text = cleaned_text.strip()

    # Agregar comentarios de debug si está habilitado
    if debug and removed_headings:
        debug_info = "<!-- DEBUG: Removed headings: " + ", ".join(
            f"L{num}: '{heading}'" for num, heading in removed_headings
        ) + " -->\n"
        cleaned_text = debug_info + cleaned_text

    # Log si se hicieron cambios
    if cleaned_text != original_text:
        logger.info(
            "Sanitized text",
            original_length=len(original_text),
            cleaned_length=len(cleaned_text),
            headings_removed=len(removed_headings) if debug else "unknown"
        )

    return cleaned_text


def sanitize_response_content(
    content: Optional[str],
    enable_sanitization: bool = True,
    debug: bool = False
) -> Optional[str]:
    """
    Sanitiza el contenido de respuesta del modelo.

    Esta es la función principal que debe ser llamada para procesar
    respuestas antes de guardarlas o mostrarlas al usuario.

    Args:
        content: Contenido a sanitizar (puede ser None)
        enable_sanitization: Si False, retorna el contenido sin modificar
        debug: Si True, habilita modo debug con comentarios HTML

    Returns:
        Contenido sanitizado o None si el input es None

    Examples:
        >>> sanitize_response_content("**Resumen:**\\nHola mundo")
        'Hola mundo'

        >>> sanitize_response_content(None)
        None

        >>> sanitize_response_content("Texto", enable_sanitization=False)
        'Texto'
    """
    if content is None:
        return None

    if not enable_sanitization:
        logger.debug("Sanitization disabled, returning original content")
        return content

    return strip_section_headings(content, debug=debug)
