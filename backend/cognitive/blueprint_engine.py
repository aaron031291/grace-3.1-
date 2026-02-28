"""
Blueprint Engine — Kimi+Opus Design, Qwen Builds, Grace Verifies

The coding architecture that removes the need for a developer:
  1. DESIGN: Kimi+Opus consensus creates a typed blueprint (JSON spec)
  2. BUILD: Qwen 2.5 (local, free) writes code from the blueprint
  3. TEST: Grace Compiler verifies (sandbox + trust + compass)
  4. RETRY: If fail → Qwen retries with error feedback (up to 20x)
  5. ESCALATE: If still fail → back to Kimi+Opus for blueprint revision
  6. DEPLOY: If pass → integrate into Grace via Live Integration Protocol

Economics:
  Kimi+Opus: ~$0.60 per blueprint (thinking)
  Qwen: $0 per build (local GPU)
  50 Qwen retries cost less than 1 Opus call
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

BLUEPRINTS_DIR = Path(__file__).parent.parent / "data" / "blueprints"

MAX_QWEN_RETRIES = 20
MAX_BLUEPRINT_REVISIONS = 3


@dataclass
class FunctionSpec:
    name: str
    inputs: Dict[str, str]
    output_type: str
    description: str
    constraints: List[str] = field(default_factory=list)
    test_cases: List[Dict] = field(default_factory=list)


@dataclass
class Blueprint:
    id: str
    task: str
    status: str = "draft"  # draft, designing, building, testing, failed, deployed
    architecture: str = ""
    functions: List[Dict] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    consensus_score: float = 0.0
    generated_code: str = ""
    build_attempts: int = 0
    revision_count: int = 0
    errors: List[str] = field(default_factory=list)
    trust_score: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


def create_from_prompt(user_prompt: str) -> Dict[str, Any]:
    """
    Full pipeline: User types what they want → code gets deployed.

    Step 1: Kimi+Opus design the blueprint
    Step 2: Qwen builds the code
    Step 3: Grace verifies
    Step 4: Retry or deploy
    """
    bp = Blueprint(id=f"bp_{uuid.uuid4().hex[:10]}", task=user_prompt)
    _save_blueprint(bp)

    # ── Step 1: DESIGN (Kimi+Opus consensus) ──────────────────────────
    bp.status = "designing"
    _save_blueprint(bp)

    blueprint_spec = _design_blueprint(user_prompt, bp)
    if not blueprint_spec:
        bp.status = "failed"
        bp.errors.append("Blueprint design failed")
        _save_blueprint(bp)
        return bp.to_dict()

    bp.architecture = blueprint_spec.get("architecture", "")
    bp.functions = blueprint_spec.get("functions", [])
    bp.dependencies = blueprint_spec.get("dependencies", [])
    bp.success_criteria = blueprint_spec.get("success_criteria", [])
    bp.consensus_score = blueprint_spec.get("consensus_score", 0)

    # ── Step 2+3+4: BUILD → TEST → RETRY loop ────────────────────────
    for attempt in range(MAX_QWEN_RETRIES):
        bp.status = "building"
        bp.build_attempts = attempt + 1
        _save_blueprint(bp)

        # Build with Qwen (or fallback to any available local model)
        code = _build_from_blueprint(bp, attempt)
        if not code:
            bp.errors.append(f"Build attempt {attempt + 1}: no code generated")
            continue

        bp.generated_code = code

        # Test with Grace Compiler
        bp.status = "testing"
        _save_blueprint(bp)

        test_result = _test_code(code)
        bp.trust_score = test_result.get("trust_score", 0)

        if test_result.get("passed"):
            bp.status = "deployed"
            _save_blueprint(bp)

            # Track success
            _track_blueprint(bp, "deployed")

            return {
                **bp.to_dict(),
                "result": "SUCCESS",
                "message": f"Code deployed after {attempt + 1} attempt(s). Trust: {bp.trust_score}",
                "test_result": test_result,
            }

        # Failed — collect errors for retry
        bp.errors.append(f"Attempt {attempt + 1}: {test_result.get('error', 'verification failed')}")

    # ── Step 5: ESCALATE back to Kimi+Opus ────────────────────────────
    if bp.revision_count < MAX_BLUEPRINT_REVISIONS:
        bp.revision_count += 1
        bp.status = "designing"
        _save_blueprint(bp)

        # Ask Kimi+Opus to revise the blueprint with error context
        revised = _revise_blueprint(bp)
        if revised:
            bp.functions = revised.get("functions", bp.functions)
            bp.architecture = revised.get("architecture", bp.architecture)
            # Recurse with new blueprint
            return _retry_with_revised_blueprint(bp)

    bp.status = "failed"
    _save_blueprint(bp)
    _track_blueprint(bp, "failed")

    return {
        **bp.to_dict(),
        "result": "FAILED",
        "message": f"Failed after {bp.build_attempts} builds and {bp.revision_count} revisions",
        "needs_human": True,
    }


def _design_blueprint(prompt: str, bp: Blueprint) -> Optional[Dict]:
    """Use Kimi+Opus consensus to design the blueprint."""
    try:
        from cognitive.consensus_engine import run_consensus

        result = run_consensus(
            prompt=(
                f"Design a code blueprint for this task:\n\n"
                f"Task: {prompt}\n\n"
                f"Output a JSON blueprint with:\n"
                f"- architecture: one paragraph describing the approach\n"
                f"- functions: list of {{name, inputs, output_type, description, constraints, test_cases}}\n"
                f"- dependencies: list of required imports\n"
                f"- success_criteria: list of what 'done' looks like\n\n"
                f"The blueprint will be given to a coding model to implement.\n"
                f"Be SPECIFIC about types, constraints, and test cases.\n"
                f"Output ONLY valid JSON."
            ),
            models=["kimi", "opus"],
            source="autonomous",
        )

        # Try to parse JSON from the consensus output
        text = result.final_output
        try:
            import re
            json_match = re.search(r'\{[\s\S]+\}', text)
            if json_match:
                spec = json.loads(json_match.group())
                spec["consensus_score"] = result.confidence
                return spec
        except Exception:
            pass

        # Fallback: extract what we can
        return {
            "architecture": text[:500],
            "functions": [],
            "dependencies": [],
            "success_criteria": [prompt],
            "consensus_score": result.confidence,
        }
    except Exception as e:
        logger.error(f"Blueprint design failed: {e}")
        return None


def _build_from_blueprint(bp: Blueprint, attempt: int) -> Optional[str]:
    """Use Qwen (local) to build code from the blueprint."""
    try:
        from llm_orchestrator.factory import get_llm_for_task
        builder = get_llm_for_task("code")

        error_context = ""
        if bp.errors:
            error_context = f"\n\nPrevious attempts failed with:\n" + "\n".join(bp.errors[-3:])

        prompt = (
            f"Build Python code for this blueprint:\n\n"
            f"Architecture: {bp.architecture}\n\n"
            f"Functions to implement:\n{json.dumps(bp.functions, indent=2)[:3000]}\n\n"
            f"Dependencies: {bp.dependencies}\n"
            f"Success criteria: {bp.success_criteria}\n"
            f"{error_context}\n\n"
            f"Output ONLY valid, runnable Python code. No explanations."
        )

        code = builder.generate(
            prompt=prompt,
            system_prompt="You are a code builder. Output ONLY Python code. No markdown, no explanations.",
            temperature=0.2,
            max_tokens=4096,
        )

        if isinstance(code, str):
            # Strip markdown code fences if present
            code = code.strip()
            if code.startswith("```python"):
                code = code[9:]
            if code.startswith("```"):
                code = code[3:]
            if code.endswith("```"):
                code = code[:-3]
            return code.strip()

    except Exception as e:
        logger.error(f"Build failed: {e}")
    return None


def _test_code(code: str) -> Dict[str, Any]:
    """Test generated code through Grace's compiler."""
    try:
        from cognitive.grace_compiler import get_grace_compiler
        compiler = get_grace_compiler()
        result = compiler.compile(code)

        return {
            "passed": result.success,
            "trust_score": result.trust_score,
            "error": "; ".join(result.errors) if result.errors else "",
            "warnings": result.warnings,
            "tests_passed": result.tests_passed,
            "tests_failed": result.tests_failed,
        }
    except Exception as e:
        return {"passed": False, "error": str(e), "trust_score": 0}


