# Database Architecture Overview

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Application                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  @app.post("/users/")                                            │
│  def create_user(name: str, session: Session = Depends(...)):   │
│      repo = UserRepository(session)                              │
│      return repo.create(username=name, email=...)              │
│                                                                   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
    ┌──────────────────────────────────┐
    │   FastAPI Dependency Injection   │
    │  session: Session = Depends(     │
    │    get_session()                 │
    │  )                               │
    └──────────────┬───────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────┐
    │   Database Session Management    │
    │                                  │
    │  database/session.py             │
    │  ├─ get_session()                │
    │  ├─ SessionLocal factory         │
    │  └─ Transaction handling         │
    └──────────────┬───────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────┐
    │   Repository Pattern             │
    │                                  │
    │  models/repositories.py          │
    │  ├─ UserRepository               │
    │  ├─ ConversationRepository       │
    │  ├─ MessageRepository            │
    │  └─ EmbeddingRepository          │
    │                                  │
    │  database/repository.py          │
    │  └─ BaseRepository (CRUD)        │
    └──────────────┬───────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────┐
    │   ORM Models                     │
    │                                  │
    │  models/database_models.py       │
    │  ├─ User                         │
    │  ├─ Conversation                 │
    │  ├─ Message                      │
    │  └─ Embedding                    │
    │                                  │
    │  database/base.py                │
    │  ├─ BaseModel (auto timestamps)  │
    │  └─ Base (declarative)           │
    └──────────────┬───────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────┐
    │   SQLAlchemy ORM Engine          │
    │                                  │
    │  database/connection.py          │
    │  ├─ DatabaseConnection (singleton)
    │  ├─ Engine creation              │
    │  ├─ Connection pooling           │
    │  └─ Health checks                │
    │                                  │
    │  database/migration.py           │
    │  ├─ Schema creation              │
    │  └─ Inspection utilities         │
    └──────────────┬───────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────┐
    │   Database Configuration         │
    │                                  │
    │  database/config.py              │
    │  ├─ DatabaseConfig               │
    │  ├─ DatabaseType enum            │
    │  ├─ Connection strings           │
    │  └─ Environment variables        │
    └──────────────┬───────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────────────────────────┐
    │          Database Drivers Layer                       │
    ├──────────────────────────────────────────────────────┤
    │                                                        │
    │  ┌─────────────┐  ┌──────────┐  ┌────────┐          │
    │  │   SQLite    │  │PostgreSQL│  │ MySQL  │          │
    │  │  (built-in) │  │(psycopg2)│  │(pymysql)
    │  │             │  │          │  │        │          │
    │  │ ./data/     │  │  TCP:5432│  │TCP:3306
    │  │ grace.db    │  │          │  │        │          │
    │  └─────────────┘  └──────────┘  └────────┘          │
    │                                                        │
    └──────────────────────────────────────────────────────┘
                        │
                        ▼
        ┌──────────────────────────────────┐
        │      Physical Database           │
        └──────────────────────────────────┘
```

## Data Flow Example: Creating a User

```
1. HTTP Request
   POST /users?username=john&email=john@example.com
        │
        ▼
2. FastAPI Route Handler
   @app.post("/users/")
   def create_user(username: str, session: Session = Depends(get_session)):
        │
        ▼
3. Dependency Injection
   get_session() yields new Session
        │
        ▼
4. Repository Pattern
   repo = UserRepository(session)
   user = repo.create(username=username, email=email)
        │
        ▼
5. Repository Operations
   - Validate input
   - Create model instance
   - session.add(instance)
   - session.commit()
   - session.refresh(instance)
        │
        ▼
6. ORM Conversion
   BaseModel instance
   - User object with id, created_at, updated_at
        │
        ▼
7. SQLAlchemy
   - Generate SQL INSERT statement
   - Use database engine
        │
        ▼
8. Database
   - INSERT INTO users (username, email, created_at, updated_at)
   - VALUES ('john', 'john@example.com', timestamp, timestamp)
        │
        ▼
