
### Conversation and Research Flow

The sequence below shows how a user message is processed, optionally including document context, routed between SAPTIVA chat and Aletheia deep research, and streamed back to the client.

```mermaid
%%{init: {'theme':'neutral','flowchart':{'curve':'basis'}}}%%
sequenceDiagram
  participant Client as Frontend (SSE)
  participant Router as /api/chat
  participant Service as ChatService
  participant Strategy as ChatStrategyFactory
  participant Doc as DocumentService
  participant SAPTIVA as SAPTIVA API
  participant Aletheia as Aletheia Orchestrator
  
  Client->>+Router: POST message + file_ids
  Router->>Router: JWT auth, rate limit
  Router->>Service: orchestrate(context)
  Service->>Strategy: select_strategy(context)
  
  alt Has file_ids (RAG)
    Strategy-->>Service: RAGChatStrategy
    Service->>Doc: retrieve_documents(file_ids)
    Doc-->>Service: document_context
    Service->>SAPTIVA: chat_completion(message + context)
    SAPTIVA-->>Service: response
  else Deep Research Tool Enabled
    Strategy-->>Service: DeepResearchStrategy
    Service->>Aletheia: start_research(query)
    Aletheia-->>Service: SSE stream (sources → evidences → report)
    Service-->>Client: Stream progress
  else Standard Chat
    Strategy-->>Service: StandardChatStrategy
    Service->>SAPTIVA: chat_completion(message)
    SAPTIVA-->>Service: response
  end
  
  Service->>Router: ChatResponse
  Router-->>-Client: JSON response
```

---

## Core Features

### 1. Multi-turn Conversations with File Context Persistence

Files uploaded in a conversation are automatically included in all subsequent messages without re-uploading.

**Implementation:**
- `ChatSession.attached_file_ids: List[str]` stores file references at session level
- Chat router merges request `file_ids` with session `attached_file_ids` using deduplication
- Backend automatically includes document context in LLM prompts

```python
# Backend merge logic (chat.py:142-181)
all_file_ids = list(dict.fromkeys(request_file_ids + session_file_ids))
```

### 2. Minimalismo Funcional (UI Philosophy)

Clean, non-redundant interface following "less is more" principles:
- ✅ Files automatically used when uploaded (no toggle)
- ✅ Single entry point for tools (+ button menu)
- ✅ Implicit intent over explicit controls

### 3. Document Intelligence (RAG)

Supports PDF and image analysis with:
- Multi-page PDF parsing with table detection
- OCR for images (Tesseract with Spanish + English)
- Vector-based semantic search
- Source attribution in responses

### 4. Deep Research Orchestration

Integrated Aletheia research engine with:
- Progress streaming (sources → evidences → report)
- Real-time updates via SSE
- Source tracking and citation
- Wizard UI for research scope configuration

### 5. Accessibility-First Design

- ARIA labels and live regions
- Full keyboard navigation (Enter, Shift+Enter, Escape)
- Screen reader announcements
- Responsive layouts (mobile, tablet, desktop)


---

## Document Processing

### PDF Analysis Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant API as Backend API
    participant DS as DocumentService
    participant OCR as Tesseract OCR
    participant Minio as MinIO S3
    participant DB as MongoDB
    participant LLM as SAPTIVA API

    U->>F: Selects PDF file
    F->>F: Validates type & size
    F->>API: POST /api/documents

    API->>Minio: Upload raw file → storage_key
    API->>DS: process_document(file, storage_key)

    DS->>DS: Extract pages with PyMuPDF

    loop For each page
        DS->>DS: Extract text_md (markdown)
        DS->>DS: Detect tables
        DS->>DS: Extract images

        alt Page has images
            DS->>OCR: Extract text from images
            OCR-->>DS: OCR text (Spanish + English)
            DS->>DS: Append OCR text to page content
        end
    end

    DS->>DB: Save Document model (READY status)
    DS-->>API: document_id, metadata
    API-->>F: { document_id, filename, status: "READY", pages }

    F->>F: Display file badge (✓ Listo)

    U->>F: Sends message with file context
    F->>API: POST /api/chat { message, file_ids: [document_id] }

    API->>DB: Fetch Document by ID
    API->>DS: retrieve_documents([document_id])
    DS-->>API: Combined document context (all pages)

    API->>LLM: Chat completion with document context
    LLM-->>API: Response based on document
    API-->>F: Assistant message

    F->>U: Display response with file indicator
```

**Key Files:**
- Frontend upload: `apps/web/src/hooks/useFiles.ts:85-120`
- Backend processing: `apps/api/src/services/document_service.py:150-250`
- OCR integration: `apps/api/src/services/document_service.py:200-220`

### Image Analysis Flow (OCR)

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant API as Backend
    participant DS as DocumentService
    participant OCR as Tesseract OCR
    participant Minio as MinIO S3
    participant DB as MongoDB
    participant LLM as SAPTIVA API

    U->>F: Selects image file (PNG/JPG)
    F->>F: Validates: maxSize=30MB
    F->>API: POST /api/documents

    API->>Minio: Store image → storage_key
    API->>DS: process_document(image_file, storage_key)

    DS->>DS: Detect mimetype: image/*
    DS->>OCR: pytesseract.image_to_string(image, lang='spa+eng')
    OCR-->>DS: Extracted text

    DS->>DS: Create single-page Document
    DS->>DS: page.text_md = OCR extracted text
    DS->>DB: Save Document (READY)

    DS-->>API: document_id
    API-->>F: { document_id, filename, status: "READY" }

    F->>U: Show file badge with "Listo" status

    U->>F: Types question about image
    F->>API: POST /api/chat { message, file_ids: [document_id] }

    API->>DS: retrieve_documents([document_id])
    DS->>DB: Fetch Document
    DS-->>API: Document with OCR text

    API->>API: Build context: "Documento: filename.png\n\n[OCR text]"
    API->>LLM: Send chat request with image context
    LLM-->>API: Response analyzing image content

    API-->>F: Assistant message
    F->>U: Display response with file indicator
```

**OCR Configuration:**
- Languages: Spanish + English (`lang='spa+eng'`)
- Engine mode: Default (PSM 3 - fully automatic page segmentation)
- Location: `apps/api/src/services/document_service.py:200-220`

**Image Requirements:**
- Formats: PNG, JPG, JPEG
- Max size: 30MB
- Resolution: Recommended 300 DPI for best OCR accuracy

