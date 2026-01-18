"""
Grace Database Module

A comprehensive SQLAlchemy-based database interface with multi-database support.

Features:

- SQLite (default, no setup required)
- PostgreSQL, MySQL, MariaDB support
- Automatic timestamps (created_at, updated_at)
- Connection pooling and health checks
- Generic base repository for CRUD operations
- Transaction management
- Relationship support (foreign keys, cascades)
- Automatic schema initialization
- Comprehensive testing utilities

Quick Start:

    from database.config import DatabaseConfig
    from database.connection import DatabaseConnection
    from database.session import get_session, initialize_session_factory
    from database.migration import create_tables

    # Initialize
    config = DatabaseConfig.from_env()
    DatabaseConnection.initialize(config)
    initialize_session_factory()
    create_tables()

    # Use in FastAPI
    @app.post("/users/")
    def create_user(name: str, session: Session = Depends(get_session)):
        repo = UserRepository(session)
        return repo.create(username=name, email=f"{name}@example.com")

Environment Variables:
DATABASE_TYPE: Type of database (sqlite, postgresql, mysql, mariadb)
DATABASE_PATH: Path for SQLite database file
DATABASE_HOST: Remote database host
DATABASE_PORT: Remote database port
DATABASE_USER: Database username
DATABASE_PASSWORD: Database password
DATABASE_NAME: Database name
DATABASE_ECHO: Enable SQL logging (true/false)

Supported Databases: - SQLite (default) - PostgreSQL (requires psycopg2-binary) - MySQL (requires pymysql) - MariaDB (requires pymysql)

Documentation: - DATABASE_GUIDE.md: Comprehensive documentation - DATABASE_QUICKSTART.md: Quick start guide - database/init_example.py: Initialization examples

See DATABASE_GUIDE.md for detailed documentation.
"""