9. Response
   200 OK
   {
     "id": 1,
     "username": "john",
     "email": "john@example.com",
     "created_at": "2025-12-11T18:35:00",
     "updated_at": "2025-12-11T18:35:00"
   }
```

## Connection Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Startup                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Load configuration from .env
│     DATABASE_TYPE=postgresql
│     DATABASE_HOST=localhost
│                                                               │
│  2. Create DatabaseConfig
│     config = DatabaseConfig.from_env()
│                                                               │
│  3. Initialize DatabaseConnection (singleton)
│     DatabaseConnection.initialize(config)
│     ├─ Create connection string
│     ├─ Create SQLAlchemy engine
│     └─ Enable features (foreign keys, pooling, etc.)
│                                                               │
│  4. Initialize SessionLocal factory
│     initialize_session_factory()
│     └─ Bind engine to session maker
│                                                               │
│  5. Create database schema
│     create_tables()
│     └─ Create tables from Base.metadata
│                                                               │
│  6. Application ready!
│                                                               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Request Handling                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  For each HTTP Request:
│                                                               │
│  1. get_session() dependency called
│     ├─ Get engine from DatabaseConnection
│     ├─ Create new session from SessionLocal factory
│     └─ Provide to route handler
│                                                               │
│  2. Route handler executes
│     ├─ Create repository with session
│     ├─ Perform database operations
│     └─ Operations are NOT committed yet
│                                                               │
│  3. Route handler returns
│     ├─ session.commit() if success
│     ├─ session.rollback() if exception
│     └─ session.close() always
│                                                               │
│  4. Response sent to client
│                                                               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  Application Shutdown                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Application receives shutdown signal
│                                                               │
│  2. Lifespan context manager exit
│     DatabaseConnection.close()
│     ├─ Dispose of all connections
│     ├─ Close connection pool
│     └─ Release resources
│                                                               │
│  3. Application stops
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Connection Pooling Visualization

### SQLite (StaticPool)

```
┌────────────────────────────────┐
│      SQLite Database           │
│  (Single file: grace.db)       │
├────────────────────────────────┤
│                                │
│  ┌──────────────────────────┐  │
│  │  Single Connection       │  │
│  │  (StaticPool)            │  │
│  └──────────────────────────┘  │
│         ▲         │             │
│         │         ▼             │
│  All requests reuse same connection
│  Fastest for single-threaded access
│                                │
└────────────────────────────────┘
```

### PostgreSQL/MySQL (QueuePool)

```
┌────────────────────────────────────────┐
│        PostgreSQL/MySQL Database       │
├────────────────────────────────────────┤
│                                        │
│  Pool Configuration:                   │
│  - pool_size: 5 (default connections)  │
│  - max_overflow: 10 (extra connections)│
│  - pool_pre_ping: true (health check)  │
│                                        │
│  ┌────────────────────────────────┐   │
│  │  Connection Pool (QueuePool)   │   │
│  ├────────────────────────────────┤   │
│  │ ┌─┐ ┌─┐ ┌─┐ ┌─┐ ┌─┐          │   │
│  │ │1│ │2│ │3│ │4│ │5│  (ready) │   │
│  │ └─┘ └─┘ └─┘ └─┘ └─┘          │   │
│  │                              │   │
│  │ +Overflow: ┌─┐ ┌─┐ ┌─┐       │   │
│  │            │6│ │7│ │8│ ...   │   │
│  │            └─┘ └─┘ └─┘       │   │
│  └────────────────────────────────┘   │
│         ▲         │                    │
│         │         ▼                    │
│  Request pool.connect() → get connection
│  Request pool.release() → return connection
│                                        │
│  Health checks with pool_pre_ping      │
│  Prevents stale connections            │
│                                        │
└────────────────────────────────────────┘
```

## Database Schema Relationships

```
users
┌──────────────┐
│ id (PK)      │◄─────────┐
│ username     │          │ 1
│ email        │          │
│ full_name    │          │
│ is_active    │          │
│ created_at   │          │
│ updated_at   │          │
└──────────────┘          │
                          │ 1:N
                          │
                    conversations
                    ┌──────────────┐
                    │ id (PK)      │◄─────────┐
                    │ user_id (FK)─┘          │ 1
                    │ title        │          │
                    │ description  │          │
                    │ model        │          │
                    │ created_at   │          │
                    │ updated_at   │          │
                    └──────────────┘          │
                                             │ 1:N
                                             │
                                        messages
                                        ┌──────────────┐
                                        │ id (PK)      │
                                        │ conversation │─┘
                                        │  _id (FK)    │
                                        │ role         │
                                        │ content      │
                                        │ tokens       │
                                        │ created_at   │
                                        │ updated_at   │
                                        └──────────────┘

