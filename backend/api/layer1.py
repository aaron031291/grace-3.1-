"""
Layer 1 API Endpoints - All Input Sources

Provides endpoints for ALL Layer 1 input sources:
1. User inputs
2. File uploads
3. External APIs
4. Web scraping / HTML
5. Memory mesh
6. Learning memory
7. Whitelist
8. System events

NOW INTEGRATED WITH COGNITIVE ENGINE:
- All Layer 1 inputs flow through OODA loop
- 12 invariants enforced automatically
- Deterministic decision-making with full audit trail
"""
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Body
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from sqlalchemy.orm import Session

from database.session import get_session
from genesis.layer1_integration import get_layer1_integration
from genesis.cognitive_layer1_integration import get_cognitive_layer1_integration

router = APIRouter(prefix="/layer1", tags=["Layer 1 Input"])


# ==================== Configuration ====================

# Enable/disable cognitive integration globally
ENABLE_COGNITIVE_INTEGRATION = True  # Set to False to disable OODA loop enforcement

# Enable Layer 3 Governance Enforcement
ENABLE_GOVERNANCE_ENFORCEMENT = True  # Set to False to disable trust verification


# ==================== Pydantic Models ====================

class UserInputRequest(BaseModel):
    """User input request."""
    user_input: str = Field(..., description="User's input text")
    user_id: str = Field(..., description="Genesis ID of user")
    input_type: str = Field("chat", description="Type of input (chat, command, ui_interaction)")
    metadata: Optional[Dict] = Field(None, description="Additional metadata")


class ExternalAPIRequest(BaseModel):
    """External API request."""
    api_name: str = Field(..., description="Name of API (e.g., OpenAI, GitHub)")
    api_endpoint: str = Field(..., description="API endpoint called")
    api_data: Dict = Field(..., description="Data received from API")
    user_id: Optional[str] = Field(None, description="Genesis ID if user-initiated")
    metadata: Optional[Dict] = Field(None, description="Additional API metadata")


class WebScrapingRequest(BaseModel):
    """Web scraping request."""
    url: str = Field(..., description="URL that was scraped")
    html_content: str = Field(..., description="Raw HTML content")
    parsed_data: Dict = Field(..., description="Parsed/extracted data")
    user_id: Optional[str] = Field(None, description="Genesis ID if user-initiated")
    metadata: Optional[Dict] = Field(None, description="Additional scraping metadata")


class MemoryMeshRequest(BaseModel):
    """Memory mesh request."""
    memory_type: str = Field(..., description="Type of memory (system, knowledge_graph, context)")
    memory_data: Dict = Field(..., description="Memory data")
    user_id: Optional[str] = Field(None, description="Genesis ID if user-specific")
    metadata: Optional[Dict] = Field(None, description="Additional memory metadata")


class LearningMemoryRequest(BaseModel):
    """Learning memory request."""
    learning_type: str = Field(..., description="Type of learning (training, feedback, pattern)")
    learning_data: Dict = Field(..., description="Learning data")
    user_id: Optional[str] = Field(None, description="Genesis ID if user-specific")
    metadata: Optional[Dict] = Field(None, description="Additional learning metadata")


class WhitelistRequest(BaseModel):
    """Whitelist request."""
    whitelist_type: str = Field(..., description="Type of whitelist (source, domain, api)")
    whitelist_data: Dict = Field(..., description="Whitelist data")
    user_id: Optional[str] = Field(None, description="Genesis ID of admin")
    metadata: Optional[Dict] = Field(None, description="Additional whitelist metadata")


class SystemEventRequest(BaseModel):
    """System event request."""
    event_type: str = Field(..., description="Type of event (error, log, telemetry)")
    event_data: Dict = Field(..., description="Event data")
    metadata: Optional[Dict] = Field(None, description="Additional event metadata")


# ==================== Endpoints ====================

