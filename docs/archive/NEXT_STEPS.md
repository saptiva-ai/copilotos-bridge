# SAPTIVA CopilotOS - Próximos Pasos

## 📊 Estado Actual
- ✅ **Frontend completo (75% del proyecto)**
- ✅ **UI funcional** con identidad SAPTIVA
- ✅ **Sistema de estado** global con Zustand
- ✅ **Cliente API** listo para backend
- ✅ **Streaming SSE** implementado

## 🎯 Próximas Prioridades Críticas

### 1. **Backend FastAPI (Crítico)**
**Tareas:** PROXY-API-040
```bash
apps/api/src/
├── main.py              # App principal con middleware
├── routers/
│   ├── chat.py         # POST /api/chat
│   ├── research.py     # POST /api/deep-research
│   ├── stream.py       # GET /api/stream/{task_id}
│   ├── history.py      # GET /api/history/{chat_id}
│   └── reports.py      # GET /api/report/{task_id}
├── services/
│   ├── chat_service.py
│   ├── research_service.py
│   └── streaming_service.py
└── middleware/
    ├── auth.py
    ├── cors.py
    └── rate_limit.py
```

### 2. **Cliente Aletheia (Alto)**  
**Tarea:** ALETHEIA-CLIENT-045
```python
# apps/api/src/services/aletheia_client.py
class AletheiaClient:
    async def start_research(self, query: str) -> str
    async def get_task_status(self, task_id: str) -> dict
    async def stream_events(self, task_id: str) -> AsyncGenerator
```

### 3. **Streaming Real (Alto)**
**Tarea:** STREAMING-SSE-050  
```python
# apps/api/src/routers/stream.py
@router.get("/api/stream/{task_id}")
async def stream_task_events(task_id: str):
    # Lee events.ndjson de Aletheia
    # Emite SSE al frontend
```

### 4. **Autenticación JWT (Alto)**
**Tarea:** AUTH-JWT-060
```python
# apps/api/src/middleware/auth.py  
def jwt_middleware(request: Request) -> User:
    # Validar JWT token
    # Proteger rutas sensibles
```

### 5. **Testing (Alto)**
**Tareas:** TESTS-UNIT-135, TESTS-E2E-140
- Unit tests para servicios y componentes
- E2E con Playwright (chat + research flow)
- Contract tests con Aletheia

## 🛠️ Setup Inmediato

### Comandos Listos para Usar:
```bash
# 1. Levantar servicios actuales
pnpm dev  # UI en http://localhost:3000

# 2. Implementar FastAPI endpoints
cd apps/api
uvicorn src.main:app --reload --port 8000

# 3. Conectar con Aletheia
# (seguir docs de Aletheia para setup)
```

### Variables de Entorno Pendientes:
```bash
# apps/api/.env
ALETHEIA_BASE_URL=http://localhost:8001
ALETHEIA_API_KEY=...
MONGODB_URL=mongodb://...
REDIS_URL=redis://...
JWT_SECRET=...
```

## 📋 Checklist de Integración

### Backend → Frontend
- [ ] Endpoints FastAPI funcionando
- [ ] Cliente API conectando correctamente  
- [ ] SSE streaming desde Aletheia
- [ ] Persistencia en MongoDB
- [ ] Cache en Redis

### Testing & Quality
- [ ] Unit tests > 80% cobertura
- [ ] E2E tests del flujo completo
- [ ] Contract tests con Aletheia
- [ ] Performance testing de streaming

### Deploy & Observabilidad  
- [ ] Docker Compose completo
- [ ] OpenTelemetry instrumentación
- [ ] Logs estructurados
- [ ] Health checks

## 🚀 Entregas Incrementales

### Sprint 1: Backend Core (1-2 semanas)
- Endpoints básicos FastAPI
- Cliente Aletheia funcional
- Streaming SSE básico

### Sprint 2: Integración (1 semana)
- Frontend ↔ Backend conectado
- Autenticación JWT
- Persistencia completa

### Sprint 3: Testing & Deploy (1 semana)  
- Tests completos
- CI/CD pipeline
- Deploy automatizado

## 💡 Decisiones Arquitecturales Pendientes

### 1. **Aletheia Integration**
- ¿API directa o message queue?
- ¿Polling vs WebHooks para eventos?
- ¿Timeout handling para research largos?

### 2. **Authentication**
- ¿JWT simple o OAuth2?
- ¿Refresh tokens necesarios?
- ¿Role-based access control?

### 3. **Scaling**
- ¿Load balancer para múltiples instancias?
- ¿Redis Cluster para alta disponibilidad?
- ¿CDN para assets estáticos?

---

## 🎯 Meta Inmediata

**Objetivo:** Tener el primer flujo completo funcionando en 1-2 semanas:
1. Usuario envía mensaje en UI ✅
2. Backend FastAPI lo procesa ⏳
3. Se conecta con Aletheia ⏳ 
4. Streaming de respuesta en tiempo real ⏳
5. Resultado guardado en DB ⏳

**Estado actual:** Frontend 100% listo, backend 0% implementado.