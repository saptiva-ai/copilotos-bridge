# Análisis de Gaps: BRD → PRD
## Bank Advisor v1.0/v1.1

**Fecha:** 27 de Diciembre de 2025
**Analista:** Claude Code
**Objetivo:** Identificar contradicciones y gaps entre Business Requirements (BRD) y Product Requirements (PRD)

---

## Resumen Ejecutivo

Se identificaron **12 gaps críticos** entre el BRD y PRD que deben resolverse antes del release. El BRD define la visión de negocio y requisitos estratégicos que **NO están completamente reflejados en el PRD técnico**.

**Riesgo:** El equipo de desarrollo puede construir un producto que funciona técnicamente pero NO cumple las expectativas de negocio ni los criterios de éxito definidos por stakeholders.

---

## Contradicciones Críticas (P0)

### 1. ❌ **Versión del Producto (CRÍTICO)**

| Documento | Versión Declarada | Ubicación |
|-----------|-------------------|-----------|
| BRD | "Bank Advisor V2 (v1.1)" | Línea 43, título |
| PRD | "Bank Advisor v1.0" | Línea 36, header |

**Impacto:** Confusión en comunicación con stakeholders y clientes. ¿Es V1.0 o V2 v1.1?

**Recomendación:**
- Si es la primera versión productiva → usar **v1.0** consistentemente
- Si es segunda versión mayor → usar **v2.0** o **v1.1** (no ambos)
- Actualizar BRD y PRD para que coincidan

---

### 2. ❌ **Usuarios Objetivo Contradictorios**

**BRD (línea 109-110):**
```
Incluye: Ejecutivos, directores de riesgo, tomadores de decisión
EXCLUYE: Analistas técnicos que requieren modelado avanzado
```

**PRD (línea 96-101):**
```
- C-Level: Dashboard ejecutivo, benchmarking
- Analistas Financieros: Queries detalladas, tendencias históricas ← CONTRADICE BRD
- Compliance/Reguladores: Validación de métricas
```

**Impacto:** El PRD diseña features para "Analistas Financieros" que el BRD explícitamente EXCLUYE del scope.

**Recomendación:**
- **Opción A:** Eliminar "Analistas Financieros" del PRD (alinearse con BRD)
- **Opción B:** Actualizar BRD para incluir analistas en scope (cambio de negocio)
- Decidir con stakeholders en reunión Go/No-Go

---

### 3. ❌ **Métricas de Éxito Incompletas**

| Métrica | BRD | PRD | ¿Alineado? |
|---------|-----|-----|------------|
| **North Star** | WAU (Weekly Active Users) | WAU ≥ 5 | ✅ Parcial |
| **TTI** | Time-To-Insight < 5s | ❌ NO EXISTE | ❌ MISSING |
| **Latencia** | "Latencia baja" (sin spec) | p50 < 2s | ⚠️ PRD más estricto |
| **Query Success Rate** | ❌ NO EXISTE | ≥ 85% | ⚠️ PRD añade métrica |
| **ARR** | USD 30k **por cliente** | $30k (sin aclarar) | ⚠️ Ambiguo |
| **Bancos cerrados** | > 3 bancos | ❌ NO EXISTE | ❌ MISSING |
| **NPS Score** | ❌ NO EXISTE | ≥ 7 | ⚠️ PRD añade métrica |

**Impacto:**
- **TTI missing:** BRD define TTI < 5s como métrica clave, PRD no la mide
- **Bancos cerrados missing:** BRD dice cerrar 3+ bancos, PRD no trackea esto
- **ARR ambiguo:** PRD no clarifica si $30k es total o por cliente

**Recomendación:**
1. Agregar TTI al PRD como métrica de performance (< 5s)
2. Agregar "Bancos cerrados" como métrica de ventas
3. Clarificar ARR: "$30k USD **por cliente**, objetivo de 3+ clientes = $90k+ total"

---

## Gaps de Contenido (P1)

### 4. ⚠️ **Funcionalidades Clave del BRD No Reflejadas en PRD**

**BRD (línea 209-222) define 7 features clave:**