@router.post("/user-input")
async def process_user_input(
    request: UserInputRequest,
    session: Session = Depends(get_session)
):
    """
    Process user input through Layer 1.

    Flows through complete pipeline:
    Layer 3 Governance → Cognitive Engine (OODA + Invariants) → Layer 1 → Genesis Key → Version Control → Librarian → Immutable Memory → RAG → World Model

    Returns result with cognitive metadata showing decision_id, invariant validation, and governance enforcement.
    """
    try:
        # Layer 3 Governance Enforcement
        governance_result = None
        if ENABLE_GOVERNANCE_ENFORCEMENT:
            from governance.layer_enforcement import enforce_layer1, EnforcementAction
            governance_result = await enforce_layer1(
                data=request.user_input,
                origin="user_input",
                input_type=request.input_type,
                user_id=request.user_id,
                metadata=request.metadata
            )
            
            # Block if governance denies
            if governance_result.action == EnforcementAction.BLOCK:
                return {
                    "success": False,
                    "blocked": True,
                    "reason": governance_result.reasoning,
                    "trust_score": governance_result.trust_score,
                    "governance": governance_result.to_dict()
                }
            
            # Quarantine requires acknowledgment (still process but flag)
            if governance_result.action == EnforcementAction.QUARANTINE:
                # Add quarantine flag to metadata
                request.metadata = request.metadata or {}
                request.metadata["quarantined"] = True
                request.metadata["quarantine_reason"] = governance_result.reasoning
        
        if ENABLE_COGNITIVE_INTEGRATION:
            # Use cognitive-enhanced Layer 1
            cognitive_layer1 = get_cognitive_layer1_integration(session=session)
            result = cognitive_layer1.process_user_input(
                user_input=request.user_input,
                user_id=request.user_id,
                input_type=request.input_type,
                metadata=request.metadata
            )
        else:
            # Direct Layer 1 (legacy mode)
            layer1 = get_layer1_integration(session=session)
            result = layer1.process_user_input(
                user_input=request.user_input,
                user_id=request.user_id,
                input_type=request.input_type,
                metadata=request.metadata
            )

        # Add governance metadata to result
        if governance_result and isinstance(result, dict):
            result["governance"] = governance_result.to_dict()

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def process_file_upload(
    file: UploadFile = File(...),
    user_id: str = Body(...),
    session: Session = Depends(get_session)
):
    """
    Process file upload through Layer 1.

    Accepts any file type and processes through complete pipeline.
    FILE UPLOADS ARE IRREVERSIBLE - enforces cognitive validation and governance.
    """
    try:
        # Read file content
        file_content = await file.read()

        # Layer 3 Governance Enforcement (files are external, require verification)
        governance_result = None
        if ENABLE_GOVERNANCE_ENFORCEMENT:
            from governance.layer_enforcement import enforce_layer1, EnforcementAction
            governance_result = await enforce_layer1(
                data={"filename": file.filename, "size": len(file_content)},
                origin="file_upload",
                input_type="upload",
                user_id=user_id,
                metadata={"content_type": file.content_type}
            )
            
            if governance_result.action == EnforcementAction.BLOCK:
                return {
                    "success": False,
                    "blocked": True,
                    "reason": governance_result.reasoning,
                    "governance": governance_result.to_dict()
                }

        if ENABLE_COGNITIVE_INTEGRATION:
            cognitive_layer1 = get_cognitive_layer1_integration(session=session)
            result = cognitive_layer1.process_file_upload(
                file_content=file_content,
                file_name=file.filename,
                file_type=file.content_type,
                user_id=user_id
            )
        else:
            layer1 = get_layer1_integration(session=session)
            result = layer1.process_file_upload(
                file_content=file_content,
                file_name=file.filename,
                file_type=file.content_type,
                user_id=user_id
            )

        if governance_result and isinstance(result, dict):
            result["governance"] = governance_result.to_dict()

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/external-api")
async def process_external_api(
    request: ExternalAPIRequest,
    session: Session = Depends(get_session)
):
    """
    Process external API data through Layer 1 with cognitive validation.

    Use this to ingest data from external APIs (OpenAI, GitHub, etc.)
    EXTERNAL SOURCES REQUIRE VERIFICATION - enforces governance trust scoring.
    """
    try:
        # Layer 3 Governance Enforcement (external APIs require verification)
        governance_result = None
        if ENABLE_GOVERNANCE_ENFORCEMENT:
            from governance.layer_enforcement import enforce_layer1, EnforcementAction
            governance_result = await enforce_layer1(
                data=request.api_data,
                origin=f"api_{request.api_name}",
                input_type="api",
                user_id=request.user_id,
                metadata={"api_name": request.api_name, "endpoint": request.api_endpoint}
            )
            
            if governance_result.action == EnforcementAction.BLOCK:
                return {
                    "success": False,
                    "blocked": True,
                    "reason": governance_result.reasoning,
                    "trust_score": governance_result.trust_score,
                    "governance": governance_result.to_dict()
                }
            
            # For quarantined data, add flag
            if governance_result.action == EnforcementAction.QUARANTINE:
                request.metadata = request.metadata or {}
                request.metadata["quarantined"] = True
                request.metadata["governance_score"] = governance_result.trust_score

        if ENABLE_COGNITIVE_INTEGRATION:
            cognitive_layer1 = get_cognitive_layer1_integration(session=session)
            result = cognitive_layer1.process_external_api(
                api_name=request.api_name,
                api_endpoint=request.api_endpoint,
                api_data=request.api_data,
                user_id=request.user_id,
                metadata=request.metadata
            )
        else:
            layer1 = get_layer1_integration(session=session)
            result = layer1.process_external_api(
                api_name=request.api_name,
                api_endpoint=request.api_endpoint,
                api_data=request.api_data,
                user_id=request.user_id,
                metadata=request.metadata
            )

        if governance_result and isinstance(result, dict):
            result["governance"] = governance_result.to_dict()

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/web-scraping")
async def process_web_scraping(
    request: WebScrapingRequest,
    session: Session = Depends(get_session)
):
    """Process web scraping data through Cognitive Layer 1."""
    try:
        if ENABLE_COGNITIVE_INTEGRATION:
            cognitive_layer1 = get_cognitive_layer1_integration(session=session)
            result = cognitive_layer1.process_web_scraping(
                url=request.url,
                html_content=request.html_content,
                parsed_data=request.parsed_data,
                user_id=request.user_id,
                metadata=request.metadata
            )
        else:
            layer1 = get_layer1_integration(session=session)
            result = layer1.process_web_scraping(
                url=request.url,
                html_content=request.html_content,
                parsed_data=request.parsed_data,
                user_id=request.user_id,
                metadata=request.metadata
            )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory-mesh")