embeddings
┌──────────────┐
│ id (PK)      │
│ text         │
│ embedding    │
│ dimension    │
│ model        │
│ source       │
│ created_at   │
│ updated_at   │
└──────────────┘

Legend:
  PK = Primary Key
  FK = Foreign Key
  1:N = One-to-Many relationship
```

## Configuration Switching

```
Development (SQLite)
├─ .env: DATABASE_TYPE=sqlite
├─ No server setup needed
├─ File: ./data/grace.db
└─ Instant startup

          │
          ▼ (Update .env)

Production (PostgreSQL)
├─ .env: DATABASE_TYPE=postgresql
├─ DATABASE_HOST=prod-db.example.com
├─ DATABASE_PORT=5432
├─ Setup PostgreSQL server
└─ Install psycopg2-binary

          │
          ▼ (Same application code!)

Code changes: 0
Configuration changes: Database credentials
Database drivers: Already installed
```

## Module Dependencies

```
FastAPI Application
    │
    ├─ settings.py (reads DATABASE_* env vars)
    │
    ├─ database/__init__.py
    │   ├─ database/config.py
    │   │   └─ ConfigType, DatabaseConfig
    │   │
    │   ├─ database/connection.py
    │   │   ├─ DatabaseConnection (uses config)
    │   │   └─ (creates engine)
    │   │
    │   ├─ database/session.py
    │   │   ├─ SessionLocal (uses engine from connection)
    │   │   └─ get_session() (creates sessions)
    │   │
    │   ├─ database/base.py
    │   │   └─ BaseModel, Base (independent)
    │   │
    │   ├─ database/migration.py
    │   │   ├─ create_tables() (uses engine)
    │   │   └─ inspection utilities
    │   │
    │   └─ database/repository.py
    │       └─ BaseRepository (uses sessions)
    │
    ├─ models/database_models.py
    │   └─ (extends BaseModel from database/base.py)
    │
    └─ models/repositories.py
        ├─ (extends BaseRepository)
        └─ (uses sessions from database/session.py)
```

## Type Safety and Error Handling

```
Try-Catch Flow in get_session()
│
├─ Create new session from SessionLocal
│
├─ TRY:
│   ├─ Yield session to route handler
│   │  (route handler uses session)
│   │
│   └─ Route handler completes
│       ├─ Success: session.commit()
│       │  (persist all changes)
│       │
│       └─ Exception: session.rollback()
│          (discard all changes)
│
└─ FINALLY:
   └─ session.close()
      (clean up resources)


Type Hints Throughout

config: DatabaseConfig
engine: Engine
session: Session
user: User  or  Optional[User]
users: List[User]
repo: UserRepository

→ IDE autocomplete
→ Type checking with mypy
→ Better error messages
```

---

This architecture provides:

✅ **Flexibility** - Switch databases by changing one setting
✅ **Simplicity** - Dependency injection in FastAPI
✅ **Reusability** - Generic repository pattern
✅ **Safety** - Automatic transaction management
✅ **Performance** - Connection pooling
✅ **Reliability** - Health checks and error handling
✅ **Scalability** - Works with SQLite to enterprise databases