| Feature BRD | Riesgo BRD | ¿En PRD? | Notas |
|-------------|------------|----------|-------|
| SLA / Seguridad / Compliance | Alto | ❌ NO | PRD no menciona compliance |
| Arquitectura multiagente | Medio | ✅ SÍ | Implícito en NL2SQL |
| **RAG CUB, Anexo 36 y Banxico** | Alto | ⚠️ PARCIAL | PRD solo dice "glosario bancario" |
| Visualizaciones benchmark | Bajo | ✅ SÍ | HU2, HU4 |
| Agent SQL | Bajo | ✅ SÍ | NL2SQL pipeline |
| Estructura de datos de catálogos | Alto | ❌ NO | No documentado en PRD |
| **Capa ontológica de datos** | Alto | ❌ NO | No documentado en PRD |

**Impacto:** PRD no documenta features de alto riesgo que son críticas según BRD:
- **RAG con Anexo 36 y Banxico:** BRD dice que es crítico, PRD solo menciona "glosario genérico"
- **Capa ontológica:** BRD dice Alto riesgo, PRD no lo menciona
- **Compliance/SLA:** BRD dice Alto riesgo, PRD no documenta requisitos de compliance

**Recomendación:**
1. Expandir sección RAG del PRD para incluir fuentes específicas:
   - CUB (Catálogo Único de Banxico)
   - Anexo 36 (CNBV)
   - Definiciones Banxico
2. Agregar sección "Compliance & Security Requirements" al PRD
3. Documentar la capa ontológica o declarar explícitamente si NO está en v1.0

---

### 5. ⚠️ **Casos de Uso BRD No Trazables a Historias de Usuario PRD**

**BRD define 5 casos de uso (línea 142-154):**

| # | Caso de Uso BRD | ¿Mapeado a HU PRD? | Notas |
|---|-----------------|---------------------|-------|
| CU1 | Consulta cualitativa CUB | ⚠️ Parcial (HU5) | HU5 es sobre "glosario", no específicamente CUB |
| CU2 | Benchmark competitivo | ✅ HU2 | Bien mapeado |
| CU3 | Consulta a cálculos/datos | ✅ HU1 | Bien mapeado |
| CU4 | Feedback de usuario | ❌ NO EXISTE | PRD no documenta feature de feedback |
| CU5 | UX de chat fluida | ⚠️ Parcial (HU3) | HU3 es sobre clarificación, no UX general |

**Impacto:**
- **CU4 (Feedback):** BRD define feedback como caso de uso crítico (mejora continua del sistema), PRD NO lo implementa
- **CU1 (CUB):** BRD enfatiza terminología CUB regulatoria, PRD habla de "glosario bancario" genérico

**Recomendación:**
1. Agregar HU7: "Sistema de Feedback de Usuario" (thumbs up/down + texto adicional)
2. Renombrar HU5 de "glosario bancario" a "Glosario CUB + Anexo 36"

---

### 6. ⚠️ **Fuera de Alcance No Documentado en PRD**

**BRD (línea 224-237) define explícitamente qué NO se hará:**

**No ahora:**
- Integración de nuevas fuentes de datos
- Ejecución de fórmulas
- Segregación por cliente, retención, "no entrenamiento con datos del cliente"

**Nunca (para esta versión):**
- Generación de fórmulas fuera de BD centralizada
- Visualizaciones no especificadas
- Generación de reportes automáticos

**PRD:** No documenta qué está fuera de alcance

**Impacto:** Sin documentación explícita de "out of scope", hay riesgo de scope creep o expectativas incorrectas de stakeholders.

**Recomendación:** Agregar sección "Fuera de Alcance v1.0" al PRD que copie del BRD.

---

### 7. ⚠️ **Demo Scripts del BRD No en PRD**

**BRD (línea 239-244) define 3 guiones de demo críticos:**

1. "¿Qué es X en CUB?" → definición oficial con fuente/tabla/fecha
2. "Compárame IMOR vs mercado / peers" → texto + gráfica + SQL trazable
3. "Explícame por qué subió/bajó y qué palancas hay" → interpretación con límites + links a cálculo

**PRD:** No menciona estos scripts de demo

**Impacto:** El equipo de desarrollo no sabe qué demos deben funcionar perfectamente para vender el producto.

**Recomendación:** Agregar sección "Demo Scripts (3 guiones que venden)" al PRD, copiando del BRD.

---

### 8. ⚠️ **Principios de Diseño No Documentados en PRD**

