# Arquitectura: Validación y Seguridad

> **Cuándo leer**: Para entender guardrails, validación y multi-tenancy.

## Validación en 3 Capas

```
Query del Usuario
       │
       ▼
┌─────────────────────────────────┐
│  CAPA 1: Intent/Bank/Metric     │
│  ─────────────────────────────  │
│  • Validar contra Ontology_Terms │
│  • Rechazar si banco/métrica     │
│    no existen                    │
└───────────────┬─────────────────┘
                │ ✓ Pasa
                ▼
┌─────────────────────────────────┐
│  CAPA 2: QuerySpec JSON Schema  │
│  ─────────────────────────────  │
│  • Validar estructura JSON       │
│  • Reparación automática si      │
│    es posible                    │
│  • Abstención si irreparable     │
└───────────────┬─────────────────┘
                │ ✓ Pasa
                ▼
┌─────────────────────────────────┐
│  CAPA 3: SQL Validator          │
│  ─────────────────────────────  │
│  • Solo SELECT (whitelist)       │
│  • Budget: tiempo/rows/joins     │
│  • Whitelist de tablas/vistas    │
└───────────────┬─────────────────┘
                │ ✓ Pasa
                ▼
         Ejecución SQL
```

---

## Guardrails de Ejecución

| Guardrail | Límite | Justificación |
|-----------|--------|---------------|
| **Timeout** | 30s máximo | Evitar queries pesadas |
| **Rows** | 5000 máximo | Limitar memoria |
| **Joins** | 2 máximo | Evitar complejidad |
| **Tablas** | Whitelist | Solo `monthly_kpis`, `vw_*` |
| **Rate limit** | 10 queries/min | Por usuario |

### Whitelist de Operaciones SQL

| Permitido | Prohibido |
|-----------|-----------|
| `SELECT` | `INSERT`, `UPDATE`, `DELETE` |
| `WHERE`, `GROUP BY` | `DROP`, `TRUNCATE` |
| `ORDER BY`, `LIMIT` | `CREATE`, `ALTER` |
| `JOIN` (hasta 2) | Subqueries anidadas (>2) |

---

## Modo Abstención

Si falta señal suficiente, el sistema **NO inventa**:

### Cuándo se activa

| Condición | Acción |
|-----------|--------|
| `confidence < 0.7` | Pedir clarificación |
| Métrica no encontrada | Ofrecer top-k candidatos |
| Banco ambiguo | Listar opciones |
| Query irreparable | Explicar limitación |

### Ejemplo

```
Usuario: "Dame la morosidad"

Sistema: "No tengo suficiente información. ¿Te refieres a:
  • IMOR (Índice de Morosidad en %)
  • Cartera vencida nominal (en MXN)

Por favor selecciona o aclara."
```

---

## Audit Trail

Cada query genera un registro estructurado:

```json
{
  "trace_id": "uuid-xxx",
  "timestamp": "2025-01-10T14:30:00Z",
  "user_id": "user_abc",
  "organization_id": "org_xyz",
  "intent": "SQL_QUERY",
  "query_text": "Dame IMOR de INVEX",
  "queryspec_confidence": 0.92,
  "validation_passed": true,
  "sql_fingerprint": "sha256:abc123",
  "result_row_count": 12,
  "latency_ms": 2340
}
```

**Nota**: Se guarda SQL fingerprint, NO los datos resultantes.

---

## Multi-tenancy (Preparación v1.2)

> El BRD identifica multi-tenancy como pregunta de **primera junta** en banca.

### Estado Actual vs Target

| Aspecto | v1.2 (Actual) | v1.3+ (Target) |
|---------|---------------|----------------|
| Segregación de datos | Single-tenant | Multi-tenant con RLS |
| Aislamiento de queries | Por usuario | Por organización |
| Datos de entrenamiento | Compartidos | Segregados por cliente |
| Audit logs | Centralizados | Por tenant |

### Preparación Arquitectónica (v1.2)

Aunque NO se implementa multi-tenancy completo, el diseño **prepara**:

1. **Schema con tenant_id**: Todas las tablas incluyen `tenant_id` (nullable)
2. **Query templates parametrizados**: Aceptan `tenant_id` como filtro
3. **Audit trail con contexto**: Logs incluyen `organization_id`
4. **Vistas SQL**: Pueden filtrar por tenant sin cambiar lógica

---

## Respuestas para Ventas

| Pregunta del Cliente | Respuesta |
|---------------------|-----------|
| "¿Los datos de mi banco están segregados?" | Sí. Cada cliente tiene vistas dedicadas con Row-Level Security. Los datos nunca se mezclan. |
| "¿Entrenan su modelo con mis datos?" | No. El modelo base es pre-entrenado. Sus datos solo responden *sus* consultas. |
| "¿Puedo auditar quién accedió?" | Sí. Cada query genera registro con usuario, timestamp, y query ejecutada. |

---

## Checklist de Seguridad

- [x] Solo SELECT permitido
- [x] Whitelist de tablas
- [x] Budget de tiempo/rows
- [x] Rate limiting por usuario
- [x] Audit trail completo
- [x] Modo abstención funcional
- [x] tenant_id en schemas (nullable)
- [ ] RLS completo (v1.3)
- [ ] Segregación por organización (v1.3)

---

**Versión**: 1.2.1 | **Fuente**: `docs/tex/Arquitectura.tex` secciones 8, 9
