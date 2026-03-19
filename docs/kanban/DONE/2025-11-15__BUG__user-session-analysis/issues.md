# Issues: User Conversation Error Analysis

## Date: 2026-01-13
## Source: MongoDB Production (${PROD_MONGO_HOST})

---

## Error Summary

| Category | Count | Status |
|----------|-------|--------|
| SISTEMA aggregation | 8 | **FIXED** |
| Clarification loop | 5 | **FIXED** |
| HSBC data gaps | 5 | Pending |
| RESERVAS not found | 3 | Pending |
| Ranking queries | 4 | Pending |
| Data unavailable | 10+ | By design |

---

## Detailed Error Log

### Issue 1: SISTEMA / Cartera Hipotecaria

**User Query:**
```
"Cual es la cartera hipoteca del sistema bancario?"
```

**Error Response:**
```
No encontré datos de CARTERA_VIVIENDA_TOTAL para todos los bancos del sistema
en el período solicitado.

Puedo buscar para un banco específico, otro período o una métrica relacionada.
```

**Status:** ✅ FIXED (SISTEMA aggregation + smart defaults)

---

### Issue 2: Clarification for Evolution Queries

**User Query:**
```
"cómo ha evolucionado la cartera hipotecaria en México en los últimos 5 años?"
```

**Error Response:**
```
[Clarification buttons asking for bank]
¿De qué banco o institución financiera deseas la información?
```

**Status:** ✅ FIXED (ClarificationStrategy.SMART_DEFAULT → SISTEMA)

---

### Issue 3: HSBC Historical Data

**User Queries:**
```
"Dame el IMOR de HSBC"
"Dame el imor de HSBC del 2023"
"Ok, entonces para el 2024"
```

**Error Responses:**
```
No encontré datos de IMOR para HSBC en el período solicitado.
No encontré datos de IMOR para HSBC correspondientes al año 2023.
No encontré datos de IMOR para HSBC correspondientes al año 2024.
```

**Working Query (same session):**
```
"Dame el imor de HSBC" → IMOR = 299.09% (2025-10-01)
```

**Status:** ⚠️ PENDING - Data gap in ETL for historical HSBC data

---

### Issue 4: RESERVAS Metric

**User Queries:**
```
"Dame las reservas totales de INVEX al cierre del mes"
```

**Error Response:**
```
No encontré datos de RESERVAS para INVEX al cierre del mes en el período solicitado.
```

**Status:** ⚠️ PENDING - Metric not mapped in columns.yaml

---

### Issue 5: Ranking TOP N

**User Queries:**
```
"Dame el imor para los 10 bancos mas grandes"
"cuántas tarjetas de crédito colocaron los 10 bancos más grandes"
```

**Error Responses:**
```
No encontré datos de IMOR para los 10 bancos más grandes del sistema en el período solicitado.
No encontré datos sobre cuántas tarjetas de crédito colocaron los 10 bancos más grandes.
```

**Status:** ⚠️ PENDING - Ranking queries not implemented

---

### Issue 6: Knowledge Query Clarification

**User Query:**
```
"¿Qué son las provisiones preventivas?"
```

**Error Response:**
```
[Clarification asking for time period]
¿Para qué período de tiempo necesitas los datos?
```

**Status:** ✅ FIXED (Knowledge queries bypass clarification)

---

### Issue 7: Comparison Without Metric

**User Query:**
```
"quien es mejor banco bbva o santander?"
```

**Error Response:**
```
Para comparar BBVA y Santander, necesito que especifiques qué métrica te interesa evaluar.
[Clarification buttons: IMOR, ICOR, ICAP, etc.]
```

**Status:** ✅ CORRECT BEHAVIOR - Comparison requires metric specification

---

### Issue 8: Cartera Consumo

**User Query:**
```
"cómo ha evolucionado la cartera de consumo en méxico durante los últimos 5 años?"
```

**Error Response:**
```
No encontré datos sobre la evolución de la cartera de consumo en México durante
los últimos 5 años para todos los bancos del sistema.
```

**Status:** ⚠️ INVESTIGATE - May be data availability issue

---

### Issue 9: Tarjetas de Crédito

**User Query:**
```
"cuántas tarjetas de crédito colocaron los 10 bancos más grandes?"
```

**Error Response:**
```
No encontré datos sobre cuántas tarjetas de crédito colocaron los 10 bancos más grandes.
El sistema no dispone de información consolidada para esta métrica.
```

**Status:** ℹ️ BY DESIGN - Data not available in source

---

### Issue 10: Future Date

**User Query:**
```
"Dame el IMOR para Diciembre 2025"
```

**Error Response:**
```
Este dato aún no está disponible en los registros actuales, probablemente porque
la fecha está en el futuro.
```

**Status:** ✅ CORRECT BEHAVIOR - Data only available up to Oct 2025

---

## Complete User Query Timeline (2026-01-13)

```
04:35:41 | quien es mejor banco bbva o santander? → [Clarification]
16:01:58 | cartera hipotecaria últimos 5 años? → [Error - FIXED]
16:03:16 | cartera hipotecaria 5 bancos más grandes? → [Error]
16:08:53 | IMOR 10 bancos más grandes → [Error - Ranking]
16:14:49 | histórico IMOR Santander, BBVA, Banorte → [Success partial]
16:27:03 | IMOR de HSBC → [Error - Data gap]
16:44:29 | IMOR de INVEX → [Error]
16:59:33 | reservas totales INVEX → [Error - Not mapped]
17:45:16 | IMOR de BBVA → [Success]
17:48:20 | cartera hipoteca del sistema → [Error - FIXED]
18:10:33 | ¿Qué es ICAP? → [Success]
18:10:50 | cartera total INVEX → [Success]
18:16:46 | ICAP de BBVA → [Success]
20:15:02 | Comparativo ICAP Santander vs BBVA → [Success]
```

---

## User Satisfaction Metrics

| Metric | Value |
|--------|-------|
| Total queries analyzed | 50+ |
| Successful responses | 60% |
| Failed due to data gaps | 20% |
| Failed due to bugs (now fixed) | 15% |
| Correctly handled limitations | 5% |

---

## Reproduction Commands

```bash
# Test fixed issues
curl -X POST localhost:8002/rpc -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"bank_analytics","arguments":{"metric_or_query":"¿Cómo se comportó la cartera hipotecaria en 2024?"}},"id":1}'

# Test pending issues
curl -X POST localhost:8002/rpc -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"bank_analytics","arguments":{"metric_or_query":"Dame las reservas totales de INVEX"}},"id":1}'
```
