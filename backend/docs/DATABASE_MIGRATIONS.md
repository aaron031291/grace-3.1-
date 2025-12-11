"""
Database Migration Guide

This guide explains how to manage database schema changes and migrations.

SQLAlchemy provides two approaches:

1. Declarative with auto schema creation (used in this project)
2. Alembic for version-controlled migrations (recommended for production)
   """

# ============================================================================

# APPROACH 1: Simple Schema Updates (Development)

# ============================================================================

"""
For development environments where you control the schema directly:

1. Define/modify your models in models/database_models.py
2. Call create_tables() to apply changes
3. This will create new tables/columns but won't drop existing ones

Example:

    from sqlalchemy import Column, String
    from database.base import BaseModel

    class Document(BaseModel):
        __tablename__ = "documents"
        title = Column(String(255))

    # In your app startup:
    from database.migration import create_tables
    create_tables()  # Will create documents table if it doesn't exist

"""

# ============================================================================

# APPROACH 2: Alembic Migrations (Production Recommended)

# ============================================================================

"""
For production environments, use Alembic for version-controlled migrations.

Installation:
pip install alembic

Setup: 1. Initialize Alembic in your project:
alembic init migrations

    2. Configure alembic.ini:
       - Set sqlalchemy.url to your database connection string
       - Or use environment variables

    3. Configure env.py for your database setup:
       Edit migrations/env.py to import and use your config

Creating a Migration:

    1. Modify your model in database/models.py

    2. Create migration:
       alembic revision --autogenerate -m "Add new column"

    3. Review the migration file in migrations/versions/

    4. Apply migration:
       alembic upgrade head

    5. Downgrade if needed:
       alembic downgrade -1

Common Alembic Commands:
alembic revision --autogenerate -m "Description" # Create migration
alembic upgrade head # Apply all pending
alembic downgrade base # Revert all
alembic current # Show current revision
alembic history # Show all revisions
"""

# ============================================================================

# MIGRATION PATTERNS

# ============================================================================

"""
Common Migration Patterns:

1. Adding a new column:

   old_definition = Column(String(100))
   new_definition = Column(String(100), nullable=True, default="")

   # In migration:

   op.add_column('table_name', sa.Column('column_name', sa.String(100), ...))

2. Renaming a column:

   # In migration:

   op.alter_column('table_name', 'old_name', new_column_name='new_name')

3. Adding/Removing constraints:

   # Add constraint

   op.create_unique_constraint('uq_email', 'users', ['email'])

   # Drop constraint

   op.drop_constraint('uq_email', 'users')

4. Creating an index:

   # In migration:

   op.create_index('idx_user_created', 'users', ['user_id', 'created_at'])

5. Changing column type:

   # In migration (PostgreSQL):

   op.alter*column('table_name', 'column_name',
   existing_type=sa.String(),
   type*=sa.Integer())

6. Adding a new table with foreign key:
   op.create_table(
   'new_table',
   sa.Column('id', sa.Integer, primary_key=True),
   sa.Column('parent_id', sa.Integer, sa.ForeignKey('parent.id')),
   sa.Column('name', sa.String(255))
   )
   """

# ============================================================================

# BEST PRACTICES FOR MIGRATIONS

# ============================================================================

"""

1. One change per migration
   - Makes it easier to understand and revert
   - Better for debugging issues
2. Always provide up and down migrations
   - Test that downgrade works
   - Make reversions easier
3. Handle data migration carefully
   - Add nullable columns first
   - Populate data in a separate step
   - Remove NOT NULL constraints later
4. Test migrations thoroughly
   - Test on a copy of production data
   - Test both upgrade and downgrade
   - Document any manual steps
5. Coordinate with deployments
   - Deploy migrations before code changes if adding columns
   - Deploy code before migrations if removing columns
   - This prevents downtime and errors
6. Keep migrations independent
   - Don't rely on previous data states
   - Use op.bulk_update or iterate if data transformation needed

Example: Adding a new required column safely

# Step 1 - Migration: Add nullable column

op.add_column('users', sa.Column('new_field', sa.String(255), nullable=True))

# Step 2 - Code: Populate new_field during operations

# Update existing records in application code

# Step 3 - Migration: Make column not nullable

op.alter_column('users', 'new_field', nullable=False)
"""

# ============================================================================

# ZERO-DOWNTIME MIGRATION EXAMPLE

# ============================================================================

