"""
Tests unitarios para el sanitizador de texto.

Verifica que la función strip_section_headings() remueva correctamente
encabezados de sección en español e inglés sin afectar contenido válido.
"""

import pytest
from src.services.text_sanitizer import strip_section_headings, sanitize_response_content


class TestStripSectionHeadings:
    """Tests para la función strip_section_headings."""

    # Tests de casos en español
    def test_spanish_heading_with_bold_and_colon(self):
        """Debe remover encabezado en español con negritas y dos puntos."""
        text = "**Resumen:**\nContenido importante\n\n**Fuentes:**\nFuente 1"
        expected = "Contenido importante\n\nFuente 1"
        assert strip_section_headings(text) == expected

    def test_spanish_heading_without_bold(self):
        """Debe remover encabezado en español sin negritas."""
        text = "Resumen:\nTexto\n\nSiguientes pasos:\nAcción 1"
        expected = "Texto\n\nAcción 1"
        assert strip_section_headings(text) == expected

    def test_spanish_heading_with_markdown_hash(self):
        """Debe remover encabezado en español con ##."""
        text = "## Resumen\nTexto\n\n## Fuentes\nFuente 1"
        expected = "Texto\n\nFuente 1"
        assert strip_section_headings(text) == expected

    def test_spanish_heading_without_colon(self):
        """Debe remover encabezado en español sin dos puntos."""
        text = "**Resumen**\nTexto\n\n**Fuentes**\nFuente 1"
        expected = "Texto\n\nFuente 1"
        assert strip_section_headings(text) == expected

    def test_spanish_all_section_types(self):
        """Debe remover todos los tipos de secciones en español."""
        text = """**Resumen:**
Esto es un resumen.

**Desarrollo:**
Contenido detallado aquí.

**Supuestos:**
- Supuesto 1
- Supuesto 2

**Fuentes:**
- Fuente 1
- Fuente 2

**Siguientes pasos:**
- Paso 1
- Paso 2"""

        result = strip_section_headings(text)

        # Verificar que no contenga los encabezados
        assert "**Resumen:**" not in result
        assert "**Desarrollo:**" not in result
        assert "**Supuestos:**" not in result
        assert "**Fuentes:**" not in result
        assert "**Siguientes pasos:**" not in result

        # Verificar que el contenido esté presente
        assert "Esto es un resumen." in result
        assert "Contenido detallado aquí." in result
        assert "Supuesto 1" in result
        assert "Fuente 1" in result
        assert "Paso 1" in result

    # Tests de casos en inglés
    def test_english_heading_with_bold_and_colon(self):
        """Debe remover encabezado en inglés con negritas y dos puntos."""
        text = "**Summary:**\nImportant content\n\n**Sources:**\nSource 1"
        expected = "Important content\n\nSource 1"
        assert strip_section_headings(text) == expected

    def test_english_heading_without_bold(self):
        """Debe remover encabezado en inglés sin negritas."""
        text = "Summary:\nText\n\nNext steps:\nAction 1"
        expected = "Text\n\nAction 1"
        assert strip_section_headings(text) == expected

    def test_english_heading_with_markdown_hash(self):
        """Debe remover encabezado en inglés con ##."""
        text = "## Summary\nText\n\n## Sources\nSource 1"
        expected = "Text\n\nSource 1"
        assert strip_section_headings(text) == expected

    def test_english_all_section_types(self):
        """Debe remover todos los tipos de secciones en inglés."""
        text = """**Summary:**
This is a summary.

**Answer:**
Detailed content here.

**Assumptions:**
- Assumption 1
- Assumption 2

**Sources:**
- Source 1
- Source 2

**Next steps:**
- Step 1
- Step 2"""

        result = strip_section_headings(text)

        # Verificar que no contenga los encabezados
        assert "**Summary:**" not in result
        assert "**Answer:**" not in result
        assert "**Assumptions:**" not in result
        assert "**Sources:**" not in result
        assert "**Next steps:**" not in result

        # Verificar que el contenido esté presente
        assert "This is a summary." in result
        assert "Detailed content here." in result
        assert "Assumption 1" in result
        assert "Source 1" in result
        assert "Step 1" in result

    # Tests de casos mixtos
    def test_mixed_spanish_and_english(self):
        """Debe remover encabezados mixtos en español e inglés."""
        text = "**Resumen:**\nContenido\n\n**Sources:**\nSource 1\n\n**Siguientes pasos:**\nPaso 1"
        result = strip_section_headings(text)

        assert "**Resumen:**" not in result
        assert "**Sources:**" not in result
        assert "**Siguientes pasos:**" not in result
        assert "Contenido" in result
        assert "Source 1" in result
        assert "Paso 1" in result

    # Tests de falsos positivos (no debe remover)
    def test_no_false_positive_in_normal_text(self):
        """No debe remover texto normal que contiene palabras similares."""
        text = "El resumen del artículo es importante. Las fuentes consultadas fueron variadas."
        result = strip_section_headings(text)
        assert result == text

    def test_no_false_positive_with_inline_bold(self):
        """No debe remover negritas inline en texto normal."""
        text = "Este **resumen** es parte del texto normal. Ver **fuentes** para más info."
        result = strip_section_headings(text)
        assert result == text

    def test_no_false_positive_in_sentences(self):
        """No debe remover encabezados que son parte de oraciones."""
        text = "Para el resumen: ver página 10. Sobre las fuentes: consultar bibliografía."
        result = strip_section_headings(text)
        assert result == text

    # Tests de edge cases
    def test_empty_string(self):
        """Debe manejar string vacío."""
        assert strip_section_headings("") == ""

    def test_none_value(self):
        """Debe manejar None retornando string vacío."""
        assert strip_section_headings(None) == None

    def test_only_headings(self):
        """Debe manejar texto con solo encabezados."""
        text = "**Resumen:**\n\n**Fuentes:**\n\n**Siguientes pasos:**"
        result = strip_section_headings(text)
        # El resultado debe estar vacío o tener solo líneas en blanco
        assert result.strip() == ""

    def test_multiple_blank_lines_cleanup(self):
        """Debe limpiar múltiples líneas en blanco consecutivas."""
        text = "Contenido 1\n\n\n\n\nContenido 2"
        result = strip_section_headings(text)
        assert "\n\n\n" not in result  # No debe haber más de 2 newlines consecutivos

    def test_whitespace_variations(self):
        """Debe manejar variaciones de espacios en blanco."""
        text = "  **Resumen:**  \n  Contenido\n\n  **Fuentes:**  \n  Fuente 1"
        result = strip_section_headings(text)
        assert "**Resumen:**" not in result
        assert "**Fuentes:**" not in result
        assert "Contenido" in result
        assert "Fuente 1" in result

    # Tests de variaciones de encabezados
    def test_heading_variations_suposiciones(self):
        """Debe reconocer variaciones de 'suposiciones'."""
        variations = [
            "**Suposiciones:**\nTexto",
            "**Supuestos:**\nTexto",
            "**Consideraciones:**\nTexto"
        ]
        for text in variations:
            result = strip_section_headings(text)
            assert "Texto" in result
            assert "**" not in result.split('\n')[0]  # Primera línea no debe tener **

    def test_heading_variations_pasos(self):
        """Debe reconocer variaciones de 'siguientes pasos'."""
        variations = [
            "**Siguientes pasos:**\nTexto",
            "**Próximos pasos:**\nTexto",
            "**Pasos siguientes:**\nTexto",
            "**Next steps:**\nTexto",
            "**Next Steps:**\nTexto"
        ]
        for text in variations:
            result = strip_section_headings(text)
            assert "Texto" in result
            assert "pasos" not in result.lower().split('\n')[0]

    def test_case_insensitive_matching(self):
        """Debe ser case-insensitive para los encabezados."""
        text = "**RESUMEN:**\nTexto\n\n**resumen:**\nMás texto\n\n**ReSuMeN:**\nOtro texto"
        result = strip_section_headings(text)
        assert "**RESUMEN:**" not in result
        assert "**resumen:**" not in result
        assert "**ReSuMeN:**" not in result
        assert "Texto" in result
        assert "Más texto" in result
        assert "Otro texto" in result

    # Tests del modo debug
    def test_debug_mode_adds_html_comments(self):
        """Modo debug debe agregar comentarios HTML con información."""
        text = "**Resumen:**\nContenido"
        result = strip_section_headings(text, debug=True)
        assert "<!-- DEBUG:" in result
        assert "Removed headings:" in result
        assert "Contenido" in result

    def test_debug_mode_without_removals(self):
        """Modo debug sin remociones no debe agregar comentarios."""
        text = "Contenido normal sin encabezados"
        result = strip_section_headings(text, debug=True)
        assert "<!-- DEBUG:" not in result
        assert result == text


