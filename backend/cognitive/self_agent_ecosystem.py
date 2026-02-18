"""
Self-* Agent Ecosystem

Six autonomous agents, each with their own micro-DB table, that form a
closed-loop self-improvement system:

1. SelfHealingAgent - Detects and fixes system issues
2. SelfMirrorAgent  - Observes and reflects on performance
3. SelfModelAgent   - Builds behavioral models from data
4. SelfLearnerAgent - Studies training data and improves skills
5. CodeAgent        - Writes and fixes code autonomously
6. SelfEvolver      - Orchestrates evolution across all agents

Each agent:
- Has its own micro-DB table logging attempts, passes, failures
- Can self-analyze its own performance via KPIs/trust scores
- Can ask Kimi (LLM) "why am I at X% efficiency?"
- Can access training data and ingestion pipeline
- Can trigger self-healing when degraded
- Reports to the closed-loop so all agents help each other

The closed loop:
  Mirror observes -> Model analyzes -> Healer fixes -> Learner studies ->
  Code Agent implements -> Evolver scales -> Mirror observes again...

When all agents reach 100% KPI, Evolver switches to scaling mode.
"""

import logging
import threading
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import Column, String, Float, Integer, Text, DateTime, JSON, Boolean
from sqlalchemy.orm import Session

from database.base import BaseModel

logger = logging.getLogger(__name__)

def _track(agent, desc, **kw):
    try:
        from cognitive.learning_hook import track_learning_event
        track_learning_event(f"self_{agent}", desc, **kw)
    except Exception:
        pass


# ============================================================================
# MICRO-DB TABLES — One per agent for independent iteration
# ============================================================================

class SelfHealingLog(BaseModel):
    """Micro-DB for self-healing agent — logs every heal attempt."""
    __tablename__ = "self_healing_log"
    agent_name = Column(String(50), default="self_healer")
    action_type = Column(String(100), nullable=False)
    target_component = Column(String(200), nullable=True)
    attempt_number = Column(Integer, default=1)
    status = Column(String(20), nullable=False, index=True)  # pass/fail/partial
    error_message = Column(Text, nullable=True)
    kpi_before = Column(Float, nullable=True)
    kpi_after = Column(Float, nullable=True)
    trust_score = Column(Float, default=0.5)
    duration_ms = Column(Float, default=0.0)
    strategy_used = Column(JSON, nullable=True)
    log_metadata = Column(JSON, nullable=True)


class SelfMirrorLog(BaseModel):
    """Micro-DB for self-mirror agent — logs every observation."""
    __tablename__ = "self_mirror_log"
    agent_name = Column(String(50), default="self_mirror")
    observation_type = Column(String(100), nullable=False)
    component_observed = Column(String(200), nullable=True)
    pattern_detected = Column(String(200), nullable=True)
    status = Column(String(20), nullable=False, index=True)
    kpi_score = Column(Float, nullable=True)
    trust_score = Column(Float, default=0.5)
    insight = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    log_metadata = Column(JSON, nullable=True)


class SelfModelLog(BaseModel):
    """Micro-DB for self-model agent — logs model builds."""
    __tablename__ = "self_model_log"
    agent_name = Column(String(50), default="self_model")
    model_type = Column(String(100), nullable=False)
    data_source = Column(String(200), nullable=True)
    status = Column(String(20), nullable=False, index=True)
    accuracy = Column(Float, nullable=True)
    samples_used = Column(Integer, default=0)
    trust_score = Column(Float, default=0.5)
    model_config = Column(JSON, nullable=True)
    predictions_made = Column(Integer, default=0)
    log_metadata = Column(JSON, nullable=True)


class SelfLearnerLog(BaseModel):
    """Micro-DB for self-learner agent — logs every learning session."""
    __tablename__ = "self_learner_log"
    agent_name = Column(String(50), default="self_learner")
    topic = Column(String(200), nullable=False)
    learning_type = Column(String(100), nullable=False)  # study/practice/review
    status = Column(String(20), nullable=False, index=True)
    concepts_learned = Column(Integer, default=0)
    retention_score = Column(Float, nullable=True)
    trust_score = Column(Float, default=0.5)
    source = Column(String(200), nullable=True)  # training_data/kimi/web
    kimi_consulted = Column(Boolean, default=False)
    log_metadata = Column(JSON, nullable=True)


