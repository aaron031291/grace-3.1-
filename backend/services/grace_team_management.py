"""
Grace Team Management Service

Skill-based auto-assignment system for tasks and jobs.
Manages team members, skills, workload, and intelligent assignment.

Features:
- Team member profiles with skills and Genesis IDs
- Skill-based task matching
- Workload balancing
- Availability tracking
- Performance history integration
- Auto-assignment with ML predictions

Author: Grace Autonomous System
"""

from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import uuid
import asyncio
from collections import defaultdict


class SkillLevel(str, Enum):
    """Skill proficiency levels"""
    NOVICE = "novice"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    MASTER = "master"


class TeamRole(str, Enum):
    """Team member roles"""
    DEVELOPER = "developer"
    DESIGNER = "designer"
    ARCHITECT = "architect"
    QA_ENGINEER = "qa_engineer"
    DEVOPS = "devops"
    DATA_SCIENTIST = "data_scientist"
    PRODUCT_MANAGER = "product_manager"
    TECH_LEAD = "tech_lead"
    GRACE_AGENT = "grace_agent"


class AssignmentStrategy(str, Enum):
    """Task assignment strategies"""
    SKILL_MATCH = "skill_match"  # Best skill match
    WORKLOAD_BALANCE = "workload_balance"  # Lowest workload
    HYBRID = "hybrid"  # Skill + workload
    ROUND_ROBIN = "round_robin"  # Fair distribution
    PRIORITY_FIRST = "priority_first"  # High priority gets best match
    LEARNING = "learning"  # Assign for skill development


@dataclass
class Skill:
    """Skill definition"""
    name: str
    category: str  # frontend, backend, devops, design, etc.
    level: SkillLevel = SkillLevel.INTERMEDIATE
    years_experience: float = 0
    certifications: List[str] = field(default_factory=list)
    last_used: Optional[datetime] = None


@dataclass
class TeamMember:
    """Team member profile"""
    id: str
    genesis_id: str  # Genesis Key for tracking
    name: str
    email: str
    role: TeamRole
    skills: List[Skill] = field(default_factory=list)

    # Availability
    is_available: bool = True
    availability_hours: int = 40  # Weekly hours
    current_capacity: float = 100  # Percentage available

    # Workload
    current_tasks: List[str] = field(default_factory=list)
    max_concurrent_tasks: int = 5
    current_workload: float = 0  # 0-100 percentage

    # Performance
    tasks_completed: int = 0
    success_rate: float = 0.8
    avg_completion_time_hours: float = 8

    # Preferences
    preferred_task_types: List[str] = field(default_factory=list)
    timezone: str = "UTC"

    # Metadata
    joined_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)


@dataclass
class GraceAgent:
    """Grace AI agent that can be assigned tasks"""
    id: str
    name: str
    agent_type: str  # analysis, coding, testing, research, etc.
    capabilities: List[str] = field(default_factory=list)
    max_concurrent: int = 10
    current_tasks: List[str] = field(default_factory=list)
    success_rate: float = 0.95
    avg_completion_time_ms: int = 5000
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class AssignmentResult:
    """Result of task assignment"""
    task_id: str
    assignee_id: str
    assignee_type: str  # team_member, grace_agent
    confidence: float
    reasoning: str
    skill_match_score: float
    workload_score: float
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    assigned_at: datetime = field(default_factory=datetime.now)