**BRD (línea 120-127) define 5 principios de diseño:**

1. **Precisión regulatoria por encima de creatividad** (no alucinar)
2. Latencia baja y experiencia conversacional fluida
3. **Explicabilidad de datos y cálculos**
4. Simplicidad para ejecutivos no técnicos
5. Feedback continuo del usuario para mejora del sistema

**PRD:** No documenta principios de diseño

**Impacto:** El equipo técnico toma decisiones de arquitectura sin conocer los principios guía del negocio. Riesgo de trade-offs incorrectos (ej: creatividad vs precisión).

**Recomendación:** Agregar sección "Principios de Diseño" al PRD al inicio, antes de las Historias de Usuario.

---

### 9. ⚠️ **Análisis Competitivo Missing en PRD**

**BRD (línea 187-202) define:**
- 4 competidores específicos: Arkham, Moody's Copilot, Dataiku, Cohere Compass
- Posicionamiento: "No somos 'otro chat con RAG'. Somos plataforma para industrias reguladas con trazabilidad completa"

**PRD:** No menciona competencia ni posicionamiento

**Impacto:** El equipo no entiende cómo diferenciarse de competidores. Riesgo de construir "otro chat con RAG" genérico.

**Recomendación:** Agregar sección "Análisis Competitivo y Posicionamiento" al PRD.

---

### 10. ⚠️ **RACI No Definido en PRD**

**BRD (línea 58-73) define claramente:**
- **Responsible:** Jaziel Flores (FDE, Saptiva)
- **Accountable:** Carlos Lara (Head of Product, Saptiva)
- **Consult:** Fernando Saavedra, Ronald Escalona
- **Informed:** Cristian Huertas, Omar Lozano, Gustavo Guevara

**PRD:** Solo menciona "Jaziel (Lead)" y "Dev 2" sin roles RACI completos

**Impacto:** No está claro quién aprueba decisiones críticas (Accountable) ni a quién consultar/informar.

**Recomendación:** Agregar tabla RACI al inicio del PRD copiando del BRD.

---

## Gaps de Validación (P1)

### 11. ⚠️ **Evidencia de Mercado No Reflejada en PRD**

**BRD (línea 93-106, 248-256) reconoce:**
- "No hay evidencia que valide la hipótesis más allá de la suposición del equipo de Bajaware"
- Necesidad de: 5-8 entrevistas, 2-3 champion quotes, cálculo de ROI
- Evidencia cuantitativa: 1 mes → 15 min, ahorro USD $1,600

**PRD:** No menciona necesidad de validación ni plan de entrevistas

**Impacto:** El PRD asume que el producto se venderá sin validar hipótesis con clientes potenciales.

**Recomendación:**
1. Agregar sección "Plan de Validación" al PRD
2. Incluir en Sprint 5 tarea: "Entrevistas con 3-5 buyer personas"

---

### 12. ⚠️ **Revisión Crítica del BRD No Incorporada**

**BRD (línea 248-256) incluye sección "Revisión crítica" que alerta sobre:**
- Multi-tenancy/segregación debe ser requisito de diseño (no "No ahora")
- Métricas de "trust" faltan (tasa de alucinación, errores de cálculo)
- Latencia necesita objetivos explícitos (p95/p99)
- Datos y actualización: falta SLA de actualización, cobertura, validación
- Benchmarks: falta especificar fuente (CNBV/Banxico), fecha de corte

**PRD:** No incorpora estas alertas críticas

**Impacto:** El PRD ignora riesgos identificados por el propio BRD.

**Recomendación:** Incorporar cada punto de la revisión crítica como:
- Requisito técnico (multi-tenancy como requirement)
- Métrica adicional (trust metrics)
- Especificación detallada (benchmarks con fuente explícita)

---

## Recomendaciones de Alineación

### Prioridad P0 (Crítico - Resolver antes de Sprint 1)

1. **✅ Unificar versión:** Decidir v1.0 o v1.1, actualizar ambos docs
2. **✅ Resolver contradicción de usuarios:** ¿Incluir o excluir analistas financieros?
3. **✅ Agregar métricas missing:** TTI, Bancos cerrados, clarificar ARR

### Prioridad P1 (Importante - Resolver durante Sprint 1-2)

