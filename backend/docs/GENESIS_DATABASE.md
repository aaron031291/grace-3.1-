# Genesis Keys and Database Choice

## Where Genesis Keys are stored

Genesis Keys are stored in the **same SQL database** as the rest of GRACE (chats, documents, etc.):
- **SQLite** (default): single file `backend/data/grace.db`
- **PostgreSQL** / MySQL / MariaDB: when configured via `DATABASE_*` in `.env`

**Redis is not used for Genesis Keys.** Redis in this project is only for:
- Caching (e.g. `cache/redis_cache.py`)
- Optional distributed state (`core/distributed_state.py`)

So switching to Redis will not fix Genesis Key creation. Use PostgreSQL (or fix SQLite usage) instead.

## SQLite vs PostgreSQL

| | SQLite | PostgreSQL |
|---|--------|------------|
| **Concurrent writes** | Can hit "database is locked" under many workers or threads | Handles concurrency well |
| **Genesis Key creation** | Now has retry on lock + duplicate key handling | Same code, fewer lock issues |
| **Setup** | None (file-based) | Install Postgres, set `DATABASE_*` in `.env` |

If Genesis Key creation fails with SQLite (e.g. locks or errors), switching to **PostgreSQL** is the recommended fix.

## How to use PostgreSQL for GRACE (and Genesis Keys)

1. Install and run PostgreSQL (e.g. local or Docker).

2. In `backend/.env` set:
   ```env
   DATABASE_TYPE=postgresql
   DATABASE_HOST=localhost
   DATABASE_PORT=5432
   DATABASE_USER=grace
   DATABASE_PASSWORD=your_password
   DATABASE_NAME=grace
   ```

3. Create the database and user (in `psql` or pgAdmin):
   ```sql
   CREATE USER grace WITH PASSWORD 'your_password';
   CREATE DATABASE grace OWNER grace;
   ```

4. Run migrations from the backend folder:
   ```bat
   python run_all_migrations.py
   ```

5. Restart the backend. Genesis Keys (and all other data) will use PostgreSQL.

## Code changes for Genesis Key creation (SQLite)

The Genesis Key service now:
- **Retries** on SQLite `OperationalError` (e.g. "database is locked") up to 3 times with short backoff.
- On **IntegrityError** (duplicate `key_id`): returns the existing row instead of failing.
- Handles **identity map** conflicts (rollback + merge + flush) so creation does not fail on session conflicts.

If you still see failures, check logs for the exact exception and consider switching to PostgreSQL as above.
