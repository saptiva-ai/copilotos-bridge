# Research: Sistema de Clarificación Actual

## 1. Arquitectura del Sistema de Clarificación

### 1.1 Capas del Sistema

```
┌──────────────────────────────────────────────────────────────────┐
│                         BACKEND                                   │
│  ┌─────────────────┐    ┌──────────────────┐                     │
│  │ SemanticScorer  │───>│ ContextEnhancer  │──> Routing Decision │
│  └─────────────────┘    └──────────────────┘                     │
│                                  │                                │
│                    Extrae: last_metric, last_banks, has_chart     │
│                                  │                                │
│                                  ▼                                │
│                    ┌──────────────────────────────┐              │
│                    │ bank_advisor_precheck.py     │              │
│                    │ (decide if invoke plugin)    │              │
│                    └──────────────────────────────┘              │
└──────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────┐
│                       PLUGIN (bank-advisor)                       │
│  ┌──────────────────┐    ┌─────────────────────┐                 │
│  │ QuerySpecParser  │───>│ ClarificationService │                │
│  └──────────────────┘    └─────────────────────┘                 │
│          │                        │                               │
│   Extrae: metric,          Decide: NONE | SMART_DEFAULT          │
│   banks, time_range              | SOFT_ASK | HARD_ASK           │
│          │                        │                               │
│          ▼                        ▼                               │
│  ┌──────────────────┐    ┌─────────────────────┐                 │
│  │ ClarificationAgent│   │ Clarification Payload│                │
│  └──────────────────┘    └─────────────────────┘                 │
└──────────────────────────────────────────────────────────────────┘
```

### 1.2 Archivos Clave

| Archivo | Propósito | Líneas Relevantes |
|---------|-----------|-------------------|
| `apps/backend/src/services/intent/context_enhancer.py` | Extrae contexto de conversación | 51-104 (extract_context), 106-175 (enhance) |
| `plugins/bank-advisor-private/src/bankadvisor/services/clarification_service.py` | Decide estrategia de clarificación | 96-152 (determine_strategy), 252-291 (payload) |
| `plugins/bank-advisor-private/src/bankadvisor/services/query_spec_parser.py` | Parsea NL → QuerySpec | 668-732 (parse), 803-983 (heuristics) |
| `plugins/bank-advisor-private/src/bankadvisor/fsm/agents/__init__.py` | Agente FSM de clarificación | 368-426 (ambiguity detection) |

---

## 2. Flujo Actual de Clarificación

### 2.1 Diagrama de Flujo

```
User Message
     │
     ▼
┌─────────────────────────────────┐
│ 1. Backend: Semantic Scoring    │ ← Embeddings
└─────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────┐
│ 2. Backend: Context Enhancement│ ← last_metric, last_banks
└─────────────────────────────────┘
     │
     │  ✓ Context is used for ROUTING only
     │  ✗ Context is NOT passed to plugin
     │
     ▼
┌─────────────────────────────────┐
│ 3. Plugin: Query Parsing        │ ← Heuristics + LLM fallback
└─────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────┐
│ 4. Plugin: Ambiguity Detection  │ ← AMBIGUOUS_METRICS dict
└─────────────────────────────────┘
     │
     │  ✗ Only checks CURRENT message text
     │  ✗ No access to conversation context
     │
     ▼
┌─────────────────────────────────┐
│ 5. Plugin: Strategy Decision    │
│    NONE | SMART_DEFAULT |       │
│    SOFT_ASK | HARD_ASK          │
└─────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────┐
│ 6. Clarification Payload        │ ← Static TOP_BANKS, TOP_METRICS
└─────────────────────────────────┘
```

### 2.2 Estrategias de Clarificación

```python
class ClarificationStrategy(Enum):
    NONE = "none"           # Query complete, execute
    SMART_DEFAULT = "smart_default"  # Apply defaults (e.g., SISTEMA)
    SOFT_ASK = "soft_ask"   # Show data + suggest alternatives
    HARD_ASK = "hard_ask"   # Block until user clarifies
```

