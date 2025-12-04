#!/bin/bash
# ============================================================================
# FIX RÁPIDO PARA ERROR 413 - Nginx Content Too Large
# ============================================================================
# Actualiza client_max_body_size en nginx del sistema
# Usage: sudo bash scripts/fix-nginx-413.sh [--dry-run]

set -e

# Verificar permisos root
if [ "$EUID" -ne 0 ] && [ "$1" != "--dry-run" ]; then
    echo "❌ Error: Este script requiere permisos de root"
    echo "   Ejecuta: sudo bash scripts/fix-nginx-413.sh"
    exit 1
fi

DRY_RUN=false
if [ "$1" = "--dry-run" ]; then
    DRY_RUN=true
    echo "🔍 MODO DRY-RUN: No se harán cambios reales"
    echo ""
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 FIX NGINX 413 - Aumentar client_max_body_size"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ============================================================================
# 1. VERIFICAR NGINX DEL SISTEMA
# ============================================================================
if [ ! -d "/etc/nginx" ]; then
    echo -e "${RED}✗${NC} /etc/nginx no existe"
    echo "   Nginx del sistema no está instalado o usa otra ruta"
    echo ""
    echo "   Si usas Docker únicamente, verifica:"
    echo "   docker exec <nginx-container> grep client_max_body_size /etc/nginx/nginx.conf"
    exit 1
fi

echo -e "${GREEN}✓${NC} Nginx del sistema detectado (/etc/nginx)"
echo ""

# ============================================================================
# 2. BUSCAR CONFIGURACIÓN DE COPILOTOS.SAPTIVA.COM
# ============================================================================
echo "Buscando configuración de octavios.saptiva.com..."

SITE_CONFIG=""
FOUND_IN=""

