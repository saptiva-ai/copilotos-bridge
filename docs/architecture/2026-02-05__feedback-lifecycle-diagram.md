# Feedback Lifecycle: Collection → Triage → Resolution → GitHub Issues

## Overview Diagram

```mermaid
flowchart TB
    subgraph COLLECTION["1. COLLECTION (Real-time)"]
        direction TB
        U[("Usuario\n(bankadvisor.spativa.com)")] -->|"thumbs down/up\n+ razon opcional"| FE
        FE["MessageFeedback.tsx\n(React component)"] -->|"POST /api/feedback\n{message_id, rating, reason}"| API
        API["feedback.py router\n(FastAPI)"] -->|"auth + dedup\n+ rate limit 60/min"| SVC
        SVC["FeedbackService\n(context enrichment)"] -->|"auto-enrich:\n- original query\n- SQL executed\n- intent + confidence\n- chart data"| DB
        DB[("MongoDB\nmessage_feedback\nFDBK-0001..N")]
    end

    subgraph TRIAGE["2. TRIAGE (Claude Code session)"]
        direction TB
        QUERY["Query MongoDB\nticket_id = null\nrating = 'down'"] --> FETCH
        FETCH["Fetch full conversation\nper feedback_id\n(context window +/-3 msgs)"] --> ANALYZE
        ANALYZE["Analyze root cause:\n- What did user ask?\n- What did system answer?\n- Why is it wrong?"] --> CLASSIFY
        CLASSIFY{"Classify"}
        CLASSIFY -->|"matches existing\nticket"| ASSIGN
        CLASSIFY -->|"new issue\nnot seen before"| CREATE
        CLASSIFY -->|"feedback post-fix\nbug persists"| REOPEN
        ASSIGN["Assign ticket_id\nin MongoDB"]
        CREATE["Create new ticket\nin docs/kanban/BACKLOG/"]
        REOPEN["Move ticket\nDONE → DOING\n+ add new context"]
    end

    subgraph WORK["3. WORK (Kanban phases)"]
        direction LR
        BACKLOG["BACKLOG\n(prioritized)"] -->|"start"| DOING
        DOING["DOING"] --> R["Research\nresearch.md"]
        R --> P["Plan\nplan.md"]
        P --> I["Implement\n(code changes)"]
        I --> V["Validate\nvalidate.md\n(E2E tests)"]
        V -->|"tests pass"| DONE["DONE"]
        V -->|"tests fail"| I
    end

    subgraph DEPLOY["4. DEPLOY"]
        direction TB
        BUILD["docker build\nbank-advisor:v1.4.X"] --> PUSH["docker push\nto Docker Hub"]
        PUSH --> MANIFEST["Update\ndocker-compose.images.yml"]
        MANIFEST --> GIT["git commit + push"]
        GIT --> SSH["SSH to prod\njf@PROD_SERVER_IP"]
        SSH --> PULL["git pull +\ndocker pull"]
        PULL --> UP["docker compose up\n+ redis flush"]
    end

    subgraph SYNC["5. GITHUB SYNC (gh CLI)"]
        direction TB
        ATOMIC["kanban_atomic_move\n(MCP tool)"] -->|"GITHUB_ACTION\nJSON block"| GH_CLI
        GH_CLI["gh issue edit\n+ gh issue close"] -->|"labels:\nstatus:backlog/doing/review/done"| GITHUB
        GITHUB[("GitHub Issues\nsaptiva-ai/octavios-chat-bajaware_invex")]
    end

    DB -->|"analyst queries\nunassigned feedback"| QUERY
    ASSIGN --> WORK
    CREATE --> WORK
    REOPEN --> WORK
    DONE --> DEPLOY
    DONE -->|"kanban_atomic_move"| ATOMIC
    CREATE -->|"kanban_atomic_move"| ATOMIC
    REOPEN -->|"kanban_atomic_move"| ATOMIC
```

## Sequence Diagram (detailed data flow)

```mermaid
sequenceDiagram
    participant U as Usuario
    participant FE as Frontend<br/>(Next.js)
    participant BE as Backend<br/>(FastAPI)
    participant MDB as MongoDB
    participant CC as Claude Code<br/>(Analyst)
    participant KB as Kanban<br/>(docs/kanban/)
    participant GH as GitHub Issues

    Note over U,FE: 1. COLLECTION
    U->>FE: Click thumbs-down + "clave incorrecta"
    FE->>BE: POST /api/feedback
    BE->>BE: Validate auth + dedup
    BE->>MDB: Lookup message context
    MDB-->>BE: original_query, response, SQL, intent
    BE->>MDB: Insert FDBK-0075 (ticket_id: null)
    BE-->>FE: { feedback_id: "FDBK-0075" }

    Note over CC,MDB: 2. TRIAGE
    CC->>MDB: Find rating="down", ticket_id=null
    MDB-->>CC: 18 unassigned feedback
    loop Per feedback
        CC->>MDB: Get conversation (+/-3 msgs around rated msg)
        MDB-->>CC: Full context
        CC->>CC: Analyze root cause
    end
    CC->>CC: Classify into categories
    CC->>MDB: Update ticket_id for each FDBK

    alt New issue
        CC->>KB: Create BACKLOG/2026-02-05__BUG__xxx/card.md
    else Existing ticket
        CC->>KB: Update card.md with new feedback reference
    else Bug persists post-fix
        CC->>KB: Move DONE → DOING + add context
    end

    Note over KB: 3. WORK (phases)
    CC->>KB: Research → research.md
    CC->>KB: Plan → plan.md
    CC->>KB: Implement → code changes
    CC->>KB: Validate → validate.md (E2E)
    CC->>KB: Move DOING → DONE

    Note over KB,GH: 4. GITHUB SYNC
    CC->>KB: kanban_atomic_move → local + MongoDB
    KB-->>CC: GITHUB_ACTION JSON
    CC->>GH: gh issue edit --add-label status:done
    CC->>GH: gh issue close
    GH-->>CC: Synced
```