def _revise_blueprint(bp: Blueprint) -> Optional[Dict]:
    """Ask Kimi+Opus to revise the blueprint based on build errors."""
    try:
        from cognitive.consensus_engine import run_consensus

        result = run_consensus(
            prompt=(
                f"A blueprint failed after {bp.build_attempts} build attempts.\n\n"
                f"Original task: {bp.task}\n"
                f"Original architecture: {bp.architecture}\n"
                f"Errors encountered:\n" + "\n".join(bp.errors[-5:]) + "\n\n"
                f"Revise the blueprint to fix these issues. Output JSON."
            ),
            models=["kimi", "opus"],
            source="autonomous",
        )

        import re
        json_match = re.search(r'\{[\s\S]+\}', result.final_output)
        if json_match:
            return json.loads(json_match.group())
    except Exception:
        pass
    return None


def _retry_with_revised_blueprint(bp: Blueprint) -> Dict[str, Any]:
    """Retry building with the revised blueprint."""
    for attempt in range(MAX_QWEN_RETRIES // 2):
        code = _build_from_blueprint(bp, bp.build_attempts + attempt)
        if not code:
            continue

        bp.generated_code = code
        bp.build_attempts += 1
        test_result = _test_code(code)
        bp.trust_score = test_result.get("trust_score", 0)

        if test_result.get("passed"):
            bp.status = "deployed"
            _save_blueprint(bp)
            _track_blueprint(bp, "deployed")
            return {
                **bp.to_dict(),
                "result": "SUCCESS",
                "message": f"Deployed after revision {bp.revision_count}",
            }

        bp.errors.append(f"Rev{bp.revision_count} attempt {attempt+1}: {test_result.get('error', '')}")

    bp.status = "failed"
    _save_blueprint(bp)
    return {**bp.to_dict(), "result": "FAILED", "needs_human": True}


def _save_blueprint(bp: Blueprint):
    BLUEPRINTS_DIR.mkdir(parents=True, exist_ok=True)
    (BLUEPRINTS_DIR / f"{bp.id}.json").write_text(json.dumps(bp.to_dict(), indent=2, default=str))


def _track_blueprint(bp: Blueprint, outcome: str):
    try:
        from api._genesis_tracker import track
        track(
            key_type="ai_code_generation",
            what=f"Blueprint {outcome}: {bp.task[:80]}",
            how=f"blueprint_engine ({bp.build_attempts} builds, {bp.revision_count} revisions)",
            output_data={
                "id": bp.id,
                "trust_score": bp.trust_score,
                "attempts": bp.build_attempts,
                "revisions": bp.revision_count,
            },
            tags=["blueprint", outcome, "autonomous_coding"],
        )
    except Exception:
        pass

    try:
        from cognitive.event_bus import publish
        publish(f"blueprint.{outcome}", {
            "id": bp.id, "task": bp.task[:100],
            "attempts": bp.build_attempts,
        }, source="blueprint_engine")
    except Exception:
        pass

    # Log the coding pattern (good or bad) for future training data
    _log_coding_pattern(bp, outcome)


def _log_coding_pattern(bp: Blueprint, outcome: str):
    """
    Log every coding pattern — successful or failed — as training data.
    Over 18 months this builds a deterministic backbone of coding knowledge.

    Successful patterns become a PLAYBOOK:
      - What was asked
      - What blueprint was designed
      - What code was generated
      - What the trust score was
      - How many attempts it took
      - Locked as a positive pattern in memory

    Failed patterns become LESSONS:
      - What went wrong
      - What errors occurred
      - What was tried
      - Why it failed
    """
    pattern = {
        "pattern_id": bp.id,
        "timestamp": datetime.utcnow().isoformat(),
        "outcome": outcome,
        "task": bp.task,
        "architecture": bp.architecture[:1000],
        "functions": bp.functions[:10],
        "code": bp.generated_code[:5000] if bp.generated_code else "",
        "trust_score": bp.trust_score,
        "build_attempts": bp.build_attempts,
        "revision_count": bp.revision_count,
        "errors": bp.errors[-5:],
    }

    # Save to playbook directory
    playbook_dir = BLUEPRINTS_DIR.parent / "coding_playbook"
    playbook_dir.mkdir(parents=True, exist_ok=True)

    if outcome == "deployed":
        # Successful pattern → positive playbook entry
        (playbook_dir / f"success_{bp.id}.json").write_text(
            json.dumps(pattern, indent=2, default=str)
        )

        # Store in unified memory as a learned procedure
        try:
            from cognitive.unified_memory import get_unified_memory
            mem = get_unified_memory()

            # Store the successful coding pattern
            mem.store_procedure(
                name=f"coding_pattern_{bp.id}",
                goal=bp.task[:200],
                steps=json.dumps({
                    "architecture": bp.architecture[:500],
                    "functions": bp.functions[:5],
                    "code_preview": bp.generated_code[:1000] if bp.generated_code else "",
                    "trust_score": bp.trust_score,
                    "attempts": bp.build_attempts,
                }, default=str),
                trust=bp.trust_score,
                proc_type="coding_playbook",
            )

            # Store as a learning example
            mem.store_learning(
                input_ctx=f"Code task: {bp.task}",
                expected=bp.generated_code[:3000] if bp.generated_code else "",
                actual=f"Trust: {bp.trust_score}, Attempts: {bp.build_attempts}",
                trust=bp.trust_score,
                source="blueprint_engine_success",
                example_type="coding_pattern",
            )
        except Exception:
            pass

        # Store in flash cache for keyword discovery
        try:
            from cognitive.flash_cache import get_flash_cache
            fc = get_flash_cache()
            kw = fc.extract_keywords(f"{bp.task} {bp.architecture}")
            fc.register(
                source_uri=f"internal://playbook/{bp.id}",
                source_type="internal",
                source_name=f"Playbook: {bp.task[:50]}",
                keywords=kw,
                summary=f"Successful coding pattern: {bp.task[:200]}",
                trust_score=bp.trust_score,
                ttl_hours=8760 * 10,
            )
        except Exception:
            pass

        # Feed to intelligence layer as positive ML observation
        try:
            from cognitive.intelligence_layer import get_intelligence_layer
            il = get_intelligence_layer()
            il.observe_loop("blueprint_build", {
                "trust_score": bp.trust_score,
                "attempts": bp.build_attempts,
                "revisions": bp.revision_count,
                "code_length": len(bp.generated_code or ""),
            }, "success")
        except Exception:
            pass

        logger.info(f"[PLAYBOOK] Positive pattern logged: {bp.task[:60]} (trust: {bp.trust_score})")

    else:
        # Failed pattern → lesson learned
        (playbook_dir / f"failure_{bp.id}.json").write_text(
            json.dumps(pattern, indent=2, default=str)
        )

        try:
            from cognitive.unified_memory import get_unified_memory
            mem = get_unified_memory()
            mem.store_episode(
                problem=f"Coding failed: {bp.task[:200]}",
                action=f"Attempted {bp.build_attempts} builds, {bp.revision_count} revisions",
                outcome=f"FAILED. Errors: {'; '.join(bp.errors[-3:])}",
                trust=0.3,
                source="blueprint_engine_failure",
            )
        except Exception:
            pass

        try:
            from cognitive.intelligence_layer import get_intelligence_layer
            il = get_intelligence_layer()
            il.observe_loop("blueprint_build", {
                "trust_score": bp.trust_score,
                "attempts": bp.build_attempts,
                "revisions": bp.revision_count,
                "code_length": len(bp.generated_code or ""),
            }, "failure")
        except Exception:
            pass

        logger.info(f"[PLAYBOOK] Failure pattern logged: {bp.task[:60]}")


def get_playbook_stats() -> Dict[str, Any]:
    """Get stats on the coding playbook — the training data being built over time."""
    playbook_dir = BLUEPRINTS_DIR.parent / "coding_playbook"
    if not playbook_dir.exists():
        return {"total": 0, "successes": 0, "failures": 0}

    successes = list(playbook_dir.glob("success_*.json"))
    failures = list(playbook_dir.glob("failure_*.json"))

    return {
        "total": len(successes) + len(failures),
        "successes": len(successes),
        "failures": len(failures),
        "success_rate": round(len(successes) / max(len(successes) + len(failures), 1), 3),
        "total_size_kb": round(sum(f.stat().st_size for f in successes + failures) / 1024, 1),
    }


def list_blueprints() -> List[Dict]:
    BLUEPRINTS_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for f in sorted(BLUEPRINTS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text())
            results.append({
                "id": data["id"], "task": data["task"][:100],
                "status": data["status"], "trust_score": data.get("trust_score", 0),
                "attempts": data.get("build_attempts", 0),
            })
        except Exception:
            pass
    return results
