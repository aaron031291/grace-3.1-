# Database Interface Guide

## Overview

A comprehensive SQLAlchemy-based database interface supporting multiple SQL databases:

- **SQLite** (default, no setup required)
- **PostgreSQL**
- **MySQL / MariaDB**

## Project Structure

```
database/
├── __init__.py           # Package exports
├── config.py             # Database configuration
├── base.py               # Base models and ORM classes
├── connection.py         # Connection management & engine
├── session.py            # Session factory and dependency injection
├── repository.py         # Base repository for CRUD operations
└── migration.py          # Schema creation and migration utilities

models/
├── database_models.py    # Example ORM models (User, Conversation, etc.)
└── repositories.py       # Example repository implementations
```

## Configuration

### Environment Variables

Configure your database via `.env` file:

```env
# Database Type (sqlite, postgresql, mysql, mariadb)
DATABASE_TYPE=sqlite

# For SQLite
DATABASE_PATH=./data/grace.db

# For PostgreSQL/MySQL (optional if using SQLite)
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_USER=grace_user
DATABASE_PASSWORD=your_password
DATABASE_NAME=grace

# Enable SQL query logging
DATABASE_ECHO=false
```

### Programmatic Configuration

```python
from database.config import DatabaseConfig, DatabaseType
from database.connection import DatabaseConnection
from database.session import initialize_session_factory
from database.migration import create_tables

# Create configuration
config = DatabaseConfig(
    db_type=DatabaseType.SQLITE,
    database_path="./data/grace.db",
)

# Or load from environment variables
config = DatabaseConfig.from_env()

# Initialize database connection
DatabaseConnection.initialize(config)

# Initialize session factory
initialize_session_factory()

# Create all tables
create_tables()
```

## Usage Examples

### 1. Basic CRUD Operations with Repository

```python
from sqlalchemy.orm import Session
from database.session import get_session
from models.database_models import User
from models.repositories import UserRepository

# Using with FastAPI dependency injection
from fastapi import Depends

@app.post("/users/")
def create_user(name: str, email: str, session: Session = Depends(get_session)):
    repo = UserRepository(session)
    user = repo.create(username=name, email=email)
    return user.to_dict()

@app.get("/users/{user_id}")
def get_user(user_id: int, session: Session = Depends(get_session)):
    repo = UserRepository(session)
    user = repo.get(user_id)
    return user.to_dict() if user else None

@app.put("/users/{user_id}")
def update_user(user_id: int, name: str, session: Session = Depends(get_session)):
    repo = UserRepository(session)
    user = repo.update(user_id, username=name)
    return user.to_dict() if user else None

@app.delete("/users/{user_id}")
def delete_user(user_id: int, session: Session = Depends(get_session)):
    repo = UserRepository(session)
    success = repo.delete(user_id)
    return {"deleted": success}
```

### 2. Querying with Filters

```python
from models.repositories import UserRepository

# Get user by username
user = repo.get_by_username("john_doe")

# Get all active users
active_users = repo.get_active_users()

# Filter with multiple conditions
users = repo.filter(is_active=True)

# Count records
total_users = repo.count()

# Check if exists
exists = repo.exists(email="john@example.com")
```

### 3. Working with Relationships

```python
from models.database_models import User, Conversation

# Access related data
user = session.query(User).filter(User.id == 1).first()

# Get all conversations for a user
conversations = user.conversations

# Create related data
conversation = Conversation(
    user_id=user.id,
    title="Chat with AI",
    model="mistral:7b"
)
session.add(conversation)
session.commit()
```

### 4. Bulk Operations

```python
# Bulk create
users = [
    User(username="user1", email="user1@example.com"),
    User(username="user2", email="user2@example.com"),
]
repo.bulk_create(users)

# Bulk delete
deleted_count = repo.bulk_delete([1, 2, 3])

# Clear all records (be careful!)
total_deleted = repo.clear()
```

### 5. Database Initialization in App Startup

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from database.config import DatabaseConfig
from database.connection import DatabaseConnection
from database.session import initialize_session_factory
from database.migration import create_tables

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    config = DatabaseConfig.from_env()
    DatabaseConnection.initialize(config)
    initialize_session_factory()
    create_tables()
    yield
    # Shutdown
    DatabaseConnection.close()

app = FastAPI(lifespan=lifespan)
```

## Creating Custom Models

Extend `BaseModel` from `database.base`:

```python
from sqlalchemy import Column, String, Text, Float, Index
from database.base import BaseModel

class Document(BaseModel):
    """Custom model for documents."""
    __tablename__ = "documents"

    title = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)
    relevance_score = Column(Float, default=0.0)

    __table_args__ = (
        Index("idx_category_score", "category", "relevance_score"),
    )
```

## Creating Custom Repositories

Extend `BaseRepository` for specialized queries:

```python
from database.repository import BaseRepository
from models.database_models import Document

