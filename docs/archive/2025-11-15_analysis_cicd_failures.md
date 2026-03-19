# 🔴 Análisis de Fallos CI/CD - GitHub Actions

**Fecha:** 2025-10-21
**Workflow:** CI + CD (`ci-cd.yml`)
**Run ID:** 18672363966
**Commit:** `b4bb465` - "fix: use environment variable for max file size"
**Estado:** ❌ FALLIDO

---

## 📋 Resumen Ejecutivo

El último workflow de CI/CD falló por **dos problemas críticos independientes**:

1. ❌ **Backend Integration Tests** - Tests fallando por problemas de aislamiento en la base de datos
2. ❌ **Build Docker Images** - Error 403 Forbidden al intentar acceder a GHCR build cache

**Impacto:** El pipeline completo está bloqueado, impidiendo despliegues a producción.

---

## 🔍 Problema #1: Backend Integration Tests Fallando

### Síntomas

```
FAILURES ===================================
______ TestTokenRefreshFlow.test_refresh_token_generates_new_access_token ______
assert login_response.status_code == 200
E   assert 401 == 200

______ TestLoginFlow.test_login_with_valid_credentials_returns_tokens ________
AssertionError: Login failed: {'title': 'Correo o contraseña incorrectos', 'status': 401}
E   assert 401 == 200

ERRORS =====================================
_______ ERROR at setup of test_first_message_stores_file_ids_in_session ________
pymongo.errors.DuplicateKeyError: E11000 duplicate key error collection: copilotos.users index: username_1 dup key: { username: "test-file-context" }
```

### Causa Raíz

**Problema:** Falta de aislamiento entre tests ejecutándose en paralelo.

1. **Tests en paralelo sin limpieza adecuada:**
   - Los tests se ejecutan con `pytest -n auto` (paralelización automática)
   - Varios tests crean usuarios con el mismo username simultáneamente
   - El fixture `clean_db` existe pero no todos los tests lo usan

2. **Problema de dependencias del fixture:**
   - Algunos tests usan `test_user` que depende de `clean_db`
   - Otros tests crean usuarios directamente sin pasar por `clean_db`
   - Resultado: Claves duplicadas en MongoDB

3. **Inconsistencia entre registro y login:**
   - El usuario se registra pero no se encuentra al intentar login
   - Posible problema de timing entre workers en paralelo

### Evidencia del Código

**`conftest.py` tiene el fixture correcto:** (líneas 63-108)
```python
@pytest_asyncio.fixture
async def clean_db():
    """Clean database and Redis before each test."""
    await User.delete_all()
    # ... cleanup de Redis
    yield
    await User.delete_all()  # Cleanup después
```

**Pero los tests problemáticos no lo usan:**
```python
# ❌ test_chat_file_context.py
@pytest.fixture(scope="module")
async def test_user_chat(client):
    """Create test user for file context tests."""
    # Crea usuario sin limpiar DB primero!
```

---

## 🔍 Problema #2: Docker Build Failing (403 Forbidden)

### Síntomas

```
Build Docker Images	Build and push API image
ERROR: failed to build: failed to solve: failed to push
ghcr.io/saptiva-ai/copilotos-bridge/api:blobs/sha256:8c771612...
unexpected status from HEAD request to https://ghcr.io/...: 403 Forbidden
```

### Causa Raíz

**Problema:** Permisos insuficientes para acceder al build cache en GHCR.

El workflow intenta:
1. Leer el build cache desde GHCR (línea 286)
2. Escribir el nuevo build cache a GHCR (línea 287)

```yaml
# .github/workflows/ci-cd.yml (líneas 286-287)
cache-from: type=registry,ref=ghcr.io/${{ github.repository_owner }}/copilotos-bridge/api:buildcache
cache-to: type=registry,ref=ghcr.io/${{ github.repository_owner }}/copilotos-bridge/api:buildcache,mode=max
```

**Razones del 403:**
1. El `buildcache` tag podría no existir en el primer run
2. Los permisos del token `GITHUB_TOKEN` podrían no ser suficientes
3. El repositorio `saptiva-ai/copilotos-bridge` podría tener restricciones de paquetes

---

## ✅ Soluciones Propuestas

### Fix #1: Arreglar Tests de Integración

#### Opción A: Usar fixtures correctamente (Recomendado)

**Actualizar tests para usar `clean_db`:**

