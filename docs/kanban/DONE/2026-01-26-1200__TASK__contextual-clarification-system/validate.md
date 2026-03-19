# Validation: Sistema de Clarificación Contextual (v2)

## Comandos de Validación

```bash
# Unit tests de enriquecimiento de contexto
make test T=api TEST_ARGS="-k test_context_enricher"

# Unit tests de resolución de ambigüedad
make test T=api TEST_ARGS="-k test_weaviate_ontology_disambiguation"

# Unit tests de clarificación contextual
make test T=api TEST_ARGS="-k test_contextual_clarification"

# E2E tests de flujo conversacional
make test T=e2e TEST_ARGS="-k test_contextual_flow"

# Regression suite completa
make pre-deploy.regression
```

---

## Criterios de Aceptación

### AC-1: Enriquecimiento de Contexto (Backend)

| Test Case | Input | Expected | Status |
|-----------|-------|----------|--------|
| Follow-up detectado por embeddings | "¿y eso?", chart reciente | is_followup=True, confidence>0.5 | [ ] |
| Similaridad calculada | query="cartera", last_metric="IMOR" | context_similarity en [0,1] | [ ] |
| Sin contexto previo | query="IMOR", no chart | is_followup=False, similarity=0 | [ ] |
| Cache de embeddings usado | misma query 2x | Segunda llamada más rápida | [ ] |

### AC-2: Inferencia de Banco en Follow-ups

| Test Case | Input | Expected | Status |
|-----------|-------|----------|--------|
| Follow-up con banco en contexto | is_followup=True, last_banks=["BBVA"] | bank_names=["BBVA"], no HARD_ASK | [ ] |
| Alta similaridad infiere banco | similarity=0.7, last_banks=["INVEX"] | bank_names=["INVEX"] | [ ] |
| Sin chart reciente no infiere | has_chart=False, last_banks=["BBVA"] | HARD_ASK para banco | [ ] |
| Múltiples bancos en contexto | last_banks=["BBVA", "SANTANDER"] | Usa ambos bancos | [ ] |

### AC-3: Resolución de Ambigüedad con Weaviate

| Test Case | Input | Expected | Status |
|-----------|-------|----------|--------|
| Capitalización + contexto IMOR | term="capitalización", last_metric="IMOR" | resolved=ICAP | [ ] |
| Capitalización + contexto MARKET_SHARE | term="capitalización", last_metric="MARKET_SHARE" | resolved=MARKET_CAP | [ ] |
| Capitalización sin contexto | term="capitalización", last_metric=None | resolved=None → HARD_ASK | [ ] |
| Un solo candidato | term="IMOR" (no ambiguo) | resolved=IMOR directamente | [ ] |
| Categorías no coinciden | term="capitalización", last_metric="CARTERA" | resolved=None → HARD_ASK | [ ] |

### AC-4: Opciones de Clarificación Contextuales

| Test Case | Input | Expected | Status |
|-----------|-------|----------|--------|
| Prioriza bancos del contexto | last_banks=["BBVA"] | BBVA primero con "(anterior)" | [ ] |
| Máximo 5 opciones | last_banks=["A","B"], TOP_BANKS=5 | Total 5 opciones | [ ] |
| Sin contexto | last_banks=[] | TOP_BANKS estándar | [ ] |

### AC-5: Tests de Regresión E2E

| Test Case | Flujo | Expected | Status |
|-----------|-------|----------|--------|
| Follow-up sin banco | "IMOR de BBVA" → "¿y la cartera?" | Cartera de BBVA, sin clarification | [ ] |
| Ambigüedad resuelta | "ICAP de INVEX" → "capitalización" | ICAP de INVEX | [ ] |
| Sin contexto es ambiguo | Nueva conv → "capitalización de BBVA" | HARD_ASK: ¿ICAP o Market Cap? | [ ] |
| Query explícito no infiere | "IMOR de BBVA" → "cartera de SANTANDER" | Cartera de SANTANDER (no BBVA) | [ ] |

### AC-6: Logging y Observabilidad

| Log Event | Condición | Status |
|-----------|-----------|--------|
| `context_enriched` | Siempre que se enriquece | [ ] |
| `clarification.inferred_bank_from_context` | Banco inferido | [ ] |
| `clarification.ambiguity_resolved` | Ambigüedad resuelta | [ ] |
| `weaviate_ontology.resolved_by_category` | Weaviate desambiguó | [ ] |

---

## Métricas de Performance

| Métrica | Baseline | Target | Actual |
|---------|----------|--------|--------|
| Latencia context_enricher | N/A | < 50ms | [ ] |
| Cache hit rate (embeddings) | ~70% | > 80% | [ ] |
| Falsos positivos en follow-ups | ~40% | < 10% | [ ] |
| Resolución automática ambigüedad | 0% | > 70% | [ ] |

---

## Checklist de Validación Manual

### Escenario 1: Follow-up de Banco
```
1. Enviar: "IMOR de BBVA últimos 6 meses"
2. Verificar: muestra gráfica, logs muestran context guardado
3. Enviar: "¿y la cartera?"
4. Esperado: muestra cartera de BBVA (sin pedir banco)
5. Verificar logs:
   - "context_enriched" con is_followup=True
   - "clarification.inferred_bank_from_context" con banks=["BBVA"]
```
- [ ] Pasa

### Escenario 2: Capitalización en Contexto Regulatorio
```
1. Enviar: "ICAP de INVEX"
2. Verificar: muestra gráfica ICAP
3. Enviar: "¿cómo está su capitalización?"
4. Esperado: muestra ICAP (no Market Cap, no clarification)
5. Verificar logs:
   - "weaviate_ontology.resolved_by_category" con category=capital
   - "clarification.ambiguity_resolved" con resolved_to=ICAP
```
- [ ] Pasa

### Escenario 3: Capitalización sin Contexto
```
1. Nueva conversación (sin historial)
2. Enviar: "capitalización de BBVA"
3. Esperado: HARD_ASK con opciones ICAP y Market Cap
4. Verificar: mensaje de clarificación apropiado
```
- [ ] Pasa

### Escenario 4: Alta Similaridad
```
1. Enviar: "IMOR de SANTANDER"
2. Enviar: "morosidad" (muy similar a IMOR semánticamente)
3. Esperado: context_similarity alto, posible inferencia
4. Verificar: logs muestran similarity > 0.6
```
- [ ] Pasa

### Escenario 5: Query Explícito Override
```
1. Enviar: "IMOR de BBVA"
2. Enviar: "cartera de SANTANDER"
3. Esperado: Cartera de SANTANDER (no BBVA)
4. Verificar: banco explícito tiene prioridad sobre contexto
```
- [ ] Pasa

---

## Resultado Final

| Categoría | Passed | Failed | Total |
|-----------|--------|--------|-------|
| AC-1: Enriquecimiento | | | 4 |
| AC-2: Inferencia banco | | | 4 |
| AC-3: Ambigüedad | | | 5 |
| AC-4: Opciones | | | 3 |
| AC-5: E2E | | | 4 |
| AC-6: Logging | | | 4 |
| **Total** | | | **24** |

---

## Sign-off

- [ ] Todos los tests unitarios pasan
- [ ] Todos los tests E2E pasan
- [ ] Regression suite sin fallos
- [ ] Performance dentro de target
- [ ] Logs verificados en staging
- [ ] Code review aprobado
- [ ] QA sign-off

---

**Fecha de validación**: ____________________
**Validado por**: ____________________
