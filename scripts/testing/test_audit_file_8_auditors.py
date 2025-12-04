#!/usr/bin/env python3
"""
Script de validación para verificar que AuditFileTool expone los 8 auditores.

Este script valida:
1. Que AuditInput acepta los 8 campos enable_*
2. Que el ToolSpec incluye los 8 campos en input_schema
3. Que no hay errores de "argumento inesperado"

Uso:
    python scripts/test_audit_file_8_auditors.py
"""

import sys
from pathlib import Path

# Agregar apps/api al path
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "api"))

from src.mcp.tools.audit_file import AuditFileTool, AuditInput
from pydantic import ValidationError


def test_audit_input_model():
    """Test 1: Validar que AuditInput acepta los 8 campos."""
    print("\n" + "=" * 70)
    print("TEST 1: Validar AuditInput con 8 auditores")
    print("=" * 70)

    try:
        # Crear instancia con todos los campos
        audit_input = AuditInput(
            doc_id="test_doc_123",
            user_id="test_user_456",
            policy_id="auto",
            enable_disclaimer=True,
            enable_format=True,
            enable_typography=True,  # NUEVO
            enable_grammar=True,
            enable_logo=True,
            enable_color_palette=True,  # NUEVO
            enable_entity_consistency=True,  # NUEVO
            enable_semantic_consistency=True,  # NUEVO
        )

        print(f"✅ AuditInput creado exitosamente")
        print(f"   - doc_id: {audit_input.doc_id}")
        print(f"   - user_id: {audit_input.user_id}")
        print(f"   - policy_id: {audit_input.policy_id}")
        print(f"\n📋 Auditores habilitados:")
        print(f"   1. enable_disclaimer: {audit_input.enable_disclaimer}")
        print(f"   2. enable_format: {audit_input.enable_format}")
        print(f"   3. enable_typography: {audit_input.enable_typography} ⭐ NUEVO")
        print(f"   4. enable_grammar: {audit_input.enable_grammar}")
        print(f"   5. enable_logo: {audit_input.enable_logo}")
        print(f"   6. enable_color_palette: {audit_input.enable_color_palette} ⭐ NUEVO")
        print(f"   7. enable_entity_consistency: {audit_input.enable_entity_consistency} ⭐ NUEVO")
        print(f"   8. enable_semantic_consistency: {audit_input.enable_semantic_consistency} ⭐ NUEVO")

        return True

    except ValidationError as e:
        print(f"❌ Error de validación en AuditInput:")
        print(f"   {e}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado:")
        print(f"   {e}")
        return False


def test_tool_spec_schema():
    """Test 2: Validar que ToolSpec expone los 8 campos en input_schema."""
    print("\n" + "=" * 70)
    print("TEST 2: Validar ToolSpec input_schema")
    print("=" * 70)

    try:
        tool = AuditFileTool()
        spec = tool.get_spec()

        print(f"✅ ToolSpec obtenido exitosamente")
        print(f"   - name: {spec.name}")
        print(f"   - version: {spec.version}")
        print(f"   - display_name: {spec.display_name}")

        # Verificar que input_schema tiene los 8 campos
        properties = spec.input_schema.get("properties", {})

        expected_fields = [
            "enable_disclaimer",
            "enable_format",
            "enable_typography",  # NUEVO
            "enable_grammar",
            "enable_logo",
            "enable_color_palette",  # NUEVO
            "enable_entity_consistency",  # NUEVO
            "enable_semantic_consistency",  # NUEVO
        ]

        print(f"\n📋 Verificando campos en input_schema:")
        all_present = True
        for field in expected_fields:
            is_present = field in properties
            status = "✅" if is_present else "❌"
            is_new = field in ["enable_typography", "enable_color_palette",
                               "enable_entity_consistency", "enable_semantic_consistency"]
            new_tag = " ⭐ NUEVO" if is_new else ""
            print(f"   {status} {field}{new_tag}")

            if is_present:
                field_config = properties[field]
                print(f"      - type: {field_config.get('type')}")
                print(f"      - default: {field_config.get('default')}")
                print(f"      - description: {field_config.get('description')}")

            if not is_present:
                all_present = False

        if all_present:
            print(f"\n✅ Todos los 8 campos están presentes en input_schema")
            return True
        else:
            print(f"\n❌ Faltan campos en input_schema")
            return False

    except Exception as e:
        print(f"❌ Error al obtener ToolSpec:")
        print(f"   {e}")
        return False