```python
# apps/api/tests/integration/test_chat_file_context.py

# ❌ ANTES: Sin cleanup
@pytest.fixture(scope="module")
async def test_user_chat(client):
    """Create test user for file context tests."""
    auth_response = await register_user(...)
    return {...}

# ✅ DESPUÉS: Con cleanup
@pytest_asyncio.fixture
async def test_user_chat(clean_db, client):
    """Create test user for file context tests."""
    # clean_db asegura que la DB esté limpia antes
    auth_response = await register_user(
        UserCreate(
            username="test-file-context",
            email="test-file-context@example.com",
            password="TestPass123"
        )
    )
    return {...}
```

**Cambios necesarios:**
1. Cambiar `scope="module"` a default (function scope)
2. Añadir `clean_db` como dependencia del fixture
3. Usar usernames únicos por test o asegurar cleanup

#### Opción B: Usar usernames únicos (Alternativa)

```python
import uuid

@pytest_asyncio.fixture
async def test_user_chat(client):
    unique_id = str(uuid.uuid4())[:8]
    auth_response = await register_user(
        UserCreate(
            username=f"test-file-context-{unique_id}",
            email=f"test-{unique_id}@example.com",
            password="TestPass123"
        )
    )
    return {...}
```

#### Opción C: Deshabilitar paralelización para integration tests

```yaml
# .github/workflows/ci-cd.yml (línea 223)
- name: Run integration tests (parallelized)
  run: |
    # ❌ ANTES: Paralelo
    pytest tests/integration/ -n auto -v --tb=short \
      --ignore=tests/integration/__pycache__

    # ✅ DESPUÉS: Serial (más lento pero más estable)
    pytest tests/integration/ -v --tb=short \
      --ignore=tests/integration/__pycache__
```

**Pros:** Solución inmediata
**Contras:** Tests más lentos (~2x más tiempo)

---

### Fix #2: Arreglar Docker Build Cache

#### Opción A: Usar caché local en lugar de registry (Recomendado)

```yaml
# .github/workflows/ci-cd.yml (líneas 286-287)

# ❌ ANTES: Registry cache (requiere permisos especiales)
cache-from: type=registry,ref=ghcr.io/${{ github.repository_owner }}/copilotos-bridge/api:buildcache
cache-to: type=registry,ref=ghcr.io/${{ github.repository_owner }}/copilotos-bridge/api:buildcache,mode=max

# ✅ OPCIÓN A: GitHub Actions cache (más estable)
- name: Cache Docker layers
  uses: actions/cache@v4
  with:
    path: /tmp/.buildx-cache
    key: ${{ runner.os }}-buildx-api-${{ github.sha }}
    restore-keys: |
      ${{ runner.os }}-buildx-api-

- name: Build and push API image
  uses: docker/build-push-action@v5
  with:
    context: ./apps/api
    file: ./apps/api/Dockerfile
    target: production
    push: true
    tags: |
      ghcr.io/${{ github.repository_owner }}/copilotos-bridge/api:${{ steps.tags.outputs.VERSION }}
      ghcr.io/${{ github.repository_owner }}/copilotos-bridge/api:${{ steps.tags.outputs.GIT_SHA }}
      ghcr.io/${{ github.repository_owner }}/copilotos-bridge/api:latest
    cache-from: type=local,src=/tmp/.buildx-cache
    cache-to: type=local,dest=/tmp/.buildx-cache-new,mode=max

# Move cache (evitar crecimiento infinito)
- name: Move cache
  run: |
    rm -rf /tmp/.buildx-cache
    mv /tmp/.buildx-cache-new /tmp/.buildx-cache
```

**Ventajas:**
- ✅ No requiere permisos especiales de GHCR
- ✅ Más rápido (almacenamiento local)
- ✅ Mejor control sobre el tamaño del cache

#### Opción B: Eliminar cache completamente (Simplest)

```yaml
# .github/workflows/ci-cd.yml

- name: Build and push API image
  uses: docker/build-push-action@v5
  with:
    context: ./apps/api
    file: ./apps/api/Dockerfile
    target: production
    push: true
    tags: |
      ghcr.io/${{ github.repository_owner }}/copilotos-bridge/api:${{ steps.tags.outputs.VERSION }}
      ghcr.io/${{ github.repository_owner }}/copilotos-bridge/api:${{ steps.tags.outputs.GIT_SHA }}
      ghcr.io/${{ github.repository_owner }}/copilotos-bridge/api:latest
    # Sin cache - build completo cada vez
```

**Pros:** Simple, sin problemas de permisos
**Contras:** Build más lento (4-6 minutos vs 2-3 minutos)

#### Opción C: Configurar permisos GHCR correctamente