4. **✅ Expandir sección RAG:** CUB + Anexo 36 + Banxico específicamente
5. **✅ Agregar HU de Feedback:** CU4 del BRD no está implementado
6. **✅ Documentar Out of Scope:** Copiar del BRD al PRD
7. **✅ Agregar Demo Scripts:** 3 guiones que venden
8. **✅ Agregar Principios de Diseño:** Al inicio del PRD
9. **✅ Agregar tabla RACI:** Copiar del BRD

### Prioridad P2 (Nice-to-have - Resolver en Sprint 3-4)

10. **✅ Agregar análisis competitivo:** Sección breve con 4 competidores
11. **✅ Plan de validación:** Entrevistas + champion quotes
12. **✅ Incorporar revisión crítica:** Trust metrics, multi-tenancy, SLAs

---

## Propuesta de Estructura Actualizada del PRD

```
# Bank Advisor v1.0 - PRD

## 1. Información del Proyecto
   - RACI (← AGREGAR del BRD)
   - Control de versión

## 2. Contexto de Negocio (← AGREGAR)
   - Problema (del BRD)
   - Propuesta de valor (del BRD)
   - Análisis competitivo (del BRD)

## 3. Principios de Diseño (← AGREGAR del BRD)

## 4. Requisitos del Producto
   - Usuarios objetivo (← CORREGIR contradicción)
   - Casos de uso (← MAPEAR a HUs)
   - Funcionalidades clave (← EXPANDIR con ontología, compliance)

## 5. Métricas de Éxito (← ACTUALIZAR)
   - North Star: WAU
   - TTI < 5s (← AGREGAR)
   - Query success rate ≥ 85%
   - Latencia p50 < 2s
   - Bancos cerrados > 3 (← AGREGAR)
   - ARR: $30k USD por cliente (← CLARIFICAR)

## 6. Historias de Usuario
   - HU1-HU6 (existentes)
   - HU7: Sistema de Feedback (← AGREGAR)

## 7. Roadmap de Ejecución
   - Sprint 1-5 (existente)

## 8. Fuera de Alcance (← AGREGAR del BRD)

## 9. Demo Scripts (← AGREGAR del BRD)

## 10. Plan de Validación (← AGREGAR)
   - Entrevistas con buyer personas
   - Champion quotes
   - Cálculo de ROI

## 11. Riesgos y Mitigación (existente)

## 12. Criterios Go/No-Go (existente)
```

---

## Siguiente Paso Recomendado

**Acción:** Reunión de alineación BRD-PRD con stakeholders clave:
- **Asistentes:** Jaziel Flores (R), Carlos Lara (A), Fernando Saavedra (C)
- **Duración:** 90 minutos
- **Objetivo:** Resolver las 3 contradicciones P0 y aprobar actualizaciones del PRD
- **Entregable:** PRD v1.2 alineado completamente con BRD

**Fecha sugerida:** Antes del 28 de diciembre (inicio de Sprint 1)

---

## Apéndice: Matriz de Trazabilidad BRD → PRD

| Requisito BRD | Sección BRD | ¿En PRD? | Ubicación PRD | Gap |
|---------------|-------------|----------|---------------|-----|
| Usuarios objetivo | §4 | ⚠️ | §1 PRD | Contradicción en analistas |
| Casos de uso (5) | §6 | ⚠️ | §3 Historias | CU4 feedback missing |
| Principios diseño | §5.2 | ❌ | - | Missing |
| Funcionalidades clave | §9 | ⚠️ | §2 Entregables | Ontología missing |
| North Star: WAU | §7.1 | ✅ | §1 Métricas | OK |
| TTI < 5s | §7.2 | ❌ | - | Missing |
| ARR $30k/cliente | §7.2 | ⚠️ | §1 | Ambiguo |
| Bancos > 3 | §7.2 | ❌ | - | Missing |
| Demo scripts | §10 | ❌ | - | Missing |
| Out of scope | §11 | ❌ | - | Missing |
| Competencia | §8 | ❌ | - | Missing |
| RACI | §2 | ⚠️ | Header | Incompleto |

**Total gaps:** 12
**Gaps críticos (P0):** 3
**Gaps importantes (P1):** 9

---

**Documento generado el:** 2025-12-27
**Próxima revisión:** Post-alineación con stakeholders
