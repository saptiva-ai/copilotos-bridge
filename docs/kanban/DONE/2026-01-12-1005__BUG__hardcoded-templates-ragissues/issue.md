# BankAdvisor — Bug Reports (Head of Product)

## Contexto general (común a todos)
- Durante testing, el sistema parece sobre-rutear preguntas hacia el flujo de ICAP + selector + gráfica, y además no está usando el glosario como fuente primaria para definiciones.
- Hay señales de hardcode / defaults hacia INVEX y hacia “ICAP” como tema central.

---

## BUG-01 — Definiciones del glosario no se están usando bien / respuesta truncada
- **Evidencia (imagen):** 4e80a854-f52e-47ed-a95d-2e69677f5f9d.png
- **Qué hay en la imagen:**  
  - En un thread de Slack, Carlos reporta: “No está tomando bien las definiciones del glosario o no está ‘aumentando’ la respuesta”.  
  - La UI de BankAdvisor muestra la pregunta: “Que es un fideicomiso?” y la respuesta aparece como:  
    - Título: “Fideicomiso de Contragarantía”  
    - Texto: “a los fideicomisos constituidos por instituciones de banca de …” (se ve incompleta / cortada)  
    - Fuentes listadas: Glosario_CUB.pdf (pág. 188), doc:Glosario_CUB.pdf, doc:database-schema-gcp-postgresql.md
- **Comportamiento actual:**  
  - La respuesta no contesta el concepto general (“fideicomiso”) sino que se va a una subdefinición específica (“de contragarantía”) sin aclarar por qué.  
  - El cuerpo aparece truncado (chunk cortado o render recortado).  
  - Parece citar el glosario, pero no integra una respuesta completa y útil.
- **Comportamiento esperado:**  
  - Si el usuario pregunta “¿Qué es un fideicomiso?”, la respuesta debería dar una definición general (nivel glosario / regulación), luego explicar variantes (“de contragarantía”, “de administración”, etc.) solo si aplica, y no truncarse.
- **Hipótesis (técnicas) de causa raíz:**  
  - Chunking defectuoso del PDF (segmentos cortados a media línea / media oración).  
  - Falta de “term-in-chunk validation”: se trae un chunk relacionado pero no necesariamente la definición correcta del término.  
  - El “answer composer” usa solo el título del término encontrado y un fragmento parcial.  
  - Bug de UI: el componente podría recortar texto (altura fija + overflow hidden) o renderizar solo “snippet”.
- **Dudas / señales de UX:**  
  - ¿El producto quiere un modo “Definición” (glosario) explícito? Si no, el usuario no sabe si ve “definición canónica” o “interpretación”.

---

## BUG-02 — Siempre se va a ICAP y muestra gráfica aunque el usuario no la pidió
- **Evidencia (imagen):** bbd13337-2e3b-4565-9cfc-9d53f0cf34ad.png
- **Qué hay en la imagen:**  
  - Texto superior: “Siempre se va al ICAP incluso cuando no necesita mostrarme ni una gráfica”.  
  - Pantalla: izquierda chat explicando ICAP para “SISTEMA”; derecha panel “GRAFICA ICAP” con serie temporal.
- **Comportamiento actual:**  
  - El sistema elige el modo “ICAP + chart” por defecto.  
  - El “tool router” interpreta muchas preguntas como “solicitud de métrica” y dispara el flujo de gráfica.
- **Comportamiento esperado:**  
  - Si el usuario no pide datos/serie temporal, debería responder en texto (glosario / explicación / normativa) y solo ofrecer la gráfica como “¿Quieres ver la serie?” o bajo un botón (“Mostrar gráfica”).
- **Hipótesis de causa raíz:**  
  - Clasificador de intención demasiado agresivo (“si detecto sigla/palabra financiera ⇒ ICAP”).  
  - Herramienta de chart priorizada en el planner (o “ICAP” está en el system prompt como “tema estrella”).  
  - Estado de conversación: el sistema arrastra el “último contexto” (ICAP) a la siguiente pregunta (sticky context).
- **Pregunta de producto (importante):**  
  - ¿El asistente debe ser “glosario-first” o “métricas-first”? Hoy se siente “métricas-first” y eso rompe la experiencia cuando alguien pregunta definiciones.

---

## BUG-03 — Fallas de recuperación de glosario para siglas/typos (CNBV vs CNVB) y falta de “glosario en contexto”
- **Evidencia (imagen):** 56b9a0ab-2e45-4f8f-a128-267182f3ed22.png
- **Qué hay en la imagen:**  
  - Texto superior: “Entiendo que es el RAG en la intencionalidad, pero si usa keyword pensaría que todos los elementos del glosario se pueden dejar in context, no?”  
  - Caso A: el asistente dice “estoy usando ICAP para SISTEMA…” y luego define CNBV (parece inferido, no recuperado).  
  - Caso B: pregunta “CNVB?” y el sistema contesta: “encontré una definición específica para ‘CNVB’…” y sugiere términos similares raros.
- **Comportamiento actual:**  
  - Para siglas o errores de dedo: o no encuentra la entrada correcta (CNBV) o “inventa” una coincidencia (“CNVB”) con sugerencias poco confiables.  
  - Se espera robustez a typos y definiciones “core” siempre disponibles.
