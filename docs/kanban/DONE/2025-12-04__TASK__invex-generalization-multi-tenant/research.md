# Research: Generalización BankAdvisor - Análisis de Acoplamiento INVEX

> **Fecha de investigación:** 2026-01-09
> **Método:** Búsqueda exhaustiva en codebase + análisis de flujos
> **Herramientas:** grep, ripgrep, análisis estático de código

---

## 1. Metodología de investigación

### 1.1 Patrones de búsqueda utilizados

```bash
# Búsqueda principal de INVEX
rg -n "INVEX|Invex|invex" .

# Búsqueda de strings relacionados
rg -n "Datos específicos|datos específicos" .

# Búsqueda de lógica de default
rg -n "defaultBank|default_bank|banco.*default|default.*banco" . -i

# Búsqueda de agregación SISTEMA
rg -n "SISTEMA.*SUM|Sistema.*total|aggregate.*SISTEMA|PE_TOTAL.*SISTEMA" . -i

# Búsqueda de prompts
rg -n "system.*prompt|SYSTEM_PROMPT|developer.*prompt|prompt.*template" . -i

# Búsqueda de configuración runtime
rg -n "primary_bank|apply_bank_default|RuntimeConfig" .
```

### 1.2 Categorización de hallazgos

Cada ocurrencia fue categorizada en:

| Categoría | Código | Descripción | Severidad típica |
|-----------|--------|-------------|------------------|
| UI Copy | (a) | Texto visible en frontend | Alta |
| Default Logic | (b) | Lógica que asume INVEX | Alta |
| RAG/KB | (c) | Knowledge base o embeddings | Media |
| Dataset/SQL | (d) | Datos o queries | Media |
| Routing/Tenant | (e) | Contexto de tenant/cliente | Alta |
| Test/Example | (f) | Código de prueba | Baja |
| Infra/Config | (g) | Nombres de proyecto | Baja |

---

## 2. Mapa exhaustivo de ocurrencias

### 2.1 Categoría (a): UI Copy - Frontend

#### Hallazgo 1: BankAdvisorHints.tsx (CRÍTICO)

**Ubicación:** `apps/web/src/components/chat/BankAdvisorHints.tsx:107-112`

**Código encontrado:**
```typescript
export const DEFAULT_BANK_ADVISOR_QUESTIONS = [
  "¿Cómo ha evolucionado la cartera vencida de INVEX en los últimos 12 meses?",
  "Compárame la cartera vencida de INVEX contra el promedio del sistema bancario.",
  "¿Cuál es la tendencia del IMOR de INVEX en 2024?",
  "Muéstrame las principales métricas de riesgo de crédito para INVEX.",
  "¿Qué tan concentrada está la cartera comercial de INVEX en 2024?",
];
```

**Análisis:**
- **5 de 5 preguntas** mencionan "INVEX" explícitamente
- Son las primeras sugerencias que ve el usuario
- No hay forma de cambiar el banco desde la UI
- Impacto directo en percepción del producto

**Flujo afectado:**
```
Usuario abre chat
       ↓
[BankAdvisorHints renderiza]
       ↓
DEFAULT_BANK_ADVISOR_QUESTIONS se muestra
       ↓
Usuario ve "INVEX" 5 veces ← PROBLEMA
```

---

### 2.2 Categoría (b): Default Logic - Backend

#### Hallazgo 2: runtime_config.py - primary_bank default

**Ubicación:** `plugins/bank-advisor-private/src/bankadvisor/runtime_config.py:77`

**Código encontrado:**
```python
@property
def primary_bank(self) -> str:
    """Get the primary bank (default for queries without bank)."""
    return os.environ.get("PRIMARY_BANK") or self._get("banks", "primary", default="INVEX")
```

**Análisis:**
- Si no hay variable de entorno `PRIMARY_BANK`
- Y no hay config en `bankadvisor.yaml` bajo `banks.primary`
- El default hardcodeado es `"INVEX"`

**Cadena de impacto:**
```
Usuario pregunta "Dame el IMOR"
       ↓
QuerySpecParser no detecta banco
       ↓
apply_bank_default=True (línea 153)
       ↓
Se usa runtime_config.primary_bank
       ↓
primary_bank="INVEX" (hardcoded)
       ↓
Respuesta habla de INVEX ← PROBLEMA
```

---

#### Hallazgo 3: query_spec_parser.py - BANK_ALIASES

**Ubicación:** `plugins/bank-advisor-private/src/bankadvisor/services/query_spec_parser.py:49-56`

