# Script de Testing MCP

Script interactivo para probar las tools MCP de OctaviOS.

## 🚀 Uso Rápido

```bash
# Hacer script ejecutable (solo primera vez)
chmod +x scripts/test_mcp_tools.sh

# Ejecutar script interactivo
./scripts/test_mcp_tools.sh
```

## 📋 Menú Interactivo

```
┌─────────────────────────────────────┐
│   OctaviOS MCP Tools - Test Menu   │
└─────────────────────────────────────┘

1) Listar tools disponibles
2) Subir archivo PDF
3) Auditar archivo (COPILOTO_414)
4) Extraer texto del archivo
5) Deep research
6) Flujo completo: Upload + Audit
7) Salir
```

## 🔧 Configuración

### Variables de Entorno

```bash
# URL de la API (default: http://localhost:8000)
export API_URL="http://localhost:8000"

# Credenciales (default: demo/Demo1234)
export USERNAME="demo"
export PASSWORD="Demo1234"
```

### Dependencias

- ✅ `curl` (requerido)
- ⭐ `jq` (recomendado para formateo JSON)

```bash
# Instalar jq (opcional pero recomendado)
# Ubuntu/Debian
sudo apt-get install jq

# MacOS
brew install jq
```

## 📝 Ejemplos de Uso

### Ejemplo 1: Flujo Completo (Upload + Audit)

```bash
./scripts/test_mcp_tools.sh
# Seleccionar opción 6
# Ingresar ruta: /ruta/a/documento.pdf
# El script subirá y auditará automáticamente
```

### Ejemplo 2: Solo Auditar

```bash
./scripts/test_mcp_tools.sh
# Seleccionar opción 3
# Ingresar File ID: 674a5b8c9e7f12a3b4c5d6e7
# Seleccionar política: auto
```

### Ejemplo 3: Listar Tools

```bash
./scripts/test_mcp_tools.sh
# Seleccionar opción 1
# Muestra todas las tools disponibles
```

## 🎯 Características

- ✅ **Menú interactivo**: Fácil de usar
- ✅ **Autenticación automática**: Login con demo user
- ✅ **Colores**: Output colorizado para mejor lectura
- ✅ **Verificaciones**: Valida dependencias y API
- ✅ **Manejo de errores**: Mensajes claros de error
- ✅ **Formateo JSON**: Usa jq si está disponible

## 📊 Output Ejemplo

```
============================================
Auditando Archivo (COPILOTO_414)
============================================

ℹ Auditando documento: 674a5b8c9e7f12a3b4c5d6e7
ℹ Política: auto
✓ Auditoría completada
ℹ Total hallazgos: 3 (Errores: 1, Warnings: 2)
ℹ Duración: 2345.67ms

Hallazgos:
  [error] disclaimer: Disclaimer 'CONFIDENCIAL' not found
  [warning] format: Font 'Arial' used instead of 'Helvetica'
  [warning] logo: Logo size below recommended (45px < 50px)
```

## 🐛 Troubleshooting

### Error: "API no responde"

**Solución**:
```bash
# Iniciar servicios
make dev

# Verificar que estén corriendo
docker compose ps
```

### Error: "Login falló"

**Solución**:
```bash
# Crear usuario demo
make create-demo-user

# O usar tus propias credenciales
export USERNAME="tu_usuario"
export PASSWORD="tu_password"
```

### Error: "command not found: jq"

**Solución**:
```bash
# El script funciona sin jq, pero instalar es recomendado
sudo apt-get install jq  # Ubuntu/Debian
brew install jq          # MacOS
```

## 🔗 Ver También

- [MCP Tools Guide](../docs/MCP_TOOLS_GUIDE.md) - Guía completa de tools
- [MCP Architecture](../docs/MCP_ARCHITECTURE.md) - Arquitectura MCP
- [Makefile](../Makefile) - Comandos disponibles
