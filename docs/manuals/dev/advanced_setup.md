# Local Development Setup

**Fecha**: 2025-10-18
**Objetivo**: Correr frontend + backend localmente sin Docker

---

## Prerequisitos

- Python 3.11+ con virtualenv
- Node.js 18+
- pnpm (ya instalado)
- MongoDB local o acceso a MongoDB remoto
- Redis local o acceso a Redis remoto

---

## 1. Backend API (FastAPI)

### Opción A: Con servicios locales (MongoDB + Redis)

```bash
cd apps/api

# Activar virtualenv
source .venv/bin/activate

# Variables de entorno (crear .env si no existe)
cp .env.example .env  # Ajustar valores

# Valores mínimos necesarios:
# MONGODB_URI=mongodb://localhost:27017/copilotos
# REDIS_URL=redis://localhost:6379/0
# JWT_SECRET_KEY=tu-secret-key-local
# SAPTIVA_API_KEY=tu-api-key

# Correr servidor
uvicorn src.main:app --reload --host 0.0.0.0 --port 8001
```

### Opción B: Con Docker Compose solo para servicios

```bash
# Desde root del proyecto
docker-compose up -d mongodb redis

# Verificar que corren
docker ps | grep -E "mongo|redis"

# Luego correr API local apuntando a estos servicios
cd apps/api
source .venv/bin/activate
uvicorn src.main:app --reload --host 0.0.0.0 --port 8001
```

**Backend disponible en**: http://localhost:8001

---

## 2. Frontend (Next.js)

```bash
cd apps/web

# Variables de entorno ya están en .env.local:
# NEXT_PUBLIC_API_URL=http://localhost:8001
# API_BASE_URL=http://localhost:8001

# Correr dev server
pnpm dev
```

**Frontend disponible en**: http://localhost:3000

**Proxy automático**:
- Requests a `http://localhost:3000/api/*` se proxean a `http://localhost:8001/api/*`
- Esto evita CORS issues en desarrollo

---

## 3. Verificar que funciona

### Backend
```bash
curl http://localhost:8001/health
# Debe retornar: {"status":"healthy"}
```

### Frontend
1. Abrir http://localhost:3000
2. Debe cargar la UI
3. Ir a Network tab en DevTools
4. Requests a /api/* deben ir a través del proxy de Next.js

---

## 4. Setup Integration Tests

Con el backend corriendo localmente, puedes correr integration tests:

```bash
cd apps/api
source .venv/bin/activate

# Tests de integración (requiere servicios corriendo)
pytest tests/integration/ -v

# Tests unitarios (no requieren servicios)
pytest tests/unit/ -v
```

---

## Troubleshooting

### Error: "Connection refused" en MongoDB
```bash
# Opción 1: Instalar MongoDB local
sudo systemctl start mongod

# Opción 2: Usar Docker
docker run -d -p 27017:27017 --name mongodb mongo:7
```

### Error: "Connection refused" en Redis
```bash
# Opción 1: Instalar Redis local
sudo systemctl start redis

# Opción 2: Usar Docker
docker run -d -p 6379:6379 --name redis redis:7-alpine
```

### Frontend no conecta a backend
1. Verificar que backend corre en puerto 8001
2. Verificar que .env.local tiene URLs correctas
3. Ver logs del proxy en terminal de Next.js
4. Debe aparecer: `[Next.js Rewrites] Proxying /api/* to: http://localhost:8001`

### "Module not found" en frontend
```bash
# Reinstalar dependencias
cd /home/jazielflo/Proyects/copilotos-bridge
pnpm install --force
```

---

## Resumen de puertos

| Servicio | Puerto | URL |
|----------|--------|-----|
| **Frontend (Next.js)** | 3000 | http://localhost:3000 |
| **Backend (FastAPI)** | 8001 | http://localhost:8001 |
| **MongoDB** | 27017 | mongodb://localhost:27017 |
| **Redis** | 6379 | redis://localhost:6379 |

---

## Next Steps

Una vez que frontend + backend corren localmente:

1. ✅ **Unit tests** (ya tenemos 226)
2. 🔄 **Integration tests** (siguiente paso)
3. ⏳ **E2E tests con Playwright** (después)
