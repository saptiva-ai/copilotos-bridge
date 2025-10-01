# Diagrama 2: Secuencia Chat Completa con Tools

## Flujo 1: Chat Simple (Sin Tools / Kill Switch Activo)

```mermaid
sequenceDiagram
    participant U as Usuario
    participant UI as ChatComposer<br/>(FE)
    participant API as ApiClient<br/>(axios)
    participant ROUTER as Chat Router<br/>(BE)
    participant KS as Kill Switch<br/>Check
    participant SAPTIVA as Saptiva Client<br/>(BE)
    participant LLM as SAPTIVA API
    participant DB as MongoDB

    U->>UI: Escribe "Hola, ¿qué es SAPTIVA?"
    UI->>UI: onChange(value)
    U->>UI: Presiona Enter / Click Send
    UI->>UI: handleSend()

    UI->>API: POST /api/chat<br/>{message, model, tools_enabled: {}}
    API->>ROUTER: HTTP Request + JWT token
    ROUTER->>ROUTER: Middleware: Verify JWT
    ROUTER->>DB: Create/Get ChatSession
    ROUTER->>DB: Add user message
    DB-->>ROUTER: message_id

    ROUTER->>KS: Check deep_research_kill_switch
    Note over KS: deep_research_kill_switch = TRUE
    KS-->>ROUTER: Bypass coordinator → Simple chat

    ROUTER->>SAPTIVA: chat_completion(messages, model="Saptiva Turbo")
    SAPTIVA->>LLM: POST /v1/chat/completions/<br/>{messages: [...]}
    LLM-->>SAPTIVA: {id, choices, usage}
    SAPTIVA-->>ROUTER: SaptivaResponse

    ROUTER->>ROUTER: Extract content from response
    ROUTER->>DB: Add assistant message
    DB-->>ROUTER: message_id
    ROUTER-->>API: ChatResponse<br/>{chat_id, message_id, content, tokens, latency_ms}
    API-->>UI: Response data
    UI->>UI: Update messages state
    UI->>U: Muestra respuesta en UI
```

**Archivos clave**:
- `apps/web/src/components/chat/ChatComposer/ChatComposer.tsx:355-373` (handleSend, handleKeyDown)
- `apps/web/src/lib/api-client.ts:300-350` (sendChatMessage)
- `apps/api/src/routers/chat.py:38-340` (send_chat_message)
- `apps/api/src/services/saptiva_client.py:165-245` (chat_completion)

---

## Flujo 2: Chat con Tool Seleccionada (Web Search - No Implementado)

```mermaid
sequenceDiagram
    participant U as Usuario
    participant TOOLMENU as ToolMenu<br/>(FE)
    participant COMPOSER as ChatComposer<br/>(FE)
    participant STORE as Zustand Store<br/>(selectedTools)
    participant API as ApiClient
    participant ROUTER as Chat Router<br/>(BE)
    participant SAPTIVA as Saptiva Client

    U->>COMPOSER: Click botón "+"
    COMPOSER->>TOOLMENU: setShowToolsMenu(true)
    TOOLMENU->>U: Muestra lista de tools
    U->>TOOLMENU: Click "Web Search"
    TOOLMENU->>STORE: addTool('web-search')
    STORE-->>COMPOSER: selectedTools = ['web-search']
    COMPOSER->>COMPOSER: Render chip "Web Search"

    U->>COMPOSER: Escribe "¿Cuáles son las noticias recientes de IA?"
    U->>COMPOSER: Presiona Enter
    COMPOSER->>API: POST /api/chat<br/>{message, tools_enabled: {web_search: true}}
    API->>ROUTER: HTTP Request

    Note over ROUTER: ⚠️ tools_enabled.web_search<br/>se acepta pero NO se procesa

    ROUTER->>SAPTIVA: chat_completion(messages)<br/>(sin context de web)
    SAPTIVA-->>ROUTER: Response basada en conocimiento interno
    ROUTER-->>API: ChatResponse
    API-->>COMPOSER: Response data
    COMPOSER->>U: Muestra respuesta (sin datos web reales)
```