**Código encontrado:**
```python
BANK_ALIASES: Dict[str, str] = {
    "invex": "INVEX",
    "banco invex": "INVEX",
    # INVEX inference: "mi", "del banco", "nuestro" imply INVEX in this product
    "mi banco": "INVEX",
    "del banco": "INVEX",
    "nuestro banco": "INVEX",
    "nuestro": "INVEX",
    "sistema": "SISTEMA",
    ...
}
```

**Análisis:**
- Los pronombres posesivos ("mi", "nuestro", "del banco") mapean directamente a INVEX
- Esto asume que el producto es **exclusivamente** para INVEX
- Impide uso multi-tenant donde "mi banco" podría ser BBVA, Santander, etc.

**Casos problemáticos:**

| Input del usuario | Banco inferido | Debería ser |
|-------------------|----------------|-------------|
| "mi IMOR" | INVEX | ❓ Preguntar |
| "nuestro ICAP" | INVEX | ❓ Preguntar |
| "cartera del banco" | INVEX | ❓ Preguntar |
| "mi PDM" | INVEX | ❓ Preguntar |

---

#### Hallazgo 4: query_spec_parser.py - Regex "mi" + métrica

**Ubicación:** `plugins/bank-advisor-private/src/bankadvisor/services/query_spec_parser.py:1073-1082`

**Código encontrado:**
```python
def _extract_banks_heuristic(self, user_query: str) -> List[Optional[str]]:
    query_lower = user_query.lower()
    found_banks = []

    # Special case: "mi" + metric pattern implies INVEX (possessive inference)
    mi_pattern = r'\bmi\s+(imor|icor|icap|cartera|pdm|market\s*share|morosidad|cobertura|capitalización|capitalizacion|reservas|provisiones)'
    if re.search(mi_pattern, query_lower):
        found_banks.append("INVEX")
        logger.debug("query_spec_parser.mi_inference", query=user_query, inferred="INVEX")
```

**Análisis:**
- El regex captura cualquier "mi" + nombre de métrica
- Automáticamente infiere INVEX sin preguntar
- Más agresivo que el diccionario de aliases

**Métricas afectadas:** imor, icor, icap, cartera, pdm, market share, morosidad, cobertura, capitalización, reservas, provisiones

---

#### Hallazgo 5: apply_bank_default = True

**Ubicación:** `plugins/bank-advisor-private/src/bankadvisor/runtime_config.py:150-153`

**Código encontrado:**
```python
@property
def apply_bank_default(self) -> bool:
    """Whether to auto-add primary bank when metric+date but no bank."""
    return self._get("defaults", "apply_bank_default", default=True)
```

**Análisis:**
- Cuando el usuario especifica métrica + fecha pero NO banco
- El sistema automáticamente agrega `primary_bank` (que es INVEX)
- Esto evita pedir clarificación al usuario

**Flujo:**
```
Query: "IMOR últimos 6 meses"
       ↓
Parsed: {metric: IMOR, months: 6, bank: null}
       ↓
apply_bank_default=True
       ↓
Final: {metric: IMOR, months: 6, bank: "INVEX"}
       ↓
SQL: WHERE banco_norm = 'INVEX' ← Sin que usuario lo pidiera
```

---

### 2.3 Categoría (c): Métricas específicas de INVEX

#### Hallazgo 6: tasa_invex_consumo

**Ubicación:** `plugins/bank-advisor-private/config/synonyms.yaml:365-378`

**Código encontrado:**
```yaml
tasa_invex_consumo:
  display_name: "Tasa Efectiva INVEX Consumo"
  column: "tasa_invex_consumo"
  type: "percentage"
  aliases:
    - "tasa invex consumo"
    - "te invex"
    - "tasa efectiva invex"
    - "efectiva invex consumo"
```

**Análisis:**
- Esta es una métrica **real** de la CNBV (dato regulatorio)
- No es un hardcode problemático, es un dato del universo de datos
- Se debe mantener como métrica válida
- **NO requiere cambio**

---

### 2.4 Categoría (d): Bug SISTEMA (BUG-10)

#### Hallazgo 7: SISTEMA usa promedio, no suma

**Ubicación:** `plugins/bank-advisor-private/config/synonyms.yaml:35-37, 190-192`