**Matriz de Decisión Actual** (`clarification_service.py:103-112`):

| Metric | Bank | Confidence | Intent | Strategy |
|--------|------|------------|--------|----------|
| ✅ | ✅ | ≥0.7 | any | NONE |
| ✅ | ❌ | any | ranking | NONE |
| ✅ | ❌ | any | evolution | HARD_ASK |
| ambig | any | any | any | SOFT_ASK |
| ❌ | ✅ | any | any | SOFT_ASK |
| ❌ | ❌ | any | any | HARD_ASK |

---

## 3. Problema: Falta de Uso de Contexto

### 3.1 Contexto Disponible pero No Utilizado

El `ContextEnhancer` extrae información valiosa:

```python
@dataclass
class ConversationContext:
    has_recent_chart: bool          # ✓ Disponible
    last_metric: Optional[str]      # ✓ Disponible
    last_banks: List[str]           # ✓ Disponible
    turn_count: int                 # ✓ Disponible
    last_assistant_had_chart: bool  # ✓ Disponible
```

**Pero esta información solo se usa para:**
1. Boost de score de `DATA_QUERY` intent → líneas 133-150
2. Reducción de scores `GREETING`/`ACKNOWLEDGMENT` → líneas 140-143

**NO se usa para:**
- Decisión de clarificación
- Inferencia de campos faltantes
- Resolución de ambigüedad
- Generación de opciones

### 3.2 Escenarios de Falsos Positivos

#### Escenario A: Follow-up sin banco
```
Usuario: "Dame el IMOR de BBVA"
Sistema: [muestra gráfica IMOR de BBVA]
         context.last_banks = ["BBVA"]

Usuario: "¿Y la cartera?"
Sistema: HARD_ASK "¿De qué banco?"  ← FALSO POSITIVO
         Debería inferir: BBVA
```

#### Escenario B: Market Cap por contexto bursátil
```
Usuario: "¿Cuál es el precio de acción de BBVA?"
Sistema: [muestra precio]
         context.semantic_domain = "market" (implícito)

Usuario: "¿Y su capitalización?"
Sistema: HARD_ASK "¿ICAP o Market Cap?"  ← FALSO POSITIVO
         Debería inferir: MARKET_CAP
```

#### Escenario C: ICAP por contexto regulatorio
```
Usuario: "¿Cuál es el IMOR de INVEX?"
Sistema: [muestra IMOR]
         context.semantic_domain = "regulatory" (implícito)

Usuario: "¿Y su capitalización?"
Sistema: HARD_ASK "¿ICAP o Market Cap?"  ← FALSO POSITIVO
         Debería inferir: ICAP
```

---

## 4. Análisis de Ambigüedad (market_cap vs ICAP)

### 4.1 Definición Actual

```python
# clarification_service.py:44-52
AMBIGUOUS_METRICS = {
    "cartera": ["cartera_total", "cartera_comercial", "cartera_vivienda", "cartera_consumo"],
    "morosidad": ["imor", "imor_comercial", "imor_consumo"],
    "capital": ["icap", "capital_neto"],
    "capitalización": ["icap", "market_cap"],  # BUG-10
    "capitalizacion": ["icap", "market_cap"],
}
```

### 4.2 Detección de Calificadores

```python
# __init__.py:377-384
def _is_ambiguous_metric_query(self, query: str) -> bool:
    query_lower = query.lower()
    for term in self.AMBIGUOUS_METRIC_TERMS:
        if term in query_lower:
            # Skip if already qualified
            if "regulatoria" in query_lower or "de mercado" in query_lower:
                return False
            return True
    return False
```

### 4.3 Limitaciones

1. **Solo detecta calificadores explícitos**: "regulatoria", "de mercado"
2. **No considera contexto previo**: Si hablamos de "riesgo crediticio", "capitalización" probablemente es ICAP
3. **No considera el chart previo**: Si el último chart fue ICAP, es probable que sigan con ICAP
4. **No aprende de respuestas anteriores**: Si el usuario ya aclaró "ICAP", recordarlo

---