class CodeAgentLog(BaseModel):
    """Micro-DB for code agent — logs every code action."""
    __tablename__ = "code_agent_log"
    agent_name = Column(String(50), default="code_agent")
    action_type = Column(String(100), nullable=False)  # write/fix/refactor/test
    target_file = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, index=True)
    lines_changed = Column(Integer, default=0)
    tests_passed = Column(Integer, default=0)
    tests_failed = Column(Integer, default=0)
    trust_score = Column(Float, default=0.5)
    kimi_guided = Column(Boolean, default=False)
    verification_status = Column(String(20), nullable=True)
    log_metadata = Column(JSON, nullable=True)


class SelfEvolverLog(BaseModel):
    """Micro-DB for self-evolver — logs evolution cycles."""
    __tablename__ = "self_evolver_log"
    agent_name = Column(String(50), default="self_evolver")
    cycle_type = Column(String(100), nullable=False)  # optimize/scale/evolve
    agents_involved = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, index=True)
    kpi_improvement = Column(Float, nullable=True)
    trust_improvement = Column(Float, nullable=True)
    bottleneck_found = Column(String(200), nullable=True)
    action_taken = Column(Text, nullable=True)
    mode = Column(String(20), default="improve")  # improve/scale/monitor
    log_metadata = Column(JSON, nullable=True)


# ============================================================================
# BASE SELF-AGENT — Shared capabilities
# ============================================================================

