# GRACE Architecture

## System Overview

GRACE (Guided Reasoning and Autonomous Cognitive Engine) is an enterprise-grade AI system built on a modular, scalable architecture.

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI[React UI]
        SW[Service Worker]
        Store[Zustand Store]
    end

    subgraph "API Gateway"
        NGINX[NGINX/Ingress]
        CORS[CORS Middleware]
        RL[Rate Limiter]
        Auth[Auth Middleware]
    end

    subgraph "Backend Services"
        API[FastAPI Server]
        WS[WebSocket Handler]
        SSE[SSE Streaming]
    end

    subgraph "Core Modules"
        Chat[Chat Engine]
        RAG[RAG Pipeline]
        Cognitive[Cognitive Layer]
        Learning[Learning Memory]
        Agent[Agent Framework]
    end

    subgraph "Data Layer"
        PG[(PostgreSQL)]
        QD[(Qdrant Vector DB)]
        Redis[(Redis Cache)]
    end

    subgraph "AI Services"
        Ollama[Ollama LLM]
        Embed[Embedding Model]
    end

    UI --> NGINX
    SW --> NGINX
    Store --> UI
    NGINX --> CORS
    CORS --> RL
    RL --> Auth
    Auth --> API
    Auth --> WS
    Auth --> SSE

    API --> Chat
    API --> RAG
    API --> Cognitive
    API --> Learning
    API --> Agent

    Chat --> Ollama
    RAG --> QD
    RAG --> Embed
    RAG --> Ollama
    Learning --> PG
    Learning --> QD

    API --> PG
    API --> Redis
```

## Component Architecture

### Frontend Architecture

```mermaid
graph LR
    subgraph "React Application"
        App[App.jsx]
        Router[React Router]

        subgraph "Pages"
            Chat[ChatPage]
            Files[FileBrowser]
            Dash[Dashboard]
            Settings[Settings]
        end

        subgraph "State Management"
            Zustand[Zustand Stores]
            LocalStorage[LocalStorage]
        end

        subgraph "Services"
            API[API Client]
            WS[WebSocket Client]
        end
    end

    App --> Router
    Router --> Chat
    Router --> Files
    Router --> Dash
    Router --> Settings

    Chat --> Zustand
    Chat --> API
    Chat --> WS

    Zustand --> LocalStorage
```

### Backend Architecture

```mermaid
graph TB
    subgraph "FastAPI Application"
        Main[app.py]

        subgraph "API Routers"
            ChatAPI[/api/chat]
            IngestAPI[/api/ingest]
            RetrieveAPI[/api/retrieve]
            HealthAPI[/api/health]
            MetricsAPI[/metrics]
        end

        subgraph "Middleware Stack"
            Security[Security Headers]
            RateLimit[Rate Limiting]
            Logging[Structured Logging]
            Genesis[Genesis Key Tracking]
        end

        subgraph "Core Services"
            OllamaClient[Ollama Client]
            Embedder[Async Embedder]
            VectorDB[Qdrant Client]
            DBSession[DB Session]
        end
    end

    Main --> Security
    Security --> RateLimit
    RateLimit --> Logging
    Logging --> Genesis

    Genesis --> ChatAPI
    Genesis --> IngestAPI
    Genesis --> RetrieveAPI
    Genesis --> HealthAPI
    Genesis --> MetricsAPI

    ChatAPI --> OllamaClient
    IngestAPI --> Embedder
    IngestAPI --> VectorDB
    RetrieveAPI --> VectorDB
    RetrieveAPI --> OllamaClient
```

### RAG Pipeline

```mermaid
sequenceDiagram
    participant User
    participant API
    participant Embedder
    participant VectorDB
    participant LLM

    User->>API: Query
    API->>Embedder: Generate Embedding
    Embedder-->>API: Query Vector
    API->>VectorDB: Semantic Search
    VectorDB-->>API: Relevant Documents
    API->>API: Build RAG Prompt
    API->>LLM: Generate Response
    LLM-->>API: Streamed Response
    API-->>User: SSE Stream
```

### Learning Memory System

```mermaid
graph TB
    subgraph "Learning Memory"
        Input[New Information]

        subgraph "Processing"
            Extract[Pattern Extraction]
            Conflict[Conflict Detection]
            Trust[Trust Scoring]
        end

        subgraph "Storage"
            ShortTerm[Short-term Memory]
            LongTerm[Long-term Memory]
            Episodic[Episodic Memory]
        end

        subgraph "Retrieval"
            Semantic[Semantic Search]
            Temporal[Temporal Search]
            Contextual[Context Matching]
        end
    end

    Input --> Extract
    Extract --> Conflict
    Conflict --> Trust
    Trust --> ShortTerm
    ShortTerm --> LongTerm
    LongTerm --> Episodic

    Semantic --> LongTerm
    Temporal --> Episodic
    Contextual --> ShortTerm
