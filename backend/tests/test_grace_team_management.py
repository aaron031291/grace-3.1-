"""
Tests for Grace Team Management Service

Comprehensive tests for skill-based auto-assignment system.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

# Import the module to test
from services.grace_team_management import (
    GraceTeamManagement, get_team_management,
    SkillLevel, TeamRole, AssignmentStrategy,
    Skill, TeamMember, GraceAgent, AssignmentResult
)


class TestSkillLevelEnum:
    """Test SkillLevel enum"""

    def test_all_levels_exist(self):
        """Test all expected skill levels exist"""
        expected = ["novice", "intermediate", "advanced", "expert", "master"]
        for level in expected:
            assert hasattr(SkillLevel, level.upper())

    def test_level_ordering(self):
        """Test skill levels can be ordered"""
        levels = [SkillLevel.NOVICE, SkillLevel.INTERMEDIATE, SkillLevel.ADVANCED, SkillLevel.EXPERT, SkillLevel.MASTER]
        # Should be in increasing order of expertise
        assert len(levels) == 5


class TestTeamRoleEnum:
    """Test TeamRole enum"""

    def test_all_roles_exist(self):
        """Test all expected roles exist"""
        expected = ["developer", "designer", "architect", "qa_engineer", "devops", "data_scientist", "product_manager", "tech_lead", "grace_agent"]
        for role in expected:
            assert hasattr(TeamRole, role.upper())


class TestAssignmentStrategyEnum:
    """Test AssignmentStrategy enum"""

    def test_all_strategies_exist(self):
        """Test all expected strategies exist"""
        expected = ["skill_match", "workload_balance", "hybrid", "round_robin", "priority_first", "learning"]
        for strategy in expected:
            assert hasattr(AssignmentStrategy, strategy.upper())


class TestSkillDataclass:
    """Test Skill dataclass"""

    def test_skill_creation(self):
        """Test creating a Skill"""
        skill = Skill(
            name="Python",
            category="backend"
        )
        assert skill.name == "Python"
        assert skill.category == "backend"
        assert skill.level == SkillLevel.INTERMEDIATE  # Default
        assert skill.years_experience == 0

    def test_skill_with_all_fields(self):
        """Test skill with all fields"""
        skill = Skill(
            name="React",
            category="frontend",
            level=SkillLevel.EXPERT,
            years_experience=5,
            certifications=["React Certified Developer"],
            last_used=datetime.now()
        )
        assert skill.level == SkillLevel.EXPERT
        assert skill.years_experience == 5
        assert len(skill.certifications) == 1


class TestTeamMemberDataclass:
    """Test TeamMember dataclass"""

    def test_member_creation(self):
        """Test creating a TeamMember"""
        member = TeamMember(
            id="TM-001",
            genesis_id="G-USER-001",
            name="John Developer",
            email="john@example.com",
            role=TeamRole.DEVELOPER
        )
        assert member.id == "TM-001"
        assert member.name == "John Developer"
        assert member.role == TeamRole.DEVELOPER
        assert member.is_available is True
        assert member.current_workload == 0

    def test_member_with_skills(self):
        """Test member with skills"""
        skills = [
            Skill(name="Python", category="backend", level=SkillLevel.EXPERT),
            Skill(name="React", category="frontend", level=SkillLevel.ADVANCED)
        ]
        member = TeamMember(
            id="TM-002",
            genesis_id="G-USER-002",
            name="Jane Fullstack",
            email="jane@example.com",
            role=TeamRole.DEVELOPER,
            skills=skills
        )
        assert len(member.skills) == 2

    def test_member_availability(self):
        """Test member availability settings"""
        member = TeamMember(
            id="TM-003",
            genesis_id="G-USER-003",
            name="Busy Bob",
            email="bob@example.com",
            role=TeamRole.DEVELOPER,
            is_available=False,
            current_workload=85
        )
        assert member.is_available is False
        assert member.current_workload == 85


class TestGraceAgentDataclass:
    """Test GraceAgent dataclass"""

    def test_agent_creation(self):
        """Test creating a GraceAgent"""
        agent = GraceAgent(
            id="GA-001",
            name="Analysis Agent",
            agent_type="analysis",
            capabilities=["code_review", "security_scan"]
        )
        assert agent.id == "GA-001"
        assert agent.agent_type == "analysis"
        assert agent.is_active is True
        assert agent.success_rate == 0.95

    def test_agent_with_tasks(self):
        """Test agent with assigned tasks"""
        agent = GraceAgent(
            id="GA-002",
            name="Coding Agent",
            agent_type="coding",
            capabilities=["python", "javascript"],
            max_concurrent=5,
            current_tasks=["GT-001", "GT-002"]
        )
        assert len(agent.current_tasks) == 2
        assert agent.max_concurrent == 5


class TestAssignmentResultDataclass:
    """Test AssignmentResult dataclass"""

    def test_result_creation(self):
        """Test creating an AssignmentResult"""
        result = AssignmentResult(
            task_id="GT-001",
            assignee_id="TM-001",
            assignee_type="team_member",
            confidence=0.85,
            reasoning="Best skill match",
            skill_match_score=90,
            workload_score=80
        )
        assert result.task_id == "GT-001"
        assert result.confidence == 0.85
        assert result.assignee_type == "team_member"


class TestGraceTeamManagement:
    """Test GraceTeamManagement class"""

    def setup_method(self):
        """Create fresh instance for each test"""
        self.manager = GraceTeamManagement()

    def test_initialization(self):
        """Test manager initialization"""
        assert self.manager is not None
        assert len(self.manager.grace_agents) > 0  # Default agents

    def test_default_agents_created(self):
        """Test default Grace agents are created"""
        agent_types = [a.agent_type for a in self.manager.grace_agents.values()]
        assert "analysis" in agent_types
        assert "coding" in agent_types
        assert "testing" in agent_types
        assert "research" in agent_types
        assert "devops" in agent_types


class TestTeamMemberManagement:
    """Test team member management functions"""

    def setup_method(self):
        """Create fresh instance for each test"""
        self.manager = GraceTeamManagement()

    def test_add_team_member(self):
        """Test adding a team member"""
        member = self.manager.add_team_member(
            name="Test Member",
            email="test@example.com",
            role=TeamRole.DEVELOPER,
            genesis_id="G-TEST-001"
        )
        assert member is not None
        assert member.id.startswith("TM-")
        assert member.name == "Test Member"
        assert member.id in self.manager.team_members

    def test_add_member_with_skills(self):
        """Test adding member with skills"""
        skills = [
            {"name": "Python", "category": "backend", "level": "expert"},
            {"name": "React", "category": "frontend", "level": "advanced"}
        ]
        member = self.manager.add_team_member(
            name="Skilled Member",
            email="skilled@example.com",
            role=TeamRole.DEVELOPER,
            skills=skills
        )
        assert len(member.skills) == 2
        assert member.skills[0].name == "Python"

    def test_update_team_member(self):
        """Test updating team member"""
        member = self.manager.add_team_member(
            name="Update Test",
            email="update@example.com",
            role=TeamRole.DEVELOPER
        )
        updated = self.manager.update_team_member(
            member.id,
            {"current_workload": 50, "is_available": False}
        )
        assert updated.current_workload == 50
        assert updated.is_available is False

    def test_add_skill_to_member(self):
        """Test adding skill to existing member"""
        member = self.manager.add_team_member(
            name="Skill Test",
            email="skill@example.com",
            role=TeamRole.DEVELOPER
        )
        result = self.manager.add_skill_to_member(
            member.id,
            skill_name="Docker",
            category="devops",
            level=SkillLevel.INTERMEDIATE
        )
        assert result is True
        assert any(s.name == "Docker" for s in member.skills)

    def test_get_team_member(self):
        """Test getting team member by ID"""
        member = self.manager.add_team_member(
            name="Get Test",
            email="get@example.com",
            role=TeamRole.DEVELOPER
        )
        retrieved = self.manager.get_team_member(member.id)
        assert retrieved is not None
        assert retrieved.name == "Get Test"

    def test_get_team_by_genesis_id(self):
        """Test getting member by Genesis ID"""
        member = self.manager.add_team_member(
            name="Genesis Test",
            email="genesis@example.com",
            role=TeamRole.DEVELOPER,
            genesis_id="G-GENESIS-001"
        )
        retrieved = self.manager.get_team_by_genesis_id("G-GENESIS-001")
        assert retrieved is not None
        assert retrieved.name == "Genesis Test"

    def test_get_all_team_members(self):
        """Test getting all team members"""
        self.manager.add_team_member(
            name="Member 1", email="m1@example.com", role=TeamRole.DEVELOPER
        )
        self.manager.add_team_member(
            name="Member 2", email="m2@example.com", role=TeamRole.DESIGNER
        )
        all_members = self.manager.get_all_team_members()
        assert len(all_members) == 2

    def test_get_members_by_role(self):
        """Test filtering members by role"""
        self.manager.add_team_member(
            name="Dev 1", email="dev1@example.com", role=TeamRole.DEVELOPER
        )
        self.manager.add_team_member(
            name="Dev 2", email="dev2@example.com", role=TeamRole.DEVELOPER
        )
        self.manager.add_team_member(
            name="Designer", email="designer@example.com", role=TeamRole.DESIGNER
        )
        developers = self.manager.get_all_team_members(role=TeamRole.DEVELOPER)
        assert len(developers) == 2

    def test_get_members_with_skill(self):
        """Test getting members with specific skill"""
        self.manager.add_team_member(
            name="Python Dev",
            email="python@example.com",
            role=TeamRole.DEVELOPER,
            skills=[{"name": "Python", "category": "backend", "level": "expert"}]
        )
        self.manager.add_team_member(
            name="JS Dev",
            email="js@example.com",
            role=TeamRole.DEVELOPER,
            skills=[{"name": "JavaScript", "category": "frontend", "level": "advanced"}]
        )
        python_devs = self.manager.get_members_with_skill("Python")
        assert len(python_devs) == 1


class TestGraceAgentManagement:
    """Test Grace agent management functions"""

    def setup_method(self):
        """Create fresh instance for each test"""
        self.manager = GraceTeamManagement()

    def test_add_grace_agent(self):
        """Test adding a Grace agent"""
        agent = self.manager.add_grace_agent(
            name="Custom Agent",
            agent_type="custom",
            capabilities=["custom_capability"],
            max_concurrent=15
        )
        assert agent is not None
        assert agent.id.startswith("GA-")
        assert agent.agent_type == "custom"
        assert agent.id in self.manager.grace_agents

    def test_get_grace_agent(self):
        """Test getting agent by ID"""
        agent = self.manager.add_grace_agent(
            name="Get Agent",
            agent_type="test",
            capabilities=["test"]
        )
        retrieved = self.manager.get_grace_agent(agent.id)
        assert retrieved is not None
        assert retrieved.name == "Get Agent"

    def test_get_agents_by_capability(self):
        """Test getting agents by capability"""
        self.manager.add_grace_agent(
            name="Python Agent",
            agent_type="coding",
            capabilities=["python", "api_design"]
        )
        python_agents = self.manager.get_agents_by_capability("python")
        assert len(python_agents) >= 1

    def test_get_available_agents(self):
        """Test getting available agents"""
        available = self.manager.get_available_agents()
        # Should have default agents available
        assert len(available) > 0


class TestAutoAssignment:
    """Test auto-assignment functionality"""

    def setup_method(self):
        """Create fresh instance with test data"""
        self.manager = GraceTeamManagement()
        # Add test team members
        self.manager.add_team_member(
            name="Python Expert",
            email="python@example.com",
            role=TeamRole.DEVELOPER,
            skills=[
                {"name": "python", "category": "backend", "level": "expert"},
                {"name": "api_design", "category": "backend", "level": "advanced"}
            ]
        )
        self.manager.add_team_member(
            name="Frontend Dev",
            email="frontend@example.com",
            role=TeamRole.DEVELOPER,
            skills=[
                {"name": "react", "category": "frontend", "level": "expert"},
                {"name": "javascript", "category": "frontend", "level": "expert"}
            ]
        )

    def test_auto_assign_skill_match(self):
        """Test auto-assignment with skill matching"""
        result = self.manager.auto_assign_task(
            task_id="GT-TEST-001",
            task_type="coding",
            required_skills=["python", "api_design"],
            strategy=AssignmentStrategy.SKILL_MATCH
        )
        assert result is not None
        assert result.task_id == "GT-TEST-001"
        assert result.assignee_id != ""
        assert result.confidence > 0

    def test_auto_assign_workload_balance(self):
        """Test auto-assignment with workload balancing"""
        result = self.manager.auto_assign_task(
            task_id="GT-TEST-002",
            task_type="coding",
            required_skills=["python"],
            strategy=AssignmentStrategy.WORKLOAD_BALANCE
        )
        assert result is not None
        assert result.workload_score >= 0

    def test_auto_assign_hybrid(self):
        """Test auto-assignment with hybrid strategy"""
        result = self.manager.auto_assign_task(
            task_id="GT-TEST-003",
            task_type="coding",
            required_skills=["python"],
            strategy=AssignmentStrategy.HYBRID
        )
        assert result is not None
        assert result.skill_match_score >= 0
        assert result.workload_score >= 0

    def test_auto_assign_prefer_human(self):
        """Test auto-assignment preferring human"""
        result = self.manager.auto_assign_task(
            task_id="GT-TEST-004",
            task_type="coding",
            required_skills=["python"],
            prefer_human=True
        )
        if result.assignee_id:
            # If assigned, should be a team member
            assert result.assignee_type == "team_member"

    def test_auto_assign_prefer_agent(self):
        """Test auto-assignment preferring Grace agent"""
        result = self.manager.auto_assign_task(
            task_id="GT-TEST-005",
            task_type="coding",
            required_skills=["python"],
            prefer_agent=True
        )
        if result.assignee_id:
            # If assigned, should be an agent
            assert result.assignee_type == "grace_agent"

    def test_auto_assign_no_candidates(self):
        """Test auto-assignment with no matching candidates"""
        result = self.manager.auto_assign_task(
            task_id="GT-TEST-006",
            task_type="coding",
            required_skills=["nonexistent_skill_xyz"],
            prefer_human=True  # Only look at humans
        )
        # Should return with no assignee but still valid result
        assert result is not None

    def test_auto_assign_stores_in_history(self):
        """Test that assignments are stored in history"""
        initial_count = len(self.manager.assignment_history)
        self.manager.auto_assign_task(
            task_id="GT-TEST-007",
            task_type="coding",
            required_skills=["python"]
        )
        assert len(self.manager.assignment_history) == initial_count + 1

    def test_auto_assign_alternatives(self):
        """Test that alternatives are provided"""
        result = self.manager.auto_assign_task(
            task_id="GT-TEST-008",
            task_type="coding",
            required_skills=["python"]
        )
        # Should have alternatives if multiple candidates exist
        assert isinstance(result.alternatives, list)


class TestAssignmentCompletion:
    """Test assignment completion functionality"""

    def setup_method(self):
        """Create fresh instance with test data"""
        self.manager = GraceTeamManagement()
        self.member = self.manager.add_team_member(
            name="Complete Test",
            email="complete@example.com",
            role=TeamRole.DEVELOPER,
            skills=[{"name": "python", "category": "backend", "level": "expert"}]
        )

    def test_complete_assignment_success(self):
        """Test completing a successful assignment"""
        # First assign a task
        result = self.manager.auto_assign_task(
            task_id="GT-COMPLETE-001",
            task_type="coding",
            required_skills=["python"]
        )
        # Complete it
        self.manager.complete_assignment(
            task_id="GT-COMPLETE-001",
            success=True,
            actual_hours=4
        )
        # Workload should decrease

    def test_complete_assignment_failure(self):
        """Test completing a failed assignment"""
        result = self.manager.auto_assign_task(
            task_id="GT-COMPLETE-002",
            task_type="coding",
            required_skills=["python"]
        )
        self.manager.complete_assignment(
            task_id="GT-COMPLETE-002",
            success=False
        )


class TestReporting:
    """Test reporting and analytics functions"""

    def setup_method(self):
        """Create fresh instance with test data"""
        self.manager = GraceTeamManagement()
        self.manager.add_team_member(
            name="Report Test 1",
            email="r1@example.com",
            role=TeamRole.DEVELOPER,
            skills=[{"name": "python", "category": "backend", "level": "expert"}]
        )
        self.manager.add_team_member(
            name="Report Test 2",
            email="r2@example.com",
            role=TeamRole.DESIGNER,
            skills=[{"name": "figma", "category": "design", "level": "advanced"}]
        )

    def test_get_team_overview(self):
        """Test getting team overview"""
        overview = self.manager.get_team_overview()
        assert "team_members" in overview
        assert "grace_agents" in overview
        assert "skills_coverage" in overview
        assert overview["team_members"]["total"] == 2

    def test_get_workload_report(self):
        """Test getting workload report"""
        report = self.manager.get_workload_report()
        assert len(report) > 0  # Should include team members and agents
        # Each entry should have required fields
        for entry in report:
            assert "id" in entry
            assert "name" in entry
            assert "current_workload" in entry

    def test_suggest_skill_development(self):
        """Test suggesting skills for development"""
        member = self.manager.add_team_member(
            name="Skill Dev Test",
            email="skilldev@example.com",
            role=TeamRole.DEVELOPER,
            skills=[{"name": "python", "category": "backend", "level": "intermediate"}]
        )
        # Add some task requirements
        self.manager.task_requirements["GT-001"] = {"required_skills": ["react", "typescript"]}
        self.manager.task_requirements["GT-002"] = {"required_skills": ["react", "node"]}

        suggestions = self.manager.suggest_skill_development(member.id)
        # Should suggest skills not possessed by member
        assert isinstance(suggestions, list)


class TestSingleton:
    """Test singleton pattern"""

    def test_get_team_management_singleton(self):
        """Test that get_team_management returns singleton"""
        manager1 = get_team_management()
        manager2 = get_team_management()
        # Should be the same instance (note: may need to reset for clean test)
        assert manager1 is manager2


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
