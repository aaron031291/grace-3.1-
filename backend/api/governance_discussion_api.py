"""
Governance Discussion API — Chat with Kimi+Opus about each approval request.

When Grace or the system needs approval for something (destructive action,
governance bypass, consensus disagreement), it creates a discussion thread.
The user can chat with both LLMs about the request before approving/denying.

Flow:
  1. System creates a governance request
  2. User sees it in the Governance tab
  3. User opens a discussion → Kimi+Opus both analyse the request
  4. User asks questions, both models respond
  5. User approves or denies with full context
  6. Decision logged via Genesis Key
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import json
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/governance/discuss", tags=["Governance Discussion"])

DISCUSSIONS_DIR = Path(__file__).parent.parent / "data" / "governance_discussions"


class DiscussionCreate(BaseModel):
    title: str
    description: str
    request_type: str = "approval"  # approval, tiebreak, override, destructive
    context: str = ""
    severity: str = "medium"  # low, medium, high, critical


class DiscussionMessage(BaseModel):
    discussion_id: str
    message: str
    ask_models: bool = True  # whether to get Kimi+Opus response


class DiscussionDecision(BaseModel):
    discussion_id: str
    decision: str  # approve, deny, defer
    reasoning: str = ""


def _ensure():
    DISCUSSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _load_discussion(did: str) -> Optional[dict]:
    path = DISCUSSIONS_DIR / f"{did}.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


def _save_discussion(did: str, data: dict):
    _ensure()
    (DISCUSSIONS_DIR / f"{did}.json").write_text(json.dumps(data, indent=2, default=str))


@router.post("/create")
async def create_discussion(req: DiscussionCreate):
    """Create a new governance discussion thread."""
    did = f"gov_{uuid.uuid4().hex[:10]}"

    discussion = {
        "id": did,
        "title": req.title,
        "description": req.description,
        "request_type": req.request_type,
        "context": req.context,
        "severity": req.severity,
        "status": "open",
        "created_at": datetime.utcnow().isoformat(),
        "messages": [],
        "decision": None,
        "decision_reasoning": None,
        "decided_at": None,
    }

    # Get initial analysis from both models
    try:
        from cognitive.consensus_engine import run_consensus
        result = run_consensus(
            prompt=(
                f"A governance approval request has been created:\n\n"
                f"Title: {req.title}\n"
                f"Type: {req.request_type}\n"
                f"Severity: {req.severity}\n"
                f"Description: {req.description}\n"
                f"Context: {req.context}\n\n"
                f"Provide your analysis: Should this be approved? What are the risks? "
                f"What questions should the human ask before deciding?"
            ),
            models=["kimi", "opus"],
            source="autonomous",
        )

        for r in result.individual_responses:
            if r.get("response"):
                discussion["messages"].append({
                    "role": r["model_name"],
                    "content": r["response"][:2000],
                    "timestamp": datetime.utcnow().isoformat(),
                })

        if result.final_output:
            discussion["messages"].append({
                "role": "consensus",
                "content": result.final_output[:2000],
                "timestamp": datetime.utcnow().isoformat(),
            })
    except Exception as e:
        discussion["messages"].append({
            "role": "system",
            "content": f"Model analysis unavailable: {e}",
            "timestamp": datetime.utcnow().isoformat(),
        })

    _save_discussion(did, discussion)

    try:
        from cognitive.event_bus import publish
        publish("governance.discussion_created", {
            "id": did, "title": req.title, "severity": req.severity,
        }, source="governance_discussion")
    except Exception:
        pass

    return discussion


@router.post("/message")
async def add_message(req: DiscussionMessage):
    """Add a message to the discussion and optionally get model responses."""
    discussion = _load_discussion(req.discussion_id)
    if not discussion:
        raise HTTPException(status_code=404, detail="Discussion not found")

    # Add user message
    discussion["messages"].append({
        "role": "user",
        "content": req.message,
        "timestamp": datetime.utcnow().isoformat(),
    })

    # Get model responses if requested
    if req.ask_models:
        history = "\n".join(
            f"{m['role']}: {m['content'][:300]}"
            for m in discussion["messages"][-6:]
        )

        try:
            from cognitive.consensus_engine import run_consensus
            result = run_consensus(
                prompt=(
                    f"Governance discussion about: {discussion['title']}\n\n"
                    f"Recent messages:\n{history}\n\n"
                    f"User just asked: {req.message}\n\n"
                    f"Respond to the user's question about this governance decision."
                ),
                models=["kimi", "opus"],
                source="user",
            )

            for r in result.individual_responses:
                if r.get("response"):
                    discussion["messages"].append({
                        "role": r["model_name"],
                        "content": r["response"][:2000],
                        "timestamp": datetime.utcnow().isoformat(),
                    })
        except Exception as e:
            discussion["messages"].append({
                "role": "system",
                "content": f"Model response unavailable: {e}",
                "timestamp": datetime.utcnow().isoformat(),
            })

    _save_discussion(req.discussion_id, discussion)
    return discussion


@router.post("/decide")
async def make_decision(req: DiscussionDecision):
    """Make a final decision on the governance request."""
    discussion = _load_discussion(req.discussion_id)
    if not discussion:
        raise HTTPException(status_code=404, detail="Discussion not found")

    discussion["decision"] = req.decision
    discussion["decision_reasoning"] = req.reasoning
    discussion["decided_at"] = datetime.utcnow().isoformat()
    discussion["status"] = "decided"

    discussion["messages"].append({
        "role": "decision",
        "content": f"Decision: {req.decision.upper()}. Reasoning: {req.reasoning}",
        "timestamp": datetime.utcnow().isoformat(),
    })

    _save_discussion(req.discussion_id, discussion)

    # Genesis Key
    try:
        from api._genesis_tracker import track
        track(
            key_type="system",
            what=f"Governance decision: {req.decision} — {discussion['title']}",
            who="user",
            why=req.reasoning,
            how="governance_discussion.decide",
            output_data={
                "discussion_id": req.discussion_id,
                "decision": req.decision,
                "message_count": len(discussion["messages"]),
            },
            tags=["governance", "decision", req.decision, discussion.get("severity", "medium")],
        )
    except Exception:
        pass

    try:
        from cognitive.event_bus import publish
        publish("governance.decision_made", {
            "id": req.discussion_id, "decision": req.decision,
            "title": discussion["title"],
        }, source="governance_discussion")
    except Exception:
        pass

    return discussion


@router.get("/list")
async def list_discussions(status: str = None):
    """List all governance discussions."""
    _ensure()
    discussions = []
    for f in sorted(DISCUSSIONS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text())
            if status and data.get("status") != status:
                continue
            discussions.append({
                "id": data["id"],
                "title": data["title"],
                "request_type": data.get("request_type"),
                "severity": data.get("severity"),
                "status": data.get("status"),
                "message_count": len(data.get("messages", [])),
                "decision": data.get("decision"),
                "created_at": data.get("created_at"),
            })
        except Exception:
            pass
    return {"discussions": discussions, "total": len(discussions)}


@router.get("/{discussion_id}")
async def get_discussion(discussion_id: str):
    """Get full discussion with all messages."""
    discussion = _load_discussion(discussion_id)
    if not discussion:
        raise HTTPException(status_code=404, detail="Discussion not found")
    return discussion
