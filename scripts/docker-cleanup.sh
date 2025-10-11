#!/bin/bash
# Docker Cleanup Script - Libera espacio de forma segura
# Ejecuta limpieza regular de recursos Docker no utilizados

set -e

# Status symbols para output
RED="✖ "
GREEN="✔ "
YELLOW="▲ "
BLUE="▸ "
NC=""

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Docker Cleanup Script${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Mostrar uso actual
echo -e "${YELLOW}Uso actual de Docker:${NC}"
docker system df
echo ""

# 1. Eliminar imágenes dangling (sin tag)
echo -e "${YELLOW}1. Eliminando imágenes sin tag (dangling)...${NC}"
DANGLING_COUNT=$(docker images -f "dangling=true" -q | wc -l)
if [ "$DANGLING_COUNT" -gt 0 ]; then
    docker image prune -f
    echo -e "${GREEN}Eliminadas $DANGLING_COUNT imágenes dangling${NC}"
else
    echo -e "${GREEN}No hay imágenes dangling${NC}"
fi
echo ""

# 2. Eliminar contenedores detenidos
echo -e "${YELLOW}2. Eliminando contenedores detenidos...${NC}"
STOPPED_COUNT=$(docker ps -aq -f status=exited -f status=created | wc -l)
if [ "$STOPPED_COUNT" -gt 0 ]; then
    docker container prune -f
    echo -e "${GREEN}Eliminados $STOPPED_COUNT contenedores detenidos${NC}"
else
    echo -e "${GREEN}No hay contenedores detenidos${NC}"
fi
echo ""

# 3. Eliminar build cache antiguo (más de 7 días)
echo -e "${YELLOW}3. Limpiando build cache antiguo (>7 días)...${NC}"
docker builder prune -af --filter "until=168h"
echo -e "${GREEN}Build cache antiguo eliminado${NC}"
echo ""

# 4. Eliminar volúmenes huérfanos (opcional)
echo -e "${YELLOW}4. Volúmenes huérfanos detectados:${NC}"
DANGLING_VOLUMES=$(docker volume ls -qf "dangling=true" | wc -l)
if [ "$DANGLING_VOLUMES" -gt 0 ]; then
    echo -e "${YELLOW} Encontrados $DANGLING_VOLUMES volúmenes huérfanos${NC}"
    read -p "   ¿Eliminar volúmenes huérfanos? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker volume prune -f
        echo -e "${GREEN}Eliminados $DANGLING_VOLUMES volúmenes${NC}"
    else
        echo -e "${YELLOW}Volúmenes conservados${NC}"
    fi
else
    echo -e "${GREEN}No hay volúmenes huérfanos${NC}"
fi
echo ""

# 5. Mostrar resultado final
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Resultado Final${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
docker system df
echo ""
echo -e "${GREEN}Limpieza completada!${NC}"
echo ""

# Opcional: Mostrar espacio total liberado
echo -e "${YELLOW}◆ Tip: Para limpieza más agresiva ejecuta:${NC}"
echo -e "   ${BLUE}docker system prune -af --volumes${NC}"
echo -e "   ${RED}▲  ADVERTENCIA: Esto eliminará TODAS las imágenes y volúmenes no usados${NC}"
echo ""
