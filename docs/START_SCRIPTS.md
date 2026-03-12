# Start scripts — one script, one command for everything

GRACE has **one script**: `start.bat` (Windows) or `start.sh` (Linux/Mac). Run it with **no arguments** to start everything.

## One command for everything

| Command | What it does |
|--------|----------------|
| **`start_everything.bat`** | **GPU + Qdrant + Backend + Frontend.** Run from the **project folder**: `.\start_everything.bat` or `.\start_everything.ps1`. **From any folder:** use the **full path** to the script, e.g. `"C:\Users\aaron\Desktop\grace-3.1--Aaron-new2\start_everything_from_anywhere.bat"` (double‑click or `cmd /c "..."`), or `& "C:\...\grace-3.1--Aaron-new2\start_everything.ps1"` in PowerShell. |
| **`start.bat`** (no args) or **`start.bat full`** | **Full stack:** Qdrant (if Docker) → Backend (GPU venv) → Frontend. |
| `start.bat backend` | Backend only — FastAPI at http://localhost:8000 |
| `start.bat frontend` | Frontend only — Vite at http://localhost:5173 |
| `start.bat all` | Backend + frontend only (no Qdrant step) |
| `start.bat services` | Qdrant only (Docker or Cloud check) |

- **Full** = ensures Qdrant is running (or Cloud configured), then starts backend (using `venv_gpu` if present) and frontend in separate windows.
- In **PowerShell** use the `.\` prefix: `.\start.bat` or `.\start.bat full`.

---

## Why so many files?

They all **call that one script** so you don’t have to remember the argument:

| File | Does this |
|------|-----------|
| **run_backend.bat** | `start.bat backend` (backend only) |
| **START_BACKEND_HERE.bat** | Same — double‑click from Explorer to start backend |
| **run_backend_from_anywhere.bat** | Same — changes to project root then `start.bat backend` |
| **start_grace.bat** | `start.bat all` (backend + frontend) |
| **start_services.bat** | `start.bat services` (Qdrant) |
| **start.ps1** | Runs `start.bat` with the argument you pass (e.g. `.\start.ps1 backend`) |
| **run_backend.ps1** | Runs `start.bat backend` (same as run_backend.bat, for PowerShell) |
| **start_everything.bat** | Preflight, GPU setup (setup_gpu.py), then `start.bat staged` (Qdrant + backend + frontend with 30s head start). |

So: **one behavior** — `start.bat` — and the rest are convenience names. Use **start_everything.bat** when you want GPU setup included.

**Python launchers** (`grace_start.py`, `start_grace_windows.py`) contain **no duplicate logic**: they delegate to `startup_preflight.py` + `start.bat staged`. Run from project root: `python grace_start.py` or `python start_grace_windows.py`.

---

## What to run (recommended)

- **Everything (GPU + Qdrant + backend + frontend):**  
  **`start_everything.bat`** - Preflight, GPU setup, then Qdrant, backend, frontend (staged).
- **Full stack (Qdrant + backend + frontend):**  
  **`start.bat`** or **`.\start.bat`** (no arguments)
- **Backend only:**  
  `run_backend.bat` or `.\start.bat backend`
- **Backend + frontend (no Qdrant step):**  
  `start_grace.bat` or `.\start.bat all`
- **Qdrant only:**  
  `start_services.bat` or `.\start.bat services`
- **Populate vector store (ingest documents):**  
  `run_ingest.bat` — Runs full reset and re-ingestion of all files in `backend/knowledge_base/`. Use when the Qdrant collection is empty or you want to re-index all documents.

### Run from any folder (Windows CMD)

- Use the **full path** to the script. In CMD, `&` is invalid (that's PowerShell). Use:
  ```
  "C:\Users\aaron\Desktop\grace-3.1--Aaron-new2\start_everything.bat"
  ```
- Or use **start_everything_from_anywhere.bat** (double‑click it from the project folder once, or run it with its full path); it changes to the project directory then runs start_everything.bat.
- To use `.\start_everything.bat` you must be in the project directory first: `cd C:\Users\aaron\Desktop\grace-3.1--Aaron-new2`.

### Run from anywhere (other)

To start GRACE from a different folder (e.g. Desktop or another drive), use the **full path** to the batch file so the script can find the project root:

- **CMD:** `"C:\Users\aaron\Desktop\grace-3.1--Aaron-new2\start_everything_from_anywhere.bat"`
- **PowerShell:** `& "C:\Users\aaron\Desktop\grace-3.1--Aaron-new2\start_everything.ps1"` (after `Set-Location` is not required; the script uses `$PSScriptRoot`)

Replace the path with your actual project folder. Without the full path, the shell may not find the script.

---

## Pull the latest GRACE

This project has no git remote until you add one. After that you can pull the latest.

```bash
# Add origin once (use the URL you clone GRACE from; example from README)
git remote add origin https://github.com/aaron031291/grace-3.1-.git

# Then pull (main or master, depending on the repo)
git pull origin main
# or:  git pull origin master
```

If you use a different repo (e.g. a fork), add it as origin or upstream and pull from that.

```bash
git pull origin main
```

If the remote is already set, run git pull origin main (or master) to get the latest.