"""
Example: Safely adding a required field to an existing table

# migration_1.py (First deployment)

def upgrade(): # Add nullable column
op.add_column('users', sa.Column('api_key', sa.String(64), nullable=True)) # Create index for performance
op.create_index('idx_users_api_key', 'users', ['api_key'], unique=True)

def downgrade():
op.drop_index('idx_users_api_key', 'users')
op.drop_column('users', 'api_key')

# In your application code (between migrations)

# Generate api_key for users who don't have one:

session = SessionLocal()
users = session.query(User).filter(User.api_key == None).all()
for user in users:
user.api_key = generate_api_key()
session.commit()

# migration_2.py (Second deployment)

def upgrade(): # Now make column not nullable
op.alter_column('users', 'api_key', nullable=False)

def downgrade():
op.alter_column('users', 'api_key', nullable=True)
"""

# ============================================================================

# DATABASE-SPECIFIC MIGRATION NOTES

# ============================================================================

"""
SQLite: - Limited ALTER TABLE support - May need to recreate table for certain changes - Foreign keys are not enforced by default (enabled in our setup)

PostgreSQL: - Full ALTER TABLE support - Transactions support (rollback on error) - Can lock tables during large operations - Use IF EXISTS clauses for safety

MySQL: - Basic ALTER TABLE support - May need to drop and recreate indexes - VARCHAR length limits - Careful with FOREIGN KEY operations

MariaDB: - Similar to MySQL with some improvements - Better ALTER TABLE support in newer versions - Good transaction support
"""

# ============================================================================

# SETUP ALEMBIC (Optional, Recommended for Production)

# ============================================================================

"""
If you want to set up Alembic for your project:

1. Install Alembic:
   pip install alembic

2. Initialize Alembic:
   alembic init migrations

3. Update migrations/env.py:

from database.base import Base
from database.connection import DatabaseConnection
from database.config import DatabaseConfig

# Configure database connection

config_obj = DatabaseConfig.from_env()
database_connection = DatabaseConnection.initialize(config_obj)

# Point sqlalchemy.url to database

# sqlalchemy.url = config_obj.get_connection_string()

4. Configure alembic.ini:

   # Either set sqlalchemy.url

   sqlalchemy.url = sqlite:///./data/grace.db

   # Or use environment variable

   sqlalchemy.url = driver://user:password@localhost/dbname

5. Create first migration from existing models:
   alembic revision --autogenerate -m "Initial migration"

6. Apply migration:
   alembic upgrade head

7. On code changes, create new migrations:
   alembic revision --autogenerate -m "Add user api_key"
   alembic upgrade head
   """

# ============================================================================

# CHECKING MIGRATION STATUS

# ============================================================================

"""
In Python code, check current migration state:

from database.migration import get_all_tables, get_db_schema

# See all tables

tables = get_all_tables()
print(f"Tables: {tables}")

# See full schema

schema = get_db_schema()
for table_name, info in schema.items():
print(f"\n{table_name}:")
for col_name, col_info in info['columns'].items():
print(f" {col_name}: {col_info['type']}")
"""

# ============================================================================

# PRODUCTION DEPLOYMENT CHECKLIST

# ============================================================================

"""
Before deploying schema changes:

☐ Run migrations on a staging database
☐ Verify all migrations work both forward and backward
☐ Test application with new schema
☐ Back up production database
☐ Schedule migration during low-traffic window
☐ Have a rollback plan ready
☐ Monitor application logs after migration
☐ Verify data integrity post-migration

For large tables:
☐ Create index concurrently (PostgreSQL: CONCURRENTLY)
☐ Use online migrations if available
☐ Monitor database performance during migration
☐ Be prepared for longer migration times
"""

# ============================================================================

# TROUBLESHOOTING MIGRATIONS

# ============================================================================

"""
Common Issues:

1. Migration fails with "table already exists"

   - Check if table was already created
   - Create migration with conditional logic
   - Use op.execute("CREATE TABLE IF NOT EXISTS ...")

2. Alembic can't detect changes

   - Models must be imported in env.py
   - Check model inheritance (must extend Base)
   - Run with --verbose for debugging

3. Column type mismatch

   - Ensure model and database column types match
   - Use explicit type in migration if Alembic guesses wrong
   - Different databases have different type names

4. Foreign key constraint violations

   - Ensure parent records exist before adding child records
   - Disable constraints temporarily if needed
   - Check order of migration operations

5. Migration locks database
   - Long migrations lock tables in MySQL
   - Use online migration tools for large tables
   - Consider zero-downtime migration patterns
     """

if **name** == "**main**": # Quick schema inspection
from database.migration import get_db_schema, table_exists

    if table_exists("users"):
        schema = get_db_schema()
        print("Current Database Schema:")
        print("-" * 50)
        for table_name, info in schema.items():
            print(f"\n{table_name}:")
            for col_name, col_info in info['columns'].items():
                print(f"  {col_name}: {col_info['type']}")
    else:
        print("No tables found. Run database initialization first.")
