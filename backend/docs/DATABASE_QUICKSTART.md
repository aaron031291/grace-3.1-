# Database Quick Start Guide

## Installation

All required database packages have been added to `requirements.txt`:

```bash
pip install -r requirements.txt
```

This includes:

- **SQLAlchemy** (2.0.28) - ORM and database toolkit
- **psycopg2-binary** - PostgreSQL driver
- **pymysql** - MySQL/MariaDB driver

SQLite is included with Python, no additional driver needed.

## Quick Start (SQLite - Default)

SQLite requires no additional setup and is configured by default.

### 1. Initialize Database in Your App

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from database.config import DatabaseConfig
from database.connection import DatabaseConnection
from database.session import get_session, initialize_session_factory
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

### 2. Use Database in Endpoints

```python
from models.repositories import UserRepository
from models.database_models import User

@app.post("/users/")
def create_user(username: str, email: str, session: Session = Depends(get_session)):
    repo = UserRepository(session)
    user = repo.create(username=username, email=email)
    return user.to_dict()

@app.get("/users/{user_id}")
def get_user(user_id: int, session: Session = Depends(get_session)):
    repo = UserRepository(session)
    user = repo.get(user_id)
    return user.to_dict() if user else None
```

### 3. Run Your Application

```bash
# Create .env file if not exists
cp .env.example .env

# Start your application
python -m uvicorn app:app --reload
```

The database will automatically be created and initialized on startup.

## Using PostgreSQL

1. **Install PostgreSQL** (if not already installed)

   ```bash
   # Ubuntu/Debian
   sudo apt-get install postgresql postgresql-contrib

   # macOS
   brew install postgresql
   ```

2. **Create a database user**

   ```bash
   sudo -u postgres psql

   CREATE USER grace_user WITH PASSWORD 'your_password';
   CREATE DATABASE grace OWNER grace_user;
   GRANT ALL PRIVILEGES ON DATABASE grace TO grace_user;
   \q
   ```

3. **Update .env file**

   ```env
   DATABASE_TYPE=postgresql
   DATABASE_HOST=localhost
   DATABASE_PORT=5432
   DATABASE_USER=grace_user
   DATABASE_PASSWORD=your_password
   DATABASE_NAME=grace
   ```

4. **Your application code stays the same** - database interface handles the connection!

## Using MySQL

1. **Install MySQL** (if not already installed)

   ```bash
   # Ubuntu/Debian
   sudo apt-get install mysql-server

   # macOS
   brew install mysql
   ```

2. **Create a database user**

   ```bash
   mysql -u root -p

   CREATE USER 'grace_user'@'localhost' IDENTIFIED BY 'your_password';
   CREATE DATABASE grace CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   GRANT ALL PRIVILEGES ON grace.* TO 'grace_user'@'localhost';
   FLUSH PRIVILEGES;
   EXIT;
   ```

3. **Update .env file**

   ```env
   DATABASE_TYPE=mysql
   DATABASE_HOST=localhost
   DATABASE_PORT=3306
   DATABASE_USER=grace_user
   DATABASE_PASSWORD=your_password
   DATABASE_NAME=grace
   ```

4. **Your application code stays the same!**

## Running Tests

```bash
# Run all database tests
pytest tests/test_database.py -v

# Run specific test
pytest tests/test_database.py::TestBaseRepository::test_create_user -v

# Run with coverage
pytest tests/test_database.py --cov=database --cov=models
```

## Common Operations

### Create a User

```python
repo = UserRepository(session)
user = repo.create(username="john_doe", email="john@example.com", full_name="John Doe")
```

### Get a User

```python
user = repo.get(user_id=1)
# or
user = repo.get_by_username("john_doe")
```

### Update a User

```python
user = repo.update(user_id=1, full_name="John Updated")
```

### Delete a User

```python
deleted = repo.delete(user_id=1)
```

### Query Multiple Records

```python
# Get all (with pagination)
users = repo.get_all(skip=0, limit=10)

# Filter
active_users = repo.filter(is_active=True)

# Count
total = repo.count()

# Check existence
exists = repo.exists(username="john_doe")
```

### Bulk Operations

```python
# Bulk create
users = [
    User(username="user1", email="user1@example.com"),
    User(username="user2", email="user2@example.com"),
]
repo.bulk_create(users)

# Bulk delete
deleted_count = repo.bulk_delete([1, 2, 3])
```

## Database Schema

The default schema includes:

- **users** - User accounts
- **conversations** - Chat conversations
- **messages** - Individual messages
- **embeddings** - Vector embeddings

All tables include `id`, `created_at`, and `updated_at` fields automatically.

## Project Structure

```
backend/
├── database/              # Database interface module
│   ├── __init__.py
│   ├── base.py           # Base model classes
│   ├── config.py         # Database configuration
│   ├── connection.py     # Connection management
│   ├── session.py        # Session factory
│   ├── repository.py     # Base repository class
│   ├── migration.py      # Schema utilities
│   └── init_example.py   # Initialization examples
│
├── models/
│   ├── database_models.py   # ORM models
│   └── repositories.py      # Repository implementations
│
├── settings.py           # Application settings
├── requirements.txt      # Python dependencies
├── .env.example         # Environment variables template
└── DATABASE_GUIDE.md    # Detailed documentation
```

## Environment Variables

| Variable          | Example         | Description                          |
| ----------------- | --------------- | ------------------------------------ |
| DATABASE_TYPE     | sqlite          | sqlite, postgresql, mysql, mariadb   |
| DATABASE_PATH     | ./data/grace.db | Path for SQLite (SQLite only)        |
| DATABASE_HOST     | localhost       | Database host (remote databases)     |
| DATABASE_PORT     | 5432            | Database port (remote databases)     |
| DATABASE_USER     | grace_user      | Database username (remote databases) |
| DATABASE_PASSWORD | secure_pass     | Database password (remote databases) |
| DATABASE_NAME     | grace           | Database name                        |
| DATABASE_ECHO     | false           | Log SQL queries (true for debugging) |

## Troubleshooting

### Database File Not Created

Ensure `./data/` directory exists or the parent directory is writable.
The interface will create it automatically.

### Connection Refused

- Check your database server is running
- Verify host, port, and credentials in `.env`
- Run `DatabaseConnection.health_check()` to test connection

### Foreign Key Constraint Error

Ensure you're creating related records in the correct order:

```python
# Create parent first
user = repo.create(...)

# Then create child with proper foreign key
conversation = Conversation(user_id=user.id, ...)
```

### Enable SQL Logging for Debugging

```env
DATABASE_ECHO=true
```

This shows all SQL statements being executed.

## Next Steps

1. Read [DATABASE_GUIDE.md](DATABASE_GUIDE.md) for detailed documentation
2. Check `models/database_models.py` for example models
3. Check `models/repositories.py` for repository patterns
4. Run tests: `pytest tests/test_database.py -v`
5. Customize models and repositories for your needs

## Support

For detailed API documentation, see [DATABASE_GUIDE.md](DATABASE_GUIDE.md)
