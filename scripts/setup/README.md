# Setup Scripts

Scripts de configuración inicial y gestión de ambiente del proyecto.

## Scripts Disponibles

### Configuración Inicial
- **`interactive-env-setup.sh`** - Setup interactivo guiado
  ```bash
  ./scripts/setup/interactive-env-setup.sh development
  ```
- **`setup.sh`** - Setup básico del proyecto
- **`setup-dev.sh`** - Setup específico para desarrollo
- **`setup-docker-secrets.sh`** - Configurar Docker secrets
- **`setup-demo-server.sh`** - Setup de servidor demo
- **`setup-ssl-414.sh`** - Configurar SSL

### Variables de Entorno
- **`env-checker.sh`** - Validación de variables de entorno
  ```bash
  ./scripts/setup/env-checker.sh [warn|strict|info]
  ```
- **`env-manager.sh`** - Gestión de variables de entorno
  ```bash
  ./scripts/setup/env-manager.sh load [local|production]
  ```

### Secrets & Seguridad
- **`generate-secrets.py`** - Generar secrets seguros
  ```bash
  python scripts/setup/generate-secrets.py
  ```

### Usuarios Demo
- **`create-demo-user.py`** - Crear usuario demo para testing
  ```bash
  python scripts/setup/create-demo-user.py
  ```
- **`create-demo-user.sh`** - Versión en bash
- **`fix_demo_user.py`** - Fix usuario demo si está corrupto

### Permisos & Configuración
- **`fix-docker-permissions.sh`** - Fix permisos de Docker
- **`fix-env-server.sh`** - Fix environment en servidor

## Uso Común

```bash
# Setup inicial interactivo
./scripts/setup/interactive-env-setup.sh development

# Verificar variables de entorno
./scripts/setup/env-checker.sh warn

# Generar secrets nuevos
python scripts/setup/generate-secrets.py

# Crear usuario demo
python scripts/setup/create-demo-user.py
```

## Modos de env-checker.sh

- **`warn`** - Muestra warnings pero no falla
- **`strict`** - Falla si hay variables faltantes
- **`info`** - Solo muestra información

## Variables de Entorno Requeridas

El setup verifica:
- `SECRET_KEY` - Secret key de Django/FastAPI (min 32 chars)
- `JWT_SECRET_KEY` - Secret para JWTs (min 32 chars)
- `MONGODB_USER`, `MONGODB_PASSWORD` - Credentials MongoDB
- `REDIS_PASSWORD` - Password de Redis
- `SAPTIVA_API_KEY` - API key de Saptiva
- Otras según ambiente

---
**Ver también:** `../README.md` para más información
