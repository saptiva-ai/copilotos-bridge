# BRD - Bank Advisor V2 (v1.1)

> **Versión:** 1.1
> **Fecha de edición:** 15 de diciembre de 2025

## Responsables (RACI)

- **Responsible (R):** Jaziel Flores - Forward Deployed Engineer, Saptiva
- **Accountable (A):** Carlos Lara - Head of Product, Saptiva
- **Consult (C):**
  - Fernando Saavedra - Product Director, Bajaware
  - Ronald Escalona - SVP Engineering, Saptiva
- **Informed (I):**
  - Cristian Huertas - CRO, Saptiva
  - Omar Lozano - CEO, Bajaware
  - Gustavo Guevara - Co-Owner, Bajaware

---

## 1. Resumen Ejecutivo

Bank Advisor V2 (v1.1) es un copiloto de IA para ejecutivos de banca múltiple que permite obtener datos, visualizaciones e interpretaciones en tiempo real mediante lenguaje natural.

El producto elimina la dependencia de equipos especializados de data para consultas operativas y estratégicas. Está diseñado para acelerar la toma de decisiones de alto impacto con un chat simple, preciso y alineado a la terminología regulatoria mexicana (CUB).

El valor se mide por adopción ejecutiva, reducción de tiempo para obtener *insights* y generación de revenue anual por cliente. El objetivo de negocio es cerrar al menos 3 bancos y alcanzar al menos USD 30k ARR por cliente.

---

## 2. Problema

Para ejecutivos y directores de banca múltiple que quieren obtener *insights* claros y accionables a partir de datos operativos y regulatorios, el problema es la alta dependencia de equipos especializados para acceder, analizar y visualizar datos, porque los datos están fragmentados y requieren interpretación experta.

Esto impacta el tiempo de toma de decisiones, el costo operativo y la calidad de decisiones estratégicas.

### 2.1 Contexto y por qué importa ahora

La presión regulatoria, competitiva y operativa en banca exige decisiones rápidas y basadas en datos. Los modelos tradicionales de BI y analítica no escalan para ejecutivos que requieren respuestas inmediatas y contexto regulatorio preciso.

### 2.2 Evidencia

- **Estado actual:** No hay evidencia que valide la hipótesis más allá de la suposición del equipo de Bajaware de que es algo que se puede vender.
- **Evidencia mínima pero vendible:** hablar con 5-8 *buyer personas* (entrevistas cortas), obtener 2-3 *champion quotes*, y armar un cálculo de ROI con supuestos claros.

#### Evidencia cuantitativa

- Tiempo promedio para obtener un análisis ejecutivo: 1 mes por tablero. Reducido a 15 minutos en Tableau (Fernando Saavedra).
- Costo mensual de equipo de data: 2 analistas y un gerente; ahora sólo tienen al gerente (se menciona ahorro de USD 1,600 al pasar a Tableau).

#### Evidencia cualitativa

No hay interés claro más allá de "probar para ver si le ven valor".

### 2.3 Alcance del problema

- **Incluye:** Ejecutivos, directores de riesgo, tomadores de decisión en banca múltiple.
- **Excluye:** Analistas técnicos que requieren modelado avanzado o construcción de reportes complejos.

---

## 3. Solución

### 3.1 Descripción (qué es y qué no es)

- **Es:** un copiloto de IA conversacional que responde en lenguaje natural con datos de la institución, visualizaciones, *benchmarks* e interpretaciones alineadas a la CUB.
- **No es:** una herramienta de generación de reportes automática, un ETL, ni un sistema de BI configurable por el usuario.

### 3.2 Principios de diseño

1. Precisión regulatoria por encima de creatividad (no alucinar).
2. Latencia baja y experiencia conversacional fluida.
3. Explicabilidad de datos y cálculos.
4. Simplicidad para ejecutivos no técnicos.
5. *Feedback* continuo del usuario para mejora del sistema.

### 3.3 Cómo resuelve el problema

| Problema | Solución |
|----------|----------|
| Dependencia de equipos de datos | Consultas en lenguaje natural vía LLM |
| Dificultad de interpretación | RAG / *fine-tuning* con glosario CUB |
| Falta de comparativos | Visualizaciones y *benchmarks* integrados |
| Tiempo de respuesta alto | Agente SQL + BD centralizada optimizada |

### 3.4 Dependencias y supuestos técnicos

- Calidad y disponibilidad de datos: los datos provistos por Bajaware están normalizados y actualizados.

---

## 4. Casos de Uso

| # | Caso de uso | Usuario | Disparador | Flujo breve | Resultado esperado |
|---|-------------|---------|------------|-------------|-------------------|
| 1 | Consulta cualitativa CUB | Ejecutivo | Duda sobre terminología | Pregunta en chat → respuesta con definición oficial | Aportar valor al cliente final |
| 2 | Benchmark competitivo | Ejecutivo | Análisis estratégico | Solicitud en chat → respuesta en lenguaje natural con razonamiento + SQL query + botón para ver gráfica comparativa | Aportar valor al cliente final |
| 3 | Consulta a cálculos / datos | Ejecutivo | Análisis estratégico | Pregunta en chat → respuesta en lenguaje natural + mención de dato específico + trazabilidad de dónde obtuvo el dato | Aportar valor al cliente final |
| 4 | *Feedback* de usuario | Usuario | Respuesta incorrecta | Error en respuesta → usuario indica "pulgar abajo" → captura de texto adicional | Mejorar el sistema |
| 5 | UX de chat fluida | Usuario | Uso continuo | Interacción rápida | Incrementar adopción |

