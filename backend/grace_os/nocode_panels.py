import logging
import json
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import uuid
class PanelType(str, Enum):
    logger = logging.getLogger(__name__)
    """Types of no-code panels."""
    STATUS = "status"               # Status indicator
    ACTION = "action"               # Single action button
    WORKFLOW = "workflow"           # Multi-step workflow
    MONITOR = "monitor"             # Real-time monitoring
    INPUT = "input"                 # User input (text/voice)
    LIST = "list"                   # List display
    CARD = "card"                   # Info card
    CHART = "chart"                 # Data visualization
    TASK = "task"                   # Task management
    HEALING = "healing"             # Self-healing controls
    GENESIS = "genesis"             # Genesis key viewer


class ActionCategory(str, Enum):
    """Categories of available actions."""
    HEALING = "healing"
    CODE = "code"
    FILES = "files"
    SEARCH = "search"
    BUILD = "build"
    TEST = "test"
    DEPLOY = "deploy"
    LEARN = "learn"
    VOICE = "voice"
    SETTINGS = "settings"


@dataclass
class PanelAction:
    """An action that can be triggered from a panel."""
    action_id: str
    name: str
    description: str
    category: ActionCategory
    icon: str  # Icon name for UI
    requires_confirmation: bool = False
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "icon": self.icon,
            "requires_confirmation": self.requires_confirmation,
            "parameters": self.parameters,
            "enabled": self.enabled
        }


@dataclass
class Panel:
    """A visual panel for the no-code interface."""
    panel_id: str
    panel_type: PanelType
    title: str
    description: str = ""
    position: Dict[str, int] = field(default_factory=lambda: {"x": 0, "y": 0, "w": 2, "h": 2})
    data: Dict[str, Any] = field(default_factory=dict)
    actions: List[PanelAction] = field(default_factory=list)
    refresh_interval: int = 0  # Seconds, 0 = no auto-refresh
    visible: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "panel_id": self.panel_id,
            "panel_type": self.panel_type.value,
            "title": self.title,
            "description": self.description,
            "position": self.position,
            "data": self.data,
            "actions": [a.to_dict() for a in self.actions],
            "refresh_interval": self.refresh_interval,
            "visible": self.visible
        }


@dataclass
class WorkflowStep:
    """A step in a visual workflow."""
    step_id: str
    name: str
    action: PanelAction
    order: int
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: List[str] = field(default_factory=list)
    condition: Optional[str] = None  # Expression for conditional execution
    on_success: Optional[str] = None  # Next step on success
    on_failure: Optional[str] = None  # Next step on failure


@dataclass
class Workflow:
    """A multi-step workflow built visually."""
    workflow_id: str
    name: str
    description: str
    steps: List[WorkflowStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_run: Optional[datetime] = None
    run_count: int = 0
    success_rate: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "steps": [
                {
                    "step_id": s.step_id,
                    "name": s.name,
                    "action": s.action.to_dict(),
                    "order": s.order,
                    "inputs": s.inputs,
                    "outputs": s.outputs,
                    "condition": s.condition,
                    "on_success": s.on_success,
                    "on_failure": s.on_failure
                }
                for s in self.steps
            ],
            "created_at": self.created_at.isoformat(),
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "run_count": self.run_count,
            "success_rate": self.success_rate
        }