**Problema actual**: `web_search` es solo un feature flag. **No hay:**
- Endpoint `/api/tools/web-search`
- Servicio de scraping/fetching
- Adaptador que procese el flag

**Archivos clave**:
- `apps/web/src/components/chat/ToolMenu/ToolMenu.tsx:16-42` (renderiza lista de tools)
- `apps/web/src/hooks/useSelectedTools.ts:4-22` (hook para gestionar tools)
- `apps/api/src/schemas/chat.py:90` (acepta tools_enabled pero no procesa)

---

## Flujo 3: Deep Research (Bloqueado por Kill Switch)

```mermaid
sequenceDiagram
    participant U as Usuario
    participant TOOLMENU as ToolMenu<br/>(FE)
    participant FLAGS as Feature Flags<br/>(FE)
    participant COMPOSER as ChatComposer
    participant API as ApiClient
    participant ROUTER as Chat Router<br/>(BE)
    participant KS as Kill Switch<br/>Check
    participant SAPTIVA as Saptiva Client

    U->>TOOLMENU: Intenta seleccionar "Deep Research"
    TOOLMENU->>FLAGS: Check featureFlags.deep_research_kill_switch
    FLAGS-->>TOOLMENU: kill_switch = TRUE
    Note over TOOLMENU: ToolsPanel NO renderiza<br/>checkbox de Deep Research

    alt Kill switch en FALSE (hipotético)
        U->>COMPOSER: Selecciona "Deep Research"
        U->>COMPOSER: Escribe query compleja
        COMPOSER->>API: POST /api/chat<br/>{message, tools_enabled: {deep_research: true}}
        API->>ROUTER: HTTP Request
        ROUTER->>KS: Check deep_research_kill_switch
        Note over KS: deep_research_kill_switch = TRUE
        KS-->>ROUTER: Bypass coordinator
        ROUTER->>SAPTIVA: Simple chat (sin research)
        SAPTIVA-->>ROUTER: Response
        ROUTER-->>API: ChatResponse (sin task_id)
    end

    Note over U,SAPTIVA: Escalación manual también bloqueada

    U->>API: POST /api/chat/{chat_id}/escalate
    API->>ROUTER: HTTP Request
    ROUTER->>KS: Check deep_research_kill_switch
    KS-->>ROUTER: kill_switch = TRUE
    ROUTER-->>API: HTTPException 410 GONE<br/>{error: "Deep Research feature is not available"}
    API-->>U: Error toast
```

**Archivos clave**:
- `apps/web/src/components/chat/ToolsPanel.tsx:49-67` (fetch feature flags)
- `apps/web/src/components/chat/ToolsPanel.tsx:156-190` (conditional render de Deep Research)
- `apps/api/src/routers/chat.py:129-172` (kill switch bypass)
- `apps/api/src/routers/chat.py:362-379` (escalate blocked)

---

## Flujo 4: Deep Research (Si estuviera habilitado - Hipotético)

