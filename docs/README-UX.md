# Notas UX

## 2025-09-24 - Migración layout grid v1

- Se activa `layout.grid.v1` para fijar una rejilla determinista: sidebar (72/280 px) + header + contenido.
- El selector de modelo vive en el header; el botón de historial se mantiene dentro del `aside` con `transition-[width]`.
- En mobile el sidebar usa overlay y `--safe-left` (48 px) para proteger el header.
- Atajo `Cmd/Ctrl+B` alterna el historial en desktop (colapsa) y mobile (abre/cierra overlay).
- Para rollback, deshabilitar `layout.grid.v1` vía `localStorage flag.layout.grid.v1=false` o `NEXT_PUBLIC_FLAG_LAYOUT_GRID_V1=false`.
