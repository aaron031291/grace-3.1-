# Get Genesis Key + SQL Working

Follow these steps so **Genesis Key tracking** and the **SQL database** (SQLite or PostgreSQL) work correctly.

## 1. Environment

- In **`backend/.env`** (copy from `backend/.env.example` if missing):
  - Set **`DISABLE_GENESIS_TRACKING=false`** or leave it unset. If `true`, Genesis Keys are disabled.
  - For **SQLite** (default): `DATABASE_TYPE=sqlite` and `DATABASE_PATH=./data/grace.db`.
  - For **PostgreSQL**: set `DATABASE_TYPE=postgresql`, `DATABASE_HOST`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_NAME`. See `backend/docs/GENESIS_DATABASE.md` for details.

## 2. Database migrations

From the **backend** directory:

```bat
cd backend
python run_all_migrations.py
```

Or from project root:

```bat
.\setup_backend.bat
```

You should see migrations pass and a line like: `genesis_key (39 columns)` in the verification output.

## 3. Verify Genesis + SQL

From the **backend** directory:

```bat
cd backend
python scripts\verify_genesis_sql.py
```

If all checks pass, Genesis Key creation and the SQL database are working.

## 4. Start the backend

From the **project root**:

```powershell
.\run_backend.bat
```

Or:

```powershell
.\start.bat backend
```

Always run the backend from the project folder so it uses `backend/` and `backend/.env`.

## 5. Optional: Qdrant

Genesis Key storage uses only the **SQL** database. For RAG/semantic search you need Qdrant:

```powershell
.\start_services.bat qdrant
```

## Troubleshooting

| Issue | What to do |
|-------|------------|
| `DISABLE_GENESIS_TRACKING` is true | Set to `false` or remove it in `backend/.env`. |
| Table `genesis_key` not found | Run `python run_all_migrations.py` from `backend/`. |
| "Database is locked" / SQLite busy | Backend uses retries and 60s busy_timeout. Restart backend; if it persists, consider PostgreSQL. |
| Genesis Key creation fails | Run `python scripts\verify_genesis_sql.py` from `backend/` to see which check fails. |
| **Verify PostgreSQL** | Same script: set `DATABASE_TYPE=postgresql` in `backend/.env`, then run `python scripts\verify_genesis_sql.py` from `backend/`. From Windows, a **private** DigitalOcean host (e.g. `private-db-postgresql-...`) will timeout; use the **public** DB host and allow your IP in the DO firewall, or run the verify script from a Droplet in the same VPC. |
| MAGMA "Genesis Key service not available" | Ensure `get_genesis_key_service` alias exists in `genesis_key_service.py` and restart backend. |

## Summary

1. **`backend/.env`**: `DISABLE_GENESIS_TRACKING=false` (or unset), and correct `DATABASE_*` for SQLite or PostgreSQL.  
2. **Migrations**: `python run_all_migrations.py` in `backend/`.  
3. **Verify**: `python scripts\verify_genesis_sql.py` in `backend/`.  
4. **Run**: `.\run_backend.bat` from project root.