```mermaid
sequenceDiagram
    participant U as Usuario
    participant UI as ChatComposer<br/>(FE)
    participant API as ApiClient
    participant ROUTER as Chat Router<br/>(BE)
    participant COORD as Research Coordinator<br/>(BE)
    participant ALETHEIA as Aletheia Client<br/>(BE)
    participant RESEARCH as Aletheia API<br/>(External)
    participant DB as MongoDB

    Note over ROUTER,COORD: Asume kill_switch = FALSE

    U->>UI: Selecciona "Deep Research"
    U->>UI: Escribe "Investiga avances en computación cuántica"
    UI->>API: POST /api/chat<br/>{message, tools_enabled: {deep_research: true}}
    API->>ROUTER: HTTP Request

    ROUTER->>COORD: execute_coordinated_research(query, force_research=True)
    COORD->>COORD: analyze_query_complexity(query)
    COORD-->>COORD: complexity.score = 0.85<br/>requires_research = TRUE

    COORD->>ALETHEIA: start_deep_research(query, params)
    ALETHEIA->>RESEARCH: POST /research/deep<br/>{query, scope, depth_level}
    RESEARCH-->>ALETHEIA: {task_id, status: "pending", stream_url}
    ALETHEIA-->>COORD: AletheiaResponse{task_id}

    COORD-->>ROUTER: {type: "deep_research", task_id, stream_url}
    ROUTER->>DB: Add research initiation message
    ROUTER-->>API: ChatResponse{task_id, stream_url}
    API-->>UI: Response data
    UI->>UI: Start streaming from stream_url

    Note over UI,RESEARCH: Streaming de progreso (SSE)

    loop Progress Updates
        RESEARCH-->>UI: Event: {phase, progress, sources}
        UI->>U: Actualiza progress bar
    end

    RESEARCH-->>UI: Event: {phase: "completed", report}
    UI->>U: Muestra reporte final
```

**Archivos clave (cuando esté habilitado)**:
- `apps/api/src/services/research_coordinator.py:238-300` (make_research_decision)
- `apps/api/src/services/aletheia_client.py` (start_deep_research)
- `apps/web/src/hooks/useDeepResearch.ts` (streaming hook)

---

## Flujo 5: Add Files (PDF) - No Implementado

```mermaid
sequenceDiagram
    participant U as Usuario
    participant COMPOSER as ChatComposer<br/>(FE)
    participant VALIDATION as File Validation<br/>(FE)
    participant API as ApiClient
    participant ROUTER as File Router<br/>(BE - NO EXISTE)

    U->>COMPOSER: Drag & drop archivo.pdf
    COMPOSER->>VALIDATION: validateFile(file)
    VALIDATION->>VALIDATION: Check extension (.pdf allowed)
    VALIDATION->>VALIDATION: Check size (< 20MB)
    VALIDATION-->>COMPOSER: {valid: true}

    COMPOSER->>COMPOSER: Add to attachments state<br/>{id, file, name, size, status: 'uploading'}
    COMPOSER->>U: Muestra chip de attachment

    U->>COMPOSER: Click Send
    COMPOSER->>API: ❌ POST /api/files/upload (NO EXISTE)
    API-->>COMPOSER: 404 Not Found

    Note over COMPOSER,ROUTER: TO-DO:<br/>- Endpoint /api/files/upload<br/>- Parser (PyPDF2, pdfplumber)<br/>- Embeddings (OpenAI, Cohere)<br/>- Vector store (Pinecone, pgvector)<br/>- RAG retrieval en prompt
```

**Archivos clave**:
- `apps/web/src/components/chat/ChatComposer/ChatComposer.tsx:123-135` (validateFile)
- `apps/web/src/components/chat/ChatComposer/ChatComposer.tsx:467-520` (handleDrop, handleFileSelect)
- **NO EXISTE**: Backend file upload/processing

---

## Resumen de Flows

| Flow | Estado | Kill Switch | Implementación |
|------|--------|-------------|----------------|
| Chat Simple | ✅ Funcional | N/A | Completa |
| Chat + Web Search | ⚠️ Parcial | N/A | Solo UI, sin backend |
| Deep Research | ❌ Bloqueado | ✅ ACTIVO | Backend completo, pero deshabilitado |
| Escalate to Research | ❌ Bloqueado | ✅ ACTIVO | Retorna 410 GONE |
| Add Files (PDF) | ❌ No Implementado | N/A | Solo UI (validación) |
| Google Drive | ❌ No Implementado | N/A | Solo feature flag |
| Canvas | ❌ No Implementado | N/A | Solo feature flag |
| Agent Mode | ❌ No Implementado | N/A | Solo feature flag |

---

## Próximo diagrama

→ [Diagrama 3: Módulos/Clases (Registry, Adapters, Interfaces)](./llm-tools-classes.md)
