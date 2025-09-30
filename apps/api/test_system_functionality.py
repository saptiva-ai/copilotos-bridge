#!/usr/bin/env python3
"""
Script para verificar la funcionalidad del sistema después de cambios de seguridad.
"""

import os
import sys
import traceback

# Configurar variables de entorno para testing
os.environ.setdefault("MONGODB_PASSWORD", "test_password_12345")
os.environ.setdefault("REDIS_PASSWORD", "test_redis_password_12345")
os.environ.setdefault("JWT_SECRET_KEY", "test_jwt_secret_key_1234567890123456")
os.environ.setdefault("SECRET_KEY", "test_secret_key_1234567890123456")
os.environ.setdefault("SAPTIVA_API_KEY", "test-api-key")

# Agregar src al path
sys.path.insert(0, "src")

def test_config_loading():
    """Test básico de carga de configuración"""
    try:
        from core.config import get_settings
        settings = get_settings()

        print("✅ Configuración cargada correctamente")
        print(f"   - App: {settings.app_name}")
        print(f"   - Version: {settings.app_version}")
        print(f"   - Debug: {settings.debug}")
        print(f"   - JWT Secret: {settings.jwt_secret_key[:8]}..." if settings.jwt_secret_key else "   - JWT Secret: No configurado")

        return True
    except Exception as e:
        print(f"❌ Error en configuración: {e}")
        traceback.print_exc()
        return False

def test_secrets_management():
    """Test del sistema de secrets"""
    try:
        from core.secrets import get_secret, mask_secret

        # Test obtener secret
        jwt_secret = get_secret("JWT_SECRET_KEY", required=True)
        print("✅ Sistema de secrets funcionando")
        print(f"   - JWT Secret cargado: {mask_secret(jwt_secret)}")

        # Test masking
        test_secret = "1234567890abcdef"
        masked = mask_secret(test_secret, 3)
        print(f"   - Masking test: {test_secret} -> {masked}")

        return True
    except Exception as e:
        print(f"❌ Error en secrets: {e}")
        traceback.print_exc()
        return False

def test_database_url_generation():
    """Test generación de URLs de base de datos"""
    try:
        from core.secrets import get_database_url

        # Test MongoDB URL
        mongodb_url = get_database_url("mongodb")
        print("✅ URLs de base de datos generadas")
        print(f"   - MongoDB: {mongodb_url.split('@')[0]}@[hidden]/{mongodb_url.split('/')[-1] if '@' in mongodb_url else mongodb_url}")

        # Test Redis URL
        redis_url = get_database_url("redis")
        print(f"   - Redis: {redis_url.split('@')[0]}@[hidden]/{redis_url.split('/')[-1] if '@' in redis_url else redis_url}")

        return True
    except Exception as e:
        print(f"❌ Error en URLs de DB: {e}")
        traceback.print_exc()
        return False

def test_model_imports():
    """Test importación de modelos"""
    try:
        from models import get_document_models

        models = get_document_models()
        print("✅ Modelos importados correctamente")
        print(f"   - Cantidad de modelos: {len(models)}")
        print(f"   - Modelos: {[model.__name__ for model in models[:3]]}{'...' if len(models) > 3 else ''}")

        return True
    except Exception as e:
        print(f"❌ Error en modelos: {e}")
        traceback.print_exc()
        return False

def test_router_imports():
    """Test importación de routers"""
    try:
        # Test algunos routers críticos
        from routers import health, auth

        print("✅ Routers importados correctamente")
        print(f"   - Health router: {hasattr(health, 'router')}")
        print(f"   - Auth router: {hasattr(auth, 'router')}")

        return True
    except Exception as e:
        print(f"❌ Error en routers: {e}")
        traceback.print_exc()
        return False

def main():
    """Función principal"""
    print("🔍 Verificación de Funcionalidad del Sistema")
    print("=" * 50)

    tests = [
        ("Carga de Configuración", test_config_loading),
        ("Sistema de Secrets", test_secrets_management),
        ("URLs de Base de Datos", test_database_url_generation),
        ("Importación de Modelos", test_model_imports),
        ("Importación de Routers", test_router_imports),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}")
        print("-" * 30)

        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Error crítico en {test_name}: {e}")
            results.append((test_name, False))

    # Resumen
    print("\n" + "=" * 50)
    print("📊 RESUMEN DE VERIFICACIÓN")
    print("=" * 50)

    passed = 0
    failed = 0

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {test_name}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\n📈 Resultados: {passed} exitosos, {failed} fallos")

    if failed == 0:
        print("\n🎉 ¡Todos los tests pasaron! El sistema está funcionando correctamente.")
        print("🚀 La refactorización de seguridad no rompió funcionalidades críticas.")
    else:
        print(f"\n⚠️  Se encontraron {failed} problemas que requieren atención.")
        print("🔧 Revisar los errores arriba para diagnosticar problemas.")

    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)