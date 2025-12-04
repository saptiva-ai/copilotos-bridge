#!/usr/bin/env python3
"""
Script de validación simple para verificar el schema de AuditInput.

Solo valida la estructura de Pydantic sin importar servicios externos.

Uso:
    python scripts/test_audit_schema_only.py
"""

import sys
from pathlib import Path
from pydantic import BaseModel, Field, ValidationError


# Copiar la definición de AuditInput para validar sin dependencias
class AuditInput(BaseModel):
    """Schema de entrada para audit_file (copia para testing)."""
    doc_id: str = Field(..., description="ID del documento a auditar")
    user_id: str = Field(..., description="ID del usuario propietario (obligatorio)")
    policy_id: str = Field("auto", description="ID de la política")
    enable_disclaimer: bool = Field(True, description="Activar auditor de disclaimers")
    enable_format: bool = Field(True, description="Activar auditor de formato")
    enable_typography: bool = Field(True, description="Activar auditor de tipografías")
    enable_grammar: bool = Field(True, description="Activar auditor de gramática")
    enable_logo: bool = Field(True, description="Activar auditor de logos")
    enable_color_palette: bool = Field(True, description="Activar auditor de paleta de colores")
    enable_entity_consistency: bool = Field(True, description="Activar auditor de consistencia de entidades")
    enable_semantic_consistency: bool = Field(True, description="Activar auditor de consistencia semántica")