class TestSanitizeResponseContent:
    """Tests para la función sanitize_response_content."""

    def test_sanitize_with_enabled(self):
        """Debe sanitizar cuando está habilitado."""
        content = "**Resumen:**\nTexto importante"
        result = sanitize_response_content(content, enable_sanitization=True)
        assert "**Resumen:**" not in result
        assert "Texto importante" in result

    def test_sanitize_with_disabled(self):
        """No debe sanitizar cuando está deshabilitado."""
        content = "**Resumen:**\nTexto importante"
        result = sanitize_response_content(content, enable_sanitization=False)
        assert result == content

    def test_sanitize_none_value(self):
        """Debe manejar None correctamente."""
        result = sanitize_response_content(None, enable_sanitization=True)
        assert result is None

    def test_sanitize_empty_string(self):
        """Debe manejar string vacío correctamente."""
        result = sanitize_response_content("", enable_sanitization=True)
        assert result == ""

    def test_sanitize_with_debug(self):
        """Debe pasar el flag de debug correctamente."""
        content = "**Resumen:**\nTexto"
        result = sanitize_response_content(content, enable_sanitization=True, debug=True)
        assert "<!-- DEBUG:" in result
        assert "Texto" in result


class TestRealWorldExamples:
    """Tests con ejemplos del mundo real."""

    def test_example_apple_question(self):
        """Test con ejemplo de pregunta 'qué es apple?'"""
        text = """**Resumen:**
Apple es una empresa tecnológica multinacional.

**Desarrollo:**
Fundada en 1976, Apple diseña y comercializa productos electrónicos de consumo.

**Supuestos:**
- Se asume que preguntas por Apple Inc., no por la fruta.
- Información actualizada a 2024.

**Fuentes:**
Sin fuente verificable (conocimiento general).

**Siguientes pasos:**
- Si necesitas información financiera específica, puedo buscarla.
- ¿Te interesa algún producto en particular?"""

        result = strip_section_headings(text)

        # Verificar que no hay encabezados
        assert "**Resumen:**" not in result
        assert "**Desarrollo:**" not in result
        assert "**Supuestos:**" not in result
        assert "**Fuentes:**" not in result
        assert "**Siguientes pasos:**" not in result

        # Verificar que el contenido está presente
        assert "Apple es una empresa tecnológica multinacional." in result
        assert "Fundada en 1976" in result
        assert "Se asume que preguntas por Apple Inc." in result
        assert "Sin fuente verificable" in result
        assert "Si necesitas información financiera específica" in result

    def test_example_with_markdown_formatting(self):
        """Test con formato markdown real."""
        text = """## Resumen
La inteligencia artificial está transformando la industria.

## Desarrollo
Los avances recientes incluyen:
- **GPT-4** para procesamiento de lenguaje
- **DALL-E** para generación de imágenes
- **AlphaFold** para predicción de proteínas

## Fuentes
- OpenAI (2024): "GPT-4 Technical Report"
- DeepMind (2024): "AlphaFold Database"

## Siguientes pasos
- Explorar casos de uso específicos
- Evaluar impacto ético y social"""

        result = strip_section_headings(text)

        # Verificar que no hay encabezados de sección
        assert "## Resumen" not in result
        assert "## Desarrollo" not in result
        assert "## Fuentes" not in result
        assert "## Siguientes pasos" not in result

        # Verificar que el contenido estructurado permanece
        assert "**GPT-4**" in result  # Negritas inline deben permanecer
        assert "**DALL-E**" in result
        assert "OpenAI (2024)" in result
        assert "Explorar casos de uso específicos" in result

    def test_example_empty_sections(self):
        """Test con secciones vacías que deben omitirse."""
        text = """**Resumen:**
Respuesta breve.

**Desarrollo:**

**Fuentes:**
Sin fuente verificable.

**Siguientes pasos:**"""

        result = strip_section_headings(text)

        # Verificar que no hay encabezados
        assert "**Resumen:**" not in result
        assert "**Desarrollo:**" not in result
        assert "**Fuentes:**" not in result
        assert "**Siguientes pasos:**" not in result

        # Verificar que el contenido válido permanece
        assert "Respuesta breve." in result
        assert "Sin fuente verificable." in result

        # No debe haber líneas huérfanas (más de 2 newlines consecutivos)
        assert "\n\n\n" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