class DocumentRepository(BaseRepository[Document]):
    """Repository for Document operations."""

    def __init__(self, session: Session):
        super().__init__(session, Document)

    def get_by_category(self, category: str):
        """Custom query - get documents by category."""
        return self.filter(category=category)

    def get_top_relevant(self, limit: int = 10):
        """Custom query - get top documents by relevance."""
        return (
            self.session.query(Document)
            .order_by(Document.relevance_score.desc())
            .limit(limit)
            .all()
        )
```

## Database Migration and Schema Management

### Create Tables

```python
from database.migration import create_tables

# Create all tables defined in Base metadata
create_tables()
```

### Check Table Existence

```python
from database.migration import table_exists, get_all_tables

# Check if specific table exists
if table_exists("users"):
    print("Users table exists")

# Get all tables
tables = get_all_tables()
print(f"Database tables: {tables}")
```

### Get Schema Information

```python
from database.migration import get_table_columns, get_db_schema

# Get columns for specific table
columns = get_table_columns("users")
for col_name, col_info in columns.items():
    print(f"{col_name}: {col_info['type']}")

# Get complete database schema
schema = get_db_schema()
```

### Drop Tables (Development Only)

```python
from database.migration import drop_tables

# WARNING: This will delete all data
drop_tables()
```

## Health Checks

```python
from database.connection import DatabaseConnection

# Check if database is healthy
if DatabaseConnection.health_check():
    print("Database is healthy")
else:
    print("Database connection failed")
```

## Switching Databases

### SQLite to PostgreSQL

1. Update `.env`:

```env
DATABASE_TYPE=postgresql
DATABASE_HOST=db.example.com
DATABASE_PORT=5432
DATABASE_USER=grace_user
DATABASE_PASSWORD=secure_password
DATABASE_NAME=grace
```

2. Install PostgreSQL driver:

```bash
pip install psycopg2-binary
```

3. Your code remains the same - the database interface handles the connection string generation.

### SQLite to MySQL

1. Update `.env`:

```env
DATABASE_TYPE=mysql
DATABASE_HOST=db.example.com
DATABASE_PORT=3306
DATABASE_USER=grace_user
DATABASE_PASSWORD=secure_password
DATABASE_NAME=grace
```

2. Install MySQL driver:

```bash
pip install pymysql
```

## Features

### Automatic Timestamps

All models using `BaseModel` automatically track:

- `created_at`: When the record was created
- `updated_at`: When the record was last modified

### Connection Pooling

- SQLite: Static pool (single connection)
- Remote DBs: Queue pool with configurable size
- Connection health checks with `pool_pre_ping`

### Foreign Keys

- SQLite: Automatically enabled
- Remote DBs: Configured in ORM relationships

### Indexing

Define indexes for performance:

```python
__table_args__ = (
    Index("idx_user_created", "user_id", "created_at"),
    Index("idx_category_score", "category", "relevance_score"),
)
```

## Advanced Topics

### Transaction Management

```python
from sqlalchemy.orm import Session

def complex_operation(session: Session):
    try:
        # Multiple operations
        user = session.query(User).first()
        user.is_active = False

        conversation = Conversation(user_id=user.id, title="Test")
        session.add(conversation)

        session.commit()  # Commit all changes
    except Exception as e:
        session.rollback()  # Rollback on error
        raise
```

### Raw SQL Queries

```python
from sqlalchemy import text

# Execute raw SQL
result = session.execute(
    text("SELECT COUNT(*) FROM users WHERE is_active = :active"),
    {"active": True}
)
count = result.scalar()
```

## Troubleshooting

### Database Connection Issues

```python
from database.connection import DatabaseConnection

# Check connection health
if not DatabaseConnection.health_check():
    print("Database is unreachable")
```

### Enable SQL Logging

```env
DATABASE_ECHO=true
```

This will print all executed SQL statements to the console.

### Check Database Configuration

```python
from database.connection import DatabaseConnection

config = DatabaseConnection.get_config()
print(config)  # Shows current configuration
```

## Best Practices

1. **Always use repositories** for data access - consistent interface
2. **Use sessions from dependency injection** in FastAPI
3. **Enable connection pre-ping** for production
4. **Create indexes** on frequently queried columns
5. **Use transactions** for complex multi-step operations
6. **Validate configuration on startup** using `settings.validate()`
7. **Close connections** properly during shutdown
8. **Log database errors** for debugging

## Performance Tips

1. Use pagination with `skip` and `limit` parameters
2. Create indexes on foreign keys and frequently filtered columns
3. Use eager loading for relationships when needed
4. Connection pooling is automatic - configure pool size based on workload
5. Enable query logging temporarily for optimization

## Environment Variables Reference

| Variable          | Default         | Example                    |
| ----------------- | --------------- | -------------------------- |
| DATABASE_TYPE     | sqlite          | postgresql, mysql, mariadb |
| DATABASE_HOST     | localhost       | db.example.com             |
| DATABASE_PORT     | DB default      | 5432, 3306                 |
| DATABASE_USER     | (empty)         | grace_user                 |
| DATABASE_PASSWORD | (empty)         | secure_pass                |
| DATABASE_NAME     | grace           | grace                      |
| DATABASE_PATH     | ./data/grace.db | /var/lib/grace.db          |
| DATABASE_ECHO     | false           | true (for debugging)       |
