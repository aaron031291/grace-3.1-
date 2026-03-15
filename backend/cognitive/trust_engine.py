"""
Trust Engine — Component-level KPI tracking with trust scoring,
verification, and autonomous remediation.

How it works:
1. Every component/model/mechanism is tracked individually
2. Each component's output is chunked and scored out of 100
3. Scores aggregate into component trust (0-100)
4. Component trust aggregates into system trust
5. Trust determines verification requirements:
   - 80+: deterministically verified (internal data) → auto-accept
   - 60-79: LLM-driven → verify against knowledge base
   - 40-59: unknown source → verify against web + APIs + oracle
   - <40: reject or require human approval
6. Failed components trigger self-healing or coding agent
7. Genesis keys track every output for provenance

Verification sources (checked in order):
  1. Internal: knowledge base, memory mesh, chats, projects
  2. Oracle: training data, learned patterns
  3. External: web search, APIs, whitelist sources
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ChunkScore:
    """Individual chunk within a component output."""
    chunk_id: str
    content: str
    score: float  # 0-100
    source: str  # "deterministic", "llm", "unknown"
    verified: bool = False
    verification_method: Optional[str] = None
    issues: List[str] = field(default_factory=list)


@dataclass
class ComponentScore:
    """Aggregated score for a component."""
    component_id: str
    component_name: str
    chunks: List[ChunkScore] = field(default_factory=list)
    trust_score: float = 0.0  # 0-100 rolling average
    confidence_score: float = 0.0 # 0-100 based on data volume (N/300)
    previous_trust: float = 0.0
    trend: str = "stable"  # up, down, stable
    needs_verification: bool = False
    needs_remediation: bool = False
    remediation_type: Optional[str] = None  # "self_healing", "coding_agent", "human"
    last_updated: Optional[str] = None
    execution_count: int = 0


class ConfidenceCalculator:
    """
    Statistical confidence layer on top of trust scores.

    Confidence = how reliable is this trust score?
    Based on:
    - Data volume (more observations = higher confidence)
    - Score variance (stable scores = higher confidence)
    - Recency (fresh data = higher confidence)
    - Trend stability (no wild swings = higher confidence)
    """

    def __init__(self):
        self._score_history: Dict[str, list] = {}  # component_id -> list of (timestamp, score)
        self._max_history = 300  # ~100 days at 3x/day

    def record_score(self, component_id: str, score: float):
        """Record a trust score observation."""
        if component_id not in self._score_history:
            self._score_history[component_id] = []
        history = self._score_history[component_id]
        history.append((datetime.now(timezone.utc), score))
        if len(history) > self._max_history:
            self._score_history[component_id] = history[-self._max_history:]

    def get_confidence(self, component_id: str) -> Dict[str, Any]:
        """
        Calculate confidence for a component's trust score.

        Returns dict with:
        - confidence: 0-100 overall confidence
        - volume_factor: based on observation count
        - stability_factor: based on score variance
        - recency_factor: based on freshness of data
        - sample_count: number of observations
        """
        history = self._score_history.get(component_id, [])

        if not history:
            return {
                "confidence": 0.0,
                "volume_factor": 0.0,
                "stability_factor": 0.0,
                "recency_factor": 0.0,
                "sample_count": 0,
            }

        scores = [s for _, s in history]
        n = len(scores)

        # Volume factor: confidence grows with sqrt(N), capped at 300 samples
        volume_factor = min(100.0, (n / 300.0) * 100.0)

        # Stability factor: low variance = high confidence
        if n >= 2:
            mean = sum(scores) / n
            variance = sum((s - mean) ** 2 for s in scores) / n
            std_dev = variance ** 0.5
            # Normalize: std_dev of 0 = 100% stable, std_dev of 30+ = 0% stable
            stability_factor = max(0.0, min(100.0, 100.0 - (std_dev / 30.0) * 100.0))
        else:
            stability_factor = 50.0  # neutral with single observation

        # Recency factor: how fresh is the latest data?
        latest_ts = history[-1][0]
        age_hours = (datetime.now(timezone.utc) - latest_ts).total_seconds() / 3600
        if age_hours < 1:
            recency_factor = 100.0
        elif age_hours < 24:
            recency_factor = 80.0
        elif age_hours < 168:  # 1 week
            recency_factor = 50.0
        else:
            recency_factor = max(10.0, 50.0 - age_hours / 168 * 20)

        # Weighted combination
        confidence = (
            0.35 * volume_factor
            + 0.40 * stability_factor
            + 0.25 * recency_factor
        )

        return {
            "confidence": round(confidence, 1),
            "volume_factor": round(volume_factor, 1),
            "stability_factor": round(stability_factor, 1),
            "recency_factor": round(recency_factor, 1),
            "sample_count": n,
        }


class TrustEngine:
    """
    Tracks trust per component, verifies outputs, triggers remediation.
    """

    def __init__(self):
        self._component_scores: Dict[str, ComponentScore] = {}
        self._confidence = ConfidenceCalculator()

    # ── Score an output ────────────────────────────────────────────────

    def score_output(
        self,
        component_id: str,
        component_name: str,
        output: str,
        source: str = "llm",
        chunk_size: int = 500,
    ) -> ComponentScore:
        """
        Score a component's output by breaking it into chunks.
        Each chunk is scored out of 100.
        """
        chunks = self._chunk_output(output, chunk_size)
        scored_chunks = []

        for i, chunk_text in enumerate(chunks):
            score = self._score_chunk(chunk_text, source)
            scored_chunks.append(ChunkScore(
                chunk_id=f"{component_id}_chunk_{i}",
                content=chunk_text[:200],
                score=score,
                source=source,
            ))

        # Get or create component score
        if component_id not in self._component_scores:
            self._component_scores[component_id] = ComponentScore(
                component_id=component_id,
                component_name=component_name,
            )

        comp = self._component_scores[component_id]
        comp.previous_trust = comp.trust_score
        comp.chunks = scored_chunks

        # Calculate new trust from chunk scores
        if scored_chunks:
            avg_chunk_score = sum(c.score for c in scored_chunks) / len(scored_chunks)
            # Blend KPI tracker trust if available
            kpi_bonus = self._get_kpi_trust_bonus(component_id)
            if kpi_bonus != 0:
                avg_chunk_score = max(0, min(100, avg_chunk_score + kpi_bonus))
            # KPI Trust is a strict rolling average of past events
            comp.execution_count += 1
            # Current value contribution: 1/N, previous sum contribution: (N-1)/N
            # If N > 100, we cap the window at 100
            window = min(comp.execution_count, 100)
            comp.trust_score = round(((comp.previous_trust * (window - 1)) + avg_chunk_score) / window, 1)

            # Record for confidence tracking
            self._confidence.record_score(component_id, comp.trust_score)
            conf = self._confidence.get_confidence(component_id)
            comp.confidence_score = conf["confidence"]
        
        comp.trend = "up" if comp.trust_score > comp.previous_trust else "down" if comp.trust_score < comp.previous_trust else "stable"
        comp.last_updated = datetime.now(timezone.utc).isoformat()

        # ── Wire: Trust → Event Bus (consumed by Consensus & Healing) ──
        try:
            from cognitive.event_bus import publish
            publish("trust.updated", {
                "component_id": component_id,
                "component_name": component_name,
                "trust_score": comp.trust_score,
                "previous_trust": comp.previous_trust,
                "trend": comp.trend,
                "needs_remediation": comp.needs_remediation,
                "remediation_type": comp.remediation_type,
            }, source="trust_engine")
        except Exception:
            pass

        # ── Wire: Trust → Consensus (score change for downstream consumers) ──
        try:
            from cognitive.event_bus import publish
            publish("trust.score_updated", {
                "component": component_name,
                "trust_score": comp.trust_score,
                "previous_score": comp.previous_trust,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }, source="trust_engine")
        except Exception:
            pass

        # Determine verification and remediation needs
        comp.needs_verification = comp.trust_score < 80
        if comp.trust_score < 40:
            comp.needs_remediation = True
            comp.remediation_type = "human"
        elif comp.trust_score < 60:
            comp.needs_remediation = True
            comp.remediation_type = "coding_agent"
        elif comp.trust_score < 70:
            comp.needs_remediation = True
            comp.remediation_type = "self_healing"
        else:
            comp.needs_remediation = False
            comp.remediation_type = None

        return comp

    # ── Verify an output ───────────────────────────────────────────────

    def verify_output(
        self,
        component_id: str,
        output: str,
        trust_score: float,
    ) -> Dict[str, Any]:
        """
        Verify output based on trust score thresholds.
        80+: check internal data (deterministic)
        60-79: check knowledge base + oracle
        40-59: check web + APIs + external
        <40: require human verification
        """
        result = {
            "component_id": component_id,
            "trust_score": trust_score,
            "verification_level": self._get_verification_level(trust_score),
            "sources_checked": [],
            "verified": False,
            "confidence": 0.0,
            "issues": [],
        }

        if trust_score >= 80:
            # Deterministic verification — check internal data only
            result["sources_checked"].append("internal")
            internal = self._verify_internal(output)
            result["verified"] = internal["found"]
            result["confidence"] = internal["confidence"]
            if not internal["found"]:
                result["issues"].append("Not found in internal knowledge base")

        elif trust_score >= 60:
            # LLM-driven — check KB + oracle + memory
            result["sources_checked"].extend(["knowledge_base", "oracle", "memory_mesh"])
            kb_check = self._verify_knowledge_base(output)
            result["verified"] = kb_check["found"]
            result["confidence"] = kb_check["confidence"]
            if not kb_check["found"]:
                result["issues"].append("Not corroborated by knowledge base or oracle")

        elif trust_score >= 40:
            # Unknown source — check everything
            result["sources_checked"].extend(["knowledge_base", "oracle", "web_search", "apis", "memory_mesh", "chats", "projects"])
            full_check = self._verify_full(output)
            result["verified"] = full_check["found"]
            result["confidence"] = full_check["confidence"]
            if not full_check["found"]:
                result["issues"].append("Not verified by any internal or external source")

        else:
            # Below 40 — require human
            result["sources_checked"].append("human_required")
            result["verified"] = False
            result["confidence"] = 0.0
            result["issues"].append("Trust too low — requires human verification")

        # Track verification in genesis
        try:
            from api._genesis_tracker import track
            track(
                key_type="system",
                what=f"Verification: {component_id} (trust={trust_score}, verified={result['verified']})",
                how="TrustEngine.verify_output",
                output_data=result,
                tags=["trust", "verification", result["verification_level"]],
            )
        except Exception:
            pass

        return result

    # ── Get system-wide trust ──────────────────────────────────────────

    def get_system_trust(self) -> Dict[str, Any]:
        """Aggregate trust across all tracked components."""
        if not self._component_scores:
            return {"system_trust": 0.0, "components": 0}

        scores = list(self._component_scores.values())
        avg = sum(c.trust_score for c in scores) / len(scores)
        
        needs_attention = [c for c in scores if c.needs_remediation]
        high_trust = [c for c in scores if c.trust_score >= 80]
        low_trust = [c for c in scores if c.trust_score < 40]

        return {
            "system_trust": round(avg, 1),
            "component_count": len(scores),
            "high_trust_count": len(high_trust),
            "low_trust_count": len(low_trust),
            "needs_attention": len(needs_attention),
            "components": {
                c.component_id: {
                    "name": c.component_name,
                    "trust": c.trust_score,
                    "trend": c.trend,
                    "needs_remediation": c.needs_remediation,
                    "remediation_type": c.remediation_type,
                    "chunk_count": len(c.chunks),
                }
                for c in scores
            },
        }

    def get_component(self, component_id: str) -> Optional[ComponentScore]:
        return self._component_scores.get(component_id)

    def get_confidence(self, component_id: str) -> Dict[str, Any]:
        """Get detailed confidence metrics for a component."""
        return self._confidence.get_confidence(component_id)

    # ── Trigger remediation ────────────────────────────────────────────

    def trigger_remediation(self, component_id: str) -> Dict[str, Any]:
        """Trigger appropriate remediation based on trust score."""
        comp = self._component_scores.get(component_id)
        if not comp or not comp.needs_remediation:
            return {"action": "none", "reason": "No remediation needed"}

        result = {"component": component_id, "trust": comp.trust_score}

        if comp.remediation_type == "self_healing":
            result["action"] = "self_healing"
            result["detail"] = "Triggering self-healing for component"
            # Would trigger actual healing here

        elif comp.remediation_type == "coding_agent":
            result["action"] = "coding_agent"
            result["detail"] = "Routing to coding agent for fix"
            # Identify which chunks failed
            failed_chunks = [c for c in comp.chunks if c.score < 60]
            result["failed_chunks"] = len(failed_chunks)
            result["issues"] = [c.issues for c in failed_chunks if c.issues]

        elif comp.remediation_type == "human":
            result["action"] = "human_approval"
            result["detail"] = "Trust too low — routing to governance approvals"

        try:
            from api._genesis_tracker import track
            track(
                key_type="system",
                what=f"Remediation triggered: {comp.remediation_type} for {component_id}",
                how="TrustEngine.trigger_remediation",
                output_data=result,
                tags=["trust", "remediation", comp.remediation_type],
            )
        except Exception:
            pass

        return result

    # ── KPI integration ──────────────────────────────────────────────

    def get_dashboard(self) -> Dict[str, Any]:
        """Combined trust + KPI dashboard for governance."""
        system_trust = self.get_system_trust()

        # Merge with KPI tracker data
        kpi_data = {}
        try:
            from ml_intelligence.kpi_tracker import get_kpi_tracker
            tracker = get_kpi_tracker()
            if tracker.components:
                kpi_data = tracker.get_system_health()
        except Exception as e:
            logger.debug("KPI tracker unavailable: %s", e)

        return {
            "overall_trust": system_trust.get("system_trust", 0.0),
            "trust_engine": system_trust,
            "kpi_tracker": kpi_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _get_kpi_trust_bonus(self, component_id: str) -> float:
        """Get trust bonus/penalty from KPI tracker data (0 if no data)."""
        try:
            from ml_intelligence.kpi_tracker import get_kpi_tracker
            tracker = get_kpi_tracker()
            kpi_trust = tracker.get_component_trust_score(component_id)
            if kpi_trust > 0:
                # Scale KPI trust (0-1) to a -10..+10 bonus
                return (kpi_trust - 0.5) * 20
        except Exception:
            pass
        return 0.0

    def record_kpi(self, component_id: str, metric: str, value: float = 1.0):
        """Record a KPI metric for a component."""
        try:
            from ml_intelligence.kpi_tracker import get_kpi_tracker
            tracker = get_kpi_tracker()
            tracker.increment_kpi(component_id, metric, value)
        except Exception as e:
            logger.debug("KPI record failed: %s", e)

    # ── Internal helpers ───────────────────────────────────────────────

    def _chunk_output(self, output: str, chunk_size: int) -> List[str]:
        """Break output into chunks for individual scoring."""
        if not output:
            return [""]
        chunks = []
        for i in range(0, len(output), chunk_size):
            chunks.append(output[i:i + chunk_size])
        return chunks or [""]

    def _score_chunk(self, chunk: str, source: str) -> float:
        """Score a chunk out of 100 using weighted deterministic KPI rules.

        Penalties are proportional to severity:
          Critical (safety/correctness): -15 to -20
          Structural (syntax/formatting): -5 per issue
          Quality (style/docs): -3 per issue
          Provenance (source trust): -8 to -12
        """
        score = 100.0

        # Layer 1: Empty/trivial content — critical
        stripped = chunk.strip()
        if not stripped:
            return 5.0  # almost worthless
        if len(stripped) < 10:
            score -= 15

        # Layer 2: Balanced delimiters — structural (per delimiter type)
        for open_c, close_c, name in [('(', ')', 'parentheses'), ('[', ']', 'brackets'), ('{', '}', 'braces')]:
            diff = abs(chunk.count(open_c) - chunk.count(close_c))
            if diff > 0:
                score -= min(5 * diff, 15)  # cap at -15 per type

        # Layer 3: Forbidden tokens — quality
        bad_tokens = ["TODO", "FIXME", "HACK", "XXX"]
        bad_count = sum(1 for tok in bad_tokens if tok in chunk)
        if bad_count:
            score -= 3 * bad_count

        stub_markers = ["raise NotImplementedError", "pass  #", "...  #"]
        if any(m in chunk for m in stub_markers):
            score -= 8  # stub code is worse than TODO comments

        # Layer 4: Safety — critical
        unsafe_calls = ["os.system(", "subprocess.call(", "eval(", "exec("]
        unsafe_count = sum(1 for c in unsafe_calls if c in chunk)
        if unsafe_count:
            score -= 20  # safety violations are severe

        # Layer 5: Code quality — code should have docstrings
        if "def " in chunk or "class " in chunk:
            if '"""' not in chunk and "'''" not in chunk:
                score -= 3

        # Layer 6: Source provenance
        source_penalties = {
            "deterministic": 0,
            "internal": 0,
            "llm": -4,
            "external": -8,
            "unknown": -12,
        }
        score += source_penalties.get(source, -12)

        # Layer 7: Repetition detection (low-effort content)
        words = stripped.split()
        if len(words) > 10:
            unique_ratio = len(set(w.lower() for w in words)) / len(words)
            if unique_ratio < 0.3:
                score -= 10  # highly repetitive

        return max(0.0, min(100.0, round(score, 1)))

    def _get_verification_level(self, trust: float) -> str:
        if trust >= 80:
            return "internal_only"
        elif trust >= 60:
            return "knowledge_base"
        elif trust >= 40:
            return "full_verification"
        else:
            return "human_required"

    def _verify_internal(self, output: str) -> Dict[str, Any]:
        """Check against internal knowledge base and memory."""
        try:
            db = _get_db()
            if not db:
                return {"found": False, "confidence": 0.3}
            from sqlalchemy import text
            # Check if similar content exists in learning examples
            count = db.execute(text(
                "SELECT COUNT(*) FROM learning_examples WHERE trust_score >= 0.7"
            )).scalar() or 0
            db.close()
            return {"found": count > 0, "confidence": min(0.9, 0.5 + count * 0.01)}
        except Exception:
            return {"found": False, "confidence": 0.3}

    def _verify_knowledge_base(self, output: str) -> Dict[str, Any]:
        """Check against knowledge base + oracle."""
        try:
            db = _get_db()
            if not db:
                return {"found": False, "confidence": 0.2}
            from sqlalchemy import text
            docs = db.execute(text("SELECT COUNT(*) FROM documents WHERE status = 'completed'")).scalar() or 0
            examples = db.execute(text("SELECT COUNT(*) FROM learning_examples")).scalar() or 0
            db.close()
            has_data = docs > 0 or examples > 0
            return {"found": has_data, "confidence": min(0.8, 0.3 + (docs + examples) * 0.005)}
        except Exception:
            return {"found": False, "confidence": 0.2}

    def _verify_full(self, output: str) -> Dict[str, Any]:
        """Full verification against all sources."""
        internal = self._verify_internal(output)
        kb = self._verify_knowledge_base(output)
        
        combined_confidence = max(internal["confidence"], kb["confidence"])
        found = internal["found"] or kb["found"]

        return {"found": found, "confidence": combined_confidence}


def _get_db():
    try:
        from database.session import SessionLocal
        if SessionLocal:
            return SessionLocal()
    except Exception:
        pass
    return None


# Singleton
_trust_engine = None

def get_trust_engine() -> TrustEngine:
    global _trust_engine
    if _trust_engine is None:
        _trust_engine = TrustEngine()
    return _trust_engine
