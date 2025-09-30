#!/usr/bin/env python3
"""
Script para limpiar conversaciones DRAFT duplicadas antes de aplicar el índice único.

P0-BE-UNIQ-EMPTY: Elimina DRAFTs vacías duplicadas, dejando solo la más reciente por usuario.

Uso:
    python scripts/cleanup-duplicate-drafts.py [--dry-run] [--force]

Opciones:
    --dry-run    Muestra lo que se eliminaría sin hacer cambios
    --force      No pide confirmación antes de eliminar
"""

import asyncio
import os
import sys
import argparse
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime


async def cleanup_duplicate_drafts(dry_run=False, force=False):
    """Elimina conversaciones DRAFT vacías duplicadas por usuario."""

    # Obtener URL de MongoDB desde variable de entorno
    mongodb_url = os.getenv('MONGODB_URL')
    if not mongodb_url:
        mongodb_url = "mongodb://copilotos_user:secure_password_change_me@localhost:27017/copilotos?authSource=admin"
        print(f"⚠️  MONGODB_URL no configurada, usando default")

    print(f"📡 Conectando a MongoDB...")

    try:
        client = AsyncIOMotorClient(mongodb_url)

        # Extraer nombre de base de datos
        db_name = mongodb_url.split('/')[-1].split('?')[0]
        if not db_name:
            db_name = 'copilotos'

        db = client[db_name]
        collection = db['chat_sessions']

        print(f"✅ Conectado a base de datos: {db_name}")

        # Buscar usuarios con múltiples DRAFTs vacías
        print("\n🔍 Buscando DRAFTs vacías duplicadas...")

        pipeline = [
            {"$match": {"state": "draft", "message_count": 0}},
            {"$group": {
                "_id": "$user_id",
                "count": {"$sum": 1},
                "sessions": {"$push": {
                    "id": "$_id",
                    "title": "$title",
                    "created_at": "$created_at",
                    "updated_at": "$updated_at"
                }}
            }},
            {"$match": {"count": {"$gt": 1}}}
        ]

        duplicates = await collection.aggregate(pipeline).to_list(length=None)

        if not duplicates:
            print("✅ No se encontraron DRAFTs vacías duplicadas.")
            print("   El índice único se puede aplicar sin problemas.")
            return

        print(f"\n⚠️  Encontrados {len(duplicates)} usuarios con DRAFTs duplicadas:")
        print()

        total_to_delete = 0
        deletion_plan = []

        for dup in duplicates:
            user_id = dup['_id']
            count = dup['count']
            sessions = dup['sessions']

            print(f"👤 Usuario: {user_id}")
            print(f"   Número de DRAFTs vacías: {count}")

            # Ordenar por updated_at DESC (más reciente primero)
            sessions_sorted = sorted(
                sessions,
                key=lambda s: s.get('updated_at', s.get('created_at', datetime.min)),
                reverse=True
            )

            # Mantener la más reciente, eliminar las demás
            keep_session = sessions_sorted[0]
            delete_sessions = sessions_sorted[1:]

            print(f"   ✅ Mantener (más reciente):")
            print(f"      - ID: {keep_session['id']}")
            print(f"      - Título: {keep_session['title']}")
            print(f"      - Actualizada: {keep_session.get('updated_at', 'N/A')}")

            if delete_sessions:
                print(f"   ❌ Eliminar ({len(delete_sessions)}):")
                for sess in delete_sessions:
                    print(f"      - ID: {sess['id']}")
                    print(f"        Título: {sess['title']}")
                    print(f"        Actualizada: {sess.get('updated_at', 'N/A')}")
                    deletion_plan.append(sess['id'])
                    total_to_delete += 1

            print()

        print(f"📊 Resumen:")
        print(f"   Usuarios afectados: {len(duplicates)}")
        print(f"   Total a eliminar: {total_to_delete}")
        print(f"   Total a mantener: {len(duplicates)}")

        if dry_run:
            print("\n🔍 DRY RUN - No se realizaron cambios.")
            print("   Ejecuta sin --dry-run para aplicar los cambios.")
            return

        if not force:
            print()
            response = input("¿Deseas continuar con la eliminación? (y/N): ")
            if response.lower() != 'y':
                print("❌ Operación cancelada.")
                return

        # Eliminar las DRAFTs duplicadas
        print("\n🗑️  Eliminando DRAFTs duplicadas...")

        deleted_count = 0
        for session_id in deletion_plan:
            result = await collection.delete_one({"_id": session_id})
            if result.deleted_count > 0:
                deleted_count += 1
                print(f"   ✅ Eliminada: {session_id}")

        print(f"\n✅ Limpieza completada!")
        print(f"   Conversaciones eliminadas: {deleted_count}")

        # Verificar resultado final
        remaining_duplicates = await collection.aggregate(pipeline).to_list(length=None)

        if remaining_duplicates:
            print(f"\n⚠️  ADVERTENCIA: Todavía hay {len(remaining_duplicates)} usuarios con duplicados.")
            print("   Ejecuta el script nuevamente para verificar.")
        else:
            print("\n✅ Ya no existen DRAFTs duplicadas.")
            print("   Ahora puedes aplicar el índice único con:")
            print("   python scripts/apply-draft-unique-index.py")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        client.close()
        print("\n👋 Conexión cerrada.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Limpia conversaciones DRAFT vacías duplicadas"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Muestra lo que se eliminaría sin hacer cambios'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='No pide confirmación antes de eliminar'
    )

    args = parser.parse_args()

    print("=" * 70)
    print("🧹 Limpieza de DRAFTs vacías duplicadas")
    print("=" * 70)
    print()

    if args.dry_run:
        print("🔍 Modo DRY RUN activado - No se harán cambios")
        print()

    asyncio.run(cleanup_duplicate_drafts(
        dry_run=args.dry_run,
        force=args.force
    ))