## Data Model

```mermaid
erDiagram
    MESSAGE_FEEDBACK {
        string feedback_id PK "FDBK-0075"
        string message_id FK "links to messages._id"
        string conversation_id FK
        string user_id FK
        enum rating "up | down"
        string reason "max 500 chars"
        dict context "auto-enriched"
        string ticket_id "assigned kanban ticket"
        enum status "NEW | OPEN | IN_PROGRESS | RESOLVED"
        string assigned_to
        datetime created_at
    }

    MESSAGES {
        string _id PK
        string conversation_id FK
        string role "user | assistant"
        string content
        dict metadata "SQL, intent, chart_data"
        datetime created_at
    }

    KANBAN_TICKET {
        string id PK "2026-02-05__BUG__slug"
        string status "BACKLOG | DOING | DONE"
        string type "BUG | TASK | REFACTOR | SEC"
        file card_md "description + feedback refs"
        file research_md "root cause analysis"
        file plan_md "implementation steps"
        file validate_md "E2E test results"
    }

    GITHUB_ISSUE {
        int number PK "42"
        string title "matches task id"
        string state "open | closed"
        list labels "status:doing, type:bug"
        datetime created_at
        datetime closed_at
    }

    MESSAGE_FEEDBACK ||--|| MESSAGES : "rates"
    MESSAGE_FEEDBACK }o--|| KANBAN_TICKET : "ticket_id"
    KANBAN_TICKET ||--o| GITHUB_ISSUE : "syncs to"
```

## Component Map

```
+-----------------------------------------------------------------+
|                        FRONTEND (Next.js)                        |
|                                                                  |
|  MessageFeedback.tsx --> useOptimizedChat.ts --> api-client.ts    |
|  (UI: thumbs up/down + textarea)  (hook)     (POST /api/feedback)|
+------------------------------+-----------------------------------+
                               | HTTP
+------------------------------v-----------------------------------+
|                        BACKEND (FastAPI)                          |
|                                                                  |
|  routers/feedback.py --> services/feedback_service.py            |
|  (auth, dedup, rate-limit)   (context enrichment, FDBK-ID gen)  |
+------------------------------+-----------------------------------+
                               |
+------------------------------v-----------------------------------+
|                     MONGODB (message_feedback)                    |
|                                                                  |
|  Indexes: message_id, conversation_id, user_id, feedback_id,    |
|           status, created_at, (composite: status+created_at)     |
+------------------------------+-----------------------------------+
                               | Query: ticket_id=null, rating=down
+------------------------------v-----------------------------------+
|                   TRIAGE (Claude Code session)                    |
|                                                                  |
|  1. Query unassigned feedback                                    |
|  2. Fetch +/-3 msgs around rated message                         |
|  3. Analyze root cause per conversation                          |
|  4. Classify -> assign/create/reopen                             |
|  5. Update MongoDB ticket_id                                     |
+------+------------------+------------------+---------------------+
       |                  |                  |
       v                  v                  v
+--------------+  +--------------+  +------------------+
| Assign to    |  | Create new   |  | Reopen ticket    |
| existing     |  | BACKLOG/     |  | DONE -> DOING    |
| ticket       |  | card.md      |  | + new context    |
+--------------+  +------+-------+  +--------+---------+
                         |                   |
+------------------------v-------------------v---------------------+
|                    KANBAN (docs/kanban/)                          |
|                                                                  |
|  BACKLOG/ --> DOING/ --> DONE/                                   |
|               |                                                  |
|               +-- Research (research.md)                         |
|               +-- Plan (plan.md)                                 |
|               +-- Implement (code)                               |
|               +-- Validate (validate.md + E2E)                   |
+------------------------+-----------------------------------------+
                         | kanban_atomic_move (local + MongoDB)
+------------------------v-----------------------------------------+
|              GITHUB_ACTION (JSON in MCP response)                 |
|                                                                  |
|  { action: "update_issue_status", repo: "...",                   |
|    add_label: "status:done", close_issue: true }                 |
+------------------------+-----------------------------------------+
                         | Claude Code executes via gh CLI
+------------------------v-----------------------------------------+
|                     GITHUB ISSUES                                 |
|                                                                  |
|  Labels: status:backlog | status:doing | status:done             |
|  State: open (active) | closed (done)                            |
+------------------------------------------------------------------+
```

## Triage Decision Tree

```mermaid
flowchart TD
    START["FDBK-XXXX\n(rating=down, ticket_id=null)"] --> FETCH["Fetch conversation\ncontext +/-3 msgs"]
    FETCH --> ROOT["Identify root cause"]
    ROOT --> MATCH{"Matches\nexisting ticket?"}

    MATCH -->|"Yes"| CHECK{"Feedback date\nvs ticket date?"}
    MATCH -->|"No"| NEW["Create new ticket\nin BACKLOG"]

    CHECK -->|"Feedback BEFORE fix"| ASSIGN_DONE["Assign ticket_id\nKeep in DONE"]
    CHECK -->|"Feedback AFTER fix"| REOPEN["Move DONE -> DOING\nAdd new context\nto card.md"]

    NEW --> ASSIGN_NEW["Set ticket_id\nin MongoDB"]
    ASSIGN_DONE --> UPDATE["Update MongoDB\nticket_id = ticket"]
    REOPEN --> UPDATE

    style START fill:#ff6b6b,color:#fff
    style ASSIGN_DONE fill:#51cf66,color:#fff
    style REOPEN fill:#ffd43b,color:#333
    style NEW fill:#339af0,color:#fff
```
