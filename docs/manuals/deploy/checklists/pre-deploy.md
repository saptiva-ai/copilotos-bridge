# Pre-Deployment Checklist

Before deploying to production, ensure all items are checked.

## Local Build & Test

- [ ] Code is up-to-date with `main` branch.
- [ ] `./scripts/deploy/build-v1.4.0.sh` (or current version) runs without error.
- [ ] `docker compose up -d` locally starts all services.
- [ ] Health checks pass locally:
    - [ ] `curl http://localhost:8000/api/health`
    - [ ] `curl http://localhost:8002/health`
    - [ ] `curl http://localhost:3000`
- [ ] **Happy Path Tests** pass: `python tests/e2e/test_happy_path_suite.py` (Expected > 95% pass rate).

## Web Build Verification (CRITICAL)

> **Why?** Next.js `NEXT_PUBLIC_*` variables are inlined at build time. A wrong value causes CORS errors in production.
> See: [Incident 2026-02-05](../lessons/2026-02-05_web_build_env_incident.md)

- [ ] Built with explicit empty `NEXT_PUBLIC_API_URL`:
    ```bash
    NEXT_PUBLIC_API_URL="" docker compose build web --build-arg NEXT_PUBLIC_API_URL=""
    ```
- [ ] Verified **NO** `localhost:8000` in JavaScript bundle:
    ```bash
    docker run --rm <image> sh -c "grep -r 'localhost:8000' /app/apps/web/.next/static/chunks/" && echo "❌ FAIL" || echo "✅ PASS"
    ```
- [ ] Verified `getApiBaseUrl()` returns empty string:
    ```bash
    docker run --rm <image> sh -c "grep -o 'getApiBaseUrl.\\{0,30\\}' /app/apps/web/.next/static/chunks/294*.js"
    # Expected: getApiBaseUrl(){return""}
    ```

See full runbook: [Web Build Verification](../runbooks/web_build_verification.md)

## Registry

- [ ] `docker login` performed successfully.
- [ ] Images pushed to Docker Hub via push script.

## Production Server Prep

- [ ] SSH access confirmed: `ssh jf@PROD_SERVER_IP`.
- [ ] **BACKUP**: MongoDB dump created and downloaded.
- [ ] `git pull` executed on server.
- [ ] **CRITICAL**: `docker volume rm octavios-chat-bajaware_invex_backend_shared` (if it exists) to prevent stale code.

## Post-Deploy Verification

- [ ] Services started successfully (`docker compose ps`).
- [ ] No critical errors in logs (`docker compose logs --tail=50`).
- [ ] Frontend accessible via public URL.
- [ ] Test Query: "Dame el IMOR de INVEX" works.
- [ ] Charts render correctly.
- [ ] No "Conversación no encontrada" errors.
