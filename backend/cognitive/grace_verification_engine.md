# Grace Verification Engine

**File:** `cognitive/grace_verification_engine.py`

## Overview

Grace Multi-Source Verification Engine

Grace does NOT blindly execute Kimi's instructions.
She verifies every instruction through multiple independent sources
before executing. Only when verification passes does Grace act.

Verification Sources:
  1. USER CONFIRMATION  - Bidirectional comms (WebSocket, chat, voice)
  2. ORACLE ML          - ML predictions on success probability and risk
  3. CHAT/MESSAGE       - Check conversation history for contradictions
  4. DATABASE TABLES    - Verify referenced data actually exists
  5. FILE SYSTEM        - Verify files, directories, paths exist
  6. WEB SEARCH         - Cross-reference claims against web sources
  7. API VALIDATION     - Check external APIs for data accuracy
  8. FILE UPLOADS       - Verify uploaded file integrity
  9. KNOWLEDGE BASE     - Check against known facts in KB
  10. GOVERNANCE        - Constitutional and policy checks
  11. OODA LOOP         - Run instruction through full OODA cycle

If ANY critical verification fails, instruction is REJECTED.
Grace explains WHY to the user through bidirectional comms.

## Classes

- `VerificationSource`
- `CheckResult`
- `VerificationCheck`
- `VerificationReport`
- `GraceVerificationEngine`

## Key Methods

- `to_dict()`
- `connect_oracle()`
- `connect_websocket()`
- `connect_governance()`
- `connect_knowledge_base()`
- `connect_search()`
- `submit_user_confirmation()`
- `get_pending_confirmations()`
- `get_verification_stats()`
- `get_grace_verification_engine()`

---
*Grace 3.1*