---

## 5. Propuesta de Valor (V1.1)

> Ayudamos a tomadores de decisión en banca múltiple a tener la inteligencia de un equipo completo de data, en la palma de su mano, mediante un chat simple y preciso.

---

## 6. Metas y Criterios de Éxito

### 6.1 North Star Metric

- **WAU:** número de ejecutivos únicos que interactúan con el copiloto al menos una vez por semana.

### 6.2 Métricas

| Métrica | Definición | Fuente | Baseline | Meta | Ventana |
|---------|------------|--------|----------|------|---------|
| WAU | Usuarios por semana | Logs | 0 | [PEND] | [PEND] |
| TTI | Time-To-Insight | Logs | [PEND] | < 5s | [PEND] |
| ARR | Revenue anual por cliente | Finanzas | 0 | USD 30k | [PEND] |
| Bancos cerrados | Número de clientes activos | Ventas | 0 | >3 | [PEND] |

---

## 7. Experiencia de Usuario

1. Usuario ingresa al chat.
2. Formula preguntas en lenguaje natural.
3. La IA interpreta intención y contexto regulatorio.
4. Un agente dentro del sistema consulta la BD centralizada (SQL) o el contexto del glosario.
5. La IA responde con texto, visualización o cálculo explicado.
6. Usuario itera o deja *feedback*.

---

## 8. Competencia

| Competidor | Tipo |
|------------|------|
| Arkham | Directo |
| Moody's Copilot | Directo |
| Dataiku | Directo |
| Cohere Compass | Indirecto |

### 8.1 Posicionamiento

Ganamos porque no somos "otro chat con RAG". Somos una plataforma de IA diseñada para industrias reguladas que convierte preguntas en resultados reproducibles: entiende tus datos, valida qué se puede responder, ejecuta con controles de seguridad y deja trazabilidad completa (fuentes, consultas y fecha de corte).

---

## 9. Versiones

- V1.1

---

## 10. Funcionalidades Clave y Releases

| Feature | Riesgo | Dependencia | Fechas | Responsable |
|---------|--------|-------------|--------|-------------|
| SLA / Seguridad / Compliance | Alto | Regulación institucional | [PEND] | Saptiva |
| Arquitectura multiagente | Medio | N.A. | [PEND] | Saptiva |
| RAG CUB, Anexo 36 y Banxico | Alto | Glosario CUB + definiciones adicionales | [PEND] | Saptiva |
| Visualizaciones benchmark | Bajo | BD centralizada + datos actualizados | [PEND] | Saptiva |
| Agent SQL | Bajo | Modelo de datos | [PEND] | Saptiva |
| Estructura de datos de catálogos con descripciones de campos | Alto | BD centralizada + definiciones recopiladas por Bajaware | [PEND] | Bajaware |
| Capa ontológica de datos | Alto | Transformar Excel + PDF en entidades `OntologyTerms` (mapeo acrónimos PDF↔Excel, definición/fórmula, sinónimos y curación) | [PEND] | Saptiva |

---

## 11. Fuera de Alcance

### 11.1 No ahora

- Integración de nuevas fuentes de datos.
- Ejecución de fórmulas.
- Segregación por cliente, retención, "no entrenamiento con datos del cliente", etc.

### 11.2 Nunca (para esta versión)

- Generación de fórmulas fuera de la BD centralizada.
- Visualizaciones no especificadas.
- Generación de reportes automáticos.

---

## 12. Demo que Vende (3 guiones, no 30 features)

1. **"¿Qué es X en CUB?"** → definición oficial (cero alucinación) con fuente/tabla/fecha de corte; respuesta segura "No cuento con información" cuando falten datos.
2. **"Compárame IMOR vs mercado / peers"** → texto + gráfica + SQL trazable.
3. **"Explícame por qué subió/bajó y qué palancas hay"** → interpretación con límites + links a cálculo.

---

## 13. Revisión Crítica (para fortalecer el BRD antes de venta)

1. **Evidencia:** el documento reconoce que hoy no hay señal real. Para vender en banca, el mínimo viable de evidencia suele exigir: (i) 5-8 entrevistas con dolor repetido, (ii) *quote* defendible de al menos 2 champion buyers, y (iii) un ROI que compare *status quo* (personas + tiempos + fricción) contra la alternativa, con supuestos auditables.

2. **Multi-tenancy / no entrenamiento / segregación:** aparece como "No ahora", pero en banca lo preguntan en la primera junta. Moverlo a *requisito de diseño* (aunque sea con implementación por fases) reduce riesgo comercial.

3. **Métricas incompletas:** WAU/TTI/ARR están bien como *output metrics*, pero falta una métrica de *trust* (por ejemplo: tasa de respuestas con trazabilidad completa, incidentes de alucinación, errores de cálculo, y fallas de *policy*).

4. **Latencia:** se declara "latencia baja", pero falta objetivo explícito (p95/p99) por tipo de query (definición vs SQL vs benchmark con gráfica).

5. **Datos y actualización:** "BD normalizada y actualizada" es un supuesto grande. Sugiero fijar SLA de actualización, cobertura por tabla, y mecanismos de validación (tests de integridad, conteos, y monitoreo de *drift*).

6. **Benchmarks:** especificar de dónde salen (CNBV/Banxico/peers), la fecha de corte y el tratamiento de comparabilidad (mismas definiciones CUB, mismos periodos).