**Código encontrado:**
```yaml
icap_total:
  # BUG-10: SISTEMA uses simple average (mean) for ICAP, not sum
  sistema_aggregation: "mean"
  sistema_note: "Para SISTEMA, el ICAP representa el promedio simple de todos los bancos del sistema"

tda_cartera_total:
  # BUG-10: SISTEMA uses weighted average for TDA
  sistema_aggregation: "weighted_avg"
  sistema_note: "Para SISTEMA, la TDA representa el promedio ponderado por cartera de todos los bancos"
```

**Análisis:**
- Para métricas tipo **ratio** (ICAP, IMOR, ICOR, TDA), SISTEMA es promedio
- Para métricas tipo **currency** (cartera_total, reservas), SISTEMA es suma
- El usuario no ve esta distinción y se confunde

**Problema visual:**
```
"Compara ICAP de INVEX vs Sistema"

Resultado:
  INVEX:   15.72%
  SISTEMA: 14.89%  ← Usuario: "¿Cómo puede ser menor?"

Explicación que falta:
  "SISTEMA representa el promedio de todos los bancos"
```

---

### 2.5 Categoría (e): Perfiles de tenant

#### Hallazgo 8: invex.yaml profile

**Ubicación:** `plugins/bank-advisor-private/config/profiles/invex.yaml`

**Código encontrado:**
```yaml
banks:
  primary: "INVEX"

defaults:
  apply_bank_default: true
```

**Análisis:**
- El perfil de INVEX es correcto para **deploys de INVEX**
- El problema es que es el único perfil y se usa como default global
- Necesita existir un "perfil neutral" o "multi-tenant"

---

### 2.6 Categoría (f): Tests y ejemplos

#### Hallazgo 9: Tests con INVEX hardcodeado

**Ubicaciones:**
- `tests/utils/test_raw_output.py:12-32`
- `tests/e2e/conversation/test_context_flow.py:99-117`
- `tests/fixtures/happy_path/expected_results.json`

**Análisis:**
- Los tests usan "INVEX" como banco de ejemplo
- Esto es **aceptable** - son tests que prueban funcionalidad
- El banco se menciona explícitamente en el query del test
- **NO requiere cambio** (el test seguirá funcionando)

---

### 2.7 Categoría (g): Infraestructura

#### Hallazgo 10: Nombres de proyecto

**Ubicaciones:**
- `Makefile:39` - `PROJECT_NAME := octavios-chat-bajaware_invex`
- `envs/.env.prod.example` - Referencias a dominio invex

**Análisis:**
- Son nombres de proyecto/infraestructura
- No afectan comportamiento del producto
- Cambiarlos requeriría renombrar repo, docker images, etc.
- **Bajo impacto, alto costo** - no recomendado cambiar

---

## 3. Análisis de flujos afectados

### 3.1 Flujo: Usuario nuevo abre chat

```
┌─────────────────────────────────────────────────────────────┐
│                    FLUJO ACTUAL (PROBLEMÁTICO)               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [Usuario abre /chat]                                        │
│         │                                                    │
│         ▼                                                    │
│  [BankAdvisorHints.tsx]                                      │
│         │                                                    │
│         ▼                                                    │
│  DEFAULT_BANK_ADVISOR_QUESTIONS                              │
│  ┌──────────────────────────────────────────┐               │
│  │ "¿Cartera vencida de INVEX...?"          │               │
│  │ "Compara INVEX contra sistema..."         │               │
│  │ "IMOR de INVEX en 2024..."                │ ← 5x INVEX    │
│  │ "Métricas de riesgo de INVEX..."          │               │
│  │ "Cartera comercial de INVEX..."           │               │
│  └──────────────────────────────────────────┘               │
│         │                                                    │
│         ▼                                                    │
│  [Usuario ve solo opciones INVEX]                            │
│         │                                                    │
│         ▼                                                    │
│  [Percepción: "Este producto es de INVEX"]                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Flujo: Usuario pregunta sin especificar banco

```
┌─────────────────────────────────────────────────────────────┐
│                    FLUJO ACTUAL (PROBLEMÁTICO)               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [Usuario: "Dame el IMOR de los últimos 3 meses"]            │
│         │                                                    │
│         ▼                                                    │
│  [QuerySpecParser._extract_banks_heuristic()]                │
│         │                                                    │
│         ▼                                                    │
│  banks = [] (ningún banco detectado)                         │
│         │                                                    │
│         ▼                                                    │
│  [apply_bank_default = True]                                 │
│         │                                                    │
│         ▼                                                    │
│  banks = ["INVEX"] ← SE AGREGA SIN PREGUNTAR                │
│         │                                                    │
│         ▼                                                    │
│  [SQL: WHERE banco_norm = 'INVEX']                           │
│         │                                                    │
│         ▼                                                    │
│  [Respuesta: "El IMOR de INVEX..."]                          │
│         │                                                    │
│         ▼                                                    │
│  [Usuario confundido: "¿Por qué INVEX?"]                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Flujo: Usuario usa pronombre posesivo