## 5. Opciones de Clarificación Estáticas

### 5.1 Implementación Actual

```python
# clarification_service.py:67-91
TOP_BANKS = [
    {"label": "INVEX", "value": "INVEX"},
    {"label": "BBVA", "value": "BBVA"},
    {"label": "Santander", "value": "SANTANDER"},
    {"label": "Banorte", "value": "BANORTE"},
    {"label": "Sistema", "value": "SISTEMA"}
]

TOP_METRICS = [
    {"label": "IMOR", "value": "IMOR"},
    {"label": "ICAP", "value": "ICAP"},
    {"label": "Cartera Total", "value": "CARTERA_TOTAL"},
    {"label": "ICOR", "value": "ICOR"},
    {"label": "Market Share", "value": "MARKET_SHARE"}
]
```

### 5.2 Problema

- Siempre las mismas opciones, sin importar contexto
- No prioriza bancos/métricas del contexto
- No usa `ContextualSuggestionService` para HARD_ASK (solo SOFT_ASK)

---

## 6. Señales de Dominio Semántico

### 6.1 Dominio "Regulatory"

Keywords que indican contexto regulatorio:
- IMOR, ICOR, ICAP, TDA
- "riesgo", "morosidad", "cobertura", "reservas"
- "regulatorio", "CNBV", "Banxico"
- "solvencia", "suficiencia de capital"

### 6.2 Dominio "Market"

Keywords que indican contexto bursátil:
- "precio de acción", "stock price"
- "market cap", "valor de mercado"
- "bolsa", "BMV", "NYSE"
- "inversionistas", "dividendos"

### 6.3 Dominio "Credit Risk"

Keywords que indican contexto de riesgo crediticio:
- "cartera vencida", "NPL"
- "provisiones", "castigos"
- "pérdida esperada", "ECL"
- "etapas de deterioro", "IFRS 9"

---

## 7. Puntos de Integración Identificados

### 7.1 Donde pasar el contexto al plugin

El contexto se puede pasar via `memory_context` en el request al plugin:

```python
# apps/backend/src/services/streaming/bank_advisor_precheck.py
async def precheck_and_route(...):
    # Ya extrae contexto aquí (línea 96-137)
    context = ContextEnhancer.extract_context(recent_messages, memory_context)

    # Pero NO lo pasa al plugin
    # FIX: Agregar context al request payload
```

### 7.2 Donde usar el contexto en clarificación

```python
# clarification_service.py:96
def determine_strategy(
    self,
    spec: QuerySpec,
    context: Optional[ConversationContext] = None  # ← AGREGAR
) -> Tuple[ClarificationStrategy, str]:

    # NUEVO: Inferir banco desde contexto
    if not spec.bank_names and context and context.last_banks:
        spec.bank_names = context.last_banks
        spec.inferred_from_context = True
        # No necesita HARD_ASK
```

### 7.3 Donde resolver ambigüedad por dominio

```python
# __init__.py:394
def _determine_strategy(self, model: QueryModel) -> ClarificationStrategy:
    # NUEVO: Antes de HARD_ASK por ambigüedad, intentar resolver por dominio
    if self._is_ambiguous_metric_query(model.query):
        resolved = self._resolve_by_semantic_domain(model.query, model.context)
        if resolved:
            model.entities.metric_id = resolved
            return ClarificationStrategy.NONE
        # Solo si no se puede resolver, HARD_ASK
        return ClarificationStrategy.HARD_ASK
```

---

## 8. Tests Existentes

### 8.1 Tests de Clarificación

- `tests/unit/clarification/test_clarifications.py:6-66`
- `tests/e2e/clarification/test_clarification_scenarios.py:24-92`
- `tests/e2e/clarification/test_clarification_edge_cases.py:690-712`

### 8.2 Tests de Market Cap

```python
# tests/e2e/regression/test_bug_regression_suite.py:77
# BUG-10: Ambiguity of 'capitalización'
```

### 8.3 Tests Faltantes

