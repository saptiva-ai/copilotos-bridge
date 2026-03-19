# Plan: Next.js 15 Upgrade (CVE-2025-59471)

## Resumen

Actualizar Next.js de 14.x a 15.5.10+ para resolver CVE-2025-59471 (DoS via Image Optimizer).

**Archivos a modificar**: 4
**Complejidad**: Baja-Media

---

## Fase 1: Actualizacion de Dependencias

### 1.1 Actualizar paquetes core

```bash
cd apps/web
pnpm update next@^15.5.10 react@^19 react-dom@^19
```

### 1.2 Actualizar tipos y tooling

```bash
pnpm update @types/react@^19 @types/react-dom@^19
pnpm update eslint-config-next@^15
pnpm update @headlessui/react@^2
pnpm update @testing-library/react@^16
```

### 1.3 Verificar instalacion

```bash
pnpm install
pnpm list next react react-dom
```

---

## Fase 2: Migracion de Codigo

### 2.1 Migrar `src/app/chat/[chatId]/page.tsx`

**Antes:**
```tsx
interface ChatRouteProps {
  params: {
    chatId: string;
  };
}

export default function ChatRoute({ params }: ChatRouteProps) {
  const { chatId } = params;
  // ...
}
```

**Despues:**
```tsx
interface ChatRouteProps {
  params: Promise<{
    chatId: string;
  }>;
}

export default async function ChatRoute({ params }: ChatRouteProps) {
  const { chatId } = await params;
  // ...
}
```

### 2.2 Migrar `src/app/api/reports/audit/[reportId]/download/route.ts`

**Antes:**
```tsx
export async function GET(
  request: NextRequest,
  { params }: { params: { reportId: string } },
) {
  const { reportId } = params;
  // ...
}
```

**Despues:**
```tsx
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ reportId: string }> },
) {
  const { reportId } = await params;
  // ...
}
```

### 2.3 Actualizar `next.config.js`

**Antes:**
```javascript
experimental: {
  outputFileTracingRoot: path.join(__dirname, '../../'),
  serverActions: {
    allowedOrigins: [...],
  },
  optimizePackageImports: [...],
},
```

**Despues:**
```javascript
serverActions: {
  allowedOrigins: [...],
},
optimizePackageImports: [...],
experimental: {
  outputFileTracingRoot: path.join(__dirname, '../../'),
},
```

---

## Fase 3: Validacion

### 3.1 Build check

```bash
cd apps/web && pnpm build
```

**Criterio**: Build exitoso sin errores de tipos

### 3.2 Lint check

```bash
cd apps/web && pnpm lint
```

**Criterio**: Sin errores de lint

### 3.3 Unit tests

```bash
cd apps/web && pnpm test
```

**Criterio**: Todos los tests pasan

### 3.4 E2E tests

```bash
make test T=e2e
```

**Criterio**: Suite E2E pasa

---

## Fase 4: Verificacion de Seguridad

### 4.1 Confirmar version parcheada

```bash
cd apps/web && pnpm list next
```

**Criterio**: next >= 15.5.10

### 4.2 Verificar advisory resuelto

```bash
cd apps/web && pnpm audit --audit-level=moderate
```

---

## Checklist de Implementacion

- [ ] 1.1 Actualizar next, react, react-dom
- [ ] 1.2 Actualizar tipos y eslint-config-next
- [ ] 1.3 Actualizar headlessui y testing-library
- [ ] 2.1 Migrar chat/[chatId]/page.tsx
- [ ] 2.2 Migrar api/reports/audit/[reportId]/download/route.ts
- [ ] 2.3 Actualizar next.config.js
- [ ] 3.1 Verificar build
- [ ] 3.2 Verificar lint
- [ ] 3.3 Verificar unit tests
- [ ] 3.4 Verificar E2E tests
- [ ] 4.1 Confirmar version >= 15.5.10
- [ ] 4.2 Confirmar audit limpio

---

## Rollback

Si la migracion falla:

```bash
git checkout develop -- apps/web/package.json apps/web/pnpm-lock.yaml
cd apps/web && pnpm install
```

---

## Notas

- El archivo `src/app/api/thumbnails/[fileId]/route.ts` ya esta migrado y sirve como referencia
- No hay uso de `cookies()` o `headers()` de next/headers
- Client components con `useSearchParams()` no requieren cambios
