"""
Multi-LLM Coding Agents — Kimi & Opus as autonomous coding agents.

Each LLM is wrapped in GovernanceAwareLLM, so all governance rules
and persona are injected. Actions tracked via Genesis Keys and
published to Spindle event bus.

Architecture:
    CodingAgentPool
    ├── KimiCodingAgent   — fast analysis, pattern recognition, imports/wiring
    ├── OpusCodingAgent   — deep reasoning, complex refactoring, architecture
    └── OllamaCodingAgent — local fallback for simple fixes

Each agent:
    - Reads code files
    - Analyzes errors/issues
    - Generates patches (unified diff format)
    - Applies fixes through safety pipeline (AST check + security scan)
    - Reports results to Spindle event bus + Genesis Keys
    - Follows ALL governance rules via GovernanceAwareLLM wrapper
"""

import logging
import threading
import time
import ast
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Project root for safe file access
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ══════════════════════════════════════════════════════════════════════════
# Bi-Directional Agent Communication Channel
# ══════════════════════════════════════════════════════════════════════════

class AgentChannel:
    """
    Shared communication channel between coding agents.
    
    All agents read/write to the same channel so they can:
    - See each other's analysis and findings
    - Build on each other's patches  
    - Avoid duplicating work
    - Reach consensus on fixes
    
    Messages published to Spindle event bus for system-wide visibility.
    """

    def __init__(self):
        self._messages: list = []  # [{agent, type, content, ts}]
        self._lock = threading.Lock()

    def post(self, agent: str, msg_type: str, content: str, data: dict = None):
        """Post a message to the channel — all agents can see it."""
        msg = {
            "agent": agent,
            "type": msg_type,  # analysis, patch, question, review, agree, disagree
            "content": content[:2000],
            "data": data or {},
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        with self._lock:
            self._messages.append(msg)
            # Keep last 100 messages per session
            if len(self._messages) > 100:
                self._messages = self._messages[-100:]
        
        # Broadcast to Spindle so all system components see agent comms
        _emit("coding_agent.channel.message", msg)

    def get_history(self, exclude_agent: str = None, limit: int = 20) -> list:
        """Read recent messages — optionally exclude own messages to see peers."""
        with self._lock:
            msgs = list(self._messages)
        if exclude_agent:
            msgs = [m for m in msgs if m["agent"] != exclude_agent]
        return msgs[-limit:]

    def get_peer_analysis(self, exclude_agent: str) -> str:
        """Get all peer analysis as context string for an agent."""
        peers = self.get_history(exclude_agent=exclude_agent, limit=10)
        if not peers:
            return ""
        lines = []
        for m in peers:
            lines.append(f"[{m['agent']}] ({m['type']}): {m['content'][:300]}")
        return "\n".join(lines)

    def clear(self):
        with self._lock:
            self._messages.clear()


# ══════════════════════════════════════════════════════════════════════════
# Group Genesis Key Ledger — tracks collective accomplishments
# ══════════════════════════════════════════════════════════════════════════

class GroupGenesisLedger:
    """
    Creates a GROUP Genesis Key per coding session and links all individual
    agent keys under it. This gives a single view of what Kimi + Opus + Ollama
    accomplished together.
    
    Structure:
        GK-GROUP-xxxx  (parent — session key)
        ├── GK-kimi-analysis-1  (child)
        ├── GK-opus-analysis-1  (child)
        ├── GK-kimi-fix-1       (child)
        └── GK-opus-review-1    (child)
    """

    def __init__(self):
        self._session_key: Optional[str] = None
        self._child_keys: list = []  # [{agent, action, key_id, ts}]
        self._lock = threading.Lock()
        self._summary: dict = {"total_actions": 0, "by_agent": {}, "files_touched": set()}

    def start_session(self, task_description: str) -> str:
        """Create the parent group Genesis Key for this coding session."""
        try:
            from api._genesis_tracker import track
            self._session_key = track(
                key_type="coding_agent_action",
                what=f"GROUP SESSION: {task_description[:100]}",
                who="coding_agent_pool",
                tags=["group_session", "multi_llm", "kimi", "opus"],
            )
        except Exception:
            self._session_key = f"GK-GROUP-{hashlib.md5(task_description.encode()).hexdigest()[:8]}"
        
        _emit("coding_agent.group_session.started", {
            "session_key": self._session_key,
            "task": task_description[:100],
        })
        
        return self._session_key or ""

    def record_action(self, agent: str, action: str, file_path: str = "",
                      confidence: float = 0.0, details: str = "") -> Optional[str]:
        """Record an individual agent action under the group key."""
        child_key = None
        try:
            from api._genesis_tracker import track
            child_key = track(
                key_type="coding_agent_action",
                what=f"{agent}: {action[:80]}",
                who=f"coding_agent_{agent}",
                where=file_path,
                parent_key_id=self._session_key,
                tags=["group_member", agent, action.split(":")[0] if ":" in action else "action"],
                context={"confidence": confidence, "details": details[:200]},
            )
        except Exception:
            pass

        entry = {
            "agent": agent, "action": action[:100],
            "key_id": child_key, "file": file_path,
            "confidence": confidence,
            "ts": datetime.now(timezone.utc).isoformat(),
        }

        with self._lock:
            self._child_keys.append(entry)
            self._summary["total_actions"] += 1
            self._summary["by_agent"].setdefault(agent, 0)
            self._summary["by_agent"][agent] += 1
            if file_path:
                self._summary["files_touched"].add(file_path)

        return child_key

    def close_session(self, status: str = "completed") -> dict:
        """Close the group session and create a summary Genesis Key."""
        summary = self.get_summary()
        try:
            from api._genesis_tracker import track
            track(
                key_type="coding_agent_action",
                what=f"GROUP SESSION {status}: {summary['total_actions']} actions by {len(summary['by_agent'])} agents",
                who="coding_agent_pool",
                parent_key_id=self._session_key,
                tags=["group_session_summary", status],
                context=summary,
            )
        except Exception:
            pass
        
        _emit("coding_agent.group_session.closed", {
            "session_key": self._session_key,
            "status": status,
            "summary": summary,
        })
        
        return summary

    def get_summary(self) -> dict:
        with self._lock:
            return {
                "session_key": self._session_key,
                "total_actions": self._summary["total_actions"],
                "by_agent": dict(self._summary["by_agent"]),
                "files_touched": list(self._summary["files_touched"]),
                "child_keys": len(self._child_keys),
                "actions": list(self._child_keys[-20:]),  # Last 20 actions
            }


@dataclass
class CodingTask:
    """A coding task assigned to an LLM agent."""
    id: str
    task_type: str  # analyze, fix, refactor, wire, test
    file_path: str
    description: str
    error: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    priority: str = "medium"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class CodingResult:
    """Result from an LLM coding agent."""
    task_id: str
    agent: str  # kimi, opus, ollama
    status: str  # completed, failed, rejected
    analysis: str = ""
    patch: str = ""
    files_modified: List[str] = field(default_factory=list)
    confidence: float = 0.0
    duration_s: float = 0.0
    error: str = ""
    genesis_key_id: str = ""
    snapshot_id: str = ""


def _emit(topic: str, data: dict):
    try:
        from cognitive.event_bus import publish_async
        publish_async(topic, data, source="coding_agents")
    except Exception:
        pass
    # Persist to Spindle event store so events survive process restarts
    try:
        from cognitive.spindle_event_store import get_event_store
        store = get_event_store()
        store.append_async(
            topic=topic,
            source_type="coding_agent",
            payload=data,
            source="coding_agents",
        )
    except Exception:
        pass


def _track(what: str, tags: list = None) -> Optional[str]:
    try:
        from api._genesis_tracker import track
        return track(key_type="coding_agent_action", what=what,
                     who="multi_llm_agent", tags=["coding_agent"] + (tags or []))
    except Exception:
        return None


def _record_agent_kpi(agent: str, task_type: str, passed: bool, confidence: float = 0):
    """Record KPI for coding agent work."""
    try:
        from core.governance_engine import record_kpi
        record_kpi("coding_agent", f"{agent}.{task_type}", passed=passed)
        record_kpi("coding_agent", f"{agent}.confidence", passed=confidence >= 0.6)
        record_kpi("coding_agent", "overall", passed=passed)
    except Exception:
        pass


def _recall_similar(task_desc: str, file_path: str = "") -> str:
    """Recall similar past fixes from episodic + learning memory for agent context."""
    memories = []
    # Episodic memory — concrete past experiences
    try:
        from database.session import session_scope
        from cognitive.episodic_memory import EpisodicBuffer
        with session_scope() as s:
            buf = EpisodicBuffer(s)
            similar = buf.recall_similar(task_desc[:100], k=3, min_trust=0.3)
            for ep in similar[:2]:
                outcome = ep.outcome if isinstance(ep.outcome, str) else str(ep.outcome)[:100]
                memories.append(f"[PAST] {ep.problem[:80]} → {outcome}")
    except Exception:
        pass
    # Unified memory — broader search
    try:
        from cognitive.unified_memory import get_unified_memory
        mem = get_unified_memory()
        hits = mem.search_all(f"{file_path} {task_desc[:50]}")
        for h in (hits.get("results", []) or [])[:2]:
            memories.append(f"[MEMORY] {str(h)[:100]}")
    except Exception:
        pass
    return "\n".join(memories) if memories else ""


def _store_outcome(task: 'CodingTask', result: 'CodingResult'):
    """Store coding agent outcome in episodic memory for future learning."""
    try:
        from database.session import session_scope
        from cognitive.episodic_memory import EpisodicBuffer
        with session_scope() as s:
            buf = EpisodicBuffer(s)
            buf.record_episode(
                problem=f"Coding fix: {task.description[:200]}",
                action={
                    "agent": result.agent,
                    "task_type": task.task_type,
                    "file": task.file_path,
                    "has_patch": bool(result.patch),
                    "patch_len": len(result.patch) if result.patch else 0,
                },
                outcome={
                    "status": result.status,
                    "confidence": result.confidence,
                },
                predicted_outcome={"status": "completed"},
                trust_score=result.confidence,
                source=f"coding_agent.{result.agent}",
                genesis_key_id=result.genesis_key_id,
            )
    except Exception:
        pass


def _snapshot_before_apply(file_path: str) -> Optional[str]:
    """Take a safety snapshot before applying agent code. Returns snapshot_id."""
    if not file_path:
        return None
    try:
        from core.safety import snapshot_state
        return snapshot_state(f"agent_fix:{file_path}")
    except Exception:
        pass
    # Fallback: Genesis version snapshot
    try:
        from genesis.symbiotic_version_control import get_symbiotic_version_control
        svc = get_symbiotic_version_control()
        result = svc.track_file_change(
            file_path=file_path,
            user_id="coding_agent.pre_apply",
            change_description="Pre-apply snapshot for rollback",
            operation_type="snapshot",
        )
        return result.get("version_key_id")
    except Exception:
        return None


def _safe_read(file_path: str) -> Optional[str]:
    """Read a file safely — only within project root."""
    try:
        p = (_PROJECT_ROOT / file_path).resolve()
        if not str(p).startswith(str(_PROJECT_ROOT)):
            return None
        if p.exists() and p.is_file():
            return p.read_text(errors="ignore")
    except Exception:
        pass
    return None


def _validate_python(code: str) -> tuple:
    """Validate Python syntax. Returns (ok, error_msg)."""
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"


class LLMCodingAgent:
    """Base class for an LLM coding agent with bi-directional comms."""

    def __init__(self, provider: str, name: str):
        self.provider = provider
        self.name = name
        self._lock = threading.Lock()
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.total_time = 0.0
        # Set by pool at dispatch time
        self.channel: Optional[AgentChannel] = None
        self.ledger: Optional[GroupGenesisLedger] = None

    def _get_client(self):
        """Get governance-wrapped LLM client for this provider."""
        from llm_orchestrator.factory import get_llm_client
        return get_llm_client(provider=self.provider)

    def analyze(self, task: CodingTask) -> CodingResult:
        """Analyze code and suggest fixes."""
        start = time.time()
        result = CodingResult(task_id=task.id, agent=self.name, status="running")

        # Read the file
        code = _safe_read(task.file_path) if task.file_path else None
        if code is None and task.file_path:
            result.status = "failed"
            result.error = f"Cannot read file: {task.file_path}"
            return result

        try:
            client = self._get_client()

            # Inject peer context from channel (bi-directional comms)
            peer_ctx = ""
            if self.channel:
                peer_ctx = self.channel.get_peer_analysis(exclude_agent=self.name)

            # Build analysis prompt with peer context
            prompt = self._build_analysis_prompt(task, code, peer_context=peer_ctx)

            response = client.generate(
                prompt=prompt,
                system_prompt=(
                    f"You are {self.name}, a coding agent for the Grace AI system. "
                    f"Analyze code and provide actionable fixes. "
                    f"Always include the exact file path and line numbers. "
                    f"If you generate code, ensure it is syntactically valid Python."
                ),
                temperature=0.2,
                max_tokens=2000,
            )

            result.analysis = response if isinstance(response, str) else str(response)
            result.status = "completed"
            result.confidence = 0.8

            # Try to extract a patch if the response contains code
            result.patch = self._extract_patch(result.analysis)

            # Post to channel so other agents see our analysis (bi-directional)
            if self.channel:
                self.channel.post(self.name, "analysis", result.analysis[:500],
                                  {"confidence": result.confidence, "file": task.file_path})

        except Exception as e:
            result.status = "failed"
            result.error = str(e)[:300]
            logger.warning(f"[CODING-AGENT-{self.name}] Analysis failed: {e}")

        result.duration_s = round(time.time() - start, 2)

        with self._lock:
            if result.status == "completed":
                self.tasks_completed += 1
            else:
                self.tasks_failed += 1
            self.total_time += result.duration_s

        # Track via Genesis (individual + group ledger)
        gk = _track(f"{self.name} analyzed: {task.file_path or task.description[:50]}",
                     tags=[self.name, task.task_type])
        result.genesis_key_id = gk or ""
        if self.ledger:
            self.ledger.record_action(self.name, f"analyze: {task.file_path or task.description[:40]}",
                                      file_path=task.file_path, confidence=result.confidence)

        # Emit to Spindle
        _emit(f"coding_agent.{self.name}.completed", {
            "task_id": task.id, "status": result.status,
            "file": task.file_path, "confidence": result.confidence,
        })

        return result

    def fix(self, task: CodingTask) -> CodingResult:
        """Generate and validate a fix for the given issue."""
        start = time.time()
        result = CodingResult(task_id=task.id, agent=self.name, status="running")

        code = _safe_read(task.file_path) if task.file_path else None

        try:
            client = self._get_client()

            # Get peer context for smarter fixes
            peer_ctx = ""
            if self.channel:
                peer_ctx = self.channel.get_peer_analysis(exclude_agent=self.name)

            prompt = self._build_fix_prompt(task, code, peer_context=peer_ctx)

            response = client.generate(
                prompt=prompt,
                system_prompt=(
                    f"You are {self.name}, a coding agent for Grace. "
                    f"Generate a COMPLETE, WORKING replacement for the broken code. "
                    f"Return ONLY the fixed code between ```python and ``` markers. "
                    f"The code MUST be syntactically valid Python."
                ),
                temperature=0.1,
                max_tokens=3000,
            )

            # Extract code from response
            fixed_code = self._extract_code_block(
                response if isinstance(response, str) else str(response)
            )

            if fixed_code:
                # Validate syntax
                ok, err = _validate_python(fixed_code)
                if ok:
                    result.patch = fixed_code
                    result.status = "completed"
                    result.confidence = 0.85
                    result.files_modified = [task.file_path] if task.file_path else []
                else:
                    result.status = "failed"
                    result.error = f"Generated code has syntax error: {err}"
                    result.confidence = 0.2
            else:
                result.analysis = response if isinstance(response, str) else str(response)
                result.status = "completed"
                result.confidence = 0.5  # Analysis only, no code generated

            # Post fix result to channel (bi-directional)
            if self.channel:
                if result.patch:
                    self.channel.post(self.name, "patch",
                                      f"Generated fix for {task.file_path}: {len(result.patch)} chars",
                                      {"confidence": result.confidence, "file": task.file_path})
                else:
                    self.channel.post(self.name, "analysis", result.analysis[:300],
                                      {"file": task.file_path})

        except Exception as e:
            result.status = "failed"
            result.error = str(e)[:300]

        result.duration_s = round(time.time() - start, 2)

        with self._lock:
            if result.status == "completed":
                self.tasks_completed += 1
            else:
                self.tasks_failed += 1
            self.total_time += result.duration_s

        gk = _track(f"{self.name} fix: {task.file_path or task.description[:50]}",
                     tags=[self.name, "fix"])
        result.genesis_key_id = gk or ""
        if self.ledger:
            self.ledger.record_action(self.name, f"fix: {task.file_path or task.description[:40]}",
                                      file_path=task.file_path, confidence=result.confidence,
                                      details=f"patch_size={len(result.patch)}")

        _emit(f"coding_agent.{self.name}.fix", {
            "task_id": task.id, "status": result.status,
            "file": task.file_path, "confidence": result.confidence,
            "has_patch": bool(result.patch),
        })

        return result

    def _build_analysis_prompt(self, task: CodingTask, code: str = None,
                                peer_context: str = "") -> str:
        parts = [f"Task: {task.description}"]
        if task.error:
            parts.append(f"Error: {task.error}")
        # Recall past experiences from memory
        memory_ctx = _recall_similar(task.description, task.file_path)
        if memory_ctx:
            parts.append(f"Past experience from memory:\n{memory_ctx}")
        if peer_context:
            parts.append(f"Other agents have already noted:\n{peer_context}")
        if code:
            # Show relevant portion (max 200 lines)
            lines = code.split("\n")
            if len(lines) > 200:
                parts.append(f"File: {task.file_path} ({len(lines)} lines, showing first 200)")
                parts.append("```python\n" + "\n".join(lines[:200]) + "\n```")
            else:
                parts.append(f"File: {task.file_path}")
                parts.append("```python\n" + code + "\n```")
        parts.append("Analyze this. What's wrong? How should it be fixed?")
        return "\n\n".join(parts)

    def _build_fix_prompt(self, task: CodingTask, code: str = None,
                           peer_context: str = "") -> str:
        parts = [f"Fix needed: {task.description}"]
        if task.error:
            parts.append(f"Error: {task.error}")
        # Recall past fixes from memory
        memory_ctx = _recall_similar(task.description, task.file_path)
        if memory_ctx:
            parts.append(f"Past fixes from memory (learn from these):\n{memory_ctx}")
        if peer_context:
            parts.append(f"Other agents have already found:\n{peer_context}")
        if code:
            lines = code.split("\n")
            parts.append(f"Current code ({task.file_path}, {len(lines)} lines):")
            parts.append("```python\n" + code[:8000] + "\n```")
        parts.append("Generate the fixed version. Return ONLY valid Python code.")
        return "\n\n".join(parts)

    def _extract_code_block(self, text: str) -> str:
        """Extract Python code from markdown code blocks."""
        import re
        # Try ```python ... ``` first
        match = re.search(r'```python\s*\n(.*?)```', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        # Try ``` ... ```
        match = re.search(r'```\s*\n(.*?)```', text, re.DOTALL)
        if match:
            code = match.group(1).strip()
            if "def " in code or "class " in code or "import " in code:
                return code
        return ""

    def _extract_patch(self, text: str) -> str:
        """Extract any code changes from analysis text."""
        import re
        match = re.search(r'```(?:python|diff)?\s*\n(.*?)```', text, re.DOTALL)
        return match.group(1).strip() if match else ""

    def get_stats(self) -> dict:
        with self._lock:
            return {
                "agent": self.name,
                "provider": self.provider,
                "completed": self.tasks_completed,
                "failed": self.tasks_failed,
                "total_time_s": round(self.total_time, 1),
                "avg_time_s": round(self.total_time / max(1, self.tasks_completed + self.tasks_failed), 1),
            }


class KimiCodingAgent(LLMCodingAgent):
    """Kimi — fast analysis, pattern recognition, import/wiring fixes."""
    def __init__(self):
        super().__init__(provider="kimi", name="kimi")


class OpusCodingAgent(LLMCodingAgent):
    """Opus — deep reasoning, complex refactoring, architecture decisions."""
    def __init__(self):
        super().__init__(provider="opus", name="opus")


class OllamaCodingAgent(LLMCodingAgent):
    """Ollama — local fallback for simple fixes when cloud is unavailable."""
    def __init__(self):
        super().__init__(provider="ollama", name="ollama")


class QwenCodingAgent(LLMCodingAgent):
    """Qwen — local reasoning model, fast iteration, code review."""
    def __init__(self):
        super().__init__(provider="qwen", name="qwen")


# ══════════════════════════════════════════════════════════════════════════
# Coding Agent Pool — manages all LLM coding agents
# ══════════════════════════════════════════════════════════════════════════

class CodingAgentPool:
    """
    Pool of LLM coding agents that can work on code issues concurrently.
    Dispatches tasks to the best agent based on complexity and availability.
    All outputs go through governance + Spindle.
    """

    MAX_CONCURRENT_JOBS = 50

    def __init__(self):
        self.agents: Dict[str, LLMCodingAgent] = {}
        self._lock = threading.Lock()
        self._results: list = []
        self._pool = None
        self._job_semaphore = threading.Semaphore(self.MAX_CONCURRENT_JOBS)
        self._active_jobs = 0
        self.channel = AgentChannel()  # Shared comms channel
        self.ledger = GroupGenesisLedger()  # Group Genesis tracking

        # Initialize available agents based on configured API keys
        self._init_agents()
        
        logger.info(f"[CODING-AGENTS] Pool initialized with {len(self.agents)} agents: "
                     f"{list(self.agents.keys())}")

    def _init_agents(self):
        """Initialize agents based on available API keys."""
        try:
            from settings import settings
        except ImportError:
            settings = None

        # Always try to add agents — they use the fallback chain
        self.agents["kimi"] = KimiCodingAgent()
        self.agents["opus"] = OpusCodingAgent()
        self.agents["ollama"] = OllamaCodingAgent()
        self.agents["qwen"] = QwenCodingAgent()
        # Wire bi-directional channel + ledger into every agent
        for agent in self.agents.values():
            agent.channel = self.channel
            agent.ledger = self.ledger

    def dispatch(self, task: CodingTask, agent_name: str = None) -> CodingResult:
        """Dispatch a coding task to a specific agent or auto-select."""
        agent = self.agents.get(agent_name) if agent_name else self._select_best_agent(task)
        if not agent:
            return CodingResult(
                task_id=task.id, agent="none", status="failed",
                error="No coding agents available"
            )

        if not self._job_semaphore.acquire(timeout=5):
            return CodingResult(
                task_id=task.id, agent=agent.name, status="queued",
                error=f"Max {self.MAX_CONCURRENT_JOBS} concurrent jobs reached, try again shortly"
            )
        try:
            with self._lock:
                self._active_jobs += 1

            # Start group Genesis session if not already active
            if not self.ledger._session_key:
                self.ledger.start_session(task.description)

            _emit("coding_agent.dispatched", {
                "task_id": task.id, "agent": agent.name,
                "task_type": task.task_type, "file": task.file_path,
                "session_key": self.ledger._session_key,
                "active_jobs": self._active_jobs,
            })

            # Snapshot for rollback before any fix
            snapshot_id = None
            if task.task_type == "fix" and task.file_path:
                snapshot_id = _snapshot_before_apply(task.file_path)

            if task.task_type == "fix":
                result = agent.fix(task)
            else:
                result = agent.analyze(task)

            # Record KPI
            _record_agent_kpi(agent.name, task.task_type,
                              passed=result.status == "completed",
                              confidence=result.confidence)
            # Store outcome in episodic memory for future learning
            _store_outcome(task, result)
            # Attach snapshot for rollback
            if snapshot_id:
                result.snapshot_id = snapshot_id

            return result
        finally:
            with self._lock:
                self._active_jobs -= 1
            self._job_semaphore.release()

    def dispatch_parallel(self, task: CodingTask, agents: List[str] = None) -> List[CodingResult]:
        """
        Dispatch to multiple agents in parallel — consensus-based coding.
        Each agent independently analyzes/fixes, then results are compared.
        """
        import concurrent.futures

        target_agents = [self.agents[a] for a in (agents or list(self.agents.keys())) if a in self.agents]
        if not target_agents:
            return []

        # Start group Genesis session for parallel work
        self.ledger.start_session(task.description)
        self.channel.clear()  # Fresh channel for this session

        _emit("coding_agent.parallel_dispatch", {
            "task_id": task.id, "agents": [a.name for a in target_agents],
            "task_type": task.task_type,
            "group_key": self.ledger._session_key,
        })

        results = []

        def _guarded_run(agent, task):
            """Run agent work under the global job semaphore."""
            if not self._job_semaphore.acquire(timeout=30):
                return CodingResult(
                    task_id=task.id, agent=agent.name, status="queued",
                    error=f"Max {self.MAX_CONCURRENT_JOBS} concurrent jobs, skipped"
                )
            try:
                with self._lock:
                    self._active_jobs += 1
                if task.task_type == "fix":
                    return agent.fix(task)
                else:
                    return agent.analyze(task)
            finally:
                with self._lock:
                    self._active_jobs -= 1
                self._job_semaphore.release()

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(len(target_agents), self.MAX_CONCURRENT_JOBS),
            thread_name_prefix="coding-agent"
        ) as pool:
            futures = {}
            for agent in target_agents:
                futures[pool.submit(_guarded_run, agent, task)] = agent.name

            for future in concurrent.futures.as_completed(futures, timeout=120):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append(CodingResult(
                        task_id=task.id, agent=futures[future],
                        status="failed", error=str(e)[:200],
                    ))

        with self._lock:
            self._results.extend(results)
            # Keep last 100 results
            if len(self._results) > 100:
                self._results = self._results[-100:]

        # Report parallel results to Spindle + close group session
        session_summary = self.ledger.close_session(
            status="completed" if any(r.status == "completed" for r in results) else "failed"
        )
        _emit("coding_agent.parallel_complete", {
            "task_id": task.id,
            "agents": [r.agent for r in results],
            "statuses": [r.status for r in results],
            "best_confidence": max((r.confidence for r in results), default=0),
            "group_session": session_summary,
        })

        return results

    def _select_best_agent(self, task: CodingTask) -> Optional[LLMCodingAgent]:
        """Select the best agent based on task complexity."""
        desc = (task.description + " " + task.error).lower()

        # Complex tasks → Opus (deep reasoning)
        if any(k in desc for k in ("refactor", "architect", "redesign", "complex", "migration")):
            return self.agents.get("opus") or self.agents.get("kimi")

        # Import/wiring/quick fixes → Kimi (fast)
        if any(k in desc for k in ("import", "wire", "connect", "missing", "typo", "quick")):
            return self.agents.get("kimi") or self.agents.get("qwen")

        # Code review / test / analysis → Qwen (local, fast iteration)
        if any(k in desc for k in ("review", "test", "analyze", "lint", "style", "format")):
            return self.agents.get("qwen") or self.agents.get("kimi")

        # Default: Kimi for speed, fallback chain
        return self.agents.get("kimi") or self.agents.get("qwen") or self.agents.get("opus") or self.agents.get("ollama")

    def get_status(self) -> Dict[str, Any]:
        """Full pool status for frontend/Ops Console."""
        agents_status = {name: agent.get_stats() for name, agent in self.agents.items()}
        with self._lock:
            recent = list(self._results[-20:])
        return {
            "agents": agents_status,
            "total_agents": len(self.agents),
            "active_jobs": self._active_jobs,
            "max_concurrent_jobs": self.MAX_CONCURRENT_JOBS,
            "channel_messages": len(self.channel._messages),
            "group_session": self.ledger.get_summary(),
            "recent_results": [
                {"task_id": r.task_id, "agent": r.agent, "status": r.status,
                 "confidence": r.confidence, "duration": r.duration_s}
                for r in recent
            ],
        }

    def set_concurrency(self, max_jobs: int):
        """Dynamically adjust max concurrent jobs (1-50) based on system needs."""
        max_jobs = max(1, min(50, max_jobs))
        old = self.MAX_CONCURRENT_JOBS
        self.MAX_CONCURRENT_JOBS = max_jobs
        self._job_semaphore = threading.Semaphore(max_jobs)
        _emit("coding_agent.concurrency_changed", {
            "old": old, "new": max_jobs,
        })
        logger.info(f"[CODING-AGENTS] Concurrency changed: {old} -> {max_jobs}")


# ── Singleton ────────────────────────────────────────────────────────────

_pool: Optional[CodingAgentPool] = None
_pool_lock = threading.Lock()


def get_coding_agent_pool() -> CodingAgentPool:
    """Get the singleton coding agent pool."""
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = CodingAgentPool()
    return _pool
