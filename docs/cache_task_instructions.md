# Cache Task – Execution Guide

Estos son los pasos que seguimos (y que debes repetir fuera del sandbox si necesitas validar contra hosts reales) para endurecer el caché del flujo `/api/chat` y documentar los hallazgos.

## 1. Diagnóstico inicial (T0)
1. Crear carpeta de logs y ejecutar el barrido de baseline:
   ```bash
   mkdir -p logs/network_checks

for URL in "http://localhost:3000"  "http://34.42.214.246"; do
  [ -z "$URL" ] && continue
  printf "\n--- GET ${URL} ---\n" | tee -a logs/network_checks/baseline.txt
  curl -sS -D - -o /dev/null "$URL" | tee -a logs/network_checks/baseline.txt
  printf "\n--- POST ${URL}/api/chat ---\n" | tee -a logs/network_checks/baseline.txt
  curl -sS -D - -o "logs/network_checks/body_$(echo "$URL" | sed 's#https\?://##; s#/##g').json" \
    -X POST "$URL/api/chat" \
    -H "Accept: application/json" \
    -H "Content-Type: application/json" \
    --data '{"message":"Hola, prueba de latido"}' \
    | tee -a logs/network_checks/baseline.txt
  printf "\n" | tee -a logs/network_checks/baseline.txt
  sleep 1
done



   ```
1. Extraer cabeceras relevantes:
   ```bash
grep -Ei 'cache-control|etag|age|x-vercel-cache|x-cache|server-timing' -n logs/network_checks/baseline.txt \
  | tee logs/network_checks/headers_clave.txt
   ```

> Nota: En el sandbox falló la resolución DNS (sin host local ni dominios públicos disponibles). Repite en un entorno con red para capturar cabeceras reales.

## 2. Hardening MSW / runtime (T1)
- No hay `mockServiceWorker.js` en el repo. Agregamos `apps/web/src/lib/runtime.ts` y llamamos a `assertProdNoMock()` desde `apps/web/src/app/chat/page.tsx` para impedir `NEXT_PUBLIC_ENABLE_MSW='true'` en producción.
- Documentamos la verificación manual en `diagnostico/cache_report.json`.

Si llegas a detectar un SW activo en el navegador, desregístralo manualmente (Application → Service Workers) y haz *clear storage*; luego actualiza `diagnostico/cache_report.json` con el resultado real.

## 3. Cache busting (T4)
1. Repite las llamadas con un parámetro `__bust` para comprobar que no hay cacheo en CDN:
   ```bash
mkdir -p logs/network_checks
TS=$(date +%s)
for URL in "http://localhost:3000" "http://34.42.214.246" do
  [ -z "$URL" ] && continue
  QURL="${URL}?__bust=${TS}"
  printf "\n--- GET ${QURL} ---\n" | tee -a logs/network_checks/postfix.txt
  curl -sS -D - -o /dev/null "$QURL" | tee -a logs/network_checks/postfix.txt
  printf "\n--- POST ${URL}/api/chat (bust) ---\n" | tee -a logs/network_checks/postfix.txt
  curl -sS -D - -o "logs/network_checks/body_after_$(echo "$URL" | sed 's#https\?://##; s#/##g').json" \
    -X POST "${URL}/api/chat?__bust=${TS}" \
    -H "Accept: application/json" \
    -H "Content-Type: application/json" \
    --data '{"message":"Hola, prueba de latido"}' \
    | tee -a logs/network_checks/postfix.txt
  printf "\n" | tee -a logs/network_checks/postfix.txt
  sleep 1
done
   ```

## 4. Reporte (diagnóstico)
- Mantén actualizado `diagnostico/cache_report.json` con el estado real (`service_worker`, guardas, notas de fallos de red, etc.). Ejemplo:
  ```bash
mkdir -p diagnostico
cat <<'JSON' > diagnostico/cache_report.json
  {
    "service_worker": "not_detected",
    "msw_runtime_guard": true,
    "notes": [
      "curl baseline/postfix fallidos por DNS en sandbox",
      "No MSW detectado en el repo",
      "Runtime guard evita habilitar mocks en producción"
    ]
  }
  JSON
  ```

## 5. Checklist final (T5)
- El archivo `CHECKLIST_CACHE_GUARD.md` contiene las guardas permanentes a validar. Márcalas cuando se comprueben (por ejemplo, `dynamic = 'force-dynamic'` en handlers, script de pánico, etc.).

## 6. Pasos pendientes / consideraciones
- Ejecutar los `curl` en cada entorno (local/staging/prod) para capturar cabeceras reales.
- Documentar limpieza de Service Workers en un navegador real si llega a existir alguno.
- Si se adopta React Query/SWR en el futuro, crear helper de invalidación como indica la tarea (T3.2).

Con esto tienes un playbook reproducible para el cache hardening solicitado en `cache_tasks.yaml`.
