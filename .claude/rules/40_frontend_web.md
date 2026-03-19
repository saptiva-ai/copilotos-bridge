---
paths:
  - apps/web/**/*.ts
  - apps/web/**/*.tsx
  - apps/web/**/*.css
  - apps/web/**/*.scss
---

# Frontend Web Rules

When this applies: editing web UI (TypeScript/TSX/CSS).

## Style
- **Components**: functional + hooks; small, focused units
- **Typing**: no `any`; explicit props interfaces
- **Imports**: `@/` alias for shared paths
- **Format**: Prettier + ESLint (Next.js config)
- **State**: hooks; `useMemo` for heavy computations
- **Styling**: Tailwind; `cn()` for conditional classes
- **Client**: `"use client"` at file top when needed
- **Errors**: handle async errors; no silent failures
- **Naming**: PascalCase components, camelCase hooks/vars, kebab-case files

## Do
- Follow component conventions; update/extend tests for UI changes

## Don't
- Add global styles without checking existing layout patterns
- Use `any` or suppress typing without justification

## Commands
- `make test T=web`
- `cd apps/web && pnpm lint`
