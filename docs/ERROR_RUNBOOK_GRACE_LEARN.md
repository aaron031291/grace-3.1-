# Error Runbook — What to Do When These Errors Happen Again

This document is for Grace and operators: it explains the main runtime breakages, their fixes (already in code), and **what to do when you see these errors again** (including restart).

---

## 1. ASGI crash: `ModuleNotFoundError: No module named 'api.brain_api'`

**Where you see it:** `brain_controller.py`, line 96 (or 41), in `directory` or `brain_dispatch`.

**What it means:** The running Python process is loading code that still imports the **deleted** module `api.brain_api`. The repo was updated to use `api.brain_api_v2`; the old module no longer exists.

**Root cause:** Either the running backend is older than the fix, or it was started from a different working tree / stale path, or the process was never restarted after the fix.

**Fix (already in code):**
- `backend/api/core/brain_controller.py`: use `from api.brain_api_v2 import call_brain` and `from api.brain_api_v2 import BRAIN_DIRECTORY, _build_directory`.
- `backend/api/autonomous_loop_api.py`: use `from api.brain_api_v2 import call_brain` (e.g. in the heal path around line 490).

**When it happens again:**
1. Confirm no file in the repo contains `from api.brain_api import` (search the codebase). If any do, change them to `api.brain_api_v2`.
2. **Restart the backend** so the process loads the updated code. Stopping and starting uvicorn/app is required; code changes are not picked up by a long-lived process until restart.

---

## 2. Ollama: `OllamaClient.generate_response() got an unexpected keyword argument 'system'`

**Where you see it:** Logs for "Model qwen failed" and "Model reasoning failed".

**What it means:** A caller is passing `system=...` (or `options=...`) to `OllamaClient.generate_response()`, but the **running** client code does not accept those parameters.

**Root cause:** The Ollama client was updated to accept `system_prompt`, `system`, and `options`; the running process is still using the old client that did not.

**Fix (already in code):**
- `backend/ollama_client/client.py`: `generate_response()` has optional `system_prompt`, `system`, and `options`; the request payload includes `"system"` and merged `options`.

**When it happens again:**
1. Confirm `ollama_client/client.py` method `generate_response` has parameters `system_prompt`, `system`, and `options` and that the payload sends them to the Ollama API.
2. **Restart the backend** so the updated client is loaded.

---

## 3. Genesis Qdrant: `genesis_qdrant_400` / "Qdrant upsert (genesis_keys) returns 400"

**Where you see it:** Deterministic bridge / health alerts: "Qdrant upsert (genesis_keys) returns 400" and "ALERT: Health issues detected: genesis_qdrant".

**What it means:** Upsert to the `genesis_keys` collection is rejected by Qdrant Cloud—almost always due to **vector size mismatch**: the backend is sending vectors of one dimension (e.g. from the embedding model or `GENESIS_VECTOR_SIZE`) but the existing `genesis_keys` collection was created with a different size.

**Root cause:** The `genesis_keys` collection in Qdrant Cloud has a fixed vector size. The backend uses `GENESIS_VECTOR_SIZE` from env, or the embedding model’s dimension, or default 384. If they don’t match, Qdrant returns 400.

**Fix (already in code):**
- `backend/api/_genesis_tracker.py`: Uses `GENESIS_VECTOR_SIZE` env; if unset, uses embedding model dimension or 384. **Skips upsert** when the existing collection’s vector size does not match (so 400s stop and logs show the right value). On 400, logs include: "Collection vector size is X — set GENESIS_VECTOR_SIZE=X in backend/.env".
- Health alert message now tells you to set `GENESIS_VECTOR_SIZE` or `DISABLE_GENESIS_QDRANT_PUSH=1`.

**When it happens again:**
1. **Quick fix (match collection):** In backend logs, find the line that says "Collection vector size is **N**". In `backend/.env` add or set `GENESIS_VECTOR_SIZE=N`. Restart the backend.
2. **Alternative (recreate collection):** In Qdrant Cloud, delete the `genesis_keys` collection. Restart the backend so it recreates the collection with the correct size (leave `GENESIS_VECTOR_SIZE` unset to use the embedding model’s dimension).
3. **Temporary (stop 400s and alerts):** In `backend/.env` set `DISABLE_GENESIS_QDRANT_PUSH=1`. Genesis keys will still be stored in the DB; only the Qdrant vector push is disabled.
4. **Restart the backend** after any `.env` change.

---

## Critical: Restart the backend after code changes

All of the above fixes are in the **source code**. If you still see these errors:

- The process serving the app is almost certainly running **old code** (no reload or restart after the fix).
- **Action:** Stop the backend (e.g. Ctrl+C in the terminal running uvicorn), then start it again from the same repo so it loads the current files.

Example (Windows, from repo root):
```powershell
# In the terminal that runs the backend: stop with Ctrl+C, then:
cd backend
.\venv_gpu\Scripts\activate
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Using `--reload` helps pick up future file changes without a manual restart; the **first** time after applying these fixes, a full stop-and-start is still required if the process was started before the fix.

---

## Summary table

| Error | Fix in code | When it happens again |
|-------|-------------|------------------------|
| `No module named 'api.brain_api'` | Use `api.brain_api_v2` everywhere; no `brain_api` imports | Replace any remaining `brain_api` imports, then **restart backend** |
| `unexpected keyword argument 'system'` (Ollama) | `generate_response()` accepts `system`/`system_prompt`/`options` | Ensure client has those params and **restart backend** |
| `genesis_qdrant_400` / Qdrant upsert 400 | Single 384-dim constant; slice/pad vectors; consistent payload | Align vector size and payload; recreate collection if needed; **restart backend** |

Learning: after any fix to these areas, **restart the backend** so the running process loads the updated code.
