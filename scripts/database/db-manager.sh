#!/bin/bash
################################################################################
# Database Manager - Consolidates database operations
#
# Usage:
#   ./scripts/db-manager.sh <CMD> [PROJECT_NAME]
#
# Examples:
#   ./scripts/db-manager.sh backup octavios-chat-capital414
#   ./scripts/db-manager.sh restore octavios-chat-capital414
#   ./scripts/db-manager.sh rotate octavios-chat-capital414
#
# Commands: backup, restore, rotate, stats
################################################################################

set -e

CMD=$1
PROJECT=${2:-octavios-chat-capital414}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Load environment variables
if [ -f "envs/.env" ]; then
    source envs/.env
fi

MONGODB_USER=${MONGODB_USER:-octavios_user}
MONGODB_PASSWORD=${MONGODB_PASSWORD:-secure_password_change_me}
MONGODB_DATABASE=${MONGODB_DATABASE:-octavios}
MONGODB_CONTAINER="${PROJECT}-mongodb"

if [ -z "$CMD" ]; then
    echo -e "${RED}❌ Error: Comando no especificado${NC}"
    echo "Uso: $0 <CMD> [PROJECT_NAME]"
    echo "Comandos: backup, restore, rotate, stats"
    exit 1
fi

echo -e "${BLUE}💾 Database Manager: $CMD${NC}"

# ============================================================================
# COMMAND SELECTOR
# ============================================================================

case "$CMD" in
  "backup")
    # Create backup directory
    BACKUP_DIR="backups/mongodb"
    mkdir -p "$BACKUP_DIR"

    # Generate backup filename with timestamp
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/mongodb-$TIMESTAMP.archive"

    echo -e "${YELLOW}Creating MongoDB backup...${NC}"

    # Create backup inside container
    docker exec "$MONGODB_CONTAINER" mongodump \
        --uri="mongodb://${MONGODB_USER}:${MONGODB_PASSWORD}@localhost:27017/${MONGODB_DATABASE}?authSource=admin" \
        --archive=/tmp/backup.archive \
        --gzip

    # Copy backup from container to host
    docker cp "$MONGODB_CONTAINER:/tmp/backup.archive" "$BACKUP_FILE"

    # Clean up temp file in container
    docker exec "$MONGODB_CONTAINER" rm /tmp/backup.archive

    # Get backup size
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)

    echo -e "${GREEN}✅ Backup completado${NC}"
    echo -e "   Archivo: $BACKUP_FILE"
    echo -e "   Tamaño: $BACKUP_SIZE"

    # List recent backups
    echo -e "\n${BLUE}Backups recientes:${NC}"
    ls -lht "$BACKUP_DIR" | head -6
    ;;

  "restore")
    echo -e "${RED}⚠️  ADVERTENCIA: Esta operación SOBRESCRIBIRÁ la base de datos actual${NC}"

    # List available backups
    BACKUP_DIR="backups/mongodb"
    if [ ! -d "$BACKUP_DIR" ] || [ -z "$(ls -A $BACKUP_DIR)" ]; then
        echo -e "${RED}❌ No hay backups disponibles en $BACKUP_DIR${NC}"
        exit 1
    fi

    echo -e "\n${BLUE}Backups disponibles:${NC}"
    ls -lht "$BACKUP_DIR"
    echo ""

    read -p "Ingresa el nombre del archivo de backup: " BACKUP_FILE

    ARCHIVE_PATH="$BACKUP_DIR/$BACKUP_FILE"

    if [ ! -f "$ARCHIVE_PATH" ]; then
        echo -e "${RED}❌ Archivo no encontrado: $ARCHIVE_PATH${NC}"
        exit 1
    fi

    read -p "¿Estás seguro? Escribe 'RESTAURAR' para continuar: " CONFIRM

    if [ "$CONFIRM" != "RESTAURAR" ]; then
        echo -e "${YELLOW}Operación cancelada${NC}"
        exit 0
    fi

    echo -e "${YELLOW}Restaurando base de datos...${NC}"

    # Copy backup to container
    docker cp "$ARCHIVE_PATH" "$MONGODB_CONTAINER:/tmp/restore.archive"

    # Restore backup
    docker exec "$MONGODB_CONTAINER" mongorestore \
        --uri="mongodb://${MONGODB_USER}:${MONGODB_PASSWORD}@localhost:27017/${MONGODB_DATABASE}?authSource=admin" \
        --archive=/tmp/restore.archive \
        --gzip \
        --drop

    # Clean up temp file
    docker exec "$MONGODB_CONTAINER" rm /tmp/restore.archive

    echo -e "${GREEN}✅ Restauración completada${NC}"
    ;;

  "rotate")
    echo -e "${YELLOW}Rotando credenciales de MongoDB...${NC}"

    # Check if rotate script exists
    ROTATE_SCRIPT="./scripts/rotate-mongo-credentials.sh"
    if [ ! -f "$ROTATE_SCRIPT" ]; then
        echo -e "${RED}❌ Script de rotación no encontrado: $ROTATE_SCRIPT${NC}"
        exit 1
    fi

    chmod +x "$ROTATE_SCRIPT"
    "$ROTATE_SCRIPT"
    ;;

  "stats")
    echo -e "${BLUE}Estadísticas de la base de datos:${NC}\n"

    docker exec "$MONGODB_CONTAINER" mongosh \
        --username "$MONGODB_USER" \
        --password "$MONGODB_PASSWORD" \
        --authenticationDatabase admin \
        --eval "
            use $MONGODB_DATABASE;
            print('=== Collections ===');
            db.getCollectionNames().forEach(function(col) {
                var stats = db[col].stats();
                print(col + ': ' + stats.count + ' documents, ' + (stats.size / 1024 / 1024).toFixed(2) + ' MB');
            });
            print('\\n=== Database Stats ===');
            printjson(db.stats());
        "
    ;;

  "shell")
    echo -e "${BLUE}Abriendo shell de MongoDB...${NC}"

    docker exec -it "$MONGODB_CONTAINER" mongosh \
        --username "$MONGODB_USER" \
        --password "$MONGODB_PASSWORD" \
        --authenticationDatabase admin \
        "$MONGODB_DATABASE"
    ;;

  *)
    echo -e "${RED}❌ Comando desconocido: $CMD${NC}"
    echo "Comandos disponibles: backup, restore, rotate, stats, shell"
    exit 1
    ;;
esac