async def process_memory_mesh(
    request: MemoryMeshRequest,
    session: Session = Depends(get_session)
):
    """Process memory mesh data through Cognitive Layer 1."""
    try:
        if ENABLE_COGNITIVE_INTEGRATION:
            cognitive_layer1 = get_cognitive_layer1_integration(session=session)
            result = cognitive_layer1.process_memory_mesh(
                memory_type=request.memory_type,
                memory_data=request.memory_data,
                user_id=request.user_id,
                metadata=request.metadata
            )
        else:
            layer1 = get_layer1_integration(session=session)
            result = layer1.process_memory_mesh(
                memory_type=request.memory_type,
                memory_data=request.memory_data,
                user_id=request.user_id,
                metadata=request.metadata
            )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learning-memory")
async def process_learning_memory(
    request: LearningMemoryRequest,
    session: Session = Depends(get_session)
):
    """
    Process learning memory through Cognitive Layer 1.

    SAFETY-CRITICAL & SYSTEMIC - Learning affects future behavior.
    """
    try:
        if ENABLE_COGNITIVE_INTEGRATION:
            cognitive_layer1 = get_cognitive_layer1_integration(session=session)
            result = cognitive_layer1.process_learning_memory(
                learning_type=request.learning_type,
                learning_data=request.learning_data,
                user_id=request.user_id,
                metadata=request.metadata
            )
        else:
            layer1 = get_layer1_integration(session=session)
            result = layer1.process_learning_memory(
                learning_type=request.learning_type,
                learning_data=request.learning_data,
                user_id=request.user_id,
                metadata=request.metadata
            )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/whitelist")
