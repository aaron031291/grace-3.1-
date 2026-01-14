"""
Governance API - Three Pillar Framework with Real Database Integration

Provides endpoints for:
1. Uploadable Governance Documents (industry rules, ISO compliance, standards)
2. Three Governance Pillars (Operational, Behavioral, Immutable)
3. Human-in-the-Loop Decision Review (pending, confirm, discuss, deny)
4. Rule management and KPI-driven governance

Integrates with:
- Database models for persistence
- security/governance.py GovernanceEngine for real enforcement
"""

import logging
import os
import re
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.session import get_session
from models.database_models import (
    GovernanceRule as GovernanceRuleModel,
    GovernanceDocument as GovernanceDocumentModel,
    GovernanceDecision as GovernanceDecisionModel
)
from security.governance import (
    GovernanceEngine,
    get_governance_engine,
    ConstitutionalRule,
    CONSTITUTIONAL_RULES,
    AutonomyTier,
    AUTONOMY_TIERS
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/governance", tags=["Governance Framework"])

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class GovernanceRuleCreate(BaseModel):
    """Create a new governance rule."""
    name: str
    description: str
    pillar_type: str  # operational, behavioral
    severity: int = Field(ge=1, le=10, default=5)
    enabled: bool = True
    pattern: Optional[str] = None
    action: str = "warn"  # warn, block, flag, redact
    source: Optional[str] = None


class GovernanceRuleUpdate(BaseModel):
    """Update an existing rule."""
    name: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[int] = Field(ge=1, le=10, default=None)
    enabled: Optional[bool] = None
    pattern: Optional[str] = None
    action: Optional[str] = None


class RuleToggle(BaseModel):
    """Toggle a rule on/off."""
    enabled: bool


class DecisionAction(BaseModel):
    """Action taken on a decision."""
    note: Optional[str] = None
    reviewed_by: str = "user"


class GovernanceCheckRequest(BaseModel):
    """Request to check governance compliance."""
    action_type: str
    content: str
    context: Optional[Dict[str, Any]] = None


# =============================================================================
# DEFAULT RULES (Seeded on first run)
# =============================================================================

DEFAULT_RULES = {
    "operational": [
        {"name": "Industry Compliance", "description": "Ensure outputs comply with industry standards", "severity": 8, "source": "ISO 27001", "pattern": None, "action": "flag"},
        {"name": "Data Classification", "description": "Classify and handle data according to sensitivity", "severity": 7, "source": "GDPR", "pattern": None, "action": "warn"},
        {"name": "Audit Trail Required", "description": "All significant actions must be logged", "severity": 6, "source": "SOC 2", "pattern": None, "action": "flag"},
    ],
    "behavioral": [
        {"name": "Professional Tone", "description": "Maintain professional communication style", "severity": 3, "pattern": None, "action": "warn"},
        {"name": "Response Clarity", "description": "Provide clear, actionable responses", "severity": 2, "pattern": None, "action": "warn"},
        {"name": "User Preferences", "description": "Respect user-defined interaction preferences", "severity": 2, "pattern": None, "action": "warn"},
    ],
    "immutable": [
        {"name": "No Harmful Content", "description": "Never generate content that could cause harm to humans", "severity": 10, "pattern": r"harm|danger|kill|attack", "action": "block"},
        {"name": "No Illegal Activities", "description": "Never assist with illegal activities", "severity": 10, "pattern": r"illegal|fraud|hack|steal", "action": "block"},
        {"name": "No PII Exposure", "description": "Never expose personally identifiable information", "severity": 10, "pattern": r"SSN|social.?security|\d{3}-\d{2}-\d{4}", "action": "redact"},
        {"name": "Safety Override Protection", "description": "Safety rules cannot be bypassed by any prompt", "severity": 10, "pattern": r"ignore.*safety|bypass.*rules", "action": "block"},
        {"name": "Constitutional Compliance", "description": "All actions must comply with constitutional rules", "severity": 10, "pattern": None, "action": "block"},
    ]
}


def seed_default_rules(session: Session):
    """Seed default rules if none exist."""
    existing = session.query(GovernanceRuleModel).count()
    if existing == 0:
        logger.info("Seeding default governance rules...")
        for pillar, rules in DEFAULT_RULES.items():
            for rule_data in rules:
                rule = GovernanceRuleModel(
                    name=rule_data["name"],
                    description=rule_data["description"],
                    pillar_type=pillar,
                    severity=rule_data["severity"],
                    enabled=True,
                    pattern=rule_data.get("pattern"),
                    action=rule_data["action"],
                    source=rule_data.get("source")
                )
                session.add(rule)
        session.commit()
        logger.info(f"Seeded {sum(len(r) for r in DEFAULT_RULES.values())} default rules")


# =============================================================================
# PILLAR & STATS ENDPOINTS
# =============================================================================

@router.get("/pillars")
async def get_governance_pillars(session: Session = Depends(get_session)):
    """
    Get all governance pillars with their rules and documents.
    Returns the three-pillar framework data from the database.
    """
    # Seed default rules if needed
    seed_default_rules(session)

    result = {}
    for pillar in ["operational", "behavioral", "immutable"]:
        # Get rules from database
        rules = session.query(GovernanceRuleModel).filter(
            GovernanceRuleModel.pillar_type == pillar
        ).order_by(GovernanceRuleModel.severity.desc()).all()

        # Get documents from database
        docs = session.query(GovernanceDocumentModel).filter(
            GovernanceDocumentModel.pillar_type == pillar
        ).all()

        result[pillar] = {
            "rules": [r.to_dict() for r in rules],
            "documents": [d.to_dict() for d in docs]
        }

    return result


@router.get("/stats")
async def get_governance_stats(session: Session = Depends(get_session)):
    """
    Get governance statistics including compliance score.
    Pulls real data from database and GovernanceEngine.
    """
    # Seed default rules if needed
    seed_default_rules(session)

    # Get rule counts
    total_rules = session.query(GovernanceRuleModel).count()
    active_rules = session.query(GovernanceRuleModel).filter(
        GovernanceRuleModel.enabled == True
    ).count()

    # Get decision counts
    pending_decisions = session.query(GovernanceDecisionModel).filter(
        GovernanceDecisionModel.status == "pending"
    ).count()

    # Get today's decisions
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    confirmed_today = session.query(GovernanceDecisionModel).filter(
        GovernanceDecisionModel.status == "confirmed",
        GovernanceDecisionModel.resolved_at >= today_start
    ).count()
    denied_today = session.query(GovernanceDecisionModel).filter(
        GovernanceDecisionModel.status == "denied",
        GovernanceDecisionModel.resolved_at >= today_start
    ).count()

    # Calculate compliance score from GovernanceEngine
    try:
        engine = get_governance_engine()
        health = engine.get_kpi_health()
        trust_score = health.get("trust_score", {}).get("value", 0.5)
        success_rate = health.get("success_rate", {}).get("value", 0.95)
        # Weighted compliance score
        compliance_score = (trust_score * 0.4) + (success_rate * 0.4) + (active_rules / max(total_rules, 1) * 0.2)
    except Exception as e:
        logger.warning(f"Could not get KPI health: {e}")
        compliance_score = active_rules / max(total_rules, 1) * 0.94 if total_rules > 0 else 0.5

    return {
        "total_rules": total_rules,
        "active_rules": active_rules,
        "pending_decisions": pending_decisions,
        "confirmed_today": confirmed_today,
        "denied_today": denied_today,
        "compliance_score": round(compliance_score, 2)
    }


# =============================================================================
# DOCUMENT MANAGEMENT
# =============================================================================

@router.post("/documents/upload")
async def upload_governance_document(
    file: UploadFile = File(...),
    pillar_type: str = Form(...),
    filename: str = Form(None),
    session: Session = Depends(get_session)
):
    """
    Upload a governance document for a specific pillar.
    Documents are processed to extract rules.
    """
    if pillar_type not in ["operational", "behavioral"]:
        raise HTTPException(status_code=400, detail="Can only upload to operational or behavioral pillars")

    fname = filename or file.filename

    # Create document record
    doc = GovernanceDocumentModel(
        filename=fname,
        pillar_type=pillar_type,
        status="processing"
    )
    session.add(doc)
    session.commit()

    try:
        # Read file content
        content = await file.read()

        # Save to governance documents folder
        gov_docs_path = os.path.join("data", "governance_documents", pillar_type)
        os.makedirs(gov_docs_path, exist_ok=True)

        file_path = os.path.join(gov_docs_path, f"{doc.id}_{fname}")
        with open(file_path, "wb") as f:
            f.write(content)

        doc.file_path = file_path

        # Extract text and rules
        try:
            from file_manager.file_handler import extract_file_text
            text = extract_file_text(file_path)
        except (ImportError, OSError, ValueError):
            text = content.decode("utf-8", errors="ignore")

        # Process document to extract rules
        extracted_count = extract_rules_from_document(session, text, pillar_type, fname)

        # Update document status
        doc.status = "processed"
        doc.extracted_rules_count = extracted_count
        doc.processed_at = datetime.now()
        session.commit()

        return {
            "document_id": str(doc.id),
            "status": "processed",
            "extracted_rules": extracted_count,
            "message": f"Successfully processed {fname} and extracted {extracted_count} rules"
        }

    except Exception as e:
        doc.status = "error"
        doc.error_message = str(e)
        session.commit()
        logger.error(f"Error processing governance document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def extract_rules_from_document(session: Session, text: str, pillar_type: str, source: str) -> int:
    """
    Extract governance rules from document text.
    Uses keyword matching (could be enhanced with NLP/LLM).
    """
    extracted_count = 0

    # Keywords that indicate rules
    keywords = {
        "operational": ["must comply", "required to", "shall ensure", "must maintain", "compliance", "mandatory"],
        "behavioral": ["should communicate", "preferred", "tone", "style", "interaction", "respond with"],
    }

    lines = text.split("\n")
    for line in lines:
        line_lower = line.lower().strip()
        if len(line_lower) < 15:
            continue

        for keyword in keywords.get(pillar_type, []):
            if keyword in line_lower:
                # Extract rule name (first sentence fragment)
                name = line.split(".")[0][:100].strip()
                if len(name) < 5:
                    name = f"Rule from {source[:30]}"

                # Determine severity and action
                severity = 7 if pillar_type == "operational" else 4
                action = "flag" if pillar_type == "operational" else "warn"

                # Check if similar rule exists
                existing = session.query(GovernanceRuleModel).filter(
                    GovernanceRuleModel.description == line[:500].strip()
                ).first()

                if not existing:
                    rule = GovernanceRuleModel(
                        name=name,
                        description=line[:500].strip(),
                        pillar_type=pillar_type,
                        severity=severity,
                        enabled=True,
                        action=action,
                        source=source
                    )
                    session.add(rule)
                    extracted_count += 1
                break

    session.commit()
    return extracted_count


@router.get("/documents")
async def list_governance_documents(
    pillar_type: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """List all governance documents, optionally filtered by pillar."""
    query = session.query(GovernanceDocumentModel)
    if pillar_type:
        query = query.filter(GovernanceDocumentModel.pillar_type == pillar_type)

    docs = query.order_by(GovernanceDocumentModel.created_at.desc()).all()
    return {"documents": [d.to_dict() for d in docs]}


# =============================================================================
# RULE MANAGEMENT
# =============================================================================

@router.get("/rules")
async def list_governance_rules(
    pillar_type: Optional[str] = None,
    enabled_only: bool = False,
    session: Session = Depends(get_session)
):
    """List all governance rules."""
    seed_default_rules(session)

    query = session.query(GovernanceRuleModel)
    if pillar_type:
        query = query.filter(GovernanceRuleModel.pillar_type == pillar_type)
    if enabled_only:
        query = query.filter(GovernanceRuleModel.enabled == True)

    rules = query.order_by(GovernanceRuleModel.severity.desc()).all()
    return {"rules": [r.to_dict() for r in rules]}


@router.post("/rules/{rule_id}/toggle")
async def toggle_rule(
    rule_id: int,
    toggle: RuleToggle,
    session: Session = Depends(get_session)
):
    """Enable or disable a rule. Immutable rules cannot be disabled."""
    rule = session.query(GovernanceRuleModel).filter(GovernanceRuleModel.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    if rule.pillar_type == "immutable":
        raise HTTPException(status_code=403, detail="Immutable rules cannot be disabled")

    rule.enabled = toggle.enabled
    session.commit()

    return {"success": True, "rule_id": rule_id, "enabled": toggle.enabled}


@router.put("/rules/{rule_id}")
async def update_rule(
    rule_id: int,
    rule_update: GovernanceRuleUpdate,
    session: Session = Depends(get_session)
):
    """Update a governance rule. Immutable rules cannot be modified."""
    rule = session.query(GovernanceRuleModel).filter(GovernanceRuleModel.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    if rule.pillar_type == "immutable":
        raise HTTPException(status_code=403, detail="Immutable rules cannot be modified")

    # Update fields if provided
    if rule_update.name is not None:
        rule.name = rule_update.name
    if rule_update.description is not None:
        rule.description = rule_update.description
    if rule_update.severity is not None:
        rule.severity = rule_update.severity
    if rule_update.enabled is not None:
        rule.enabled = rule_update.enabled
    if rule_update.pattern is not None:
        rule.pattern = rule_update.pattern
    if rule_update.action is not None:
        rule.action = rule_update.action

    session.commit()
    return {"success": True, "rule": rule.to_dict()}


@router.post("/rules/new")
async def create_rule(
    rule: GovernanceRuleCreate,
    session: Session = Depends(get_session)
):
    """Create a new governance rule. Cannot create immutable rules via API."""
    if rule.pillar_type == "immutable":
        raise HTTPException(
            status_code=403,
            detail="Immutable rules can only be created by system administrators"
        )

    if rule.pillar_type not in ["operational", "behavioral"]:
        raise HTTPException(status_code=400, detail="Invalid pillar type")

    new_rule = GovernanceRuleModel(
        name=rule.name,
        description=rule.description,
        pillar_type=rule.pillar_type,
        severity=rule.severity,
        enabled=rule.enabled,
        pattern=rule.pattern,
        action=rule.action,
        source=rule.source
    )
    session.add(new_rule)
    session.commit()

    return {"success": True, "rule": new_rule.to_dict()}


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: int,
    session: Session = Depends(get_session)
):
    """Delete a governance rule. Immutable rules cannot be deleted."""
    rule = session.query(GovernanceRuleModel).filter(GovernanceRuleModel.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    if rule.pillar_type == "immutable":
        raise HTTPException(status_code=403, detail="Immutable rules cannot be deleted")

    session.delete(rule)
    session.commit()

    return {"success": True, "message": f"Rule {rule_id} deleted"}


# =============================================================================
# HUMAN-IN-THE-LOOP DECISIONS
# =============================================================================

@router.get("/decisions/pending")
async def get_pending_decisions(session: Session = Depends(get_session)):
    """Get all pending decisions requiring human review."""
    decisions = session.query(GovernanceDecisionModel).filter(
        GovernanceDecisionModel.status.in_(["pending", "discussing"])
    ).order_by(GovernanceDecisionModel.severity.desc()).all()

    return {"decisions": [d.to_dict() for d in decisions], "count": len(decisions)}


@router.get("/decisions/history")
async def get_decision_history(
    pillar_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    session: Session = Depends(get_session)
):
    """Get decision history with optional filters."""
    query = session.query(GovernanceDecisionModel).filter(
        GovernanceDecisionModel.status.in_(["confirmed", "denied"])
    )

    if pillar_type:
        query = query.filter(GovernanceDecisionModel.pillar_type == pillar_type)
    if status:
        query = query.filter(GovernanceDecisionModel.status == status)

    decisions = query.order_by(GovernanceDecisionModel.resolved_at.desc()).limit(limit).all()
    return {"decisions": [d.to_dict() for d in decisions], "total": len(decisions)}


@router.post("/decisions/{decision_id}/confirm")
async def confirm_decision(
    decision_id: int,
    action: DecisionAction,
    session: Session = Depends(get_session)
):
    """Confirm/approve a pending decision."""
    decision = session.query(GovernanceDecisionModel).filter(
        GovernanceDecisionModel.id == decision_id
    ).first()

    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    decision.status = "confirmed"
    decision.resolved_at = datetime.now()
    decision.resolved_by = action.reviewed_by
    decision.resolution_note = action.note
    session.commit()

    # If linked to GovernanceEngine, process the approval
    if decision.approval_id:
        try:
            engine = get_governance_engine()
            import asyncio
            asyncio.create_task(engine.process_approval(
                approval_id=decision.approval_id,
                approved=True,
                justification=action.note or "Approved by human reviewer"
            ))
        except Exception as e:
            logger.warning(f"Could not process GovernanceEngine approval: {e}")

    return {"success": True, "decision_id": decision_id, "status": "confirmed"}


@router.post("/decisions/{decision_id}/deny")
async def deny_decision(
    decision_id: int,
    action: DecisionAction,
    session: Session = Depends(get_session)
):
    """Deny/reject a pending decision."""
    decision = session.query(GovernanceDecisionModel).filter(
        GovernanceDecisionModel.id == decision_id
    ).first()

    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    decision.status = "denied"
    decision.resolved_at = datetime.now()
    decision.resolved_by = action.reviewed_by
    decision.resolution_note = action.note
    session.commit()

    # If linked to GovernanceEngine, process the denial
    if decision.approval_id:
        try:
            engine = get_governance_engine()
            import asyncio
            asyncio.create_task(engine.process_approval(
                approval_id=decision.approval_id,
                approved=False,
                justification=action.note or "Denied by human reviewer"
            ))
        except Exception as e:
            logger.warning(f"Could not process GovernanceEngine denial: {e}")

    return {"success": True, "decision_id": decision_id, "status": "denied"}


@router.post("/decisions/{decision_id}/discuss")
async def discuss_decision(
    decision_id: int,
    action: DecisionAction,
    session: Session = Depends(get_session)
):
    """Flag a decision for discussion."""
    decision = session.query(GovernanceDecisionModel).filter(
        GovernanceDecisionModel.id == decision_id
    ).first()

    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    decision.status = "discussing"

    # Add to discussion thread
    discussion = decision.discussion or []
    discussion.append({
        "from": "user",
        "content": action.note,
        "timestamp": datetime.now().isoformat()
    })
    decision.discussion = discussion
    session.commit()

    return {
        "success": True,
        "decision_id": decision_id,
        "status": "discussing",
        "discussion": decision.discussion
    }


@router.post("/decisions/create")
async def create_decision(
    title: str,
    description: str,
    pillar_type: str,
    severity: int = 5,
    context: Optional[Dict] = None,
    rule_reference: Optional[str] = None,
    action_type: Optional[str] = None,
    target_resource: Optional[str] = None,
    approval_id: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """
    Create a new decision for human review.
    Called by Grace/GovernanceEngine when encountering governance-sensitive scenarios.
    """
    decision = GovernanceDecisionModel(
        title=title,
        description=description,
        pillar_type=pillar_type,
        severity=severity,
        status="pending",
        context=context or {},
        rule_reference=rule_reference,
        action_type=action_type,
        target_resource=target_resource,
        approval_id=approval_id
    )
    session.add(decision)
    session.commit()

    return {"success": True, "decision": decision.to_dict()}


# =============================================================================
# GOVERNANCE CHECK & ENFORCEMENT
# =============================================================================

@router.post("/check")
async def check_governance(
    request: GovernanceCheckRequest,
    session: Session = Depends(get_session)
):
    """
    Check if an action/content complies with governance rules.
    Returns whether the action is allowed, blocked, or needs review.
    Uses both database rules and GovernanceEngine constitutional rules.
    """
    violations = []
    requires_review = False

    # 1. Check against database rules
    rules = session.query(GovernanceRuleModel).filter(
        GovernanceRuleModel.enabled == True
    ).all()

    for rule in rules:
        if rule.pattern:
            try:
                if re.search(rule.pattern, request.content, re.IGNORECASE):
                    violation = {
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "pillar": rule.pillar_type,
                        "severity": rule.severity,
                        "action": rule.action
                    }
                    violations.append(violation)

                    if rule.action == "block":
                        return {
                            "allowed": False,
                            "blocked": True,
                            "reason": f"Blocked by {rule.pillar_type} rule: {rule.name}",
                            "violations": violations
                        }
                    elif rule.action == "flag":
                        requires_review = True
            except re.error as e:
                logger.warning(f"Invalid regex pattern in rule {rule.id}: {e}")

    # 2. Check GovernanceEngine constitutional rules
    try:
        engine = get_governance_engine()
        from security.governance import GovernanceContext

        context = GovernanceContext(
            action_type=request.action_type,
            target_resource=request.context.get("target_resource") if request.context else None,
            impact_scope=request.context.get("impact_scope", "local") if request.context else "local",
            reversible=request.context.get("reversible", True) if request.context else True,
            financial_impact=request.context.get("financial_impact", 0.0) if request.context else 0.0,
            metadata=request.context or {}
        )

        constitutional_violations = engine.check_constitutional_rules(context)
        for rule_name, violation in constitutional_violations.items():
            violations.append({
                "rule_id": f"constitutional_{rule_name}",
                "rule_name": f"Constitutional: {rule_name}",
                "pillar": "immutable",
                "severity": 10,
                "action": "block",
                "details": violation
            })

        if constitutional_violations:
            return {
                "allowed": False,
                "blocked": True,
                "reason": f"Blocked by constitutional rules: {list(constitutional_violations.keys())}",
                "violations": violations
            }
    except Exception as e:
        logger.warning(f"Could not check GovernanceEngine: {e}")

    # 3. Return result
    if violations and requires_review:
        # Create a decision for human review
        decision = GovernanceDecisionModel(
            title=f"Review Required: {request.action_type}",
            description=f"Action flagged for review: {request.content[:200]}...",
            pillar_type="operational",
            severity=max(v["severity"] for v in violations),
            status="pending",
            context=request.context,
            action_type=request.action_type
        )
        session.add(decision)
        session.commit()

        return {
            "allowed": False,
            "requires_review": True,
            "decision_id": decision.id,
            "violations": violations,
            "message": "This action requires human review before proceeding"
        }

    if violations:
        return {
            "allowed": True,
            "warnings": violations,
            "message": "Action allowed with warnings"
        }

    return {
        "allowed": True,
        "violations": [],
        "message": "Action complies with all governance rules"
    }


@router.get("/kpi-status")
async def get_kpi_governance_status():
    """
    Get current KPI-driven governance status.
    Integrates with existing governance engine.
    """
    try:
        engine = get_governance_engine()
        health = engine.get_kpi_health()

        return {
            "trust_score": health.get("trust_score", {}).get("value", 0.5),
            "success_rate": health.get("success_rate", {}).get("value", 0.95),
            "confidence_score": health.get("confidence_score", {}).get("value", 0.85),
            "overall_status": "healthy" if all(
                kpi.get("status") != "critical" for kpi in health.values()
            ) else "degraded",
            "kpi_details": health
        }
    except Exception as e:
        logger.warning(f"Could not get KPI status: {e}")
        return {
            "trust_score": 0.5,
            "success_rate": 0.95,
            "confidence_score": 0.85,
            "overall_status": "unknown",
            "error": str(e)
        }


@router.get("/constitutional-rules")
async def get_constitutional_rules():
    """Get the immutable constitutional rules from GovernanceEngine."""
    rules = []
    for rule, meta in CONSTITUTIONAL_RULES.items():
        rules.append({
            "name": rule.value,
            "description": meta.description,
            "severity": meta.severity,
            "enforcement_mode": meta.enforcement_mode,
            "required": meta.required
        })
    return {"rules": rules}


@router.get("/autonomy-tiers")
async def get_autonomy_tiers():
    """Get the autonomy tier configuration from GovernanceEngine."""
    tiers = []
    for tier, config in AUTONOMY_TIERS.items():
        tiers.append({
            "tier": tier.value,
            "description": config.description,
            "requires_approval": config.requires_approval,
            "requires_notification": config.requires_notification,
            "max_impact_scope": config.max_impact_scope,
            "max_financial_impact": config.max_financial_impact,
            "reversibility_required": config.reversibility_required
        })
    return {"tiers": tiers}
