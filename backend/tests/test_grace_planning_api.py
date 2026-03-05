"""
import pytest; pytest.importorskip("api.grace_planning_api", reason="api.grace_planning_api removed — consolidated into Brain API")
Tests for Grace Planning API

Comprehensive tests for planning workflow system.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock

# Import the module to test
from api.grace_planning_api import (
    router,
    PlanningPhase, ConceptStatus, QuestionType, TechnicalDecisionStatus, ExecutionStatus,
    PlanningConcept, ConceptQuestion, TechnicalStackItem, TechnicalDecision,
    ExecutionPlan, IDEHandoff, PlanningSession,
    planning_sessions, concepts, questions, tech_stack, tech_decisions, execution_plans, ide_handoffs
)


class TestPlanningPhaseEnum:
    """Test PlanningPhase enum"""

    def test_all_phases_exist(self):
        """Test all expected phases exist"""
        expected = ["concept", "questions", "technical_stack", "technical_acceptance", "execute", "ide_handoff", "completed"]
        for phase in expected:
            assert hasattr(PlanningPhase, phase.upper())

    def test_phase_order(self):
        """Test phase progression order"""
        phase_order = [
            PlanningPhase.CONCEPT,
            PlanningPhase.QUESTIONS,
            PlanningPhase.TECHNICAL_STACK,
            PlanningPhase.TECHNICAL_ACCEPTANCE,
            PlanningPhase.EXECUTE,
            PlanningPhase.IDE_HANDOFF,
            PlanningPhase.COMPLETED
        ]
        # Each phase should be unique
        assert len(set(phase_order)) == len(phase_order)


class TestConceptStatusEnum:
    """Test ConceptStatus enum"""

    def test_all_statuses_exist(self):
        """Test all expected statuses exist"""
        expected = ["draft", "in_discussion", "approved", "rejected", "archived"]
        for status in expected:
            assert hasattr(ConceptStatus, status.upper())


class TestQuestionTypeEnum:
    """Test QuestionType enum"""

    def test_all_types_exist(self):
        """Test all expected question types exist"""
        expected = ["clarification", "scope", "functionality", "user_experience", "integration", "constraints"]
        for qtype in expected:
            assert hasattr(QuestionType, qtype.upper())


class TestPlanningConcept:
    """Test PlanningConcept model"""

    def test_concept_creation(self):
        """Test creating a PlanningConcept"""
        concept = PlanningConcept(
            title="New Feature",
            description="A new feature description",
            genesis_id="G-TEST-001"
        )
        assert concept.title == "New Feature"
        assert concept.id.startswith("GPC-")
        assert concept.status == ConceptStatus.DRAFT
        assert concept.phase == PlanningPhase.CONCEPT

    def test_concept_with_full_details(self):
        """Test concept with all fields"""
        concept = PlanningConcept(
            title="Complex Feature",
            description="Complex feature description",
            genesis_id="G-TEST-002",
            vision="Long-term vision statement",
            goals=["Goal 1", "Goal 2", "Goal 3"],
            success_criteria=["Criterion 1", "Criterion 2"],
            status=ConceptStatus.APPROVED,
            priority=8,
            estimated_complexity="high",
            tags=["important", "q1"]
        )
        assert concept.vision == "Long-term vision statement"
        assert len(concept.goals) == 3
        assert len(concept.success_criteria) == 2
        assert concept.priority == 8
        assert concept.estimated_complexity == "high"

    def test_concept_relationships(self):
        """Test concept parent-child relationships"""
        parent = PlanningConcept(
            title="Parent Concept",
            description="Parent description",
            genesis_id="G-PARENT"
        )
        child = PlanningConcept(
            title="Child Concept",
            description="Child description",
            genesis_id="G-CHILD",
            parent_concept_id=parent.id
        )
        parent.child_concepts.append(child.id)

        assert child.parent_concept_id == parent.id
        assert child.id in parent.child_concepts

    def test_concept_grace_analysis(self):
        """Test Grace analysis on concept"""
        concept = PlanningConcept(
            title="Analyzed Concept",
            description="To be analyzed",
            genesis_id="G-ANALYZE"
        )
        concept.grace_analysis = {
            "feasibility_score": 0.85,
            "complexity_assessment": "medium",
            "recommended_approach": "phased_implementation"
        }
        concept.grace_recommendations = ["Break into smaller tasks", "Define clear acceptance criteria"]

        assert concept.grace_analysis["feasibility_score"] == 0.85
        assert len(concept.grace_recommendations) == 2


class TestConceptQuestion:
    """Test ConceptQuestion model"""

    def test_question_creation(self):
        """Test creating a ConceptQuestion"""
        question = ConceptQuestion(
            concept_id="GPC-001",
            question="What are the user requirements?",
            genesis_id="G-TEST"
        )
        assert question.concept_id == "GPC-001"
        assert question.id.startswith("GPQ-")
        assert question.question_type == QuestionType.CLARIFICATION
        assert question.is_resolved is False

    def test_question_with_answers(self):
        """Test question with answers"""
        question = ConceptQuestion(
            concept_id="GPC-002",
            question="How should this integrate?",
            genesis_id="G-TEST",
            question_type=QuestionType.INTEGRATION
        )
        question.answers = [
            {"id": "ANS-001", "author": "Developer", "content": "Via REST API", "timestamp": datetime.now().isoformat()},
            {"id": "ANS-002", "author": "Architect", "content": "Use event-driven approach", "timestamp": datetime.now().isoformat()}
        ]
        question.accepted_answer = "ANS-001"
        question.is_resolved = True

        assert len(question.answers) == 2
        assert question.accepted_answer == "ANS-001"
        assert question.is_resolved is True

    def test_grace_suggested_answer(self):
        """Test Grace suggested answer"""
        question = ConceptQuestion(
            concept_id="GPC-003",
            question="What technology should we use?",
            genesis_id="G-TEST"
        )
        question.grace_suggested_answer = "Based on the requirements, I suggest using React for frontend"
        question.grace_confidence = 0.85

        assert question.grace_suggested_answer is not None
        assert question.grace_confidence == 0.85


class TestTechnicalStackItem:
    """Test TechnicalStackItem model"""

    def test_stack_item_creation(self):
        """Test creating a TechnicalStackItem"""
        item = TechnicalStackItem(
            concept_id="GPC-001",
            category="backend",
            name="FastAPI",
            purpose="API framework"
        )
        assert item.id.startswith("GTS-")
        assert item.category == "backend"
        assert item.name == "FastAPI"
        assert item.status == TechnicalDecisionStatus.PROPOSED

    def test_stack_item_with_pros_cons(self):
        """Test stack item with pros and cons"""
        item = TechnicalStackItem(
            concept_id="GPC-002",
            category="database",
            name="PostgreSQL",
            version="15",
            purpose="Primary database",
            pros=["ACID compliant", "Rich features", "Great performance"],
            cons=["More complex setup", "Requires more resources"]
        )
        assert len(item.pros) == 3
        assert len(item.cons) == 2
        assert item.version == "15"

    def test_stack_item_dependencies(self):
        """Test stack item dependencies"""
        item = TechnicalStackItem(
            concept_id="GPC-003",
            category="infrastructure",
            name="Kubernetes",
            purpose="Container orchestration",
            depends_on=["docker", "cloud_provider"]
        )
        assert len(item.depends_on) == 2


class TestTechnicalDecision:
    """Test TechnicalDecision model"""

    def test_decision_creation(self):
        """Test creating a TechnicalDecision"""
        decision = TechnicalDecision(
            concept_id="GPC-001",
            title="Database Selection",
            description="Choose primary database",
            decision_type="technology"
        )
        assert decision.id.startswith("GTD-")
        assert decision.status == TechnicalDecisionStatus.PROPOSED
        assert decision.decision_type == "technology"

    def test_decision_with_options(self):
        """Test decision with multiple options"""
        decision = TechnicalDecision(
            concept_id="GPC-002",
            title="Frontend Framework",
            description="Select frontend framework",
            decision_type="technology",
            options=[
                {"name": "React", "description": "Component-based library", "pros": ["Large ecosystem"], "cons": ["Learning curve"]},
                {"name": "Vue", "description": "Progressive framework", "pros": ["Easy to learn"], "cons": ["Smaller ecosystem"]},
                {"name": "Angular", "description": "Full framework", "pros": ["Complete solution"], "cons": ["Verbose"]}
            ]
        )
        assert len(decision.options) == 3

    def test_decision_acceptance(self):
        """Test accepting a decision"""
        decision = TechnicalDecision(
            concept_id="GPC-003",
            title="API Architecture",
            description="REST vs GraphQL",
            decision_type="architecture"
        )
        decision.selected_option = "REST"
        decision.rationale = "Better fit for our team's expertise"
        decision.status = TechnicalDecisionStatus.ACCEPTED
        decision.decided_at = datetime.now()

        assert decision.selected_option == "REST"
        assert decision.status == TechnicalDecisionStatus.ACCEPTED
        assert decision.decided_at is not None


class TestExecutionPlan:
    """Test ExecutionPlan model"""

    def test_plan_creation(self):
        """Test creating an ExecutionPlan"""
        plan = ExecutionPlan(
            concept_id="GPC-001",
            title="Feature Implementation Plan",
            description="Plan for implementing the feature"
        )
        assert plan.id.startswith("GPE-")
        assert plan.status == ExecutionStatus.NOT_STARTED
        assert plan.progress == 0

    def test_plan_with_phases(self):
        """Test plan with phases and milestones"""
        plan = ExecutionPlan(
            concept_id="GPC-002",
            title="Sprint Plan",
            description="Sprint implementation plan",
            phases=[
                {"name": "Setup", "description": "Initialize project", "order": 1},
                {"name": "Development", "description": "Core implementation", "order": 2},
                {"name": "Testing", "description": "QA and testing", "order": 3}
            ],
            milestones=[
                {"name": "MVP", "criteria": "Core features working", "phase": 2},
                {"name": "Release", "criteria": "All tests passing", "phase": 3}
            ]
        )
        assert len(plan.phases) == 3
        assert len(plan.milestones) == 2

    def test_plan_progress_tracking(self):
        """Test plan progress tracking"""
        plan = ExecutionPlan(
            concept_id="GPC-003",
            title="Progress Test",
            description="Testing progress"
        )
        plan.status = ExecutionStatus.IN_PROGRESS
        plan.started_at = datetime.now()
        plan.progress = 45
        plan.current_phase = "Development"

        assert plan.status == ExecutionStatus.IN_PROGRESS
        assert plan.progress == 45
        assert plan.current_phase == "Development"

    def test_plan_completion(self):
        """Test completing a plan"""
        plan = ExecutionPlan(
            concept_id="GPC-004",
            title="Completion Test",
            description="Testing completion"
        )
        plan.progress = 100
        plan.status = ExecutionStatus.COMPLETED
        plan.completed_at = datetime.now()

        assert plan.progress == 100
        assert plan.status == ExecutionStatus.COMPLETED
        assert plan.completed_at is not None


class TestIDEHandoff:
    """Test IDEHandoff model"""

    def test_handoff_creation(self):
        """Test creating an IDEHandoff"""
        handoff = IDEHandoff(
            concept_id="GPC-001",
            execution_plan_id="GPE-001"
        )
        assert handoff.id.startswith("GPH-")
        assert handoff.target_ide == "vscode"
        assert handoff.handoff_status == "pending"

    def test_handoff_with_files(self):
        """Test handoff with file specifications"""
        handoff = IDEHandoff(
            concept_id="GPC-002",
            execution_plan_id="GPE-002",
            files_to_create=[
                {"path": "src/components/NewFeature.tsx", "description": "Main component"},
                {"path": "src/services/api.ts", "description": "API service"}
            ],
            files_to_modify=[
                {"path": "src/App.tsx", "changes": "Add new route"}
            ]
        )
        assert len(handoff.files_to_create) == 2
        assert len(handoff.files_to_modify) == 1

    def test_handoff_send(self):
        """Test sending handoff to IDE"""
        handoff = IDEHandoff(
            concept_id="GPC-003",
            execution_plan_id="GPE-003"
        )
        handoff.handoff_status = "sent"
        handoff.handed_off_at = datetime.now()
        handoff.ide_session_id = "IDE-abc123"

        assert handoff.handoff_status == "sent"
        assert handoff.ide_session_id == "IDE-abc123"


class TestPlanningSession:
    """Test PlanningSession model"""

    def test_session_creation(self):
        """Test creating a PlanningSession"""
        session = PlanningSession(
            genesis_id="G-USER-001",
            title="New Project Planning"
        )
        assert session.id.startswith("GPS-")
        assert session.current_phase == PlanningPhase.CONCEPT
        assert "G-USER-001" in session.participants

    def test_session_phase_completion(self):
        """Test session phase completion tracking"""
        session = PlanningSession(
            genesis_id="G-USER-002",
            title="Phase Test Session"
        )
        session.phase_completion[PlanningPhase.CONCEPT] = 100
        session.phase_completion[PlanningPhase.QUESTIONS] = 50

        assert session.phase_completion[PlanningPhase.CONCEPT] == 100
        assert session.phase_completion[PlanningPhase.QUESTIONS] == 50

    def test_session_components(self):
        """Test session component tracking"""
        session = PlanningSession(
            genesis_id="G-USER-003",
            title="Component Test Session"
        )
        session.concepts.extend(["GPC-001", "GPC-002"])
        session.questions.extend(["GPQ-001", "GPQ-002", "GPQ-003"])
        session.tech_stack_items.extend(["GTS-001"])
        session.technical_decisions.extend(["GTD-001"])

        assert len(session.concepts) == 2
        assert len(session.questions) == 3
        assert len(session.tech_stack_items) == 1
        assert len(session.technical_decisions) == 1


class TestSessionStorage:
    """Test in-memory session storage"""

    def setup_method(self):
        """Clear storage before each test"""
        planning_sessions.clear()
        concepts.clear()
        questions.clear()
        tech_stack.clear()
        tech_decisions.clear()
        execution_plans.clear()
        ide_handoffs.clear()

    def test_add_session_to_storage(self):
        """Test adding session to storage"""
        session = PlanningSession(
            genesis_id="G-TEST",
            title="Storage Test"
        )
        planning_sessions[session.id] = session
        assert session.id in planning_sessions

    def test_add_concept_to_storage(self):
        """Test adding concept to storage"""
        concept = PlanningConcept(
            title="Storage Concept",
            description="Test",
            genesis_id="G-TEST"
        )
        concepts[concept.id] = concept
        assert concept.id in concepts


class TestPhaseTransitions:
    """Test phase transition logic"""

    def test_valid_phase_progression(self):
        """Test valid forward phase progression"""
        session = PlanningSession(
            genesis_id="G-TEST",
            title="Transition Test"
        )
        # Start at concept
        assert session.current_phase == PlanningPhase.CONCEPT

        # Progress through phases
        phases = [
            PlanningPhase.QUESTIONS,
            PlanningPhase.TECHNICAL_STACK,
            PlanningPhase.TECHNICAL_ACCEPTANCE,
            PlanningPhase.EXECUTE,
            PlanningPhase.IDE_HANDOFF,
            PlanningPhase.COMPLETED
        ]

        for phase in phases:
            session.current_phase = phase
            assert session.current_phase == phase


class TestGraceIntegration:
    """Test Grace AI integration features"""

    def test_concept_grace_analysis_structure(self):
        """Test Grace analysis structure"""
        analysis = {
            "feasibility_score": 0.85,
            "complexity_assessment": "medium",
            "recommended_approach": "phased_implementation",
            "potential_risks": ["Integration complexity"],
            "success_factors": ["Clear requirements"]
        }
        concept = PlanningConcept(
            title="Grace Analysis Test",
            description="Test",
            genesis_id="G-TEST"
        )
        concept.grace_analysis = analysis

        assert concept.grace_analysis["feasibility_score"] >= 0
        assert concept.grace_analysis["feasibility_score"] <= 1

    def test_decision_grace_recommendation(self):
        """Test Grace recommendation on decisions"""
        decision = TechnicalDecision(
            concept_id="GPC-001",
            title="Test Decision",
            description="Test",
            decision_type="technology"
        )
        decision.grace_analysis = {
            "grace_recommendation": "Option A",
            "recommendation_reason": "Best fit for requirements"
        }

        assert decision.grace_analysis["grace_recommendation"] == "Option A"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