async def process_whitelist(
    request: WhitelistRequest,
    session: Session = Depends(get_session)
):
    """
    Process whitelist operations through Cognitive Layer 1.

    SAFETY-CRITICAL & SYSTEMIC - Affects security.
    """
    try:
        if ENABLE_COGNITIVE_INTEGRATION:
            cognitive_layer1 = get_cognitive_layer1_integration(session=session)
            result = cognitive_layer1.process_whitelist(
                whitelist_type=request.whitelist_type,
                whitelist_data=request.whitelist_data,
                user_id=request.user_id,
                metadata=request.metadata
            )
        else:
            layer1 = get_layer1_integration(session=session)
            result = layer1.process_whitelist(
                whitelist_type=request.whitelist_type,
                whitelist_data=request.whitelist_data,
                user_id=request.user_id,
                metadata=request.metadata
            )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/system-event")
async def process_system_event(
    request: SystemEventRequest,
    session: Session = Depends(get_session)
):
    """Process system events through Cognitive Layer 1."""
    try:
        if ENABLE_COGNITIVE_INTEGRATION:
            cognitive_layer1 = get_cognitive_layer1_integration(session=session)
            result = cognitive_layer1.process_system_event(
                event_type=request.event_type,
                event_data=request.event_data,
                metadata=request.metadata
            )
        else:
            layer1 = get_layer1_integration(session=session)
            result = layer1.process_system_event(
                event_type=request.event_type,
                event_data=request.event_data,
                metadata=request.metadata
            )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_layer1_stats(session: Session = Depends(get_session)):
    """
    Get Layer 1 statistics with cognitive metadata.
    """
    try:
        if ENABLE_COGNITIVE_INTEGRATION:
            cognitive_layer1 = get_cognitive_layer1_integration(session=session)
            stats = cognitive_layer1.get_layer1_stats()
        else:
            layer1 = get_layer1_integration(session=session)
            stats = layer1.get_layer1_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/verify")
async def verify_layer1_structure(session: Session = Depends(get_session)):
    """
    Verify Layer 1 directory structure is complete.

    Checks all Layer 1 folders exist.
    """
    try:
        if ENABLE_COGNITIVE_INTEGRATION:
            cognitive_layer1 = get_cognitive_layer1_integration(session=session)
            verification = cognitive_layer1.verify_layer1_structure()
        else:
            layer1 = get_layer1_integration(session=session)
            verification = layer1.verify_layer1_structure()
        return verification
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Cognitive Endpoints ====================

