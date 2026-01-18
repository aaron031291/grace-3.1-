# GRACE 3.1 - Complete System Overview

## 🏗️ Architecture at a Glance

GRACE (Graceful Autonomous Cognitive Engine) is a comprehensive AI system built around **autonomous learning**, **complete audit trails**, and **cognitive decision-making**. The system follows a layered architecture with multiple integrated subsystems.

---

## 📐 System Layers

### **1. Frontend Layer** (React + Vite)
- **Location**: `frontend/`
- **Purpose**: User interface for interacting with all GRACE capabilities
- **Key Components**:
  - Chat interface with folder-scoped conversations
  - Knowledge base management
  - Genesis Key tracking dashboard
  - Cognitive engine visualization
  - Monitoring and telemetry dashboards
  - Version control interface
  - Voice interaction (STT/TTS)
  - Multiple specialized tabs (Librarian, Sandbox Lab, ML Intelligence, etc.)

### **2. API Layer** (FastAPI)
- **Location**: `backend/app.py` + `backend/api/`
- **Purpose**: RESTful API exposing all system capabilities
- **Key Features**:
  - **48+ API routers** covering all subsystems
  - RAG-first chat (rejects queries without knowledge base context)
  - Folder-scoped chat conversations
  - Comprehensive health checks
  - Security middleware (CORS, rate limiting, validation)
  - Genesis Key middleware (automatic tracking)

### **3. Core Systems**

#### **A. Layer 1 - Universal Input & Communication**
- **Location**: `backend/layer1/`
- **Purpose**: Unified input handling and autonomous component communication
- **Components**:
  - **Message Bus**: Central routing for all component communication
  - **8 Input Sources**:
    1. User inputs (chat, commands, UI interactions)
    2. File uploads
    3. External APIs
    4. Web scraping/HTML
    5. Memory mesh
    6. Learning memory
    7. Whitelist (human-curated learning)
    8. System events
  - **Connectors**: Memory Mesh, Genesis Keys, RAG, Ingestion, LLM Orchestration, Version Control, Neuro-Symbolic (optional)

#### **B. Genesis Key System - Universal Tracking**
- **Location**: `backend/genesis/`
- **Purpose**: Complete audit trail for every action, change, and decision
- **Features**:
  - Automatic tracking of all operations (what, where, when, why, who, how)
  - File version tracking
  - Git integration (symbiotic version control)
  - Autonomous trigger system
  - Complete provenance tracking
  - Middleware for automatic API tracking

#### **C. Cognitive Engine - Decision Making**
- **Location**: `backend/cognitive/`
- **Purpose**: Structured decision-making with OODA loop and invariants
- **Components**:
  - **OODA Loop**: Observe → Orient → Decide → Act
  - **12 Invariants**: Core principles enforced across all operations
  - **Ambiguity Accounting**: Tracks uncertainty in decisions
  - **Decision Logging**: Complete audit trail of reasoning
  - **Decorators**: Easy integration with existing code

#### **D. Learning & Memory Systems**
- **Memory Mesh**: `backend/cognitive/memory_mesh_integration.py`
  - Immutable learning memory
  - Trust scoring
  - Procedural memory storage
- **Autonomous Learning**: `backend/cognitive/continuous_learning_orchestrator.py`
  - Continuous learning from new data
  - Multi-process learning agents
  - Sandbox lab integration
- **Active Learning**: Proactive learning from user interactions

#### **E. Retrieval & Knowledge**
- **RAG System**: `backend/retrieval/`
  - Trust-aware retrieval
  - Hybrid search (semantic + keyword)
  - Reranking with confidence scores
- **Ingestion Pipeline**: `backend/ingestion/`
  - Document processing
  - Chunking and embedding
  - Automatic indexing
- **Librarian System**: `backend/librarian/`
  - Document categorization
  - Relationship detection
  - Tag management
  - Approval workflows

#### **F. LLM Orchestration**
- **Location**: `backend/llm_orchestrator/`
- **Purpose**: Multi-LLM coordination and skill-based routing
- **Features**:
  - Multiple LLM support (Ollama-based)
  - Skill-based task routing
  - Collaboration modes
  - Fine-tuning integration
  - Cognitive constraints enforcement

#### **G. ML Intelligence**
- **Location**: `backend/ml_intelligence/`
- **Components**:
  - Neural Trust Network
  - Multi-Armed Bandit optimization
  - Meta-Learning system
  - Integration orchestrator