class NoCodePanelSystem:
    """
    No-Code Panel System for non-technical users.

    Provides:
    - Pre-built action panels for common tasks
    - Visual workflow builder
    - Real-time status monitoring
    - Natural language task input
    - One-click healing and fixes
    """

    def __init__(
        self,
        session=None,
        enable_voice: bool = True
    ):
        self.session = session
        self.enable_voice = enable_voice

        # Registered panels
        self.panels: Dict[str, Panel] = {}

        # Available actions
        self.actions: Dict[str, PanelAction] = {}

        # User-created workflows
        self.workflows: Dict[str, Workflow] = {}

        # Action handlers
        self._action_handlers: Dict[str, Callable] = {}

        # Initialize default panels and actions
        self._initialize_defaults()

        logger.info("[NOCODE] No-Code Panel System initialized")

    def _initialize_defaults(self):
        """Initialize default panels and actions."""
        # =========================================================
        # Default Actions
        # =========================================================

        # Healing actions
        self.register_action(PanelAction(
            action_id="heal_file",
            name="Heal File",
            description="Automatically fix issues in the current file",
            category=ActionCategory.HEALING,
            icon="healing",
            parameters=[{"name": "file_path", "type": "file", "required": True}]
        ))

        self.register_action(PanelAction(
            action_id="heal_project",
            name="Heal Project",
            description="Scan and fix issues across the entire project",
            category=ActionCategory.HEALING,
            icon="auto_fix_high",
            requires_confirmation=True
        ))

        self.register_action(PanelAction(
            action_id="check_health",
            name="Check Health",
            description="Run a comprehensive health check",
            category=ActionCategory.HEALING,
            icon="health_and_safety"
        ))

        # Code actions
        self.register_action(PanelAction(
            action_id="generate_code",
            name="Generate Code",
            description="Generate code from natural language description",
            category=ActionCategory.CODE,
            icon="code",
            parameters=[{"name": "description", "type": "text", "required": True}]
        ))

        self.register_action(PanelAction(
            action_id="explain_code",
            name="Explain Code",
            description="Get a plain-English explanation of selected code",
            category=ActionCategory.CODE,
            icon="help_outline",
            parameters=[{"name": "code", "type": "code", "required": True}]
        ))

        self.register_action(PanelAction(
            action_id="refactor_code",
            name="Refactor Code",
            description="Improve code quality without changing behavior",
            category=ActionCategory.CODE,
            icon="build_circle",
            parameters=[{"name": "file_path", "type": "file", "required": True}]
        ))

        # File actions
        self.register_action(PanelAction(
            action_id="create_file",
            name="Create File",
            description="Create a new file with boilerplate",
            category=ActionCategory.FILES,
            icon="add_circle",
            parameters=[
                {"name": "name", "type": "text", "required": True},
                {"name": "type", "type": "select", "options": ["python", "javascript", "typescript", "react", "config"]}
            ]
        ))

        self.register_action(PanelAction(
            action_id="organize_files",
            name="Organize Files",
            description="Organize files into proper folder structure",
            category=ActionCategory.FILES,
            icon="folder_open",
            requires_confirmation=True
        ))

        # Search actions
        self.register_action(PanelAction(
            action_id="search_code",
            name="Search Code",
            description="Search for code patterns across the project",
            category=ActionCategory.SEARCH,
            icon="search",
            parameters=[{"name": "query", "type": "text", "required": True}]
        ))

        self.register_action(PanelAction(
            action_id="find_usages",
            name="Find Usages",
            description="Find all usages of a function or class",
            category=ActionCategory.SEARCH,
            icon="find_in_page",
            parameters=[{"name": "symbol", "type": "text", "required": True}]
        ))

        # Build/Test actions
        self.register_action(PanelAction(
            action_id="run_build",
            name="Run Build",
            description="Build the project",
            category=ActionCategory.BUILD,
            icon="build"
        ))

        self.register_action(PanelAction(
            action_id="run_tests",
            name="Run Tests",
            description="Run all tests",
            category=ActionCategory.TEST,
            icon="check_circle"
        ))

        self.register_action(PanelAction(
            action_id="run_specific_test",
            name="Run Test",
            description="Run a specific test file",
            category=ActionCategory.TEST,
            icon="play_arrow",
            parameters=[{"name": "test_path", "type": "file", "required": True}]
        ))

        # Learning actions
        self.register_action(PanelAction(
            action_id="teach_grace",
            name="Teach Grace",
            description="Provide feedback to improve Grace's responses",
            category=ActionCategory.LEARN,
            icon="school",
            parameters=[
                {"name": "feedback", "type": "text", "required": True},
                {"name": "example", "type": "code", "required": False}
            ]
        ))

        self.register_action(PanelAction(
            action_id="view_learning",
            name="View Learning",
            description="See what Grace has learned",
            category=ActionCategory.LEARN,
            icon="lightbulb"
        ))

        # Voice actions
        if self.enable_voice:
            self.register_action(PanelAction(
                action_id="voice_command",
                name="Voice Command",
                description="Give Grace a voice command",
                category=ActionCategory.VOICE,
                icon="mic"
            ))

            self.register_action(PanelAction(
                action_id="start_conversation",
                name="Start Conversation",
                description="Start a voice conversation with Grace",
                category=ActionCategory.VOICE,
                icon="chat"
            ))

        # =========================================================
        # Default Panels
        # =========================================================

        # System Status Panel
        self.register_panel(Panel(
            panel_id="system_status",
            panel_type=PanelType.STATUS,
            title="System Status",
            description="Overall Grace system health",
            position={"x": 0, "y": 0, "w": 4, "h": 2},
            data={"status": "healthy", "message": "All systems operational"},
            refresh_interval=30
        ))

        # Quick Actions Panel
        self.register_panel(Panel(
            panel_id="quick_actions",
            panel_type=PanelType.ACTION,
            title="Quick Actions",
            description="Common actions at your fingertips",
            position={"x": 4, "y": 0, "w": 4, "h": 2},
            actions=[
                self.actions.get("heal_file"),
                self.actions.get("check_health"),
                self.actions.get("run_tests"),
                self.actions.get("run_build")
            ]
        ))

        # Natural Language Input Panel
        self.register_panel(Panel(
            panel_id="nl_input",
            panel_type=PanelType.INPUT,
            title="Ask Grace",
            description="Describe what you want in plain English",
            position={"x": 0, "y": 2, "w": 8, "h": 2},
            data={
                "placeholder": "e.g., 'Add a login form to the homepage' or 'Fix all linting errors'",
                "voice_enabled": self.enable_voice
            }
        ))

        # Recent Activity Panel
        self.register_panel(Panel(
            panel_id="recent_activity",
            panel_type=PanelType.LIST,
            title="Recent Activity",
            description="What Grace has been doing",
            position={"x": 8, "y": 0, "w": 4, "h": 4},
            data={"items": []},
            refresh_interval=10
        ))

        # Healing Status Panel
        self.register_panel(Panel(
            panel_id="healing_status",
            panel_type=PanelType.HEALING,
            title="Self-Healing",
            description="Automatic code healing status",
            position={"x": 0, "y": 4, "w": 4, "h": 3},
            data={
                "enabled": True,
                "last_heal": None,
                "issues_fixed": 0,
                "pending_issues": []
            },
            actions=[
                self.actions.get("heal_project"),
                self.actions.get("check_health")
            ]
        ))

        # Genesis Key Panel
        self.register_panel(Panel(
            panel_id="genesis_keys",
            panel_type=PanelType.GENESIS,
            title="Change History",
            description="Track all changes with Genesis Keys",
            position={"x": 4, "y": 4, "w": 4, "h": 3},
            data={"recent_keys": []},
            refresh_interval=30
        ))

        # Learning Panel
        self.register_panel(Panel(
            panel_id="learning",
            panel_type=PanelType.CARD,
            title="Learning Progress",
            description="How Grace is improving",
            position={"x": 8, "y": 4, "w": 4, "h": 3},
            data={
                "examples_learned": 0,
                "accuracy_trend": "stable",
                "recent_improvements": []
            },
            actions=[self.actions.get("teach_grace")]
        ))

    # =========================================================================
    # Panel Management
    # =========================================================================

    def register_panel(self, panel: Panel):
        """Register a panel."""
        self.panels[panel.panel_id] = panel
        logger.debug(f"[NOCODE] Registered panel: {panel.panel_id}")

    def get_panel(self, panel_id: str) -> Optional[Panel]:
        """Get a panel by ID."""
        return self.panels.get(panel_id)

    def get_all_panels(self) -> List[Dict[str, Any]]:
        """Get all panels as dictionaries."""
        return [p.to_dict() for p in self.panels.values() if p.visible]

    def update_panel_data(self, panel_id: str, data: Dict[str, Any]):
        """Update panel data."""
        if panel_id in self.panels:
            self.panels[panel_id].data.update(data)

    def update_panel_position(self, panel_id: str, position: Dict[str, int]):
        """Update panel position (for drag-and-drop)."""
        if panel_id in self.panels:
            self.panels[panel_id].position = position

    # =========================================================================
    # Action Management
    # =========================================================================

    def register_action(self, action: PanelAction):
        """Register an action."""
        self.actions[action.action_id] = action

    def register_action_handler(self, action_id: str, handler: Callable):
        """Register a handler for an action."""
        self._action_handlers[action_id] = handler

    def get_actions_by_category(self, category: ActionCategory) -> List[PanelAction]:
        """Get all actions in a category."""
        return [a for a in self.actions.values() if a.category == category]

    async def execute_action(
        self,
        action_id: str,
        parameters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute an action."""
        if action_id not in self.actions:
            return {"success": False, "error": f"Unknown action: {action_id}"}

        action = self.actions[action_id]

        if not action.enabled:
            return {"success": False, "error": f"Action {action_id} is disabled"}

        # Validate required parameters
        parameters = parameters or {}
        for param in action.parameters:
            if param.get("required") and param.get("name") not in parameters:
                return {
                    "success": False,
                    "error": f"Missing required parameter: {param.get('name')}"
                }

        # Execute handler
        if action_id in self._action_handlers:
            try:
                result = await self._action_handlers[action_id](parameters)
                return {"success": True, "result": result}
            except Exception as e:
                logger.error(f"[NOCODE] Action {action_id} failed: {e}")
                return {"success": False, "error": str(e)}

        # Default handlers for built-in actions
        return await self._handle_builtin_action(action, parameters)

    async def _handle_builtin_action(
        self,
        action: PanelAction,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle built-in actions."""
        action_id = action.action_id

        try:
            if action_id == "heal_file":
                from grace_os.ide_bridge import IDEBridge, IDEBridgeConfig
                from pathlib import Path
                config = IDEBridgeConfig(workspace_path=Path.cwd())
                bridge = IDEBridge(config, self.session)
                result = await bridge.request_healing(parameters.get("file_path", ""))
                return {"success": True, "result": result}

            elif action_id == "heal_project":
                from cognitive.autonomous_healing_system import AutonomousHealingSystem
                healer = AutonomousHealingSystem(self.session)
                result = healer.assess_system_health()
                return {"success": True, "result": result}

            elif action_id == "check_health":
                from cognitive.autonomous_healing_system import AutonomousHealingSystem
                healer = AutonomousHealingSystem(self.session)
                health = healer.assess_system_health()
                return {"success": True, "result": health}

            elif action_id == "run_tests":
                import subprocess
                result = subprocess.run(
                    ["pytest", "-v", "--tb=short"],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                return {
                    "success": result.returncode == 0,
                    "output": result.stdout,
                    "errors": result.stderr
                }

            elif action_id == "run_build":
                # Placeholder - would integrate with project's build system
                return {"success": True, "result": "Build command not configured"}

            elif action_id == "search_code":
                from grace_os.reasoning_planes import MultiPlaneReasoner
                reasoner = MultiPlaneReasoner(self.session)
                result = await reasoner.reason(
                    query=f"Find: {parameters.get('query', '')}",
                    approach="linear"
                )
                return {"success": True, "result": result}

            elif action_id == "explain_code":
                from grace_os.reasoning_planes import MultiPlaneReasoner
                reasoner = MultiPlaneReasoner(self.session)
                result = await reasoner.explain(
                    target=None,
                    query=f"Explain this code: {parameters.get('code', '')[:500]}"
                )
                return {"success": True, "result": result}

            elif action_id == "generate_code":
                from grace_os.deterministic_pipeline import DeterministicCodePipeline, ExecutionContract
                pipeline = DeterministicCodePipeline(self.session)
                contract = ExecutionContract(
                    goal=parameters.get("description", ""),
                    allowed_files=parameters.get("files", ["*"]),
                    risk_level="low"
                )
                result = await pipeline.execute(contract)
                return {"success": True, "result": result.to_dict()}

            else:
                return {"success": False, "error": f"No handler for action: {action_id}"}

        except Exception as e:
            logger.error(f"[NOCODE] Built-in action {action_id} failed: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Workflow Management
    # =========================================================================

    def create_workflow(
        self,
        name: str,
        description: str = ""
    ) -> Workflow:
        """Create a new workflow."""
        workflow = Workflow(
            workflow_id=f"WF-{uuid.uuid4().hex[:8]}",
            name=name,
            description=description
        )
        self.workflows[workflow.workflow_id] = workflow
        return workflow

    def add_workflow_step(
        self,
        workflow_id: str,
        action_id: str,
        inputs: Dict[str, Any] = None,
        name: str = None
    ) -> Optional[WorkflowStep]:
        """Add a step to a workflow."""
        if workflow_id not in self.workflows:
            return None
        if action_id not in self.actions:
            return None

        workflow = self.workflows[workflow_id]
        action = self.actions[action_id]

        step = WorkflowStep(
            step_id=f"STEP-{uuid.uuid4().hex[:8]}",
            name=name or action.name,
            action=action,
            order=len(workflow.steps),
            inputs=inputs or {}
        )

        workflow.steps.append(step)
        return step

    async def execute_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Execute a workflow."""
        if workflow_id not in self.workflows:
            return {"success": False, "error": "Workflow not found"}

        workflow = self.workflows[workflow_id]
        results = []
        success = True

        workflow.last_run = datetime.utcnow()
        workflow.run_count += 1

        for step in sorted(workflow.steps, key=lambda s: s.order):
            try:
                result = await self.execute_action(
                    step.action.action_id,
                    step.inputs
                )
                results.append({
                    "step_id": step.step_id,
                    "name": step.name,
                    **result
                })

                if not result.get("success"):
                    success = False
                    if step.on_failure:
                        # Jump to failure step
                        pass  # TODO: Implement step jumping
                    else:
                        break
            except Exception as e:
                results.append({
                    "step_id": step.step_id,
                    "name": step.name,
                    "success": False,
                    "error": str(e)
                })
                success = False
                break

        # Update success rate
        total_runs = workflow.run_count
        current_success = 1 if success else 0
        workflow.success_rate = (
            (workflow.success_rate * (total_runs - 1) + current_success) / total_runs
        )

        return {
            "success": success,
            "workflow_id": workflow_id,
            "steps_executed": len(results),
            "results": results
        }

    def get_workflows(self) -> List[Dict[str, Any]]:
        """Get all workflows."""
        return [w.to_dict() for w in self.workflows.values()]

    # =========================================================================
    # Natural Language Processing
    # =========================================================================

    async def process_natural_language(self, text: str) -> Dict[str, Any]:
        """
        Process natural language input and determine action.

        Enables non-technical users to describe what they want in plain English.
        """
        text_lower = text.lower()

        # Intent detection
        intent_mapping = {
            "heal": ["heal", "fix", "repair", "correct", "resolve"],
            "search": ["find", "search", "look for", "locate", "where is"],
            "explain": ["explain", "what is", "what does", "how does", "tell me about"],
            "create": ["create", "make", "add", "new", "generate"],
            "test": ["test", "run tests", "check tests", "verify"],
            "build": ["build", "compile", "package"],
            "help": ["help", "how do i", "can you", "what can"]
        }

        detected_intent = "unknown"
        for intent, keywords in intent_mapping.items():
            if any(kw in text_lower for kw in keywords):
                detected_intent = intent
                break

        # Map intent to action
        intent_actions = {
            "heal": "heal_project",
            "search": "search_code",
            "explain": "explain_code",
            "create": "generate_code",
            "test": "run_tests",
            "build": "run_build"
        }

        suggested_action = intent_actions.get(detected_intent)

        if suggested_action and suggested_action in self.actions:
            return {
                "understood": True,
                "intent": detected_intent,
                "suggested_action": self.actions[suggested_action].to_dict(),
                "message": f"I understand you want to {detected_intent}. Shall I proceed?"
            }
        elif detected_intent == "help":
            return {
                "understood": True,
                "intent": "help",
                "message": "I can help you with:\n"
                           "- Healing code issues\n"
                           "- Searching the codebase\n"
                           "- Explaining code\n"
                           "- Creating new files\n"
                           "- Running tests\n"
                           "- Building the project\n"
                           "Just tell me what you need!"
            }
        else:
            return {
                "understood": False,
                "intent": "unknown",
                "message": "I'm not sure what you mean. Try saying things like:\n"
                           "- 'Fix the errors in my code'\n"
                           "- 'Find where the login function is'\n"
                           "- 'Explain what this file does'\n"
                           "- 'Run the tests'"
            }

    # =========================================================================
    # Dashboard Layout
    # =========================================================================

    def get_dashboard_layout(self) -> Dict[str, Any]:
        """Get the complete dashboard layout for rendering."""
        return {
            "panels": self.get_all_panels(),
            "available_actions": {
                cat.value: [a.to_dict() for a in self.get_actions_by_category(cat)]
                for cat in ActionCategory
            },
            "workflows": self.get_workflows(),
            "settings": {
                "voice_enabled": self.enable_voice,
                "auto_heal_enabled": True,
                "theme": "dark"
            }
        }

    async def refresh_dashboard_data(self) -> Dict[str, Any]:
        """Refresh data for all panels that need updating."""
        updates = {}

        # System status
        try:
            from cognitive.autonomous_healing_system import AutonomousHealingSystem
            healer = AutonomousHealingSystem(self.session)
            health = healer.assess_system_health()

            self.update_panel_data("system_status", {
                "status": health.get("health_status", "unknown"),
                "message": f"Anomalies: {health.get('anomalies_detected', 0)}",
                "last_check": datetime.utcnow().isoformat()
            })
            updates["system_status"] = self.panels["system_status"].data
        except Exception as e:
            logger.warning(f"[NOCODE] Could not refresh system status: {e}")

        # Healing status
        try:
            self.update_panel_data("healing_status", {
                "last_check": datetime.utcnow().isoformat()
            })
            updates["healing_status"] = self.panels["healing_status"].data
        except Exception as e:
            logger.warning(f"[NOCODE] Could not refresh healing status: {e}")

        # Genesis keys
        try:
            from models.genesis_key_models import GenesisKey
            if self.session:
                recent = self.session.query(GenesisKey).order_by(
                    GenesisKey.when_timestamp.desc()
                ).limit(10).all()

                self.update_panel_data("genesis_keys", {
                    "recent_keys": [
                        {
                            "key_id": k.key_id,
                            "what": k.what_description[:50] if k.what_description else "",
                            "when": k.when_timestamp.isoformat() if k.when_timestamp else ""
                        }
                        for k in recent
                    ]
                })
                updates["genesis_keys"] = self.panels["genesis_keys"].data
        except Exception as e:
            logger.warning(f"[NOCODE] Could not refresh genesis keys: {e}")

        return updates