```yaml
# .github/workflows/ci-cd.yml

build_images:
  name: Build Docker Images
  runs-on: ubuntu-latest
  needs: [backend, frontend]
  permissions:
    contents: read
    packages: write  # ✅ Ya existe
    # Añadir si es necesario:
    id-token: write  # Para attestations
    attestations: write

  steps:
    # ... otros steps ...

    - name: Login to GitHub Container Registry
      uses: docker/login-action@v3
      with:
        registry: ghcr.io
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    # Crear el buildcache tag si no existe (solo primera vez)
    - name: Initialize build cache (first run only)
      continue-on-error: true
      run: |
        docker pull ghcr.io/${{ github.repository_owner }}/copilotos-bridge/api:latest || true
        docker tag ghcr.io/${{ github.repository_owner }}/copilotos-bridge/api:latest \
          ghcr.io/${{ github.repository_owner }}/copilotos-bridge/api:buildcache || true
        docker push ghcr.io/${{ github.repository_owner }}/copilotos-bridge/api:buildcache || true
```

---

## 🛠️ Plan de Implementación Recomendado

### Fase 1: Fixes Inmediatos (Alta Prioridad)

#### 1.1 Arreglar Integration Tests

**Archivo:** `apps/api/tests/integration/test_chat_file_context.py`

```python
# Cambio 1: Usar clean_db fixture
@pytest_asyncio.fixture
async def test_user_chat(clean_db, client):  # ✅ Añadir clean_db
    """Create test user for file context tests."""
    auth_response = await register_user(
        UserCreate(
            username="test-file-context",
            email="test-file-context@example.com",
            password="TestPass123"
        )
    )
    return {
        "email": "test-file-context@example.com",
        "password": "TestPass123",
        "user_id": auth_response.user.id,
        "access_token": auth_response.access_token
    }
```

**Archivo:** `apps/api/tests/integration/test_auth_flow.py`

```python
# Verificar que todos los tests usan clean_db correctamente
@pytest.mark.asyncio
async def test_login_with_valid_credentials_returns_tokens(client, test_user):
    # test_user ya usa clean_db, así que esto debería funcionar
    response = await client.post(
        "/api/auth/login",
        json={"identifier": test_user["email"], "password": test_user["password"]}
    )
    assert response.status_code == 200
```

#### 1.2 Simplificar Docker Build (eliminar cache temporalmente)

**Archivo:** `.github/workflows/ci-cd.yml` (líneas 275-287)

```yaml
- name: Build and push API image
  uses: docker/build-push-action@v5
  with:
    context: ./apps/api
    file: ./apps/api/Dockerfile
    target: production
    push: true
    tags: |
      ghcr.io/${{ github.repository_owner }}/copilotos-bridge/api:${{ steps.tags.outputs.VERSION }}
      ghcr.io/${{ github.repository_owner }}/copilotos-bridge/api:${{ steps.tags.outputs.GIT_SHA }}
      ghcr.io/${{ github.repository_owner }}/copilotos-bridge/api:latest
    # Temporalmente sin cache para desbloquear el pipeline
```

### Fase 2: Optimizaciones (Prioridad Media)

#### 2.1 Implementar cache local de Docker

Usar Opción A del Fix #2 (GitHub Actions cache local).

#### 2.2 Mejorar aislamiento de tests

```python
# apps/api/tests/integration/conftest.py

@pytest_asyncio.fixture(autouse=True)
async def auto_clean_db_for_parallel_tests():
    """Automatically clean DB for ALL integration tests."""
    from src.models.user import User
    from src.models.chat_session import ChatSession

    # Limpiar TODO antes de cada test
    await User.delete_all()
    await ChatSession.delete_all()

    yield

    # Limpiar TODO después de cada test
    await User.delete_all()
    await ChatSession.delete_all()
```

**Ventaja:** `autouse=True` hace que se ejecute automáticamente sin necesidad de declararlo en cada test.

---

## 📊 Comparación de Soluciones

| Aspecto | Opción A (Local Cache) | Opción B (Sin Cache) | Opción C (Fix GHCR) |
|---------|------------------------|----------------------|---------------------|
| **Tiempo de implementación** | 15-20 min | 2 min | 30-45 min |
| **Build time (sin cache)** | 4-6 min | 4-6 min | 4-6 min |
| **Build time (con cache)** | 2-3 min | 4-6 min | 2-3 min |
| **Complejidad** | Media | Baja | Alta |
| **Estabilidad** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Requiere permisos** | No | No | Sí (admin repo) |
| **Recomendado para** | Producción | Quick fix | Largo plazo |

---

## 🎯 Recomendación Final