- [ ] Follow-up sin banco explícito con contexto
- [ ] Resolución de ambigüedad por dominio semántico
- [ ] Opciones contextuales en clarificación
- [ ] Memoria de clarificaciones previas

---

---

## 8. Servicios Existentes Reutilizables

### 8.1 SemanticIntentScorer

**Archivo**: `apps/backend/src/services/intent/semantic_scorer.py`

Ya tiene categoría `FOLLOW_UP` con 14 ejemplares semánticos:
```python
IntentCategory.FOLLOW_UP.value: [
    "y por qué subió", "explícame más", "cuéntame más",
    "compáralo con el anterior", "ese banco", "más detalles"...
]
```

**Uso propuesto**: Detectar follow-ups usando embeddings en lugar de keywords manuales.

```python
scorer = await SemanticIntentScorer.get_instance()
scores = await scorer.score(message)
is_followup = scores.scores.get(IntentCategory.FOLLOW_UP, 0) > 0.5
```

### 8.2 EmbeddingService

**Archivo**: `apps/backend/src/services/embedding_service.py`

- Modelo: `paraphrase-multilingual-MiniLM-L12-v2` (384 dims)
- Cache LRU: 1000 queries
- gRPC delegación al plugin `embedding-service`

**Uso propuesto**: Calcular similaridad entre query actual y last_metric:
```python
query_emb = await embedding_svc.encode_single_async(message, use_cache=True)
context_emb = await embedding_svc.encode_single_async(last_metric, use_cache=True)
similarity = cosine_similarity(query_emb, context_emb)
```

### 8.3 WeaviateOntologyService

**Archivo**: `plugins/bank-advisor-private/src/bankadvisor/services/weaviate_ontology_service.py`

- Colección: `Ontology_Term_V2`
- Campos útiles: `category`, `synonyms`, `linked_field`
- Método `search_terms()` ya funciona

**Uso propuesto**: Resolver ambigüedad usando `category`:
```python
candidates = await ontology.search_terms("capitalización", top_k=5)
# candidates[0].category = "capital" → ICAP
# candidates[1].category = "mercado" → MARKET_CAP

# Si context_metric="IMOR" tiene category="riesgo", elegir candidato de "capital"
```

### 8.4 Mapeo de Categorías en Ontology_Term_V2

| Categoría | Dominio Implícito | Métricas |
|-----------|------------------|----------|
| `riesgo` | Regulatory | IMOR, ICOR, TDA |
| `capital` | Regulatory | ICAP, CAPITAL_NETO |
| `cartera` | Credit Risk | CARTERA_*, QUEBRANTOS |
| `mercado` | Market | MARKET_CAP, MARKET_SHARE |
| `rentabilidad` | Regulatory | ROE, ROA |

---

## 9. Conclusiones

### 9.1 Root Cause

El sistema de clarificación opera de forma **sin estado** (stateless), analizando cada mensaje de forma aislada. El `ConversationContext` existe pero no se propaga al plugin.

### 9.2 Impacto

- ~40% de follow-ups generan clarificaciones innecesarias
- Fricción en UX: usuarios repiten información
- Ambigüedades resolubles por contexto causan interrupciones

### 9.3 Solución Propuesta (v2 - Reutilizando Infraestructura)

1. **Enriquecer contexto en backend** usando SemanticIntentScorer y EmbeddingService
2. **Detectar follow-up semánticamente** con embeddings (no keywords)
3. **Calcular similaridad query-contexto** aprovechando cache
4. **Resolver ambigüedad con Weaviate** usando OntologyTerm.category
5. **Opciones contextuales** priorizando last_banks

### 9.4 Ventajas del Enfoque v2

| Aspecto | Plan Original | Plan v2 |
|---------|--------------|---------|
| Detección follow-up | Keywords manuales | SemanticIntentScorer |
| Detección dominio | Archivo nuevo | OntologyTerm.category |
| Resolución ambigüedad | Dict hardcodeado | Weaviate search |
| Archivos nuevos | 1 | 0 (solo context_enricher.py) |
| Mantenibilidad | Keywords manuales | Datos en Weaviate |