#### **H. Neuro-Symbolic AI - Unified Reasoning**
- **Location**: `backend/ml_intelligence/neuro_symbolic_reasoner.py` + `backend/layer1/components/neuro_symbolic_connector.py`
- **Purpose**: True bidirectional integration of neural (fuzzy) and symbolic (precise) reasoning
- **Architecture**:
  - **Neural Component** (Pattern Learning):
    - Vector embeddings in Qdrant
    - Semantic similarity search
    - Pattern recognition
    - Probabilistic matching
  - **Symbolic Component** (Explicit Knowledge):
    - Trust-scored facts in `learning_examples` table
    - Logic-based reasoning
    - Deterministic trust calculations
    - Provenance tracking
  - **Unified Integration**:
    - Bidirectional cross-information (neural ↔ symbolic)
    - Joint inference combining both approaches
    - Trust-weighted fusion
    - Context-aware reasoning
- **Features**:
  - Neural finds similar concepts (fuzzy search)
  - Symbolic provides trusted facts (precise knowledge)
  - Both inform each other in joint inference
  - Automatic rule generation from neural patterns
  - Trust-aware embeddings
  - Layer 1 connector for autonomous integration

---

## 🔄 Data Flow

### **Input → Processing → Output**

```
User Input / File Upload / API Data
    ↓
Layer 1 Message Bus (routes to appropriate handler)
    ↓
Genesis Key Created (automatic tracking)
    ↓
Cognitive Engine (OODA loop + invariants)
    ↓
Processing (RAG retrieval, LLM orchestration, learning)
    ↓
Output (response, file processing, learning memory update)
    ↓
Genesis Key Updated (complete audit trail)
```

### **Autonomous Learning Cycle**

```
New Data Detected (file watcher / auto-ingestion)
    ↓
Ingestion Pipeline (chunking, embedding)
    ↓
Vector Database (Qdrant)
    ↓
Autonomous Learning Triggered
    ↓
Learning Agents (Study, Practice, Mirror)
    ↓
Sandbox Lab (experiments)
    ↓
Approval Workflow (human-in-the-loop)
    ↓
Learning Memory Updated
```

### **Neuro-Symbolic Reasoning Flow**

```
User Query
    ↓
┌─────────────────────────────────────┐
│   Neuro-Symbolic Reasoner           │
├─────────────────────────────────────┤
│                                     │
│  Neural Search (Fuzzy)             │
│  ↓ Find similar concepts            │
│  ↓ Pattern matching                  │
│                                     │
│  Symbolic Query (Precise)           │
│  ↓ Get trusted facts                │
│  ↓ Logic reasoning                   │
│                                     │
│  Cross-Inform                       │
│  ↓ Neural ranks symbolic            │
│  ↓ Symbolic weights neural          │
│                                     │
│  Joint Fusion                       │
│  ↓ Trust-weighted combination       │
│  ↓ Context-aware reasoning          │
│                                     │
└─────────────────────────────────────┘
    ↓
Unified Result (Neural + Symbolic)
```

---

## 🗄️ Data Storage

### **1. SQLite/PostgreSQL Database**
- **Location**: `backend/data/grace.db` (default)
- **Stores**:
  - Chats and messages
  - Documents metadata
  - Genesis Keys (complete audit trail)
  - User profiles
  - Librarian tags and relationships
  - Learning memory
  - System configuration

### **2. Qdrant Vector Database**
- **Purpose**: Semantic search and embeddings
- **Stores**:
  - Document chunks with embeddings
  - Metadata for retrieval
  - Trust scores

### **3. File System**
- **Knowledge Base**: `backend/knowledge_base/`
  - Source documents
  - Organized by folders
  - Auto-ingestion monitoring

---

## 🔧 Key Technologies

- **Backend**: Python 3.x, FastAPI, SQLAlchemy
- **Frontend**: React, Vite
- **LLM**: Ollama (local LLM hosting)
- **Embeddings**: Custom embedding models (qwen_4b default)
- **Vector DB**: Qdrant
- **Database**: SQLite (default) or PostgreSQL
- **Version Control**: Git integration

---

## 🚀 Startup Sequence

1. **Database Initialization**: Connection, tables creation
2. **Embedding Model Loading**: Pre-loads at startup
3. **Ollama Check**: Verifies LLM service availability
4. **Qdrant Check**: Verifies vector database connection
5. **File Watcher Start**: Monitors knowledge base for changes
6. **ML Intelligence Init**: Loads ML orchestrator
7. **Auto-Ingestion Start**: Background monitoring of knowledge base
8. **Continuous Learning Start**: Autonomous learning orchestrator
9. **API Ready**: All routers registered, middleware active

---

