# Connecting Grace to PostgreSQL

Grace can use the same PostgreSQL server as your other tools (e.g. stGIS Shapefile Import/Export Manager, pgAdmin). Use the **same host, port, username, and password** that work there.

## 1. Fix the authentication error (stGIS / pgAdmin)

If you see:

```text
FATAL: password authentication failed for user "localhost"
```

then:

- **Username:** Use your actual PostgreSQL role name (e.g. `postgres`), not `localhost`. `localhost` is the host, not a user.
- **Password:** Use the password you set for that role when installing PostgreSQL.

In stGIS or pgAdmin, set **User** to `postgres` (or your role) and **Password** to the correct value, then test the connection.

## 2. Configure Grace to use PostgreSQL

In the backend folder, copy `.env.example` to `.env` (if you don’t have `.env` yet), then set:

```env
DATABASE_TYPE=postgresql
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_USER=postgres
DATABASE_PASSWORD=your_actual_postgres_password
DATABASE_NAME=grace
DATABASE_SSLMODE=
```

- Use the **same** `DATABASE_USER` and `DATABASE_PASSWORD` that work in stGIS/pgAdmin.
- `DATABASE_NAME` can be `grace` (Grace will create tables there) or an existing database you use for Grace only.

## 3. Create the database (if needed)

If the database `grace` doesn’t exist yet:

```bash
# In psql or pgAdmin:
CREATE DATABASE grace;
```

Or use an existing database and set `DATABASE_NAME` to that name.

## 4. Run Grace and verify

Start the backend (e.g. `uvicorn app:app`). Grace will create its tables on first use. To check the connection:

- **Health:** `GET /api/component-health/health` or your app’s health endpoint (should report DB OK).
- **Direct test:** From the backend directory, with your venv activated:
  ```bash
  python -c "
  from database.config import DatabaseConfig
  from database.connection import DatabaseConnection
  cfg = DatabaseConfig.from_env()
  DatabaseConnection.initialize(cfg)
  from database.session import DatabaseConnection
  print('OK' if DatabaseConnection.health_check() else 'FAIL')
  "
  ```

## 5. Optional: PostGIS / shapefiles

Grace’s core uses standard PostgreSQL (no PostGIS required). If you want to store or query spatial data from shapefiles in the same server:

- Install the PostGIS extension in your PostgreSQL server and create the database with PostGIS if needed.
- Use Grace’s PostgreSQL connection only for Grace’s tables; use stGIS or other tools to import/export shapefiles into PostGIS tables. Grace can then query those tables over the same connection if you point it at that database or schema.

## Summary

| Setting            | Example / note                          |
|--------------------|-----------------------------------------|
| `DATABASE_TYPE`    | `postgresql`                            |
| `DATABASE_HOST`    | `localhost` (or your server)            |
| `DATABASE_PORT`    | `5432`                                  |
| `DATABASE_USER`    | `postgres` (or your role; **not** `localhost`) |
| `DATABASE_PASSWORD`| The password for that role             |
| `DATABASE_NAME`    | `grace` or your chosen database         |

Use the same credentials in Grace that work in stGIS or pgAdmin.