# Buscar en sites-enabled (Debian/Ubuntu)
if [ -d "/etc/nginx/sites-enabled" ]; then
    for site in /etc/nginx/sites-enabled/*; do
        if [ -f "$site" ] && grep -q "octavios\.saptiva\.com\|server_name.*saptiva" "$site" 2>/dev/null; then
            SITE_CONFIG="$site"
            FOUND_IN="sites-enabled"
            break
        fi
    done
fi

# Buscar en conf.d (CentOS/RHEL)
if [ -z "$SITE_CONFIG" ] && [ -d "/etc/nginx/conf.d" ]; then
    for conf in /etc/nginx/conf.d/*.conf; do
        if [ -f "$conf" ] && grep -q "octavios\.saptiva\.com\|server_name.*saptiva" "$conf" 2>/dev/null; then
            SITE_CONFIG="$conf"
            FOUND_IN="conf.d"
            break
        fi
    done
fi

# Buscar en nginx.conf principal
if [ -z "$SITE_CONFIG" ] && [ -f "/etc/nginx/nginx.conf" ]; then
    if grep -q "octavios\.saptiva\.com\|server_name.*saptiva" /etc/nginx/nginx.conf 2>/dev/null; then
        SITE_CONFIG="/etc/nginx/nginx.conf"
        FOUND_IN="nginx.conf"
    fi
fi

if [ -z "$SITE_CONFIG" ]; then
    echo -e "${YELLOW}⚠${NC} No se encontró configuración específica de octavios.saptiva.com"
    echo ""
    echo "Buscando 'default' o primera configuración disponible..."

    # Usar default
    if [ -f "/etc/nginx/sites-enabled/default" ]; then
        SITE_CONFIG="/etc/nginx/sites-enabled/default"
        FOUND_IN="sites-enabled (default)"
    elif [ -f "/etc/nginx/conf.d/default.conf" ]; then
        SITE_CONFIG="/etc/nginx/conf.d/default.conf"
        FOUND_IN="conf.d (default)"
    elif [ -f "/etc/nginx/nginx.conf" ]; then
        SITE_CONFIG="/etc/nginx/nginx.conf"
        FOUND_IN="nginx.conf (global)"
    else
        echo -e "${RED}✗${NC} No se pudo encontrar ninguna configuración"
        echo "   Archivos disponibles:"
        ls -la /etc/nginx/sites-enabled/ 2>/dev/null || echo "   /etc/nginx/sites-enabled no existe"
        ls -la /etc/nginx/conf.d/ 2>/dev/null || echo "   /etc/nginx/conf.d no existe"
        exit 1
    fi
fi

echo -e "${GREEN}✓${NC} Configuración encontrada:"
echo "  Archivo: $SITE_CONFIG"
echo "  Ubicación: $FOUND_IN"
echo ""

# ============================================================================
# 3. VERIFICAR ESTADO ACTUAL
# ============================================================================
echo "Verificando client_max_body_size actual..."

CURRENT_LIMIT=$(grep -E "^\s*client_max_body_size" "$SITE_CONFIG" 2>/dev/null || echo "")

if [ -n "$CURRENT_LIMIT" ]; then
    echo -e "${CYAN}ℹ${NC} Configuración actual:"
    echo "  $CURRENT_LIMIT"

    # Extraer valor numérico
    CURRENT_VALUE=$(echo "$CURRENT_LIMIT" | grep -oP '\d+[MmGg]?' || echo "")
    if [[ "$CURRENT_VALUE" =~ ^[0-9]+[Mm]?$ ]]; then
        NUMERIC_VALUE=$(echo "$CURRENT_VALUE" | grep -oP '\d+')
        if [ "$NUMERIC_VALUE" -ge 50 ]; then
            echo -e "${GREEN}✓${NC} Ya está configurado >= 50M ($CURRENT_VALUE)"
            echo "   El problema puede estar en otro lugar. Ejecuta:"
            echo "   bash scripts/diagnose-nginx-413.sh"
            exit 0
        fi
    fi
else
    echo -e "${YELLOW}⚠${NC} client_max_body_size NO configurado"
    echo "  Default de nginx: 1M (muy bajo)"
fi

# ============================================================================
# 4. CREAR BACKUP
# ============================================================================
if [ "$DRY_RUN" = false ]; then
    BACKUP_FILE="${SITE_CONFIG}.backup-$(date +%Y%m%d-%H%M%S)"
    cp "$SITE_CONFIG" "$BACKUP_FILE"
    echo -e "${GREEN}✓${NC} Backup creado: $BACKUP_FILE"
else
    echo -e "${CYAN}[DRY-RUN]${NC} Se crearía backup de: $SITE_CONFIG"
fi

# ============================================================================
# 5. ACTUALIZAR CONFIGURACIÓN
# ============================================================================
echo ""
echo "Actualizando client_max_body_size a 50M..."

TARGET_VALUE="client_max_body_size 50M;"

if [ -n "$CURRENT_LIMIT" ]; then
    # Ya existe, reemplazar
    if [ "$DRY_RUN" = false ]; then
        sed -i "s/client_max_body_size.*;/${TARGET_VALUE}/" "$SITE_CONFIG"
        echo -e "${GREEN}✓${NC} Valor actualizado a 50M"
    else
        echo -e "${CYAN}[DRY-RUN]${NC} sed -i 's/client_max_body_size.*;/${TARGET_VALUE}/' $SITE_CONFIG"
    fi
else
    # No existe, agregar dentro del bloque http {} o server {}
    if [ "$DRY_RUN" = false ]; then
        # Buscar el primer bloque server {} y agregar después de {
        if grep -q "server\s*{" "$SITE_CONFIG"; then
            # Agregar después de la primera línea 'server {'
            sed -i "/server\s*{/a \    ${TARGET_VALUE}" "$SITE_CONFIG"
            echo -e "${GREEN}✓${NC} Configuración agregada en bloque server {}"
        elif grep -q "http\s*{" "$SITE_CONFIG"; then
            # Agregar en bloque http {} si no hay server {}
            sed -i "/http\s*{/a \    ${TARGET_VALUE}" "$SITE_CONFIG"
            echo -e "${GREEN}✓${NC} Configuración agregada en bloque http {}"
        else
            # Agregar al final del archivo como último recurso
            echo "" >> "$SITE_CONFIG"
            echo "# File upload limit (added by fix-nginx-413.sh)" >> "$SITE_CONFIG"
            echo "$TARGET_VALUE" >> "$SITE_CONFIG"
            echo -e "${YELLOW}⚠${NC} Configuración agregada al final del archivo"
            echo "   IMPORTANTE: Verifica que esté dentro de un bloque server {} o http {}"
        fi
    else
        echo -e "${CYAN}[DRY-RUN]${NC} Se agregaría: $TARGET_VALUE"
    fi
fi

# ============================================================================
# 6. VALIDAR SINTAXIS DE NGINX
# ============================================================================
echo ""
echo "Validando configuración de nginx..."

if [ "$DRY_RUN" = false ]; then
    if nginx -t 2>&1 | grep -q "syntax is ok"; then
        echo -e "${GREEN}✓${NC} Configuración válida"
    else
        echo -e "${RED}✗${NC} Error en la configuración de nginx:"
        nginx -t

        echo ""
        echo "Restaurando backup..."
        mv "$BACKUP_FILE" "$SITE_CONFIG"
        echo -e "${YELLOW}⚠${NC} Cambios revertidos. Verifica manualmente el archivo."
        exit 1
    fi
else
    echo -e "${CYAN}[DRY-RUN]${NC} nginx -t (validar sintaxis)"
fi

# ============================================================================
# 7. RECARGAR NGINX
# ============================================================================
echo ""
echo "Recargando nginx..."

if [ "$DRY_RUN" = false ]; then
    if systemctl is-active --quiet nginx; then
        systemctl reload nginx
        echo -e "${GREEN}✓${NC} Nginx recargado exitosamente"
    elif service nginx status >/dev/null 2>&1; then
        service nginx reload
        echo -e "${GREEN}✓${NC} Nginx recargado exitosamente (via service)"
    else
        echo -e "${YELLOW}⚠${NC} No se pudo detectar servicio nginx"
        echo "   Recarga manual: sudo systemctl reload nginx"
        echo "                   o: sudo service nginx reload"
    fi
else
    echo -e "${CYAN}[DRY-RUN]${NC} systemctl reload nginx"
fi

# ============================================================================
# 8. VERIFICAR CAMBIO
# ============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ ACTUALIZACIÓN COMPLETADA${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$DRY_RUN" = false ]; then
    echo ""
    echo "Configuración actualizada:"
    grep -E "client_max_body_size" "$SITE_CONFIG" | sed 's/^/  /'

    echo ""
    echo "Archivo modificado: $SITE_CONFIG"
    echo "Backup disponible: $BACKUP_FILE"

    echo ""
    echo "Siguiente paso:"
    echo "  1. Probar upload de HPE.pdf (2.3MB) desde el navegador"
    echo "  2. Verificar en DevTools que no aparezca error 413"
    echo ""
    echo "  Si persiste el problema:"
    echo "  • Ejecuta: bash scripts/diagnose-nginx-413.sh"
    echo "  • Verifica nginx Docker: docker exec <nginx-container> cat /etc/nginx/nginx.conf"
else
    echo ""
    echo "Para aplicar los cambios, ejecuta sin --dry-run:"
    echo "  sudo bash scripts/fix-nginx-413.sh"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