## 🎯 Core Principles

1. **RAG-First**: All responses require knowledge base context
2. **Complete Audit Trail**: Every action tracked via Genesis Keys
3. **Cognitive Decision-Making**: OODA loop + invariants for all operations
4. **Autonomous Learning**: Continuous improvement from new data
5. **Trust & Truth**: Layer 1 foundation ensures data integrity
6. **Human-in-the-Loop**: Governance framework for critical decisions
7. **Neuro-Symbolic Architecture**: Hybrid system combining neural (pattern learning) and symbolic (logic-based reasoning) approaches

---

## 📊 System Capabilities

### **User-Facing**
- ✅ Chat with knowledge base (folder-scoped or general)
- ✅ Document upload and ingestion
- ✅ Voice interaction (STT/TTS)
- ✅ Version control visualization
- ✅ Genesis Key tracking dashboard
- ✅ Monitoring and health metrics
- ✅ Knowledge base management

### **Autonomous**
- ✅ Automatic file ingestion
- ✅ Continuous learning from new data
- ✅ Self-healing systems
- ✅ Autonomous experiments (sandbox lab)
- ✅ Proactive learning
- ✅ Diagnostic machine (4-layer)

### **Advanced**
- ✅ Multi-LLM orchestration
- ✅ ML Intelligence (neural trust, bandits, meta-learning)
- ✅ **Neuro-Symbolic AI** (unified neural + symbolic reasoning)
- ✅ Cognitive engine with OODA loop
- ✅ Librarian system (categorization, relationships)
- ✅ CI/CD integration
- ✅ Governance framework (3-pillar)
- ✅ Telemetry and drift detection

---

## 🔐 Security & Governance

- **Security Middleware**: CORS, rate limiting, request validation
- **Genesis Keys**: Complete audit trail
- **Governance Framework**: Three-pillar system (technical, ethical, operational)
- **Human-in-the-Loop**: Approval workflows for critical actions
- **Trust Scoring**: Confidence levels for all operations

---

## 📈 Monitoring & Observability

- **Health Checks**: Comprehensive service health monitoring
- **Telemetry**: System metrics and drift detection
- **KPI Dashboard**: Performance indicators
- **Diagnostic Machine**: 4-layer diagnostic system
- **Prometheus Metrics**: `/metrics` endpoint

---

## 🎓 Learning & Improvement

- **Memory Mesh**: Immutable learning memory
- **Autonomous Learning**: Continuous improvement
- **Sandbox Lab**: Safe experimentation
- **Whitelist Pipeline**: Human-curated learning
- **Proactive Learning**: Task queue system

---

## 🧠 Neuro-Symbolic AI Deep Dive

### **What Makes GRACE Neuro-Symbolic?**

GRACE is **NOT** just an LLM with RAG. It's a true **Neuro-Symbolic AI** system that combines:

1. **Neural Component** (Fuzzy, Pattern-Based):
   - Vector embeddings for semantic similarity
   - Pattern recognition in data
   - Probabilistic matching
   - Learning from examples

2. **Symbolic Component** (Precise, Rule-Based):
   - Trust-scored facts in database
   - Logic-based reasoning
   - Deterministic trust calculations
   - Explicit knowledge graphs

3. **Bidirectional Integration**:
   - Neural informs symbolic (similarity ranking)
   - Symbolic informs neural (trust weighting)
   - Joint inference combining both
   - Trust-weighted fusion

### **Key Neuro-Symbolic Components**

- **NeuroSymbolicReasoner** (`backend/ml_intelligence/neuro_symbolic_reasoner.py`):
  - Unified reasoning system
  - Combines neural search + symbolic query
  - Cross-information between components
  - Trust-weighted fusion

- **NeuroSymbolicConnector** (`backend/layer1/components/neuro_symbolic_connector.py`):
  - Layer 1 integration
  - Autonomous reasoning on queries
  - Automatic rule generation
  - Message bus integration

- **Trust-Aware Embeddings**:
  - Embeddings that incorporate symbolic knowledge
  - Trust scores influence similarity calculations
  - Hybrid neural-symbolic search

### **Layer 2 Note**

Layer 2 is referenced in some documentation but appears to be a conceptual layer rather than a separate code directory. The system architecture primarily uses:
- **Layer 1**: Universal input and communication layer (implemented in `backend/layer1/`)
- **Neuro-Symbolic AI**: Integrated throughout the system via connectors and reasoners

---

This system represents a complete autonomous AI platform with full audit trails, cognitive decision-making, continuous learning capabilities, and true neuro-symbolic AI architecture.
