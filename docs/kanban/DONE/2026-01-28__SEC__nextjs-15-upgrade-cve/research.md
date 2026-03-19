# Research: Next.js 15 Upgrade (CVE-2025-59471)

## Versiones Actuales

| Paquete | Version Actual | Version Target |
|---------|----------------|----------------|
| next | ^14.2.35 | ^15.5.10 |
| react | ^18.3.1 | ^19.0.0 |
| react-dom | ^18.3.1 | ^19.0.0 |

---

## Archivos que Requieren Migracion

### 1. Params Async (Breaking Change)

En Next.js 15, `params` en rutas dinamicas es ahora `Promise<T>`.

| Archivo | Estado | Cambio Requerido |
|---------|--------|------------------|
| `src/app/chat/[chatId]/page.tsx` | **PENDIENTE** | Migrar a async params |
| `src/app/api/reports/audit/[reportId]/download/route.ts` | **PENDIENTE** | Migrar a async params |
| `src/app/api/thumbnails/[fileId]/route.ts` | **YA MIGRADO** | Ninguno (referencia) |

#### Ejemplo de Referencia (ya migrado)

```typescript
// src/app/api/thumbnails/[fileId]/route.ts - YA COMPATIBLE
export async function GET(
  request: NextRequest,
  context: { params: Promise<{ fileId: string }> },
) {
  const params = await context.params;
  const { fileId } = params;
  // ...
}
```

### 2. searchParams (Client Components)

| Archivo | Estado | Cambio Requerido |
|---------|--------|------------------|
| `src/app/(auth)/reset-password/page.tsx` | **OK** | Ninguno - usa `useSearchParams()` hook (client) |

### 3. cookies() / headers()

**No se encontro uso de estas APIs** en el codebase. No requiere cambios.

### 4. Archivos Sin Cambios Requeridos

- `src/app/chat/[chatId]/loading.tsx` - No usa params
- `src/app/chat/[chatId]/not-found.tsx` - No usa params

---

## Compatibilidad de Dependencias con React 19

### Dependencias Criticas a Verificar

| Paquete | Version | React 19 Compatible | Notas |
|---------|---------|---------------------|-------|
| @headlessui/react | ^1.7.19 | SI (>=2.0) | Actualizar a v2.x |
| @tanstack/react-query | ^5.90.11 | SI | Compatible desde v5 |
| framer-motion | ^12.23.25 | SI | Compatible |
| react-hot-toast | ^2.6.0 | SI | Compatible |
| react-markdown | ^10.1.0 | SI | Compatible |
| zustand | ^4.5.7 | SI | Compatible desde v4 |
| @testing-library/react | ^14.3.1 | PARCIAL | Actualizar a v15+ |
| eslint-config-next | ^14.2.35 | NO | Actualizar a ^15 |
| @types/react | ^18.3.27 | NO | Actualizar a ^19 |
| @types/react-dom | ^18.3.7 | NO | Actualizar a ^19 |

---

## Cambios en next.config.js

### Experimental -> Stable en Next 15

```javascript
// Antes (Next 14)
experimental: {
  serverActions: { ... },           // -> Ahora estable
  optimizePackageImports: [...],    // -> Ahora estable
  outputFileTracingRoot: path,      // -> Mantener
}

// Despues (Next 15)
serverActions: { ... },             // Mover fuera de experimental
optimizePackageImports: [...],      // Mover fuera de experimental
experimental: {
  outputFileTracingRoot: path,      // Mantener aqui
}
```

---

## Cambios de Caching (Next 15)

- `fetch()` ya **NO cachea por defecto**
- Revisar si hay fetch calls que dependan del cache implicito
- **Impacto**: Bajo - la app usa principalmente WebSocket y React Query

---

## Estrategia de Migracion Propuesta

### Fase 1: Preparacion
1. Crear branch `feature/nextjs-15-upgrade`
2. Actualizar dependencias de tipos primero

### Fase 2: Actualizacion de Dependencias
1. `pnpm update next@^15.5.10 react@^19 react-dom@^19`
2. `pnpm update @types/react@^19 @types/react-dom@^19`
3. `pnpm update eslint-config-next@^15 @headlessui/react@^2`
4. `pnpm update @testing-library/react@^15`

### Fase 3: Migracion de Codigo
1. Migrar `src/app/chat/[chatId]/page.tsx`
2. Migrar `src/app/api/reports/audit/[reportId]/download/route.ts`
3. Actualizar `next.config.js`

### Fase 4: Validacion
1. `pnpm build`
2. `pnpm test`
3. `pnpm lint`
4. `make test T=e2e`

---

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Mitigacion |
|--------|--------------|------------|
| Dependencias incompatibles | Baja | Ya verificadas arriba |
| Cambios de comportamiento en cache | Media | Revisar fetch calls |
| Tipos de React 19 incompatibles | Baja | Actualizar types primero |
| Tests E2E fallan | Media | Correr suite completa antes de merge |

---

## Conclusion

**Complejidad**: Baja-Media
**Archivos a modificar**: 4 (2 migracion params, 1 config, 1 package.json)
**Tiempo estimado**: 1-2 horas

La migracion es straightforward porque:
1. No hay uso de `cookies()`/`headers()`
2. Solo 2 archivos necesitan migracion de params
3. Ya existe un archivo migrado como referencia
4. Dependencias principales son compatibles con React 19