class GraceTeamManagement:
    """
    Team management system with skill-based auto-assignment.
    """

    def __init__(self):
        self.team_members: Dict[str, TeamMember] = {}
        self.grace_agents: Dict[str, GraceAgent] = {}
        self.skills_registry: Dict[str, List[str]] = defaultdict(list)  # skill -> member_ids
        self.assignment_history: List[AssignmentResult] = []
        self.task_requirements: Dict[str, Dict[str, Any]] = {}  # task_id -> requirements

        # Initialize default Grace agents
        self._initialize_default_agents()

    def _initialize_default_agents(self):
        """Initialize default Grace AI agents"""
        default_agents = [
            GraceAgent(
                id="GA-ANALYSIS-001",
                name="Grace Analyst",
                agent_type="analysis",
                capabilities=["code_review", "architecture_analysis", "security_scan", "performance_analysis"],
                max_concurrent=20
            ),
            GraceAgent(
                id="GA-CODING-001",
                name="Grace Coder",
                agent_type="coding",
                capabilities=["python", "javascript", "typescript", "api_development", "database_design"],
                max_concurrent=10
            ),
            GraceAgent(
                id="GA-TESTING-001",
                name="Grace Tester",
                agent_type="testing",
                capabilities=["unit_testing", "integration_testing", "e2e_testing", "test_automation"],
                max_concurrent=15
            ),
            GraceAgent(
                id="GA-RESEARCH-001",
                name="Grace Researcher",
                agent_type="research",
                capabilities=["documentation", "research", "learning", "knowledge_synthesis"],
                max_concurrent=25
            ),
            GraceAgent(
                id="GA-DEVOPS-001",
                name="Grace DevOps",
                agent_type="devops",
                capabilities=["ci_cd", "deployment", "monitoring", "infrastructure"],
                max_concurrent=8
            )
        ]

        for agent in default_agents:
            self.grace_agents[agent.id] = agent

    # =========================================================================
    # TEAM MEMBER MANAGEMENT
    # =========================================================================

    def add_team_member(
        self,
        name: str,
        email: str,
        role: TeamRole,
        genesis_id: Optional[str] = None,
        skills: Optional[List[Dict[str, Any]]] = None
    ) -> TeamMember:
        """Add a new team member"""
        member_id = f"TM-{uuid.uuid4().hex[:8]}"
        genesis_id = genesis_id or f"G-{uuid.uuid4().hex[:8]}"

        # Convert skill dicts to Skill objects
        skill_objects = []
        if skills:
            for s in skills:
                skill = Skill(
                    name=s.get("name", ""),
                    category=s.get("category", "general"),
                    level=SkillLevel(s.get("level", "intermediate")),
                    years_experience=s.get("years_experience", 0)
                )
                skill_objects.append(skill)

                # Register in skills index
                self.skills_registry[skill.name.lower()].append(member_id)

        member = TeamMember(
            id=member_id,
            genesis_id=genesis_id,
            name=name,
            email=email,
            role=role,
            skills=skill_objects
        )

        self.team_members[member_id] = member
        return member

    def update_team_member(
        self,
        member_id: str,
        updates: Dict[str, Any]
    ) -> Optional[TeamMember]:
        """Update team member details"""
        if member_id not in self.team_members:
            return None

        member = self.team_members[member_id]

        for key, value in updates.items():
            if hasattr(member, key):
                setattr(member, key, value)

        member.last_active = datetime.now()
        return member

    def add_skill_to_member(
        self,
        member_id: str,
        skill_name: str,
        category: str,
        level: SkillLevel = SkillLevel.INTERMEDIATE,
        years_experience: float = 0
    ) -> bool:
        """Add a skill to a team member"""
        if member_id not in self.team_members:
            return False

        member = self.team_members[member_id]
        skill = Skill(
            name=skill_name,
            category=category,
            level=level,
            years_experience=years_experience,
            last_used=datetime.now()
        )

        member.skills.append(skill)
        self.skills_registry[skill_name.lower()].append(member_id)
        return True

    def get_team_member(self, member_id: str) -> Optional[TeamMember]:
        """Get a team member by ID"""
        return self.team_members.get(member_id)

    def get_team_by_genesis_id(self, genesis_id: str) -> Optional[TeamMember]:
        """Get team member by Genesis ID"""
        for member in self.team_members.values():
            if member.genesis_id == genesis_id:
                return member
        return None

    def get_all_team_members(
        self,
        role: Optional[TeamRole] = None,
        available_only: bool = False
    ) -> List[TeamMember]:
        """Get all team members with optional filters"""
        members = list(self.team_members.values())

        if role:
            members = [m for m in members if m.role == role]
        if available_only:
            members = [m for m in members if m.is_available and m.current_workload < 100]

        return members

    def get_members_with_skill(
        self,
        skill_name: str,
        min_level: SkillLevel = SkillLevel.NOVICE
    ) -> List[TeamMember]:
        """Get team members with a specific skill"""
        level_order = [SkillLevel.NOVICE, SkillLevel.INTERMEDIATE, SkillLevel.ADVANCED, SkillLevel.EXPERT, SkillLevel.MASTER]
        min_level_idx = level_order.index(min_level)

        result = []
        member_ids = self.skills_registry.get(skill_name.lower(), [])

        for mid in member_ids:
            member = self.team_members.get(mid)
            if member:
                for skill in member.skills:
                    if skill.name.lower() == skill_name.lower():
                        skill_level_idx = level_order.index(skill.level)
                        if skill_level_idx >= min_level_idx:
                            result.append(member)
                            break

        return result

    # =========================================================================
    # GRACE AGENT MANAGEMENT
    # =========================================================================

    def add_grace_agent(
        self,
        name: str,
        agent_type: str,
        capabilities: List[str],
        max_concurrent: int = 10
    ) -> GraceAgent:
        """Add a new Grace AI agent"""
        agent_id = f"GA-{agent_type.upper()}-{uuid.uuid4().hex[:6]}"

        agent = GraceAgent(
            id=agent_id,
            name=name,
            agent_type=agent_type,
            capabilities=capabilities,
            max_concurrent=max_concurrent
        )

        self.grace_agents[agent_id] = agent
        return agent

    def get_grace_agent(self, agent_id: str) -> Optional[GraceAgent]:
        """Get a Grace agent by ID"""
        return self.grace_agents.get(agent_id)

    def get_agents_by_capability(
        self,
        capability: str,
        active_only: bool = True
    ) -> List[GraceAgent]:
        """Get Grace agents with a specific capability"""
        result = []
        for agent in self.grace_agents.values():
            if capability.lower() in [c.lower() for c in agent.capabilities]:
                if not active_only or agent.is_active:
                    result.append(agent)
        return result

    def get_available_agents(self) -> List[GraceAgent]:
        """Get all available Grace agents"""
        return [
            agent for agent in self.grace_agents.values()
            if agent.is_active and len(agent.current_tasks) < agent.max_concurrent
        ]

    # =========================================================================
    # SKILL-BASED AUTO-ASSIGNMENT
    # =========================================================================

    def auto_assign_task(
        self,
        task_id: str,
        task_type: str,
        required_skills: List[str],
        priority: int = 5,
        estimated_hours: float = 4,
        strategy: AssignmentStrategy = AssignmentStrategy.HYBRID,
        prefer_human: bool = False,
        prefer_agent: bool = False
    ) -> AssignmentResult:
        """
        Automatically assign a task to the best available resource.

        Args:
            task_id: Task identifier
            task_type: Type of task
            required_skills: Required skills/capabilities
            priority: Task priority (1-10)
            estimated_hours: Estimated time to complete
            strategy: Assignment strategy to use
            prefer_human: Prefer human team member
            prefer_agent: Prefer Grace AI agent
        """
        # Store task requirements
        self.task_requirements[task_id] = {
            "type": task_type,
            "required_skills": required_skills,
            "priority": priority,
            "estimated_hours": estimated_hours
        }

        # Get candidates
        candidates = self._get_assignment_candidates(
            required_skills=required_skills,
            prefer_human=prefer_human,
            prefer_agent=prefer_agent
        )

        if not candidates:
            # No candidates available
            return AssignmentResult(
                task_id=task_id,
                assignee_id="",
                assignee_type="none",
                confidence=0,
                reasoning="No available candidates with required skills",
                skill_match_score=0,
                workload_score=0
            )

        # Score candidates based on strategy
        scored_candidates = self._score_candidates(
            candidates=candidates,
            required_skills=required_skills,
            priority=priority,
            estimated_hours=estimated_hours,
            strategy=strategy
        )

        # Sort by score (highest first)
        scored_candidates.sort(key=lambda x: x["total_score"], reverse=True)

        # Select best candidate
        best = scored_candidates[0]
        alternatives = scored_candidates[1:4]  # Top 3 alternatives

        result = AssignmentResult(
            task_id=task_id,
            assignee_id=best["id"],
            assignee_type=best["type"],
            confidence=min(best["total_score"] / 100, 1.0),
            reasoning=best["reasoning"],
            skill_match_score=best["skill_score"],
            workload_score=best["workload_score"],
            alternatives=[
                {
                    "id": alt["id"],
                    "name": alt["name"],
                    "type": alt["type"],
                    "score": alt["total_score"]
                }
                for alt in alternatives
            ]
        )

        # Assign the task
        self._execute_assignment(result, estimated_hours)

        # Store in history
        self.assignment_history.append(result)

        return result

    def _get_assignment_candidates(
        self,
        required_skills: List[str],
        prefer_human: bool,
        prefer_agent: bool
    ) -> List[Dict[str, Any]]:
        """Get all potential candidates for assignment"""
        candidates = []

        # Get team members
        if not prefer_agent:
            for member in self.team_members.values():
                if member.is_available and member.current_workload < 100:
                    candidates.append({
                        "id": member.id,
                        "name": member.name,
                        "type": "team_member",
                        "skills": [s.name.lower() for s in member.skills],
                        "skill_levels": {s.name.lower(): s.level for s in member.skills},
                        "workload": member.current_workload,
                        "max_workload": 100,
                        "success_rate": member.success_rate,
                        "role": member.role.value
                    })

        # Get Grace agents
        if not prefer_human:
            for agent in self.grace_agents.values():
                if agent.is_active and len(agent.current_tasks) < agent.max_concurrent:
                    candidates.append({
                        "id": agent.id,
                        "name": agent.name,
                        "type": "grace_agent",
                        "skills": [c.lower() for c in agent.capabilities],
                        "skill_levels": {c.lower(): SkillLevel.EXPERT for c in agent.capabilities},
                        "workload": (len(agent.current_tasks) / agent.max_concurrent) * 100,
                        "max_workload": 100,
                        "success_rate": agent.success_rate,
                        "role": agent.agent_type
                    })

        return candidates

    def _score_candidates(
        self,
        candidates: List[Dict[str, Any]],
        required_skills: List[str],
        priority: int,
        estimated_hours: float,
        strategy: AssignmentStrategy
    ) -> List[Dict[str, Any]]:
        """Score candidates based on assignment strategy"""
        level_weights = {
            SkillLevel.NOVICE: 20,
            SkillLevel.INTERMEDIATE: 40,
            SkillLevel.ADVANCED: 60,
            SkillLevel.EXPERT: 80,
            SkillLevel.MASTER: 100
        }

        scored = []

        for candidate in candidates:
            # Calculate skill match score (0-100)
            skill_score = 0
            matched_skills = 0
            required_skills_lower = [s.lower() for s in required_skills]

            for req_skill in required_skills_lower:
                if req_skill in candidate["skills"]:
                    matched_skills += 1
                    level = candidate["skill_levels"].get(req_skill, SkillLevel.INTERMEDIATE)
                    skill_score += level_weights.get(level, 40)

            if required_skills:
                skill_score = skill_score / len(required_skills)
            else:
                skill_score = 50  # Default if no skills required

            # Calculate workload score (0-100, higher is better = lower workload)
            workload_score = 100 - candidate["workload"]

            # Calculate availability score
            availability_score = 100 if candidate["workload"] < 80 else 50

            # Calculate success rate score
            success_score = candidate["success_rate"] * 100

            # Calculate total score based on strategy
            if strategy == AssignmentStrategy.SKILL_MATCH:
                total_score = skill_score * 0.7 + success_score * 0.2 + workload_score * 0.1
            elif strategy == AssignmentStrategy.WORKLOAD_BALANCE:
                total_score = workload_score * 0.6 + skill_score * 0.3 + availability_score * 0.1
            elif strategy == AssignmentStrategy.PRIORITY_FIRST:
                # High priority tasks get best skill match
                skill_weight = 0.4 + (priority / 10) * 0.4
                total_score = skill_score * skill_weight + success_score * 0.3 + workload_score * (0.7 - skill_weight)
            elif strategy == AssignmentStrategy.LEARNING:
                # Assign to develop skills - prefer lower skill levels
                learning_score = 100 - skill_score  # Inverse - lower skill = higher learning opportunity
                total_score = learning_score * 0.5 + workload_score * 0.3 + availability_score * 0.2
            else:  # HYBRID (default)
                total_score = skill_score * 0.4 + workload_score * 0.3 + success_score * 0.2 + availability_score * 0.1

            # Build reasoning
            reasoning_parts = []
            if matched_skills > 0:
                reasoning_parts.append(f"Matched {matched_skills}/{len(required_skills)} required skills")
            reasoning_parts.append(f"Current workload: {candidate['workload']:.0f}%")
            reasoning_parts.append(f"Success rate: {candidate['success_rate']*100:.0f}%")
            if candidate["type"] == "grace_agent":
                reasoning_parts.append("Grace AI agent - fast execution")

            scored.append({
                **candidate,
                "skill_score": skill_score,
                "workload_score": workload_score,
                "success_score": success_score,
                "total_score": total_score,
                "reasoning": "; ".join(reasoning_parts)
            })

        return scored

    def _execute_assignment(
        self,
        result: AssignmentResult,
        estimated_hours: float
    ):
        """Execute the assignment by updating assignee workload"""
        if result.assignee_type == "team_member":
            member = self.team_members.get(result.assignee_id)
            if member:
                member.current_tasks.append(result.task_id)
                # Increase workload based on estimated hours (40h = 100%)
                workload_increase = (estimated_hours / 40) * 100
                member.current_workload = min(100, member.current_workload + workload_increase)
                member.last_active = datetime.now()

        elif result.assignee_type == "grace_agent":
            agent = self.grace_agents.get(result.assignee_id)
            if agent:
                agent.current_tasks.append(result.task_id)

    def complete_assignment(
        self,
        task_id: str,
        success: bool,
        actual_hours: Optional[float] = None
    ):
        """Mark an assignment as complete and update metrics"""
        # Find the assignment
        assignment = None
        for a in reversed(self.assignment_history):
            if a.task_id == task_id:
                assignment = a
                break

        if not assignment:
            return

        if assignment.assignee_type == "team_member":
            member = self.team_members.get(assignment.assignee_id)
            if member:
                if task_id in member.current_tasks:
                    member.current_tasks.remove(task_id)
                member.tasks_completed += 1

                # Update success rate (rolling average)
                member.success_rate = (member.success_rate * (member.tasks_completed - 1) + (1 if success else 0)) / member.tasks_completed

                # Update average completion time
                if actual_hours:
                    member.avg_completion_time_hours = (member.avg_completion_time_hours * (member.tasks_completed - 1) + actual_hours) / member.tasks_completed

                # Reduce workload
                task_req = self.task_requirements.get(task_id, {})
                estimated = task_req.get("estimated_hours", 4)
                workload_decrease = (estimated / 40) * 100
                member.current_workload = max(0, member.current_workload - workload_decrease)

        elif assignment.assignee_type == "grace_agent":
            agent = self.grace_agents.get(assignment.assignee_id)
            if agent:
                if task_id in agent.current_tasks:
                    agent.current_tasks.remove(task_id)
                # Update success rate
                agent.success_rate = (agent.success_rate + (1 if success else 0)) / 2

    # =========================================================================
    # REPORTING & ANALYTICS
    # =========================================================================

    def get_team_overview(self) -> Dict[str, Any]:
        """Get overview of team status"""
        members = list(self.team_members.values())
        agents = list(self.grace_agents.values())

        return {
            "team_members": {
                "total": len(members),
                "available": len([m for m in members if m.is_available]),
                "by_role": self._count_by_attr(members, "role"),
                "avg_workload": sum(m.current_workload for m in members) / len(members) if members else 0,
                "total_active_tasks": sum(len(m.current_tasks) for m in members)
            },
            "grace_agents": {
                "total": len(agents),
                "active": len([a for a in agents if a.is_active]),
                "by_type": self._count_by_attr(agents, "agent_type"),
                "total_active_tasks": sum(len(a.current_tasks) for a in agents)
            },
            "skills_coverage": self._get_skills_coverage(),
            "assignment_stats": self._get_assignment_stats()
        }

    def _count_by_attr(self, items: List, attr: str) -> Dict[str, int]:
        """Count items by attribute"""
        counts = defaultdict(int)
        for item in items:
            val = getattr(item, attr, "unknown")
            if hasattr(val, "value"):
                val = val.value
            counts[val] += 1
        return dict(counts)

    def _get_skills_coverage(self) -> Dict[str, int]:
        """Get coverage count for each skill"""
        return {skill: len(members) for skill, members in self.skills_registry.items()}

    def _get_assignment_stats(self) -> Dict[str, Any]:
        """Get assignment statistics"""
        if not self.assignment_history:
            return {"total": 0}

        total = len(self.assignment_history)
        by_type = defaultdict(int)
        avg_confidence = 0

        for a in self.assignment_history:
            by_type[a.assignee_type] += 1
            avg_confidence += a.confidence

        return {
            "total": total,
            "by_assignee_type": dict(by_type),
            "avg_confidence": avg_confidence / total if total else 0
        }

    def get_workload_report(self) -> List[Dict[str, Any]]:
        """Get workload report for all team members and agents"""
        report = []

        for member in self.team_members.values():
            report.append({
                "id": member.id,
                "name": member.name,
                "type": "team_member",
                "role": member.role.value,
                "current_workload": member.current_workload,
                "active_tasks": len(member.current_tasks),
                "max_tasks": member.max_concurrent_tasks,
                "is_available": member.is_available,
                "success_rate": member.success_rate
            })

        for agent in self.grace_agents.values():
            workload = (len(agent.current_tasks) / agent.max_concurrent) * 100 if agent.max_concurrent else 0
            report.append({
                "id": agent.id,
                "name": agent.name,
                "type": "grace_agent",
                "role": agent.agent_type,
                "current_workload": workload,
                "active_tasks": len(agent.current_tasks),
                "max_tasks": agent.max_concurrent,
                "is_available": agent.is_active,
                "success_rate": agent.success_rate
            })

        return sorted(report, key=lambda x: x["current_workload"], reverse=True)

    def suggest_skill_development(
        self,
        member_id: str
    ) -> List[Dict[str, Any]]:
        """Suggest skills for a team member to develop"""
        member = self.team_members.get(member_id)
        if not member:
            return []

        current_skills = set(s.name.lower() for s in member.skills)
        suggestions = []

        # Find skills from recent task requirements that member doesn't have
        skill_demand = defaultdict(int)
        for task_req in self.task_requirements.values():
            for skill in task_req.get("required_skills", []):
                skill_lower = skill.lower()
                if skill_lower not in current_skills:
                    skill_demand[skill_lower] += 1

        # Sort by demand
        for skill, demand in sorted(skill_demand.items(), key=lambda x: -x[1])[:5]:
            suggestions.append({
                "skill": skill,
                "demand": demand,
                "reason": f"Required in {demand} recent tasks",
                "category": self._infer_skill_category(skill)
            })

        return suggestions

    def _infer_skill_category(self, skill: str) -> str:
        """Infer skill category from skill name"""
        skill_lower = skill.lower()
        if any(kw in skill_lower for kw in ["python", "javascript", "java", "api", "backend"]):
            return "backend"
        elif any(kw in skill_lower for kw in ["react", "vue", "css", "html", "frontend"]):
            return "frontend"
        elif any(kw in skill_lower for kw in ["docker", "kubernetes", "ci", "deploy", "aws"]):
            return "devops"
        elif any(kw in skill_lower for kw in ["test", "qa", "selenium"]):
            return "testing"
        elif any(kw in skill_lower for kw in ["design", "ux", "figma"]):
            return "design"
        else:
            return "general"


# Singleton instance
_team_management_instance: Optional[GraceTeamManagement] = None


def get_team_management() -> GraceTeamManagement:
    """Get the Team Management singleton"""
    global _team_management_instance
    if _team_management_instance is None:
        _team_management_instance = GraceTeamManagement()
    return _team_management_instance