def test_defaults():
    """Test 3: Validar que los valores por defecto son True."""
    print("\n" + "=" * 70)
    print("TEST 3: Validar valores por defecto")
    print("=" * 70)

    try:
        # Crear AuditInput solo con campos requeridos (sin enable_*)
        audit_input = AuditInput(
            doc_id="test_doc_789",
            user_id="test_user_101"
        )

        print(f"✅ AuditInput creado con valores por defecto")
        print(f"\n📋 Verificando que todos son True por defecto:")

        fields_to_check = [
            ("enable_disclaimer", audit_input.enable_disclaimer),
            ("enable_format", audit_input.enable_format),
            ("enable_typography", audit_input.enable_typography),
            ("enable_grammar", audit_input.enable_grammar),
            ("enable_logo", audit_input.enable_logo),
            ("enable_color_palette", audit_input.enable_color_palette),
            ("enable_entity_consistency", audit_input.enable_entity_consistency),
            ("enable_semantic_consistency", audit_input.enable_semantic_consistency),
        ]

        all_true = True
        for field_name, field_value in fields_to_check:
            status = "✅" if field_value is True else "❌"
            print(f"   {status} {field_name}: {field_value}")
            if field_value is not True:
                all_true = False

        if all_true:
            print(f"\n✅ Todos los valores por defecto son True")
            return True
        else:
            print(f"\n❌ Algunos valores por defecto no son True")
            return False

    except Exception as e:
        print(f"❌ Error al verificar defaults:")
        print(f"   {e}")
        return False


def test_selective_disable():
    """Test 4: Validar que se pueden desactivar auditores selectivamente."""
    print("\n" + "=" * 70)
    print("TEST 4: Validar desactivación selectiva de auditores")
    print("=" * 70)

    try:
        # Desactivar los 4 nuevos auditores
        audit_input = AuditInput(
            doc_id="test_doc_selective",
            user_id="test_user_selective",
            enable_typography=False,  # DESACTIVAR
            enable_color_palette=False,  # DESACTIVAR
            enable_entity_consistency=False,  # DESACTIVAR
            enable_semantic_consistency=False,  # DESACTIVAR
        )

        print(f"✅ AuditInput creado con desactivación selectiva")
        print(f"\n📋 Estado de auditores:")
        print(f"   Activos (por defecto):")
        print(f"   - enable_disclaimer: {audit_input.enable_disclaimer}")
        print(f"   - enable_format: {audit_input.enable_format}")
        print(f"   - enable_grammar: {audit_input.enable_grammar}")
        print(f"   - enable_logo: {audit_input.enable_logo}")
        print(f"\n   Desactivados (explícitamente):")
        print(f"   - enable_typography: {audit_input.enable_typography}")
        print(f"   - enable_color_palette: {audit_input.enable_color_palette}")
        print(f"   - enable_entity_consistency: {audit_input.enable_entity_consistency}")
        print(f"   - enable_semantic_consistency: {audit_input.enable_semantic_consistency}")

        # Verificar que los valores son correctos
        actives_ok = (
            audit_input.enable_disclaimer is True and
            audit_input.enable_format is True and
            audit_input.enable_grammar is True and
            audit_input.enable_logo is True
        )

        disabled_ok = (
            audit_input.enable_typography is False and
            audit_input.enable_color_palette is False and
            audit_input.enable_entity_consistency is False and
            audit_input.enable_semantic_consistency is False
        )

        if actives_ok and disabled_ok:
            print(f"\n✅ Desactivación selectiva funciona correctamente")
            return True
        else:
            print(f"\n❌ Error en desactivación selectiva")
            return False

    except Exception as e:
        print(f"❌ Error al validar desactivación selectiva:")
        print(f"   {e}")
        return False


def main():
    """Ejecutar todos los tests."""
    print("\n" + "=" * 70)
    print("VALIDACIÓN DE AUDIT_FILE_TOOL - 8 AUDITORES")
    print("=" * 70)
    print(f"Archivo: apps/api/src/mcp/tools/audit_file.py")
    print(f"Objetivo: Verificar que AuditFileTool expone los 8 auditores")

    results = {
        "AuditInput Model": test_audit_input_model(),
        "ToolSpec Schema": test_tool_spec_schema(),
        "Default Values": test_defaults(),
        "Selective Disable": test_selective_disable(),
    }

    # Resumen final
    print("\n" + "=" * 70)
    print("RESUMEN DE RESULTADOS")
    print("=" * 70)

    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 TODOS LOS TESTS PASARON")
        print("=" * 70)
        print("\n✅ AuditFileTool está correctamente sincronizado con los 8 auditores")
        print("✅ Los LLMs pueden ahora controlar:")
        print("   - Typography checks")
        print("   - Color palette validation")
        print("   - Entity consistency analysis")
        print("   - Semantic coherence validation")
        return 0
    else:
        print("❌ ALGUNOS TESTS FALLARON")
        print("=" * 70)
        print("\n⚠️  Revisar los errores anteriores")
        return 1


if __name__ == "__main__":
    sys.exit(main())
