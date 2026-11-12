# Architecture Diagrams

This document contains project-specific diagrams based on the current codebase.

## 1) UML Component Diagram

```mermaid
flowchart LR
    User[(User)]

    subgraph Browser[Client Side]
        Frontend["Vue Frontend App<br/>(frontend)"]
        ExtBG["Chrome Extension Background<br/>(google_add/src/background.js)"]
        ExtContent["Content/Page Analyzer<br/>(content.js + page_analyzer.js)"]
        ExtPopup["Extension Popup UI<br/>(popup.js)"]
    end

    subgraph APILayer[Backend API Layer]
        IngestAPI["FastAPI Ingestion API<br/>(server:8000)"]
        RecoAPI["Recommendations API<br/>(RecommendationsReader:8001)"]
    end

    subgraph Queue[Messaging]
        Rabbit[(RabbitMQ)]
    end

    subgraph Processing[Processing Layer]
        Collector[RawDataCollector Worker]
        Ollama[Ollama LLM Service]
        RecoWorker["Recommendations Builder Worker<br/>(Celery Worker)"]
        RecoBeat["Recommendations Builder Scheduler<br/>(Celery Beat)"]
        Redis[(Redis)]
    end

    GraphDB[(Neo4j Graph DB)]

    User --> Frontend
    User --> ExtPopup
    ExtContent --> ExtBG
    ExtBG --> IngestAPI
    IngestAPI --> Rabbit
    Rabbit --> Collector
    Collector --> Ollama
    Collector --> GraphDB

    Frontend --> RecoAPI
    RecoAPI --> GraphDB

    RecoBeat --> Rabbit
    Rabbit --> RecoWorker
    RecoWorker --> GraphDB
    RecoWorker --> Redis
```

## 2) UML Deployment Diagram

```mermaid
flowchart TB
    subgraph ClientMachine[User Machine]
        Browser[Chrome Browser]
        FE["Vite/Vue Frontend<br/>localhost:5173"]
        EXT["Chrome Extension<br/>Manifest V3"]
        Browser --> FE
        Browser --> EXT
    end

    subgraph DockerHost[Docker Compose Environment]
        FastAPI["fastapi-server<br/>:8000"]
        Reader["recommendationsreader<br/>:8001"]
        Collector["rawdatacollector<br/>(worker process)"]
        Rabbit[("rabbitmq<br/>:5672,:15672")]
        Ollama["ollama_service<br/>:11434"]
        Jaeger["jaeger<br/>:16686,:4318"]
        RecoWorker["reco_worker<br/>Celery"]
        RecoBeat["reco_beat<br/>Celery Beat"]
        Redis[("redis<br/>:6379")]
    end

    Neo4j[("Neo4j + GDS<br/>docker compose")]

    EXT -->|POST /data/post-collected-data| FastAPI
    FE -->|GET/POST /recommendations, /stats, /history| Reader

    FastAPI --> Rabbit
    Collector -->|consume raw_data_queue| Rabbit
    Collector --> Ollama
    Collector --> Neo4j

    Reader --> Neo4j

    RecoBeat --> Rabbit
    Rabbit --> RecoWorker
    RecoWorker --> Neo4j
    RecoWorker --> Redis

    FastAPI --> Jaeger
    Reader --> Jaeger
    Collector --> Jaeger
    RecoWorker --> Jaeger
```

## 3) UML Sequence Diagram

Scenario: browser activity is collected, stored in graph, then user opens recommendations and sends feedback visit.

```mermaid
sequenceDiagram
    participant U as User
    participant EXT as Chrome Extension (background)
    participant API as FastAPI Ingestion API (:8000)
    participant MQ as RabbitMQ
    participant RDC as RawDataCollector
    participant AI as Ollama + AI services
    participant G as Neo4j
    participant FE as Vue Frontend
    participant RR as Recommendations Reader API (:8001)

    U->>EXT: Browse pages
    EXT->>EXT: Extract url/title/text/image + timings
    EXT->>API: POST /data/post-collected-data
    API->>MQ: Publish payload to raw_data_queue
    MQ->>RDC: Deliver message
    RDC->>RDC: Normalize URL, filter, enrich
    RDC->>AI: Categorize/summarize/embed (when needed)
    AI-->>RDC: categories + summary + vectors
    RDC->>G: MERGE User, Page, Category, VISIT, IN_CATEGORY

    U->>FE: Open Recommendations page
    FE->>RR: GET /recommendations?page&size
    RR->>G: Read user embeddings + vector search in page indexes
    G-->>RR: Candidate pages + scores
    RR-->>FE: Paginated recommendations
    FE-->>U: Render recommendation cards

    U->>FE: Click recommendation card
    FE->>RR: POST /recommendations/visit
    RR->>G: MERGE (User)-[VISIT]->(Page), update visit props
    RR-->>FE: success
```