- **Comportamiento esperado:**  
  - Si el usuario escribe CNVB, el sistema debería normalizar (mayúsculas/acentos), buscar fuzzy (Levenshtein/trigramas), y responder “Parece que te refieres a CNBV (… definición …)”.  
  - Si el glosario es pequeño/mediano: considerar tener un “glossary memory” (resumen/índice) siempre en contexto para no dejar ciego al LLM.
- **Hipótesis de causa raíz:**  
  - Recuperación exact-match o BM25 sin fuzzy + sin sinónimos.  
  - No existe un “glossary index” de alta prioridad (diccionario: término → definición corta + source pointer).  
  - El router sigue “ICAP mode” por defecto y contamina el razonamiento.
- **Nota filosófico-práctica (estoica, pero útil):**  
  - La IA sin buen grounding rellena huecos; sin mecanismo claro de “no sé / no encontré”, improvisa.

---

## BUG-04 — Sospecha de hardcode: “estoy usando ICAP para INVEX/HSBC” aparece como plantilla fija
- **Evidencia (imagen):** a3b9cdf1-ea6e-4ade-9ca2-36c4d7c7bc19.png
- **Qué hay en la imagen:**  
  - Texto: “Esto está hardcodeado para todas las respuestas?”  
  - Se resalta: “y usando ICAP para INVEX, HSBC. Exacto.”
- **Comportamiento actual:**  
  - El asistente parece usar una frase plantilla mencionando ICAP + bancos en cualquier respuesta.  
  - Percibido como demo/hardcode, baja confianza.
- **Comportamiento esperado:**  
  - Solo mencionar ICAP + bancos si el usuario pidió explícitamente una métrica o si se necesita confirmar contexto (“¿Te refieres al ICAP de INVEX o al sistema?”).
- **Hipótesis de causa raíz:**  
  - Prompt del sistema o “assistant preamble” que fuerza “responde en marco ICAP y bancos X”.  
  - `primary_bank` o “bank universe” hardcodeado en backend (ej. lista fija: INVEX, HSBC) o en el schema de la tool.  
  - Memory/estado persistente mal reseteado entre chats.

---

## BUG-05 — Anclaje a INVEX: selector obliga a elegir INVEX o “Sistema” (no hay otros bancos)
- **Evidencia (imagen):** b242429d-fb3a-44f9-8afc-4a2cde628349.png
- **Qué hay en la imagen:**  
  - Texto: “Sigue anclado a Invex por lo que está hardcodeado”.  
  - UI muestra un paso guiado: “Para ayudarte, necesito que especifiques la métrica y el banco…”  
  - Botones:  
    - Métricas: Morosidad, Cobertura, Capitalización, Cartera Total, etc.  
    - Banco: INVEX (solo datos de INVEX) y Sistema (comparativa del sistema bancario)
- **Comportamiento actual:**  
  - El flujo obliga a escoger “métrica + banco” aunque la pregunta sea conceptual.  
  - Solo existen INVEX/Sistema ⇒ el producto queda “especializado” en INVEX aunque el usuario quiera HSBC, Banorte, etc.
- **Comportamiento esperado:**  
  - Si la pregunta no es de métricas ⇒ no forzar selector.  
  - Si sí es de métricas ⇒ permitir banco configurable (catálogo/lista dinámica) o al menos un campo de búsqueda (“escribe el banco”).  
  - Si solo soporta INVEX/Sistema, decirlo explícitamente (“por ahora solo INVEX/Sistema”) en vez de aparentar generalidad.
- **Hipótesis de causa raíz:**  
  - Backend con `default bank = INVEX` o `available_banks = [INVEX, SISTEMA]` en config fija.  
  - Tool definition (schema) restringe enum a INVEX/Sistema.  
  - UI/agent diseñado como “guided demo” y no como producto general.

---

## Preguntas abiertas (para no arreglar lo incorrecto “correctamente”)
- ¿Cuándo debe dispararse chart mode?  
  - ¿Solo si el usuario pide “gráfica/serie/evolución”?  
  - ¿O si pide “métrica X en el tiempo”?  
  - Si no se define, el router seguirá adivinando.
- ¿El glosario es “fuente primaria” o “fuente opcional”?  
  - Si es primaria: definiciones primero, métricas después.
- ¿Cuál es el scope real de bancos soportados hoy?  
  - Si solo INVEX, hay que hacer UX honesto y evitar prometer HSBC.

---

## Resolution Status (2026-01-19)

**Status: RESOLVED (Consolidated)**

This issue was resolved as part of **ISSUE-003** fixes. The overlapping bugs were addressed by:

| Bug | Resolution |
|-----|------------|
| BUG-01 (Glosario) | RAG priority fix (`ea5eff58`, `db9ca3e0`) |
| BUG-02 (ICAP default) | BA-002 multi-tenant fix (`fead91a5`) |
| BUG-03 (Fuzzy/typos) | RAG grounding improvements |
| BUG-04 (Hardcode) | Multi-tenant generalization (`d3901120`) |

**Related:** See `docs/kanban/DONE/ISSUE-003_user-reported-bugs/` for full fix details.