```

## Data Flow

### Chat Message Flow

```mermaid
sequenceDiagram
    participant Client
    participant WebSocket
    participant ChatEngine
    participant RAG
    participant Ollama
    participant Memory

    Client->>WebSocket: Connect
    WebSocket-->>Client: Connected

    Client->>WebSocket: Send Message
    WebSocket->>ChatEngine: Process Message

    ChatEngine->>RAG: Get Context
    RAG-->>ChatEngine: Relevant Docs

    ChatEngine->>Memory: Get History
    Memory-->>ChatEngine: Chat History

    ChatEngine->>Ollama: Generate (Stream)

    loop Streaming
        Ollama-->>ChatEngine: Token
        ChatEngine-->>WebSocket: Token
        WebSocket-->>Client: Token
    end

    ChatEngine->>Memory: Store Exchange
    Memory-->>ChatEngine: Stored

    WebSocket-->>Client: Complete
```

### Document Ingestion Flow

```mermaid
sequenceDiagram
    participant User
    participant API
    participant Parser
    participant Chunker
    participant Embedder
    participant VectorDB
    participant Metadata

    User->>API: Upload Document
    API->>Parser: Parse Document
    Parser-->>API: Raw Text

    API->>Chunker: Split into Chunks
    Chunker-->>API: Text Chunks

    loop Each Chunk
        API->>Embedder: Generate Embedding
        Embedder-->>API: Vector
        API->>VectorDB: Store Vector
    end

    API->>Metadata: Store Document Info
    Metadata-->>API: Stored

    API-->>User: Ingestion Complete
```

## Deployment Architecture

### Docker Compose (Development)

```mermaid
graph TB
    subgraph "Docker Network"
        Frontend[Frontend:3000]
        Backend[Backend:8000]
        Postgres[PostgreSQL:5432]
        Qdrant[Qdrant:6333]
        Ollama[Ollama:11434]
        Redis[Redis:6379]
    end

    Frontend --> Backend
    Backend --> Postgres
    Backend --> Qdrant
    Backend --> Ollama
    Backend --> Redis
```

### Kubernetes (Production)

```mermaid
graph TB
    subgraph "Kubernetes Cluster"
        subgraph "Ingress"
            NGINX[NGINX Ingress]
        end

        subgraph "Application Pods"
            FE1[Frontend Pod 1]
            FE2[Frontend Pod 2]
            BE1[Backend Pod 1]
            BE2[Backend Pod 2]
        end

        subgraph "Services"
            FESvc[Frontend Service]
            BESvc[Backend Service]
        end

        subgraph "Data Pods"
            PG[PostgreSQL]
            QD[Qdrant]
            OL[Ollama]
            RD[Redis]
        end

        subgraph "Persistent Volumes"
            PGV[(PG Volume)]
            QDV[(Qdrant Volume)]
            OLV[(Ollama Volume)]
        end
    end

    NGINX --> FESvc
    NGINX --> BESvc
    FESvc --> FE1
    FESvc --> FE2
    BESvc --> BE1
    BESvc --> BE2

    BE1 --> PG
    BE2 --> PG
    BE1 --> QD
    BE2 --> QD
    BE1 --> OL
    BE2 --> OL
    BE1 --> RD
    BE2 --> RD

    PG --> PGV
    QD --> QDV
    OL --> OLV
```

## Security Architecture

```mermaid
graph TB
    subgraph "Security Layers"
        subgraph "Transport"
            TLS[TLS/SSL]
        end

        subgraph "Application"
            Auth[JWT Authentication]
            RBAC[Role-Based Access]
            API_Key[API Key Validation]
        end

        subgraph "Request Processing"
            RateLimit[Rate Limiting]
            Validation[Input Validation]
            Sanitization[Data Sanitization]
        end

        subgraph "Data"
            Encryption[At-Rest Encryption]
            Secrets[Secret Management]
        end
    end

    TLS --> Auth
    Auth --> RBAC
    RBAC --> API_Key
    API_Key --> RateLimit
    RateLimit --> Validation
    Validation --> Sanitization
    Sanitization --> Encryption
    Encryption --> Secrets
```

## Module Dependencies

```mermaid
graph LR
    subgraph "Core"
        Settings[Settings]
        DB[Database]
        Ollama[Ollama Client]
    end

    subgraph "Services"
        Chat[Chat Service]
        RAG[RAG Service]
        Ingest[Ingest Service]
        Learning[Learning Service]
    end

    subgraph "API"
        Routers[API Routers]
        Middleware[Middleware]
    end

    Settings --> DB
    Settings --> Ollama
    DB --> Chat
    DB --> Learning
    Ollama --> Chat
    Ollama --> RAG
    DB --> RAG
    DB --> Ingest

    Chat --> Routers
    RAG --> Routers
    Ingest --> Routers
    Learning --> Routers

    Middleware --> Routers
```

## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19, Material-UI, Zustand |
| Backend | Python 3.11, FastAPI, Pydantic |
| Database | PostgreSQL 15, SQLAlchemy |
| Vector DB | Qdrant |
| LLM | Ollama (Mistral, Llama, etc.) |
| Cache | Redis |
| Container | Docker, Kubernetes |
| CI/CD | Genesis CI (native) |
| Monitoring | Prometheus, Grafana |
