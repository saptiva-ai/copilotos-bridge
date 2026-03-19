# Research - BUG-2026-01-13-0530__date-validation-vivienda

## What I tried
- Intenté correr el test E2E `python tests/e2e/conversation/test_hipotecario_bugs.py -k HIP-005 or HIP-016` y falla con `FATAL: Authentication failed` (login demo/Demo1234 devuelve 401). No pude reproducir el fallo real sin credenciales válidas.
- Consulté directamente al servicio `bank-advisor` (puerto 8002) vía RPC para los dos queries problemáticos:
  - `cartera vivienda de INVEX y BBVA`
  - `cartera hipotecaria de INVEX, BBVA y Santander`

## Findings (bank-advisor directo)
- Ambos queries regresan `visualization: line_chart` con ejes X de fechas correctas (2019-2025) y `metric_name: Cartera Vivienda`.
- Para múltiples bancos, el servicio filtra a los que tienen datos:
  - `INVEX, BBVA` → solo grafica `INVEX` (BBVA sin datos en la vista).
  - `INVEX, BBVA y Santander` → grafica `INVEX` y `SANTANDER`.
- Los SQL generados usan `monthly_kpis` con `WHERE banco_norm IN (...) ORDER BY fecha ASC;`, no se ve el bug de fechas 2017 ni x-values con nombres de bancos.

## Hypothesis
- El fallo descrito (x-values con bancos o sin años 2019-2025) no se reproduce en el servicio de métricas; probablemente ocurre en el flujo E2E por:
  - Falta de autenticación en backend (`/api/auth/login` con demo falla), por lo que el test no está ejercitando el pipeline real.
  - Posible transformación/parseo SSE en backend/frontend que degrade la respuesta (sin poder validar sin token).
  - Tests asumen que todos los bancos solicitados regresan datos; en realidad algunos bancos no tienen serie y se filtran, lo que podría romper una aserción rígida de fechas.

## Recommendations / Next steps
1) Conseguir credenciales válidas para `/api/auth/login` o parametrizar `AUTH_PAYLOAD` con variables de entorno para poder correr los E2E reales.
2) Relajar/ajustar las aserciones:
   - Aceptar que la serie incluya solo bancos con datos (ej. INVEX, SANTANDER) y no fallar si un banco queda fuera.
   - Validar fechas solo cuando `plotly_config.data[*].x` contiene valores con dígitos y separadores (`-` o `/`); si son categorías (bancos), omitir chequeo.
3) Si el backend sigue retornando x-values con bancos, capturar un payload SSE real con credenciales para contrastar contra la respuesta directa de `bank-advisor`.

## Blockers
- Autenticación inválida (demo/Demo1234) impide correr los tests E2E y ver el fallo exacto.