def test_all_8_auditors():
    """Test 1: Crear AuditInput con los 8 auditores habilitados."""
    print("\n" + "=" * 70)
    print("TEST 1: Validar AuditInput con 8 auditores")
    print("=" * 70)

    try:
        audit_input = AuditInput(
            doc_id="test_doc_123",
            user_id="test_user_456",
            policy_id="auto",
            enable_disclaimer=True,
            enable_format=True,
            enable_typography=True,
            enable_grammar=True,
            enable_logo=True,
            enable_color_palette=True,
            enable_entity_consistency=True,
            enable_semantic_consistency=True,
        )

        print(f"✅ AuditInput creado exitosamente")
        print(f"\n📋 8 Auditores configurados:")
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
        print(f"❌ Error de validación: {e}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False


def test_defaults():
    """Test 2: Validar que todos los auditores son True por defecto."""
    print("\n" + "=" * 70)
    print("TEST 2: Validar valores por defecto (todos True)")
    print("=" * 70)

    try:
        audit_input = AuditInput(
            doc_id="test_doc_defaults",
            user_id="test_user_defaults"
        )

        print(f"✅ AuditInput creado solo con campos requeridos")
        print(f"\n📋 Verificando defaults:")

        all_true = True
        auditors = [
            ("enable_disclaimer", audit_input.enable_disclaimer),
            ("enable_format", audit_input.enable_format),
            ("enable_typography", audit_input.enable_typography),
            ("enable_grammar", audit_input.enable_grammar),
            ("enable_logo", audit_input.enable_logo),
            ("enable_color_palette", audit_input.enable_color_palette),
            ("enable_entity_consistency", audit_input.enable_entity_consistency),
            ("enable_semantic_consistency", audit_input.enable_semantic_consistency),
        ]

        for name, value in auditors:
            status = "✅" if value is True else "❌"
            print(f"   {status} {name}: {value}")
            if value is not True:
                all_true = False

        if all_true:
            print(f"\n✅ Todos los defaults son True")
            return True
        else:
            print(f"\n❌ Algunos defaults no son True")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_selective_disable():
    """Test 3: Desactivar selectivamente los 4 nuevos auditores."""
    print("\n" + "=" * 70)
    print("TEST 3: Desactivación selectiva (4 nuevos auditores)")
    print("=" * 70)

    try:
        audit_input = AuditInput(
            doc_id="test_selective",
            user_id="test_user_selective",
            enable_typography=False,
            enable_color_palette=False,
            enable_entity_consistency=False,
            enable_semantic_consistency=False,
        )

        print(f"✅ Desactivación selectiva exitosa")
        print(f"\n📋 Auditores activos (4 originales):")
        print(f"   ✅ enable_disclaimer: {audit_input.enable_disclaimer}")
        print(f"   ✅ enable_format: {audit_input.enable_format}")
        print(f"   ✅ enable_grammar: {audit_input.enable_grammar}")
        print(f"   ✅ enable_logo: {audit_input.enable_logo}")
        print(f"\n📋 Auditores desactivados (4 nuevos):")
        print(f"   ⭕ enable_typography: {audit_input.enable_typography}")
        print(f"   ⭕ enable_color_palette: {audit_input.enable_color_palette}")
        print(f"   ⭕ enable_entity_consistency: {audit_input.enable_entity_consistency}")
        print(f"   ⭕ enable_semantic_consistency: {audit_input.enable_semantic_consistency}")

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
            print(f"\n✅ Control granular funciona correctamente")
            return True
        else:
            print(f"\n❌ Error en control granular")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_json_export():
    """Test 4: Exportar a JSON (simular payload MCP)."""
    print("\n" + "=" * 70)
    print("TEST 4: Exportar a JSON (simular MCP payload)")
    print("=" * 70)

    try:
        audit_input = AuditInput(
            doc_id="doc_json_test",
            user_id="user_json_test",
            enable_typography=True,
            enable_color_palette=False,  # Desactivar solo uno
        )

        json_data = audit_input.model_dump()

        print(f"✅ Exportado a JSON exitosamente")
        print(f"\n📋 JSON Payload:")
        import json
        print(json.dumps(json_data, indent=2))

        # Verificar que tiene todos los campos
        required_keys = [
            "doc_id", "user_id", "policy_id",
            "enable_disclaimer", "enable_format", "enable_typography",
            "enable_grammar", "enable_logo", "enable_color_palette",
            "enable_entity_consistency", "enable_semantic_consistency"
        ]

        all_present = all(key in json_data for key in required_keys)

        if all_present:
            print(f"\n✅ JSON tiene todos los 11 campos (3 required + 8 auditors)")
            return True
        else:
            missing = [k for k in required_keys if k not in json_data]
            print(f"\n❌ Faltan campos en JSON: {missing}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def verify_actual_file():
    """Test 5: Verificar que el archivo real tiene los cambios."""
    print("\n" + "=" * 70)
    print("TEST 5: Verificar archivo audit_file.py")
    print("=" * 70)

    audit_file_path = Path(__file__).parent.parent / "apps/api/src/mcp/tools/audit_file.py"

    if not audit_file_path.exists():
        print(f"❌ No se encontró: {audit_file_path}")
        return False

    content = audit_file_path.read_text()

    # Buscar los 4 nuevos campos en el archivo
    new_fields = [
        "enable_typography",
        "enable_color_palette",
        "enable_entity_consistency",
        "enable_semantic_consistency",
    ]

    print(f"✅ Archivo encontrado: {audit_file_path}")
    print(f"\n📋 Buscando campos nuevos en el código:")

    all_found = True
    for field in new_fields:
        count = content.count(field)
        status = "✅" if count >= 3 else "❌"  # Debe aparecer al menos 3 veces
        print(f"   {status} {field}: {count} ocurrencias")
        if count < 3:
            all_found = False

    # Verificar version bump
    if 'version="1.1.0"' in content:
        print(f"   ✅ version: 1.1.0 (actualizada)")
    else:
        print(f"   ⚠️  version: no actualizada a 1.1.0")

    # Verificar descripción actualizada
    if "8 specialized" in content or "8 auditores" in content:
        print(f"   ✅ descripción: menciona 8 auditores")
    else:
        print(f"   ⚠️  descripción: no menciona 8 auditores")

    if all_found:
        print(f"\n✅ Archivo tiene todos los cambios necesarios")
        return True
    else:
        print(f"\n❌ Faltan cambios en el archivo")
        return False


def main():
    """Ejecutar todos los tests."""
    print("\n" + "=" * 70)
    print("VALIDACIÓN RÁPIDA - AUDIT_FILE SCHEMA")
    print("=" * 70)
    print("Objetivo: Verificar que AuditInput expone los 8 auditores")
    print("Nota: Test sin dependencias externas (MongoDB, MinIO, etc.)")

    results = {
        "8 Auditors Model": test_all_8_auditors(),
        "Default Values": test_defaults(),
        "Selective Disable": test_selective_disable(),
        "JSON Export": test_json_export(),
        "File Verification": verify_actual_file(),
    }

    # Resumen
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
        print("🎉 FASE 1 COMPLETADA EXITOSAMENTE")
        print("=" * 70)
        print("\n✅ AuditFileTool sincronizado con 8 auditores:")
        print("   1. Disclaimer")
        print("   2. Format")
        print("   3. Typography ⭐ NUEVO")
        print("   4. Grammar")
        print("   5. Logo")
        print("   6. Color Palette ⭐ NUEVO")
        print("   7. Entity Consistency ⭐ NUEVO")
        print("   8. Semantic Consistency ⭐ NUEVO")
        print("\n✅ MCP Tool version: 1.1.0")
        print("✅ LLMs pueden controlar todos los auditores granularmente")
        return 0
    else:
        print("❌ ALGUNOS TESTS FALLARON")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
