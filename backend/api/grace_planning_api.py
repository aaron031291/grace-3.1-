"""
Grace Planning API

Full planning workflow system that flows from high-level concepts
through technical decisions to IDE execution.

Planning Flow:
1. CONCEPT - Big overarching concepts, product, feature
2. QUESTIONS - Non-technical questions about how concepts work
3. TECHNICAL_STACK - Technical discussion about implementation
4. TECHNICAL_ACCEPTANCE - Accept and apply technical decisions
5. EXECUTE - Execute the plan
6. IDE_HANDOFF - Hand off to IDE for implementation

Author: Grace Autonomous System
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid
import asyncio
import json

router = APIRouter(prefix="/api/grace-planning", tags=["Grace Planning"])


# ============================================================================
# ENUMS
# ============================================================================

class PlanningPhase(str, Enum):
    CONCEPT = "concept"
    QUESTIONS = "questions"
    TECHNICAL_STACK = "technical_stack"
    TECHNICAL_ACCEPTANCE = "technical_acceptance"
    EXECUTE = "execute"
    IDE_HANDOFF = "ide_handoff"
    COMPLETED = "completed"


class ConceptStatus(str, Enum):
    DRAFT = "draft"
    IN_DISCUSSION = "in_discussion"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class QuestionType(str, Enum):
    CLARIFICATION = "clarification"
    SCOPE = "scope"
    FUNCTIONALITY = "functionality"
    USER_EXPERIENCE = "user_experience"
    INTEGRATION = "integration"
    CONSTRAINTS = "constraints"


class TechnicalDecisionStatus(str, Enum):
    PROPOSED = "proposed"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class ExecutionStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================================
# MODELS
# ============================================================================

class PlanningConcept(BaseModel):
    """High-level concept/feature/product idea"""
    id: str = Field(default_factory=lambda: f"GPC-{uuid.uuid4().hex[:8]}")
    genesis_id: str = Field(default="")  # Who created this concept
    title: str
    description: str
    vision: str = Field(default="")  # Long-term vision
    goals: List[str] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)
    status: ConceptStatus = Field(default=ConceptStatus.DRAFT)
    phase: PlanningPhase = Field(default=PlanningPhase.CONCEPT)

    # Relationships
    parent_concept_id: Optional[str] = None
    child_concepts: List[str] = Field(default_factory=list)
    related_concepts: List[str] = Field(default_factory=list)

    # Metadata
    tags: List[str] = Field(default_factory=list)
    priority: int = Field(default=5, ge=1, le=10)
    estimated_complexity: str = Field(default="medium")  # low, medium, high, very_high
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Grace integration
    grace_analysis: Optional[Dict[str, Any]] = None
    grace_recommendations: List[str] = Field(default_factory=list)


class ConceptQuestion(BaseModel):
    """Non-technical question about a concept"""
    id: str = Field(default_factory=lambda: f"GPQ-{uuid.uuid4().hex[:8]}")
    concept_id: str
    genesis_id: str = Field(default="")
    question: str
    question_type: QuestionType = Field(default=QuestionType.CLARIFICATION)
    context: str = Field(default="")

    # Answers and discussion
    answers: List[Dict[str, Any]] = Field(default_factory=list)  # {author, content, timestamp}
    accepted_answer: Optional[str] = None
    is_resolved: bool = Field(default=False)

    # Follow-ups
    follow_up_questions: List[str] = Field(default_factory=list)
    leads_to_concepts: List[str] = Field(default_factory=list)

    # Grace analysis
    grace_suggested_answer: Optional[str] = None
    grace_confidence: float = Field(default=0.0, ge=0, le=1)

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class TechnicalStackItem(BaseModel):
    """Technical stack component"""
    id: str = Field(default_factory=lambda: f"GTS-{uuid.uuid4().hex[:8]}")
    concept_id: str
    category: str  # frontend, backend, database, infrastructure, etc.
    name: str
    version: Optional[str] = None
    purpose: str
    alternatives_considered: List[Dict[str, str]] = Field(default_factory=list)
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)
    decision_rationale: str = Field(default="")
    status: TechnicalDecisionStatus = Field(default=TechnicalDecisionStatus.PROPOSED)

    # Dependencies
    depends_on: List[str] = Field(default_factory=list)
    required_by: List[str] = Field(default_factory=list)

    # Grace recommendations
    grace_recommendation: Optional[str] = None
    grace_alternatives: List[Dict[str, Any]] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=datetime.now)
    decided_at: Optional[datetime] = None


class TechnicalDecision(BaseModel):
    """Technical decision record"""
    id: str = Field(default_factory=lambda: f"GTD-{uuid.uuid4().hex[:8]}")
    concept_id: str
    title: str
    description: str
    decision_type: str  # architecture, technology, pattern, convention

    # Decision details
    options: List[Dict[str, Any]] = Field(default_factory=list)  # {name, description, pros, cons}
    selected_option: Optional[str] = None
    rationale: str = Field(default="")
    trade_offs: List[str] = Field(default_factory=list)

    # Status
    status: TechnicalDecisionStatus = Field(default=TechnicalDecisionStatus.PROPOSED)
    reviewers: List[str] = Field(default_factory=list)
    approvers: List[str] = Field(default_factory=list)

    # Impact analysis
    affected_components: List[str] = Field(default_factory=list)
    estimated_effort: str = Field(default="")
    risk_level: str = Field(default="medium")

    # Grace input
    grace_analysis: Optional[Dict[str, Any]] = None
    grace_recommendation: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.now)
    decided_at: Optional[datetime] = None


class ExecutionPlan(BaseModel):
    """Execution plan for a concept"""
    id: str = Field(default_factory=lambda: f"GPE-{uuid.uuid4().hex[:8]}")
    concept_id: str
    title: str
    description: str

    # Phases and milestones
    phases: List[Dict[str, Any]] = Field(default_factory=list)
    milestones: List[Dict[str, Any]] = Field(default_factory=list)

    # Tasks generated
    tasks: List[Dict[str, Any]] = Field(default_factory=list)  # Links to Grace Todos
    task_dependencies: Dict[str, List[str]] = Field(default_factory=dict)

    # Status
    status: ExecutionStatus = Field(default=ExecutionStatus.NOT_STARTED)
    progress: float = Field(default=0.0, ge=0, le=100)
    current_phase: Optional[str] = None

    # Resources
    assigned_team: List[str] = Field(default_factory=list)
    assigned_agents: List[str] = Field(default_factory=list)

    # Timeline (no time estimates, just sequence)
    execution_order: List[str] = Field(default_factory=list)
    blockers: List[Dict[str, Any]] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class IDEHandoff(BaseModel):
    """Handoff record to IDE for implementation"""
    id: str = Field(default_factory=lambda: f"GPH-{uuid.uuid4().hex[:8]}")
    concept_id: str
    execution_plan_id: str

    # IDE target
    target_ide: str = Field(default="vscode")  # vscode, cursor, etc.
    target_workspace: Optional[str] = None

    # Implementation details
    files_to_create: List[Dict[str, str]] = Field(default_factory=list)
    files_to_modify: List[Dict[str, str]] = Field(default_factory=list)
    implementation_notes: str = Field(default="")

    # Code snippets/templates
    code_templates: List[Dict[str, Any]] = Field(default_factory=list)

    # Status
    handoff_status: str = Field(default="pending")  # pending, sent, acknowledged, in_progress, completed
    ide_session_id: Optional[str] = None

    # Grace integration
    grace_instructions: str = Field(default="")
    autonomous_execution: bool = Field(default=False)

    created_at: datetime = Field(default_factory=datetime.now)
    handed_off_at: Optional[datetime] = None


class PlanningSession(BaseModel):
    """Full planning session containing all elements"""
    id: str = Field(default_factory=lambda: f"GPS-{uuid.uuid4().hex[:8]}")
    genesis_id: str
    title: str
    description: str = Field(default="")

    # Current state
    current_phase: PlanningPhase = Field(default=PlanningPhase.CONCEPT)

    # Components
    concepts: List[str] = Field(default_factory=list)  # concept IDs
    questions: List[str] = Field(default_factory=list)  # question IDs
    tech_stack_items: List[str] = Field(default_factory=list)
    technical_decisions: List[str] = Field(default_factory=list)
    execution_plans: List[str] = Field(default_factory=list)
    ide_handoffs: List[str] = Field(default_factory=list)

    # Progress tracking
    phase_completion: Dict[str, float] = Field(default_factory=lambda: {
        PlanningPhase.CONCEPT: 0,
        PlanningPhase.QUESTIONS: 0,
        PlanningPhase.TECHNICAL_STACK: 0,
        PlanningPhase.TECHNICAL_ACCEPTANCE: 0,
        PlanningPhase.EXECUTE: 0,
        PlanningPhase.IDE_HANDOFF: 0,
    })

    # Participants
    participants: List[str] = Field(default_factory=list)

    # Grace involvement
    grace_active: bool = Field(default=True)
    grace_conversation_id: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ============================================================================
# IN-MEMORY STORAGE (Replace with database in production)
# ============================================================================

planning_sessions: Dict[str, PlanningSession] = {}
concepts: Dict[str, PlanningConcept] = {}
questions: Dict[str, ConceptQuestion] = {}
tech_stack: Dict[str, TechnicalStackItem] = {}
tech_decisions: Dict[str, TechnicalDecision] = {}
execution_plans: Dict[str, ExecutionPlan] = {}
ide_handoffs: Dict[str, IDEHandoff] = {}

# WebSocket connections for real-time updates
planning_connections: Dict[str, List[WebSocket]] = {}


# ============================================================================
# PLANNING SESSION ENDPOINTS
# ============================================================================

@router.post("/sessions", response_model=PlanningSession)
async def create_planning_session(
    genesis_id: str,
    title: str,
    description: str = ""
) -> PlanningSession:
    """Create a new planning session"""
    session = PlanningSession(
        genesis_id=genesis_id,
        title=title,
        description=description,
        participants=[genesis_id]
    )
    planning_sessions[session.id] = session
    return session


@router.get("/sessions", response_model=List[PlanningSession])
async def list_planning_sessions(
    genesis_id: Optional[str] = None,
    phase: Optional[PlanningPhase] = None
) -> List[PlanningSession]:
    """List all planning sessions with optional filters"""
    result = list(planning_sessions.values())

    if genesis_id:
        result = [s for s in result if genesis_id in s.participants]
    if phase:
        result = [s for s in result if s.current_phase == phase]

    return sorted(result, key=lambda x: x.updated_at, reverse=True)


@router.get("/sessions/{session_id}", response_model=PlanningSession)
async def get_planning_session(session_id: str) -> PlanningSession:
    """Get a specific planning session"""
    if session_id not in planning_sessions:
        raise HTTPException(status_code=404, detail="Planning session not found")
    return planning_sessions[session_id]


@router.put("/sessions/{session_id}/phase", response_model=PlanningSession)
async def advance_session_phase(
    session_id: str,
    target_phase: PlanningPhase
) -> PlanningSession:
    """Advance a planning session to the next phase"""
    if session_id not in planning_sessions:
        raise HTTPException(status_code=404, detail="Planning session not found")

    session = planning_sessions[session_id]

    # Validate phase transition
    phase_order = [
        PlanningPhase.CONCEPT,
        PlanningPhase.QUESTIONS,
        PlanningPhase.TECHNICAL_STACK,
        PlanningPhase.TECHNICAL_ACCEPTANCE,
        PlanningPhase.EXECUTE,
        PlanningPhase.IDE_HANDOFF,
        PlanningPhase.COMPLETED
    ]

    current_idx = phase_order.index(session.current_phase)
    target_idx = phase_order.index(target_phase)

    if target_idx < current_idx:
        raise HTTPException(status_code=400, detail="Cannot move to a previous phase")

    session.current_phase = target_phase
    session.updated_at = datetime.now()

    # Notify connected clients
    await broadcast_to_session(session_id, {
        "type": "phase_changed",
        "session_id": session_id,
        "phase": target_phase
    })

    return session


# ============================================================================
# CONCEPT ENDPOINTS (Phase 1)
# ============================================================================

@router.post("/concepts", response_model=PlanningConcept)
async def create_concept(
    session_id: str,
    title: str,
    description: str,
    genesis_id: str,
    vision: str = "",
    goals: List[str] = None,
    success_criteria: List[str] = None,
    parent_concept_id: Optional[str] = None,
    tags: List[str] = None,
    priority: int = 5
) -> PlanningConcept:
    """Create a new planning concept"""
    if session_id not in planning_sessions:
        raise HTTPException(status_code=404, detail="Planning session not found")

    concept = PlanningConcept(
        genesis_id=genesis_id,
        title=title,
        description=description,
        vision=vision,
        goals=goals or [],
        success_criteria=success_criteria or [],
        parent_concept_id=parent_concept_id,
        tags=tags or [],
        priority=priority
    )

    concepts[concept.id] = concept
    planning_sessions[session_id].concepts.append(concept.id)
    planning_sessions[session_id].updated_at = datetime.now()

    # If parent concept, add as child
    if parent_concept_id and parent_concept_id in concepts:
        concepts[parent_concept_id].child_concepts.append(concept.id)

    await broadcast_to_session(session_id, {
        "type": "concept_created",
        "concept": concept.dict()
    })

    return concept


@router.get("/concepts/{concept_id}", response_model=PlanningConcept)
async def get_concept(concept_id: str) -> PlanningConcept:
    """Get a specific concept"""
    if concept_id not in concepts:
        raise HTTPException(status_code=404, detail="Concept not found")
    return concepts[concept_id]


@router.get("/sessions/{session_id}/concepts", response_model=List[PlanningConcept])
async def get_session_concepts(session_id: str) -> List[PlanningConcept]:
    """Get all concepts for a session"""
    if session_id not in planning_sessions:
        raise HTTPException(status_code=404, detail="Planning session not found")

    session = planning_sessions[session_id]
    return [concepts[cid] for cid in session.concepts if cid in concepts]


@router.put("/concepts/{concept_id}/status", response_model=PlanningConcept)
async def update_concept_status(
    concept_id: str,
    status: ConceptStatus
) -> PlanningConcept:
    """Update concept status"""
    if concept_id not in concepts:
        raise HTTPException(status_code=404, detail="Concept not found")

    concept = concepts[concept_id]
    concept.status = status
    concept.updated_at = datetime.now()

    return concept


@router.post("/concepts/{concept_id}/grace-analyze", response_model=PlanningConcept)
async def grace_analyze_concept(concept_id: str) -> PlanningConcept:
    """Have Grace analyze and provide recommendations for a concept"""
    if concept_id not in concepts:
        raise HTTPException(status_code=404, detail="Concept not found")

    concept = concepts[concept_id]

    # Grace analysis simulation (integrate with actual Grace systems)
    concept.grace_analysis = {
        "feasibility_score": 0.85,
        "complexity_assessment": concept.estimated_complexity,
        "recommended_approach": "phased_implementation",
        "potential_risks": [
            "Integration complexity",
            "Scope creep possibility"
        ],
        "success_factors": [
            "Clear requirements",
            "Modular architecture",
            "Incremental delivery"
        ],
        "analyzed_at": datetime.now().isoformat()
    }

    concept.grace_recommendations = [
        "Break down into smaller sub-concepts for better tracking",
        "Define clear acceptance criteria before technical discussion",
        "Consider parallel workstreams for independent components",
        "Establish feedback loops for early validation"
    ]

    concept.updated_at = datetime.now()

    return concept


# ============================================================================
# QUESTIONS ENDPOINTS (Phase 2)
# ============================================================================

@router.post("/questions", response_model=ConceptQuestion)
async def create_question(
    session_id: str,
    concept_id: str,
    question: str,
    genesis_id: str,
    question_type: QuestionType = QuestionType.CLARIFICATION,
    context: str = ""
) -> ConceptQuestion:
    """Create a non-technical question about a concept"""
    if concept_id not in concepts:
        raise HTTPException(status_code=404, detail="Concept not found")

    q = ConceptQuestion(
        concept_id=concept_id,
        genesis_id=genesis_id,
        question=question,
        question_type=question_type,
        context=context
    )

    questions[q.id] = q
    planning_sessions[session_id].questions.append(q.id)

    # Have Grace suggest an answer
    q.grace_suggested_answer = await grace_suggest_answer(q)
    q.grace_confidence = 0.75

    await broadcast_to_session(session_id, {
        "type": "question_created",
        "question": q.dict()
    })

    return q


async def grace_suggest_answer(question: ConceptQuestion) -> str:
    """Grace suggests an answer to a question"""
    # Integrate with actual Grace AI system
    concept = concepts.get(question.concept_id)
    if not concept:
        return "Unable to analyze without concept context"

    return f"Based on the concept '{concept.title}', I suggest considering: " \
           f"The question about '{question.question[:50]}...' relates to the core vision. " \
           f"Key considerations include the success criteria and goals defined."


@router.get("/questions/{question_id}", response_model=ConceptQuestion)
async def get_question(question_id: str) -> ConceptQuestion:
    """Get a specific question"""
    if question_id not in questions:
        raise HTTPException(status_code=404, detail="Question not found")
    return questions[question_id]


@router.get("/concepts/{concept_id}/questions", response_model=List[ConceptQuestion])
async def get_concept_questions(concept_id: str) -> List[ConceptQuestion]:
    """Get all questions for a concept"""
    return [q for q in questions.values() if q.concept_id == concept_id]


@router.post("/questions/{question_id}/answer", response_model=ConceptQuestion)
async def answer_question(
    question_id: str,
    author: str,
    content: str,
    is_accepted: bool = False
) -> ConceptQuestion:
    """Add an answer to a question"""
    if question_id not in questions:
        raise HTTPException(status_code=404, detail="Question not found")

    q = questions[question_id]
    answer = {
        "id": f"GPA-{uuid.uuid4().hex[:8]}",
        "author": author,
        "content": content,
        "timestamp": datetime.now().isoformat()
    }
    q.answers.append(answer)

    if is_accepted:
        q.accepted_answer = answer["id"]
        q.is_resolved = True

    q.updated_at = datetime.now()

    return q


@router.post("/questions/{question_id}/resolve", response_model=ConceptQuestion)
async def resolve_question(
    question_id: str,
    accepted_answer_id: Optional[str] = None
) -> ConceptQuestion:
    """Mark a question as resolved"""
    if question_id not in questions:
        raise HTTPException(status_code=404, detail="Question not found")

    q = questions[question_id]
    q.is_resolved = True
    if accepted_answer_id:
        q.accepted_answer = accepted_answer_id
    q.updated_at = datetime.now()

    return q


# ============================================================================
# TECHNICAL STACK ENDPOINTS (Phase 3)
# ============================================================================

@router.post("/tech-stack", response_model=TechnicalStackItem)
async def add_tech_stack_item(
    session_id: str,
    concept_id: str,
    category: str,
    name: str,
    purpose: str,
    version: Optional[str] = None,
    alternatives_considered: List[Dict[str, str]] = None,
    pros: List[str] = None,
    cons: List[str] = None
) -> TechnicalStackItem:
    """Add a technical stack item"""
    if concept_id not in concepts:
        raise HTTPException(status_code=404, detail="Concept not found")

    item = TechnicalStackItem(
        concept_id=concept_id,
        category=category,
        name=name,
        purpose=purpose,
        version=version,
        alternatives_considered=alternatives_considered or [],
        pros=pros or [],
        cons=cons or []
    )

    # Grace recommendation
    item.grace_recommendation = await grace_tech_recommendation(item)

    tech_stack[item.id] = item
    planning_sessions[session_id].tech_stack_items.append(item.id)

    await broadcast_to_session(session_id, {
        "type": "tech_stack_added",
        "item": item.dict()
    })

    return item


async def grace_tech_recommendation(item: TechnicalStackItem) -> str:
    """Grace provides recommendation on tech stack choice"""
    return f"{item.name} is a solid choice for {item.purpose}. " \
           f"Consider compatibility with existing stack and team expertise."


@router.get("/sessions/{session_id}/tech-stack", response_model=List[TechnicalStackItem])
async def get_session_tech_stack(session_id: str) -> List[TechnicalStackItem]:
    """Get all tech stack items for a session"""
    if session_id not in planning_sessions:
        raise HTTPException(status_code=404, detail="Planning session not found")

    session = planning_sessions[session_id]
    return [tech_stack[tid] for tid in session.tech_stack_items if tid in tech_stack]


@router.put("/tech-stack/{item_id}/status", response_model=TechnicalStackItem)
async def update_tech_stack_status(
    item_id: str,
    status: TechnicalDecisionStatus,
    decision_rationale: str = ""
) -> TechnicalStackItem:
    """Update tech stack item status"""
    if item_id not in tech_stack:
        raise HTTPException(status_code=404, detail="Tech stack item not found")

    item = tech_stack[item_id]
    item.status = status
    if decision_rationale:
        item.decision_rationale = decision_rationale
    if status == TechnicalDecisionStatus.ACCEPTED:
        item.decided_at = datetime.now()

    return item


# ============================================================================
# TECHNICAL DECISIONS ENDPOINTS (Phase 4)
# ============================================================================

@router.post("/decisions", response_model=TechnicalDecision)
async def create_technical_decision(
    session_id: str,
    concept_id: str,
    title: str,
    description: str,
    decision_type: str,
    options: List[Dict[str, Any]] = None
) -> TechnicalDecision:
    """Create a technical decision record"""
    if concept_id not in concepts:
        raise HTTPException(status_code=404, detail="Concept not found")

    decision = TechnicalDecision(
        concept_id=concept_id,
        title=title,
        description=description,
        decision_type=decision_type,
        options=options or []
    )

    # Grace analysis
    decision.grace_analysis = await grace_analyze_decision(decision)

    tech_decisions[decision.id] = decision
    planning_sessions[session_id].technical_decisions.append(decision.id)

    await broadcast_to_session(session_id, {
        "type": "decision_created",
        "decision": decision.dict()
    })

    return decision


async def grace_analyze_decision(decision: TechnicalDecision) -> Dict[str, Any]:
    """Grace analyzes technical decision options"""
    analysis = {
        "analyzed_at": datetime.now().isoformat(),
        "options_analysis": []
    }

    for opt in decision.options:
        analysis["options_analysis"].append({
            "option": opt.get("name", "Unknown"),
            "score": 0.75,  # Would calculate based on actual analysis
            "recommendation": "Consider" if len(decision.options) > 1 else "Proceed"
        })

    if decision.options:
        analysis["grace_recommendation"] = decision.options[0].get("name", "First option")
        analysis["recommendation_reason"] = "Based on project requirements and technical compatibility"

    return analysis


@router.get("/sessions/{session_id}/decisions", response_model=List[TechnicalDecision])
async def get_session_decisions(session_id: str) -> List[TechnicalDecision]:
    """Get all technical decisions for a session"""
    if session_id not in planning_sessions:
        raise HTTPException(status_code=404, detail="Planning session not found")

    session = planning_sessions[session_id]
    return [tech_decisions[did] for did in session.technical_decisions if did in tech_decisions]


@router.put("/decisions/{decision_id}/select", response_model=TechnicalDecision)
async def select_decision_option(
    decision_id: str,
    selected_option: str,
    rationale: str,
    approvers: List[str] = None
) -> TechnicalDecision:
    """Select an option for a technical decision"""
    if decision_id not in tech_decisions:
        raise HTTPException(status_code=404, detail="Decision not found")

    decision = tech_decisions[decision_id]
    decision.selected_option = selected_option
    decision.rationale = rationale
    decision.status = TechnicalDecisionStatus.ACCEPTED
    decision.approvers = approvers or []
    decision.decided_at = datetime.now()

    return decision


# ============================================================================
# EXECUTION PLAN ENDPOINTS (Phase 5)
# ============================================================================

@router.post("/execution-plans", response_model=ExecutionPlan)
async def create_execution_plan(
    session_id: str,
    concept_id: str,
    title: str,
    description: str,
    phases: List[Dict[str, Any]] = None,
    milestones: List[Dict[str, Any]] = None
) -> ExecutionPlan:
    """Create an execution plan"""
    if concept_id not in concepts:
        raise HTTPException(status_code=404, detail="Concept not found")

    plan = ExecutionPlan(
        concept_id=concept_id,
        title=title,
        description=description,
        phases=phases or [],
        milestones=milestones or []
    )

    execution_plans[plan.id] = plan
    planning_sessions[session_id].execution_plans.append(plan.id)

    await broadcast_to_session(session_id, {
        "type": "execution_plan_created",
        "plan": plan.dict()
    })

    return plan


@router.post("/execution-plans/{plan_id}/generate-tasks", response_model=ExecutionPlan)
async def generate_tasks_from_plan(
    plan_id: str,
    background_tasks: BackgroundTasks
) -> ExecutionPlan:
    """Generate Grace Todo tasks from execution plan"""
    if plan_id not in execution_plans:
        raise HTTPException(status_code=404, detail="Execution plan not found")

    plan = execution_plans[plan_id]

    # Generate tasks based on phases and milestones
    generated_tasks = []

    for i, phase in enumerate(plan.phases):
        task = {
            "id": f"GT-{uuid.uuid4().hex[:8]}",
            "title": phase.get("name", f"Phase {i+1}"),
            "description": phase.get("description", ""),
            "phase": i + 1,
            "type": "phase_task",
            "status": "queued",
            "generated_from": plan_id
        }
        generated_tasks.append(task)

    for milestone in plan.milestones:
        task = {
            "id": f"GT-{uuid.uuid4().hex[:8]}",
            "title": f"Milestone: {milestone.get('name', 'Unnamed')}",
            "description": milestone.get("criteria", ""),
            "type": "milestone_task",
            "status": "queued",
            "generated_from": plan_id
        }
        generated_tasks.append(task)

    plan.tasks = generated_tasks
    plan.execution_order = [t["id"] for t in generated_tasks]

    return plan


@router.get("/sessions/{session_id}/execution-plans", response_model=List[ExecutionPlan])
async def get_session_execution_plans(session_id: str) -> List[ExecutionPlan]:
    """Get all execution plans for a session"""
    if session_id not in planning_sessions:
        raise HTTPException(status_code=404, detail="Planning session not found")

    session = planning_sessions[session_id]
    return [execution_plans[eid] for eid in session.execution_plans if eid in execution_plans]


@router.put("/execution-plans/{plan_id}/start", response_model=ExecutionPlan)
async def start_execution(plan_id: str) -> ExecutionPlan:
    """Start executing a plan"""
    if plan_id not in execution_plans:
        raise HTTPException(status_code=404, detail="Execution plan not found")

    plan = execution_plans[plan_id]
    plan.status = ExecutionStatus.IN_PROGRESS
    plan.started_at = datetime.now()

    if plan.phases:
        plan.current_phase = plan.phases[0].get("name", "Phase 1")

    return plan


@router.put("/execution-plans/{plan_id}/progress", response_model=ExecutionPlan)
async def update_execution_progress(
    plan_id: str,
    progress: float,
    current_phase: Optional[str] = None
) -> ExecutionPlan:
    """Update execution progress"""
    if plan_id not in execution_plans:
        raise HTTPException(status_code=404, detail="Execution plan not found")

    plan = execution_plans[plan_id]
    plan.progress = min(100, max(0, progress))

    if current_phase:
        plan.current_phase = current_phase

    if progress >= 100:
        plan.status = ExecutionStatus.COMPLETED
        plan.completed_at = datetime.now()

    return plan


# ============================================================================
# IDE HANDOFF ENDPOINTS (Phase 6)
# ============================================================================

@router.post("/ide-handoffs", response_model=IDEHandoff)
async def create_ide_handoff(
    session_id: str,
    concept_id: str,
    execution_plan_id: str,
    target_ide: str = "vscode",
    target_workspace: Optional[str] = None,
    files_to_create: List[Dict[str, str]] = None,
    files_to_modify: List[Dict[str, str]] = None,
    implementation_notes: str = "",
    autonomous_execution: bool = False
) -> IDEHandoff:
    """Create an IDE handoff for implementation"""
    handoff = IDEHandoff(
        concept_id=concept_id,
        execution_plan_id=execution_plan_id,
        target_ide=target_ide,
        target_workspace=target_workspace,
        files_to_create=files_to_create or [],
        files_to_modify=files_to_modify or [],
        implementation_notes=implementation_notes,
        autonomous_execution=autonomous_execution
    )

    # Generate Grace instructions for IDE
    concept = concepts.get(concept_id)
    plan = execution_plans.get(execution_plan_id)

    handoff.grace_instructions = generate_grace_ide_instructions(concept, plan, handoff)

    ide_handoffs[handoff.id] = handoff
    planning_sessions[session_id].ide_handoffs.append(handoff.id)

    await broadcast_to_session(session_id, {
        "type": "ide_handoff_created",
        "handoff": handoff.dict()
    })

    return handoff


def generate_grace_ide_instructions(
    concept: Optional[PlanningConcept],
    plan: Optional[ExecutionPlan],
    handoff: IDEHandoff
) -> str:
    """Generate instructions for Grace IDE integration"""
    instructions = []

    if concept:
        instructions.append(f"## Concept: {concept.title}")
        instructions.append(f"Vision: {concept.vision}")
        instructions.append(f"Goals: {', '.join(concept.goals)}")

    if plan:
        instructions.append(f"\n## Execution Plan: {plan.title}")
        for i, phase in enumerate(plan.phases):
            instructions.append(f"Phase {i+1}: {phase.get('name', 'Unnamed')}")

    instructions.append(f"\n## Implementation")
    instructions.append(f"Target IDE: {handoff.target_ide}")

    if handoff.files_to_create:
        instructions.append("Files to Create:")
        for f in handoff.files_to_create:
            instructions.append(f"  - {f.get('path', 'Unknown')}: {f.get('description', '')}")

    if handoff.files_to_modify:
        instructions.append("Files to Modify:")
        for f in handoff.files_to_modify:
            instructions.append(f"  - {f.get('path', 'Unknown')}: {f.get('changes', '')}")

    if handoff.implementation_notes:
        instructions.append(f"\nNotes: {handoff.implementation_notes}")

    return "\n".join(instructions)


@router.post("/ide-handoffs/{handoff_id}/send", response_model=IDEHandoff)
async def send_to_ide(handoff_id: str) -> IDEHandoff:
    """Send handoff to IDE for implementation"""
    if handoff_id not in ide_handoffs:
        raise HTTPException(status_code=404, detail="Handoff not found")

    handoff = ide_handoffs[handoff_id]
    handoff.handoff_status = "sent"
    handoff.handed_off_at = datetime.now()

    # In production, this would trigger the IDE integration
    # For now, we'll create a session ID
    handoff.ide_session_id = f"IDE-{uuid.uuid4().hex[:8]}"

    return handoff


@router.put("/ide-handoffs/{handoff_id}/status", response_model=IDEHandoff)
async def update_handoff_status(
    handoff_id: str,
    status: str,
    ide_session_id: Optional[str] = None
) -> IDEHandoff:
    """Update IDE handoff status"""
    if handoff_id not in ide_handoffs:
        raise HTTPException(status_code=404, detail="Handoff not found")

    handoff = ide_handoffs[handoff_id]
    handoff.handoff_status = status

    if ide_session_id:
        handoff.ide_session_id = ide_session_id

    return handoff


# ============================================================================
# GRACE INTEGRATION ENDPOINTS
# ============================================================================

@router.post("/sessions/{session_id}/grace/analyze-all")
async def grace_full_session_analysis(session_id: str) -> Dict[str, Any]:
    """Have Grace analyze the entire planning session"""
    if session_id not in planning_sessions:
        raise HTTPException(status_code=404, detail="Planning session not found")

    session = planning_sessions[session_id]

    analysis = {
        "session_id": session_id,
        "analyzed_at": datetime.now().isoformat(),
        "phase_analysis": {},
        "recommendations": [],
        "risks": [],
        "next_steps": []
    }

    # Analyze concepts
    session_concepts = [concepts[cid] for cid in session.concepts if cid in concepts]
    analysis["phase_analysis"]["concepts"] = {
        "total": len(session_concepts),
        "approved": len([c for c in session_concepts if c.status == ConceptStatus.APPROVED]),
        "draft": len([c for c in session_concepts if c.status == ConceptStatus.DRAFT]),
        "health": "good" if len([c for c in session_concepts if c.status == ConceptStatus.APPROVED]) > 0 else "needs_attention"
    }

    # Analyze questions
    session_questions = [questions[qid] for qid in session.questions if qid in questions]
    unresolved = [q for q in session_questions if not q.is_resolved]
    analysis["phase_analysis"]["questions"] = {
        "total": len(session_questions),
        "resolved": len([q for q in session_questions if q.is_resolved]),
        "unresolved": len(unresolved),
        "health": "good" if len(unresolved) == 0 else "needs_attention"
    }

    # Recommendations
    if analysis["phase_analysis"]["questions"]["unresolved"] > 0:
        analysis["recommendations"].append(
            f"Resolve {len(unresolved)} pending questions before advancing to technical phase"
        )

    # Analyze tech decisions
    session_decisions = [tech_decisions[did] for did in session.technical_decisions if did in tech_decisions]
    pending_decisions = [d for d in session_decisions if d.status == TechnicalDecisionStatus.PROPOSED]
    analysis["phase_analysis"]["technical"] = {
        "stack_items": len([tech_stack[tid] for tid in session.tech_stack_items if tid in tech_stack]),
        "decisions": len(session_decisions),
        "pending_decisions": len(pending_decisions),
        "health": "good" if len(pending_decisions) == 0 else "needs_attention"
    }

    # Next steps based on current phase
    if session.current_phase == PlanningPhase.CONCEPT:
        analysis["next_steps"] = [
            "Finalize and approve core concepts",
            "Identify key questions about concept implementation",
            "Move to Questions phase when concepts are approved"
        ]
    elif session.current_phase == PlanningPhase.QUESTIONS:
        analysis["next_steps"] = [
            "Answer all outstanding questions",
            "Ensure stakeholder alignment",
            "Move to Technical Stack phase when questions resolved"
        ]
    elif session.current_phase == PlanningPhase.TECHNICAL_STACK:
        analysis["next_steps"] = [
            "Define technology choices",
            "Document rationale for selections",
            "Move to Technical Acceptance phase"
        ]

    return analysis


@router.post("/sessions/{session_id}/grace/suggest-questions")
async def grace_suggest_questions(
    session_id: str,
    concept_id: str
) -> List[Dict[str, Any]]:
    """Grace suggests questions to ask about a concept"""
    if concept_id not in concepts:
        raise HTTPException(status_code=404, detail="Concept not found")

    concept = concepts[concept_id]

    # Generate contextual questions based on concept
    suggested_questions = [
        {
            "question": f"What are the key user personas for {concept.title}?",
            "type": QuestionType.USER_EXPERIENCE,
            "priority": "high"
        },
        {
            "question": f"What existing systems need to integrate with {concept.title}?",
            "type": QuestionType.INTEGRATION,
            "priority": "high"
        },
        {
            "question": f"What are the must-have vs nice-to-have features for {concept.title}?",
            "type": QuestionType.SCOPE,
            "priority": "high"
        },
        {
            "question": f"What constraints (budget, resources, compliance) affect {concept.title}?",
            "type": QuestionType.CONSTRAINTS,
            "priority": "medium"
        },
        {
            "question": f"How will success be measured for {concept.title}?",
            "type": QuestionType.FUNCTIONALITY,
            "priority": "medium"
        }
    ]

    return suggested_questions


@router.post("/sessions/{session_id}/grace/generate-execution-plan")
async def grace_generate_execution_plan(
    session_id: str,
    concept_id: str
) -> ExecutionPlan:
    """Grace generates an execution plan from approved concept and decisions"""
    if session_id not in planning_sessions:
        raise HTTPException(status_code=404, detail="Planning session not found")
    if concept_id not in concepts:
        raise HTTPException(status_code=404, detail="Concept not found")

    concept = concepts[concept_id]
    session = planning_sessions[session_id]

    # Gather all relevant decisions
    relevant_decisions = [
        tech_decisions[did] for did in session.technical_decisions
        if did in tech_decisions and tech_decisions[did].concept_id == concept_id
    ]

    # Generate phases based on concept and decisions
    phases = [
        {
            "name": "Setup & Infrastructure",
            "description": "Initialize project structure and development environment",
            "order": 1
        },
        {
            "name": "Core Implementation",
            "description": f"Implement core functionality for {concept.title}",
            "order": 2
        },
        {
            "name": "Integration",
            "description": "Integrate with existing systems",
            "order": 3
        },
        {
            "name": "Testing & Validation",
            "description": "Comprehensive testing and validation",
            "order": 4
        },
        {
            "name": "Deployment",
            "description": "Deploy and monitor",
            "order": 5
        }
    ]

    milestones = [
        {
            "name": "MVP Complete",
            "criteria": "Core functionality working end-to-end",
            "phase": 2
        },
        {
            "name": "Integration Complete",
            "criteria": "All systems integrated and communicating",
            "phase": 3
        },
        {
            "name": "Production Ready",
            "criteria": "All tests passing, documentation complete",
            "phase": 4
        }
    ]

    plan = ExecutionPlan(
        concept_id=concept_id,
        title=f"Execution Plan: {concept.title}",
        description=f"Auto-generated execution plan for {concept.title}",
        phases=phases,
        milestones=milestones
    )

    execution_plans[plan.id] = plan
    session.execution_plans.append(plan.id)

    return plan


# ============================================================================
# WEBSOCKET FOR REAL-TIME UPDATES
# ============================================================================

@router.websocket("/ws/{session_id}")
async def planning_websocket(websocket: WebSocket, session_id: str):
    """WebSocket for real-time planning updates"""
    await websocket.accept()

    if session_id not in planning_connections:
        planning_connections[session_id] = []
    planning_connections[session_id].append(websocket)

    try:
        # Send current session state
        if session_id in planning_sessions:
            await websocket.send_json({
                "type": "session_state",
                "session": planning_sessions[session_id].dict()
            })

        while True:
            data = await websocket.receive_json()

            # Handle incoming messages
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        planning_connections[session_id].remove(websocket)


async def broadcast_to_session(session_id: str, message: dict):
    """Broadcast message to all connected clients for a session"""
    if session_id in planning_connections:
        for ws in planning_connections[session_id]:
            try:
                await ws.send_json(message)
            except:
                pass


# ============================================================================
# FULL WORKFLOW ENDPOINTS
# ============================================================================

@router.post("/sessions/{session_id}/complete-phase")
async def complete_current_phase(session_id: str) -> Dict[str, Any]:
    """Complete current phase and advance to next"""
    if session_id not in planning_sessions:
        raise HTTPException(status_code=404, detail="Planning session not found")

    session = planning_sessions[session_id]
    current_phase = session.current_phase

    # Mark current phase as 100%
    session.phase_completion[current_phase] = 100

    # Determine next phase
    phase_order = [
        PlanningPhase.CONCEPT,
        PlanningPhase.QUESTIONS,
        PlanningPhase.TECHNICAL_STACK,
        PlanningPhase.TECHNICAL_ACCEPTANCE,
        PlanningPhase.EXECUTE,
        PlanningPhase.IDE_HANDOFF,
        PlanningPhase.COMPLETED
    ]

    current_idx = phase_order.index(current_phase)
    if current_idx < len(phase_order) - 1:
        next_phase = phase_order[current_idx + 1]
        session.current_phase = next_phase
        session.updated_at = datetime.now()

        await broadcast_to_session(session_id, {
            "type": "phase_completed",
            "completed_phase": current_phase,
            "next_phase": next_phase
        })

        return {
            "success": True,
            "completed_phase": current_phase,
            "next_phase": next_phase,
            "session": session.dict()
        }

    return {
        "success": True,
        "completed_phase": current_phase,
        "next_phase": None,
        "message": "Planning session completed"
    }


@router.get("/sessions/{session_id}/full-state")
async def get_full_session_state(session_id: str) -> Dict[str, Any]:
    """Get complete session state with all related data"""
    if session_id not in planning_sessions:
        raise HTTPException(status_code=404, detail="Planning session not found")

    session = planning_sessions[session_id]

    return {
        "session": session.dict(),
        "concepts": [concepts[cid].dict() for cid in session.concepts if cid in concepts],
        "questions": [questions[qid].dict() for qid in session.questions if qid in questions],
        "tech_stack": [tech_stack[tid].dict() for tid in session.tech_stack_items if tid in tech_stack],
        "decisions": [tech_decisions[did].dict() for did in session.technical_decisions if did in tech_decisions],
        "execution_plans": [execution_plans[eid].dict() for eid in session.execution_plans if eid in execution_plans],
        "ide_handoffs": [ide_handoffs[hid].dict() for hid in session.ide_handoffs if hid in ide_handoffs]
    }
