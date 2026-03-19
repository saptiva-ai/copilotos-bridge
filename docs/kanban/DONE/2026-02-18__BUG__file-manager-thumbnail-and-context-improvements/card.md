---
id: "BUG-2026-02-18__file-manager-thumbnail-and-context-improvements"
title: "File Manager: thumbnails rotos y mejoras de contexto en chat"
status: "DONE"
phase: "Research"
scope_in:
  - "Fix: thumbnails no se muestran para PDFs e imagenes (legacy y nuevos)"
  - "Fix: ThumbnailImage retorna null silenciosamente, dejando espacio vacio"
  - "Fix: fallback visual no se muestra cuando thumbnail falla en documentos READY"
  - "Mejora: pre-generar thumbnails durante upload (eager) en vez de lazy"
  - "Mejora: reducir double-hop en proxy de thumbnails"
  - "Mejora: contexto de documentos truncado a 4000 chars pierde informacion"
  - "Mejora: RAG limitado a 2 segmentos por query"
  - "Mejora: persistencia de contexto de archivos entre turnos del chat"
scope_out:
  - "Cambios en el flujo de autenticacion"
  - "Nuevos formatos de archivo (xlsx, docx, etc.)"
  - "Migracion de storage engine (seguir con MinIO)"
  - "Cambios en la UI del composer (solo preview/thumbnails)"
next_action: "Investigar logs de PROD para confirmar frecuencia de fallo de thumbnails"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 0
validation_commands: []
pr_files: []
test_status: "research"
---

# Summary

El plugin file-manager presenta dos categorias de problemas:

1. **Thumbnails rotos**: Las imagenes de preview (PDF e imagenes) no se muestran correctamente en el chat. El componente `ThumbnailImage` falla silenciosamente y el fallback visual no siempre se activa.

2. **Contexto limitado en chat**: El texto extraido de documentos se trunca a 4000 chars, solo se recuperan 2 segmentos RAG, y el cache de Redis expira en 1 hora, perdiendo contexto entre sesiones.

# Problemas Identificados

## P1: Thumbnails (Frontend + Backend)

### P1.1 - Legacy documents sin thumbnail
- Documentos con `minio_bucket="temp"` y `minio_key=/tmp/...` no pueden generar thumbnail
- El endpoint `GET /api/documents/{doc_id}/thumbnail` retorna 404
- Frontend muestra espacio vacio en vez de fallback icon

### P1.2 - ThumbnailImage falla silenciosamente
- Cuando el fetch falla, retorna `null` (linea 103 de ThumbnailImage.tsx)
- El padre `PreviewAttachment` no detecta que ThumbnailImage fallo
- Resultado: espacio vacio donde deberia haber un icon de fallback

### P1.3 - Thumbnails no se pre-generan
- Generacion lazy (primer request) causa latencia en primer render
- No hay cache warming durante el upload pipeline

### P1.4 - Double-hop en proxy
- `ThumbnailImage` -> Next.js proxy -> Backend = 2 HTTP hops
- Podria usar presigned URL directa a MinIO para imagenes

## P2: Contexto de Documentos en Chat

### P2.1 - Truncamiento agresivo
- `DocumentContextBuilder.max_text_chars = 4000` chars por documento
- PDFs de 10+ paginas pierden >80% del contenido

### P2.2 - RAG con pocos segmentos
- `max_segments = 2` limita la cobertura semantica
- Queries que abarcan multiples secciones del documento pierden contexto

### P2.3 - TTL corto en Redis
- Cache de texto extraido expira en 1 hora
- Usuario que regresa a conversacion despues de 1h pierde contexto

### P2.4 - Sin resumen persistente
- No se genera resumen/metadata del documento para referencia rapida
- Cada turno debe hacer full RAG retrieval

# Criterios de Aceptacion
- [ ] Thumbnails visibles para PDFs e imagenes en status READY
- [ ] Fallback visual (icon SVG) cuando thumbnail no disponible
- [ ] Contexto de documentos > 4000 chars disponible via RAG
- [ ] Tests unitarios para thumbnail generation pipeline
- [ ] Tests E2E para upload + preview visible

# Updates
- 2026-02-18 - Ticket creado con investigacion inicial del pipeline completo