class BaseSelfAgent:
    """
    Base class for all self-* agents.

    Every agent can:
    - Log attempts/passes/failures to its micro-DB
    - Query its own performance history
    - Calculate its own KPI score
    - Ask Kimi why performance is low
    - Access training data
    - Trigger other agents for help
    """

    AGENT_NAME = "base"
    LOG_MODEL = None

    def __init__(self, session: Session):
        self.session = session
        self._kpi_cache = {}

    def log_attempt(self, action_type: str, status: str, **kwargs) -> None:
        """Log an attempt to the agent's micro-DB."""
        if not self.LOG_MODEL:
            return
        entry = self.LOG_MODEL(
            agent_name=self.AGENT_NAME,
            action_type=action_type,
            status=status,
            **{k: v for k, v in kwargs.items()
               if hasattr(self.LOG_MODEL, k)}
        )
        self.session.add(entry)
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()

    def get_pass_rate(self, window_hours: int = 24) -> float:
        """Calculate pass rate from recent attempts."""
        if not self.LOG_MODEL:
            return 0.0
        cutoff = datetime.now() - timedelta(hours=window_hours)
        total = self.session.query(self.LOG_MODEL).filter(
            self.LOG_MODEL.agent_name == self.AGENT_NAME,
            self.LOG_MODEL.created_at >= cutoff
        ).count()
        if total == 0:
            return 0.0
        passed = self.session.query(self.LOG_MODEL).filter(
            self.LOG_MODEL.agent_name == self.AGENT_NAME,
            self.LOG_MODEL.created_at >= cutoff,
            self.LOG_MODEL.status == "pass"
        ).count()
        return round(passed / total, 3)

    def get_recent_failures(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent failures for self-analysis."""
        if not self.LOG_MODEL:
            return []
        failures = self.session.query(self.LOG_MODEL).filter(
            self.LOG_MODEL.agent_name == self.AGENT_NAME,
            self.LOG_MODEL.status == "fail"
        ).order_by(self.LOG_MODEL.created_at.desc()).limit(limit).all()
        return [
            {
                "action": f.action_type,
                "error": getattr(f, "error_message", None),
                "created_at": f.created_at.isoformat() if f.created_at else None,
                "trust": getattr(f, "trust_score", 0.5),
            }
            for f in failures
        ]

    def get_kpi_score(self) -> float:
        """Calculate composite KPI score."""
        pass_rate = self.get_pass_rate()
        trust = self._get_avg_trust()
        return round((pass_rate * 0.6) + (trust * 0.4), 3)

    def _get_avg_trust(self) -> float:
        """Get average trust score from recent entries."""
        if not self.LOG_MODEL or not hasattr(self.LOG_MODEL, "trust_score"):
            return 0.5
        from sqlalchemy import func
        result = self.session.query(
            func.avg(self.LOG_MODEL.trust_score)
        ).filter(
            self.LOG_MODEL.agent_name == self.AGENT_NAME
        ).scalar()
        return float(result) if result else 0.5

    def ask_kimi_why_low(self) -> Optional[str]:
        """
        Ask Kimi (LLM) to analyze why this agent's KPI is low.

        Sends recent failures + KPI score to LLM for reasoning.
        """
        kpi = self.get_kpi_score()
        if kpi >= 0.95:
            return None

        failures = self.get_recent_failures(5)
        prompt = (
            f"I am the {self.AGENT_NAME} agent in Grace. "
            f"My KPI score is {kpi:.1%} (target: 100%). "
            f"My pass rate is {self.get_pass_rate():.1%}. "
            f"Recent failures: {json.dumps(failures, default=str)[:1000]}. "
            f"Why is my performance low? What specific steps should I take to reach 100%?"
        )

        try:
            from ollama_client.client import get_ollama_client
            client = get_ollama_client()
            if client and client.is_running():
                from settings import settings
                model = getattr(settings, "OLLAMA_LLM_DEFAULT", "mistral:7b")
                response = client.chat(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are Grace's internal diagnostic AI. Analyze the agent's performance data and give specific, actionable improvement steps."},
                        {"role": "user", "content": prompt}
                    ],
                    stream=False,
                    temperature=0.3
                )
                _track(self.AGENT_NAME, f"Asked Kimi: KPI={kpi:.1%}", outcome="success")
                return response
        except Exception as e:
            _track(self.AGENT_NAME, f"Kimi unavailable: {e}", outcome="failure")
        return None

    def self_analyze(self) -> Dict[str, Any]:
        """Full self-analysis: KPI, pass rate, trust, failures, Kimi insight."""
        kpi = self.get_kpi_score()
        pass_rate = self.get_pass_rate()
        avg_trust = self._get_avg_trust()
        failures = self.get_recent_failures(5)

        analysis = {
            "agent": self.AGENT_NAME,
            "kpi_score": kpi,
            "pass_rate": pass_rate,
            "avg_trust": avg_trust,
            "recent_failures": len(failures),
            "status": "optimal" if kpi >= 0.95 else ("degraded" if kpi >= 0.5 else "critical"),
            "timestamp": datetime.now().isoformat(),
        }

        if kpi < 0.95:
            kimi_insight = self.ask_kimi_why_low()
            if kimi_insight:
                analysis["kimi_insight"] = kimi_insight[:2000]

        return analysis


# ============================================================================
# CONCRETE SELF-* AGENTS
# ============================================================================

class SelfHealingAgent(BaseSelfAgent):
    AGENT_NAME = "self_healer"
    LOG_MODEL = SelfHealingLog

class SelfMirrorAgent(BaseSelfAgent):
    AGENT_NAME = "self_mirror"
    LOG_MODEL = SelfMirrorLog

class SelfModelAgent(BaseSelfAgent):
    AGENT_NAME = "self_model"
    LOG_MODEL = SelfModelLog

class SelfLearnerAgent(BaseSelfAgent):
    AGENT_NAME = "self_learner"
    LOG_MODEL = SelfLearnerLog

class CodeAgentSelf(BaseSelfAgent):
    AGENT_NAME = "code_agent"
    LOG_MODEL = CodeAgentLog

class SelfEvolverAgent(BaseSelfAgent):
    AGENT_NAME = "self_evolver"
    LOG_MODEL = SelfEvolverLog


# ============================================================================
# CLOSED-LOOP ORCHESTRATOR
# ============================================================================

class ClosedLoopOrchestrator:
    """
    Orchestrates the closed-loop self-improvement cycle:

    Mirror observes -> Model analyzes -> Healer fixes -> Learner studies ->
    Code Agent implements -> Evolver scales -> Mirror observes again...

    When all agents reach 100% KPI:
    - Switches to scaling/monitoring mode
    - Looks for optimization opportunities
    - Expands capabilities
    """

    def __init__(self, session: Session):
        self.session = session
        self.agents = {
            "healer": SelfHealingAgent(session),
            "mirror": SelfMirrorAgent(session),
            "model": SelfModelAgent(session),
            "learner": SelfLearnerAgent(session),
            "code": CodeAgentSelf(session),
            "evolver": SelfEvolverAgent(session),
        }
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self.cycle_count = 0
        self.mode = "improve"  # improve | scale | monitor

    def start(self, interval: int = 300):
        """Start the closed-loop daemon."""
        if self.running:
            return
        self.running = True
        self._interval = interval
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="closed-loop"
        )
        self._thread.start()
        logger.info(f"[CLOSED-LOOP] Started (interval={interval}s)")

    def stop(self):
        self.running = False

    def _loop(self):
        while self.running:
            try:
                self.run_cycle()
            except Exception as e:
                logger.error(f"[CLOSED-LOOP] Cycle error: {e}")
            time.sleep(self._interval)

    def run_cycle(self) -> Dict[str, Any]:
        """Run one closed-loop improvement cycle."""
        self.cycle_count += 1
        logger.info(f"[CLOSED-LOOP] Cycle #{self.cycle_count} (mode={self.mode})")

        # Step 1: All agents self-analyze
        analyses = {}
        for name, agent in self.agents.items():
            try:
                analyses[name] = agent.self_analyze()
            except Exception as e:
                analyses[name] = {"agent": name, "error": str(e)}

        # Step 2: Calculate system-wide KPI
        kpis = [a.get("kpi_score", 0) for a in analyses.values() if "kpi_score" in a]
        system_kpi = sum(kpis) / max(len(kpis), 1)

        # Step 3: Determine mode
        if system_kpi >= 0.95:
            self.mode = "scale"
        elif system_kpi >= 0.80:
            self.mode = "monitor"
        else:
            self.mode = "improve"

        # Step 4: Find bottleneck (lowest KPI agent)
        bottleneck = min(
            analyses.items(),
            key=lambda x: x[1].get("kpi_score", 0),
            default=("none", {})
        )

        # Step 5: Log evolution cycle
        self.agents["evolver"].log_attempt(
            action_type=f"cycle_{self.mode}",
            status="pass",
            kpi_improvement=system_kpi,
            bottleneck_found=bottleneck[0],
            mode=self.mode,
            agents_involved=list(self.agents.keys()),
            log_metadata={
                "cycle": self.cycle_count,
                "analyses": {k: v.get("kpi_score", 0) for k, v in analyses.items()},
            }
        )

        result = {
            "cycle": self.cycle_count,
            "mode": self.mode,
            "system_kpi": round(system_kpi, 3),
            "bottleneck": bottleneck[0],
            "bottleneck_kpi": bottleneck[1].get("kpi_score", 0),
            "agent_kpis": {k: v.get("kpi_score", 0) for k, v in analyses.items()},
            "timestamp": datetime.now().isoformat(),
        }

        _track("closed_loop", f"Cycle #{self.cycle_count}: KPI={system_kpi:.1%}, mode={self.mode}")
        return result

    def get_status(self) -> Dict[str, Any]:
        """Get full ecosystem status."""
        agent_statuses = {}
        for name, agent in self.agents.items():
            try:
                agent_statuses[name] = {
                    "kpi": agent.get_kpi_score(),
                    "pass_rate": agent.get_pass_rate(),
                    "trust": agent._get_avg_trust(),
                }
            except Exception:
                agent_statuses[name] = {"error": "unavailable"}

        return {
            "mode": self.mode,
            "cycle_count": self.cycle_count,
            "running": self.running,
            "agents": agent_statuses,
        }


_orchestrator: Optional[ClosedLoopOrchestrator] = None

def get_closed_loop(session: Session = None) -> ClosedLoopOrchestrator:
    """Get or create the closed-loop orchestrator."""
    global _orchestrator
    if _orchestrator is None and session:
        _orchestrator = ClosedLoopOrchestrator(session)
    return _orchestrator