@router.get("/cognitive/decisions")
async def get_decision_history(
    limit: int = 100,
    session: Session = Depends(get_session)
):
    """
    Get cognitive decision history.

    Shows all OODA loop decisions made by Layer 1 with full audit trail.

    Args:
        limit: Maximum number of decisions to return (default 100)

    Returns:
        List of decision contexts with OODA phases and invariant validation
    """
    try:
        if not ENABLE_COGNITIVE_INTEGRATION:
            return {
                "message": "Cognitive integration is disabled",
                "decisions": []
            }

        cognitive_layer1 = get_cognitive_layer1_integration(session=session)
        decisions = cognitive_layer1.get_decision_history(limit=limit)

        return {
            "total": len(decisions),
            "decisions": decisions
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cognitive/active")
async def get_active_decisions(session: Session = Depends(get_session)):
    """
    Get currently active cognitive decisions.

    Shows Layer 1 operations currently in progress.

    Returns:
        List of active decision contexts
    """
    try:
        if not ENABLE_COGNITIVE_INTEGRATION:
            return {
                "message": "Cognitive integration is disabled",
                "active_decisions": []
            }

        cognitive_layer1 = get_cognitive_layer1_integration(session=session)
        active = cognitive_layer1.get_active_decisions()

        return {
            "total": len(active),
            "active_decisions": [
                {
                    "decision_id": ctx.decision_id,
                    "problem_statement": ctx.problem_statement,
                    "goal": ctx.goal,
                    "is_safety_critical": ctx.is_safety_critical,
                    "impact_scope": ctx.impact_scope,
                    "is_reversible": ctx.is_reversible,
                    "created_at": ctx.created_at.isoformat()
                }
                for ctx in active
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cognitive/status")
async def get_cognitive_status(session: Session = Depends(get_session)):
    """
    Get cognitive integration status.

    Shows whether OODA loop and invariants are enforced.

    Returns:
        Cognitive engine configuration and status
    """
    try:
        return {
            "cognitive_integration_enabled": ENABLE_COGNITIVE_INTEGRATION,
            "features": {
                "ooda_loop": ENABLE_COGNITIVE_INTEGRATION,
                "12_invariants": ENABLE_COGNITIVE_INTEGRATION,
                "decision_logging": ENABLE_COGNITIVE_INTEGRATION,
                "ambiguity_tracking": ENABLE_COGNITIVE_INTEGRATION,
                "blast_radius_analysis": ENABLE_COGNITIVE_INTEGRATION
            },
            "invariants": [
                "1. OODA Loop - Primary Control Loop",
                "2. Ambiguity Accounting - Known/Unknown Tracking",
                "3. Reversibility - Before Commitment",
                "4. Determinism - Where Safety Depends on It",
                "5. Blast Radius - Minimization",
                "6. Observability - Complete Traceability",
                "7. Simplicity - Complexity Must Justify Benefit",
                "8. Feedback - Results Inform Future Decisions",
                "9. Bounded Recursion - No Infinite Loops",
                "10. Optionality - Over Optimization",
                "11. Time-Bounded Reasoning - Planning Must Terminate",
                "12. Forward Simulation - Chess Mode"
            ],
            "operation_classification": {
                "user_input": {"reversible": True, "safety_critical": False, "impact_scope": "local"},
                "file_upload": {"reversible": False, "safety_critical": False, "impact_scope": "component"},
                "learning_memory": {"reversible": False, "safety_critical": True, "impact_scope": "systemic"},
                "whitelist": {"reversible": False, "safety_critical": True, "impact_scope": "systemic"}
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Whitelist Management Endpoints ====================

# In-memory whitelist storage (in production, use database)
_whitelist_store = {
    "domains": [
        {"id": "d-1", "domain": "github.com", "status": "active", "added": "2025-01-01", "hits": 245, "description": "GitHub API access"},
        {"id": "d-2", "domain": "api.openai.com", "status": "active", "added": "2025-01-02", "hits": 189, "description": "OpenAI API"},
        {"id": "d-3", "domain": "huggingface.co", "status": "active", "added": "2025-01-03", "hits": 67, "description": "Hugging Face models"},
    ],
    "paths": [
        {"id": "p-1", "path": "/api/*", "type": "wildcard", "status": "active", "hits": 1250, "description": "All API endpoints"},
        {"id": "p-2", "path": "/auth/login", "type": "exact", "status": "active", "hits": 450, "description": "Login endpoint"},
    ],
    "patterns": [
        {"id": "pt-1", "pattern": "^[a-zA-Z0-9_]+\\.py$", "type": "regex", "status": "active", "hits": 890, "description": "Python files"},
        {"id": "pt-2", "pattern": "*.md", "type": "glob", "status": "active", "hits": 156, "description": "Markdown files"},
    ],
}

_whitelist_logs = [
    {"id": "l-1", "timestamp": "2025-01-11T10:28:00Z", "action": "allowed", "type": "domain", "value": "github.com", "source": "API request"},
    {"id": "l-2", "timestamp": "2025-01-11T10:27:00Z", "action": "blocked", "type": "path", "value": "/admin/delete", "source": "User input"},
    {"id": "l-3", "timestamp": "2025-01-11T10:25:00Z", "action": "allowed", "type": "pattern", "value": "utils.py", "source": "File access"},
]


class WhitelistResponse(BaseModel):
    """Response for whitelist data."""
    total_entries: int = Field(0, description="Total whitelist entries")
    domains_count: int = Field(0, description="Number of domain entries")
    paths_count: int = Field(0, description="Number of path entries")
    patterns_count: int = Field(0, description="Number of pattern entries")
    last_updated: str = Field(..., description="Last update timestamp")
    blocked_today: int = Field(0, description="Blocked requests today")
    allowed_today: int = Field(0, description="Allowed requests today")
    domains: List[Dict] = Field(default_factory=list)
    paths: List[Dict] = Field(default_factory=list)
    patterns: List[Dict] = Field(default_factory=list)


class WhitelistLogsResponse(BaseModel):
    """Response for whitelist logs."""
    logs: List[Dict] = Field(default_factory=list)


@router.get("/whitelist", response_model=WhitelistResponse)
async def get_whitelist():
    """
    Get all whitelist entries.

    Returns domains, paths, and patterns with statistics.
    """
    from datetime import datetime

    return WhitelistResponse(
        total_entries=len(_whitelist_store["domains"]) + len(_whitelist_store["paths"]) + len(_whitelist_store["patterns"]),
        domains_count=len(_whitelist_store["domains"]),
        paths_count=len(_whitelist_store["paths"]),
        patterns_count=len(_whitelist_store["patterns"]),
        last_updated=datetime.now().isoformat(),
        blocked_today=12,
        allowed_today=892,
        domains=_whitelist_store["domains"],
        paths=_whitelist_store["paths"],
        patterns=_whitelist_store["patterns"]
    )


@router.get("/whitelist/logs", response_model=WhitelistLogsResponse)
async def get_whitelist_logs():
    """
    Get whitelist access logs.

    Returns recent allowed/blocked requests.
    """
    return WhitelistLogsResponse(logs=_whitelist_logs)


@router.patch("/whitelist/{entry_type}/{entry_id}")
async def update_whitelist_entry(
    entry_type: str,
    entry_id: str,
    status: str = Body(..., embed=True)
):
    """
    Update a whitelist entry status.

    Args:
        entry_type: Type of entry (domains, paths, patterns)
        entry_id: Entry ID
        status: New status (active, paused)
    """
    if entry_type not in _whitelist_store:
        raise HTTPException(status_code=400, detail=f"Invalid entry type: {entry_type}")

    for entry in _whitelist_store[entry_type]:
        if entry["id"] == entry_id:
            entry["status"] = status
            return {"success": True, "entry": entry}

    raise HTTPException(status_code=404, detail=f"Entry not found: {entry_id}")


@router.delete("/whitelist/{entry_type}/{entry_id}")
async def delete_whitelist_entry(entry_type: str, entry_id: str):
    """
    Delete a whitelist entry.

    Args:
        entry_type: Type of entry (domains, paths, patterns)
        entry_id: Entry ID
    """
    if entry_type not in _whitelist_store:
        raise HTTPException(status_code=400, detail=f"Invalid entry type: {entry_type}")

    for i, entry in enumerate(_whitelist_store[entry_type]):
        if entry["id"] == entry_id:
            deleted = _whitelist_store[entry_type].pop(i)
            return {"success": True, "deleted": deleted}

    raise HTTPException(status_code=404, detail=f"Entry not found: {entry_id}")