```
┌─────────────────────────────────────────────────────────────┐
│                    FLUJO ACTUAL (PROBLEMÁTICO)               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [Usuario (de BBVA): "¿Cuál es mi IMOR?"]                    │
│         │                                                    │
│         ▼                                                    │
│  [QuerySpecParser._extract_banks_heuristic()]                │
│         │                                                    │
│         ▼                                                    │
│  [Regex: r'\bmi\s+(imor|...)']                               │
│         │                                                    │
│         ▼                                                    │
│  MATCH! → banks.append("INVEX") ← ASUME INVEX               │
│         │                                                    │
│         ▼                                                    │
│  [SQL: WHERE banco_norm = 'INVEX']                           │
│         │                                                    │
│         ▼                                                    │
│  [Respuesta: "Tu IMOR (INVEX) es 2.3%"]                      │
│         │                                                    │
│         ▼                                                    │
│  [Usuario BBVA: "¡Eso no es mi banco!"]                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Matriz de dependencias

```
┌────────────────────────────────────────────────────────────────────┐
│                      DEPENDENCIAS IDENTIFICADAS                     │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  BankAdvisorHints.tsx ──────┐                                       │
│         │                   │                                       │
│         │                   ▼                                       │
│         │         [Preguntas sugeridas]                             │
│         │                   │                                       │
│         ▼                   │                                       │
│  [Usuario selecciona]       │                                       │
│         │                   │                                       │
│         ▼                   ▼                                       │
│  query_spec_parser.py ◄─────────────────────────────────────────┐  │
│         │                                                        │  │
│         ├── BANK_ALIASES (diccionario)                           │  │
│         │                                                        │  │
│         ├── _extract_banks_heuristic (regex)                     │  │
│         │                                                        │  │
│         └── apply_bank_default flag ◄───── runtime_config.py     │  │
│                    │                              │               │  │
│                    ▼                              ▼               │  │
│         [Banco determinado]              [primary_bank]          │  │
│                    │                              │               │  │
│                    └──────────────┬───────────────┘               │  │
│                                   │                               │  │
│                                   ▼                               │  │
│                         [SQL generado]                            │  │
│                                   │                               │  │
│                                   ▼                               │  │
│                         [Respuesta final]                         │  │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 5. Conclusiones de la investigación

### 5.1 Resumen de hallazgos críticos

| # | Hallazgo | Severidad | Requiere cambio |
|---|----------|-----------|-----------------|
| 1 | DEFAULT_BANK_ADVISOR_QUESTIONS hardcodeado | **ALTA** | ✅ SÍ |
| 2 | primary_bank default "INVEX" | **ALTA** | ✅ SÍ |
| 3 | BANK_ALIASES con posesivos → INVEX | **ALTA** | ✅ SÍ |
| 4 | Regex "mi" + métrica → INVEX | **ALTA** | ✅ SÍ |
| 5 | apply_bank_default = True | **ALTA** | ✅ SÍ |
| 6 | tasa_invex_consumo (métrica CNBV) | BAJA | ❌ NO |
| 7 | SISTEMA promedio no documentado | MEDIA | ✅ SÍ |
| 8 | invex.yaml profile | MEDIA | ⚠️ PRESERVAR |
| 9 | Tests con INVEX | BAJA | ❌ NO |
| 10 | Nombres de proyecto | BAJA | ❌ NO |

### 5.2 Riesgo de no actuar

| Riesgo | Probabilidad | Impacto | Resultado si no se corrige |
|--------|--------------|---------|---------------------------|
| Bloqueo de ventas | Alta | Alto | No se pueden hacer demos a otros bancos |
| Pérdida de confianza | Alta | Alto | Usuario ve datos de banco equivocado |
| Costo de soporte | Media | Medio | Parches manuales por cliente |
| Percepción de producto | Alta | Medio | "Es herramienta interna de INVEX" |

### 5.3 Recomendación

**PRIORIDAD 1 (Blocker):** Corregir hallazgos 1-5
**PRIORIDAD 2 (Should):** Documentar hallazgo 7 (SISTEMA)
**PRIORIDAD 3 (Won't):** No cambiar hallazgos 6, 8-10

---

## 6. Próximos pasos

Ver `plan.md` para el plan de implementación detallado.