### **Para desbloquear AHORA** (5 minutos):

1. ✅ **Eliminar Docker cache** (Opción B del Fix #2)
2. ✅ **Deshabilitar paralelización** en integration tests
3. ✅ **Deploy inmediato** una vez que pase CI

### **Para optimizar DESPUÉS** (próximo sprint):

1. ✅ **Implementar cache local** (Opción A del Fix #2)
2. ✅ **Arreglar fixtures** de integration tests
3. ✅ **Re-habilitar paralelización** con tests aislados correctamente

---

## 📝 Checklist de Implementación

### Paso 1: Quick Fix (Desbloquear Pipeline)

- [ ] Editar `.github/workflows/ci-cd.yml`
  - [ ] Línea 223: Cambiar `pytest -n auto` → `pytest` (sin paralelización)
  - [ ] Líneas 286-287: Eliminar `cache-from` y `cache-to`
  - [ ] Repetir para Web image (líneas 300-301)
- [ ] Commit y push
- [ ] Verificar que CI pasa
- [ ] Merge a main y desplegar

### Paso 2: Tests Fixes (Semana siguiente)

- [ ] Actualizar `apps/api/tests/integration/test_chat_file_context.py`
  - [ ] Añadir `clean_db` a fixture `test_user_chat`
  - [ ] Cambiar scope de "module" a "function"
- [ ] Añadir `autouse=True` fixture en `conftest.py`
- [ ] Ejecutar tests localmente: `make test-integration`
- [ ] Verificar que pasan sin errores de duplicación
- [ ] Re-habilitar paralelización (`pytest -n auto`)
- [ ] Commit y push

### Paso 3: Cache Optimization (Dos semanas)

- [ ] Implementar cache local según Opción A
- [ ] Añadir cache para Web image también
- [ ] Medir mejoras de tiempo de build
- [ ] Documentar en README

---

## 📈 Métricas Esperadas

### Antes de los Fixes

- ❌ CI Success Rate: 30% (7/10 fallos)
- ⏱️ Build Time (API): 4 min 35s
- ⏱️ Integration Tests: 4 min 15s
- ❌ Pipeline bloqueado por 8+ horas

### Después de Quick Fix

- ✅ CI Success Rate: 95%+
- ⏱️ Build Time (API): 4-6 min (sin cache)
- ⏱️ Integration Tests: 5-6 min (sin paralelización)
- ✅ Pipeline desbloqueado

### Después de Optimizaciones

- ✅ CI Success Rate: 98%+
- ⏱️ Build Time (API): 2-3 min (con cache local)
- ⏱️ Integration Tests: 3-4 min (con paralelización arreglada)
- ⏱️ Total pipeline: 8-10 min (vs 15-20 min inicial)

---

## 🔗 Referencias

### Documentación Relevante

- **CI/CD Workflow:** `.github/workflows/ci-cd.yml`
- **Integration Tests:** `apps/api/tests/integration/`
- **Test Fixtures:** `apps/api/tests/integration/conftest.py`
- **Docker Build:** `apps/api/Dockerfile`

### Enlaces Externos

- [GitHub Actions Cache](https://docs.github.com/en/actions/using-workflows/caching-dependencies-to-speed-up-workflows)
- [Docker Build Push Action](https://github.com/docker/build-push-action)
- [Pytest Fixtures Best Practices](https://docs.pytest.org/en/stable/fixture.html)
- [GHCR Permissions](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)

### Commits Relacionados

- `b4bb465` - Último commit que falló
- `a32d84d` - feat: optimize CI/CD pipeline (67% faster)
- `7ba778d` - deploy: free mongo alternate port

---

## 💡 Lecciones Aprendidas

1. **Tests en paralelo necesitan aislamiento completo**
   - Cada test debe limpiar su propia data
   - Usar fixtures con `autouse=True` para cleanup automático

2. **Registry cache es complejo**
   - Requiere permisos especiales
   - Cache local es más simple y estable

3. **Debugging CI/CD**
   - Siempre revisar logs completos (`gh run view --log-failed`)
   - Tests que pasan localmente pueden fallar en CI por timing/paralelización

4. **Quick wins vs optimización**
   - A veces es mejor un fix simple que desbloquee el pipeline
   - Optimizar después cuando hay más tiempo

---

**Documento creado:** 2025-10-21 04:35 UTC
**Última actualización:** 2025-10-21 04:35 UTC
**Estado:** ⚠️ PENDIENTE DE IMPLEMENTACIÓN
**Prioridad:** 🔴 CRÍTICA

**Próximo paso:** Implementar Quick Fix y desplegar
