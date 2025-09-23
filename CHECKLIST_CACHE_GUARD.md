## Guardas permanentes (Next.js Chat LLM)
- [ ] MSW solo se activa con doble condición (env + flag de usuario) y se desregistra si no procede.
- [ ] Handlers del chat exportan `dynamic = 'force-dynamic'` y `revalidate = 0`.
- [ ] Respuestas del handler incluyen `Cache-Control: no-store` y `Pragma: no-cache`.
- [ ] Fetch del cliente usa `{ cache: 'no-store', next: { revalidate: 0 } }`.
- [ ] Sin `generateStaticParams`/ISR en rutas con I/O de LLM.
- [ ] React Query/SWR: invalidación en login/logout/cambio de API_BASE.
- [ ] Sin fallback silencioso a mocks en producción (asserts).
- [ ] Script de pánico documentado para limpiar Storage/SW/IDB/Caches.
