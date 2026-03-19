# Research: Regional Queries Feedback Analysis

**Fecha:** 2026-02-04
**Fuente:** Dashboard Feedback Panel

---

## Feedback Recolectado

### Usuario: 7f5aa3b9-8f98 (4 reports en 2026-02-03)
### Conversación: 06dbbe9d-64f8-452a-a656-c1ee531d2ecd

**Secuencia de queries (todas fallaron):**

1. **Query:** `cual es la distribucion por estado de la cartera comercial de invex?`
   **Feedback:** "no me entrego el resultado"
   **Hora:** 17:54

2. **Query:** `cual es la concentracion por estado de la cartera comercial de invex`
   **Feedback:** "se rompio"
   **Hora:** 17:55

3. **Query:** `CARTERA_COMERCIAL de INVEX de 2025 puedes mostrar un comparativo por region?`
   **Feedback:** "Ya no presenta el detalle por estado"
   **Hora:** 17:56

4. **Query:** `puedes darme el detalle de la cartera comercial de invex por entidad federativa`
   **Feedback:** "No tomo en cuenta los estados precargados"
   **Hora:** 17:58

---

## Análisis

### Contexto Previo (funcionaba antes)

En la conversación `ea9ea471` del 2026-01-21, el mismo tipo de query SÍ funcionó:
- Query: "CARTERA_COMERCIAL de INVEX de 2025 puedes mostrar un comparativo por region?"
- Respuesta: Datos por región (Centro: 7,745M, Occidente: 4,471M, etc.)
- Pero el usuario reportó: "el grafico no se actualiza, se queda pendiente del anterior"

### Patrón del Problema

1. **Antes (2026-01-21):** Queries regionales funcionaban pero el chart no se actualizaba
2. **Después (2026-02-03):** Queries regionales ya no funcionan en absoluto

Esto sugiere que un cambio entre estas fechas rompió la funcionalidad regional.

### Commits a Investigar

```bash
git log --oneline --since="2026-01-21" --until="2026-02-03" -- plugins/bank-advisor-private/
```

### Keywords de Routing

Las queries usan keywords que deberían activar el regional handler:
- "por estado"
- "por entidad federativa"
- "por region"
- "distribucion por estado"
- "concentracion por estado"

### Tabla de Datos

```sql
-- Verificar datos existen
SELECT COUNT(*) FROM bank_mv_cartera_por_estado
WHERE banco ILIKE '%INVEX%';
-- Esperado: datos para 32 estados
```

---

## Prioridad

**P2 - Medium** → Considerar subir a **P1 - High**

El usuario intentó 4 queries consecutivas, todas fallaron. Esto indica:
1. Funcionalidad completamente rota (no parcial)
2. Usuario dedicó tiempo a intentar diferentes formulaciones
3. Afecta casos de uso core (análisis regional)

---

## Acción Recomendada

Mover de BACKLOG a DOING y asignar para investigación.