## 4) Graph Database Logical Scheme (Nodes and Relations)

```mermaid
erDiagram
    USER ||--o{ VISIT : performs
    PAGE ||--o{ VISIT : receives
    PAGE }o--o{ CATEGORY : IN_CATEGORY

    USER {
        string id PK
        string email
        float[] text_embedding
        float[] hybridEmbedding
        float[] sumWeightedTextEmbedding
        float totalWeight
    }

    PAGE {
        string url UK
        string title
        string meta_description
        string text_sample
        string image
        string ai_summary
        boolean is_unsafe
        float[] text_embedding
        float[] hybridEmbedding
    }

    CATEGORY {
        string name PK
        float[] text_embedding
        datetime createdAt
        datetime updatedAt
    }

    VISIT {
        string source
        float active_time
        float total_open_time
        datetime last_visited
        datetime[] visitedAt
        boolean tracked
    }
```

Typical relationship directions in code:
- `(User)-[:VISIT]->(Page)`
- `(Page)-[:IN_CATEGORY]->(Category)`

## 5) Flowchart (Raw Data Processing Algorithm)

```mermaid
flowchart TD
    A["Receive message from raw_data_queue] --> B[Parse payload and extract user + entries"]
    B --> C{Any valid entries?}
    C -- No --> Z[Skip message]
    C -- Yes --> D[Ensure User node exists/updated]

    D --> E[For each entry: normalize URL]
    E --> F{Canonical URL exists?}
    F -- No --> N[Skip entry]
    F -- Yes --> G{Page exists in Neo4j?}

    G -- Yes --> H[Update Page metadata]
    G -- No --> I[Run filtration rules]
    I --> J{Should process?}
    J -- No --> N
    J -- Yes --> K[Categorize and summarize content]
    K --> L[Build embeddings for categories and page text]
    L --> M[Create Page + Category + IN_CATEGORY]

    H --> O[Prepare VISIT properties\n(active time, open time, timestamp)]
    M --> O
    O --> P{User id present?}
    P -- No --> Q[Finish entry]
    P -- Yes --> R[MERGE VISIT relation with additive metrics]
    R --> Q
    N --> Q
    Q --> S{More entries?}
    S -- Yes --> E
    S -- No --> T[Done]
```

## 6) Simple Interface Wireframes (2-3)

### Wireframe A: Home (unauthenticated)

```text
+--------------------------------------------------------------------------------+
| HEADER: Logo | Home | Recommendations | Statistics | Sign In                  |
+--------------------------------------------------------------------------------+
|                                                                            (bg)|
|                    [ AI-powered analytics badge ]                              |
|               Analyze your browser activity with Insights                       |
|      Smart assistant for personal recommendations and productivity stats        |
|                                                                                |
|   +---------------------------+    +---------------------------+               |
|   | Install Chrome Extension  |    | Secure SSO Login         |               |
|   | short help text           |    | short help text          |               |
|   +---------------------------+    +---------------------------+               |
|                                                                                |
|                     [ Sign in via Chrome Extension ]                            |
|                                                                                |
+--------------------------------------------------------------------------------+
```

### Wireframe B: Recommendations Page

```text
+--------------------------------------------------------------------------------+
| HEADER: Logo | Home | Recommendations* | Statistics | User                     |
+--------------------------------------------------------------------------------+
| Recommendations for you                                                        |
|--------------------------------------------------------------------------------|
| +-------------------+ +-------------------+ +-------------------+              |
| | image             | | image             | | image             |              |
| | page title        | | page title        | | page title        |              |
| | score + type      | | score + type      | | score + type      |              |
| | [Open]            | | [Open]            | | [Open]            |              |
| +-------------------+ +-------------------+ +-------------------+              |
| +-------------------+ +-------------------+ +-------------------+              |
| | ...               | | ...               | | ...               |              |
| +-------------------+ +-------------------+ +-------------------+              |
|                             [loading sentinel]                                  |
|                             [spinner / end text]                                |
+--------------------------------------------------------------------------------+
```

### Wireframe C: Statistics Dashboard

```text
+--------------------------------------------------------------------------------+
| HEADER: Logo | Home | Recommendations | Statistics* | User                     |
+--------------------------------------------------------------------------------+
| Your Analytics                                                                 |
|--------------------------------------------------------------------------------|
| +------------------+ +------------------+ +------------------+                 |
| | Total Visits     | | Unique Pages     | | Categories       |                 |
| | 1234             | | 321              | | 18               |                 |
| +------------------+ +------------------+ +------------------+                 |
|                                                                                |
| +----------------------------------+ +--------------------------------------+  |
| | Activity (7 days)                | | Interest Categories (donut)          |  |
| | [bar chart area]                 | | [donut chart area]                   |  |
| |                                  | |                                      |  |
| +----------------------------------+ +--------------------------------------+  |
+--------------------------------------------------------------------------------+
```
