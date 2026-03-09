---
description: Front‑end Healing Agent with Browser Integration, Genesis‑Key Self‑Healing, Diagnostics & Validation Pipeline
---

# Overview
This workflow defines a **Front‑End Healing Agent** that can autonomously detect UI errors, run diagnostics, apply fixes via the coding‑agent, hot‑reload the UI, and verify the outcome. It leverages the existing **Antigravity browser sub‑agent** to interact with the running front‑end, updates **Genesis keys** for version tracking, and loops recursively until the validation stage passes.

## Steps
1. **Initialize Browser Sub‑Agent**
   ```
   // turbo-all
   TaskName: Launch Front‑End UI
   RecordingName: frontend_view
   Task: "Open http://localhost:3000 in the browser, wait for the page to load, and capture a screenshot of the initial UI state."
   ```
2. **Run UI Diagnostics**
   - Execute a series of JavaScript snippets via the sub‑agent to collect console errors, network failures, and CSS warnings.
   - Publish a `ui_diagnostics` event containing the error list.
3. **Map Diagnostics to Genesis Keys**
   - For each affected component (e.g., `frontend/src/components/Header.jsx`), emit a `genesis_key_updated` event with the component’s key and a **self‑healing** flag.
4. **Generate Fix Proposal**
   - Invoke the **coding‑agent** with `submit_coding_task` (dry_run = false) using the diagnostics payload.
   - Include `target_file` pointing to the component source file.
5. **Apply Fix & Hot‑Reload**
   - Once the task succeeds, trigger the **Hot‑Reload Agent** (listening on `genesis_key_updated`) to reload the affected module without restarting the dev server.
6. **Validation Pipeline (12‑Stage)**
   - Stage 1‑3: Unit‑test execution (`npm test --filter component`).
   - Stage 4‑6: Integration‑test against a headless browser (Playwright).
   - Stage 7‑9: Visual regression comparison (pixel‑diff against baseline screenshots).
   - Stage 10‑12: Performance & accessibility audit (Lighthouse).
   - Each stage publishes `validation_stage_completed` events; failures cause a **recursive loop** back to step 2.
7. **Alert & Reporting**
   - On successful completion, send a summary to the **Grace Activity** UI tab via the WebSocket endpoint.
   - On persistent failure after 3 recursion cycles, raise a high‑severity alert for human intervention.

## Recursion Logic
```python
max_attempts = 3
attempt = 0
while attempt < max_attempts:
    run_diagnostics()
    if all_stages_pass():
        break
    attempt += 1
    # Re‑trigger fix generation with updated diagnostics
```

## Integration Points
- **Event Bus**: `ui_diagnostics`, `genesis_key_updated`, `validation_stage_completed`.
- **Hot‑Reload Agent**: already exists for backend; extend to watch front‑end module keys.
- **WebSocket UI**: add a **Front‑End Healing** sub‑tab under the existing **Grace Activity** panel.

---
*This workflow is intentionally concise to respect the artifact size guideline.*
