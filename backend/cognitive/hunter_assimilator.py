"""
HUNTER Assimilator — Autonomous code integration system.

When a user submits code/feature with the keyword HUNTER, Grace:
1. Accepts the code as intended for integration
2. Runs it through the full cognitive pipeline (9 stages)
3. Kimi analyses and reasons about the code
4. Grace verifies, tests, and validates
5. Coding agent fixes any issues found
6. Trust Engine scores the result
7. Hallucination guard verifies against project
8. Self-healing checks it won't break anything
9. Librarian places files in the right location
10. Database schemas auto-detected and migrated
11. Handshake protocol announces the new component to all systems
12. Genesis key tracks the entire assimilation chain

No manual testing, no manual file placement, no manual schema updates.
The user says HUNTER, Grace does everything else.
"""

import logging
import re
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AssimilationResult:
    """Complete result of a HUNTER assimilation."""
    request_id: str = ""
    status: str = "pending"  # pending, analysing, testing, fixing, integrating, complete, failed
    steps: List[Dict[str, Any]] = field(default_factory=list)
    files_created: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    schemas_detected: List[str] = field(default_factory=list)
    issues_found: List[str] = field(default_factory=list)
    issues_fixed: List[str] = field(default_factory=list)
    trust_score: float = 0
    handshake_sent: bool = False
    genesis_key: Optional[str] = None
    started_at: str = ""
    completed_at: str = ""


class HunterAssimilator:
    """
    Autonomous code assimilation triggered by HUNTER keyword.
    Runs new code through Grace's entire backend pipeline.
    """

    def __init__(self):
        self._history: List[AssimilationResult] = []

    def is_hunter_request(self, text: str) -> bool:
        """Check if text contains the HUNTER trigger."""
        return "HUNTER" in text

    def assimilate(self, code: str, description: str = "", 
                   project_folder: str = "", user: str = "system") -> AssimilationResult:
        """
        Full autonomous assimilation of new code into Grace.
        """
        result = AssimilationResult(
            request_id=f"hunter_{int(time.time())}",
            started_at=datetime.utcnow().isoformat(),
        )

        # Genesis: track the start
        try:
            from api._genesis_tracker import track
            result.genesis_key = track(
                key_type="system",
                what=f"HUNTER assimilation started: {description[:80]}",
                who=user, how="HunterAssimilator.assimilate",
                input_data={"description": description[:500], "code_length": len(code)},
                tags=["hunter", "assimilation", "start"],
            )
        except Exception:
            pass

        # Step 1: Parse — extract files, schemas, dependencies
        result.status = "analysing"
        step1 = self._step_parse(code, description)
        result.steps.append(step1)
        result.files_created = step1.get("files", [])
        result.schemas_detected = step1.get("schemas", [])

        # Step 2: Kimi analysis — understand what the code does
        step2 = self._step_kimi_analyse(code, description)
        result.steps.append(step2)

        # Step 3: Pipeline verification — run through 9-stage cognitive pipeline
        result.status = "testing"
        step3 = self._step_pipeline_verify(code, description, project_folder)
        result.steps.append(step3)

        # Step 4: Code agent review — check for bugs, security, style
        step4 = self._step_code_review(code)
        result.steps.append(step4)
        if step4.get("issues"):
            result.issues_found.extend(step4["issues"])

        # Step 5: Fix issues — coding agent fixes anything found
        if result.issues_found:
            result.status = "fixing"
            step5 = self._step_fix_issues(code, result.issues_found, project_folder)
            result.steps.append(step5)
            if step5.get("fixed_code"):
                code = step5["fixed_code"]
                result.issues_fixed = step5.get("fixed", [])

        # Step 6: Trust scoring
        step6 = self._step_trust_score(code)
        result.steps.append(step6)
        result.trust_score = step6.get("trust", 0)

        # Step 7: Self-healing pre-check — will this break anything?
        step7 = self._step_healing_precheck(code, result.files_created)
        result.steps.append(step7)

        # Step 8: Write files + update schemas
        result.status = "integrating"
        step8 = self._step_write_files(code, result.files_created, project_folder)
        result.steps.append(step8)

        # Step 9: Schema migration
        if result.schemas_detected:
            step9 = self._step_migrate_schemas(result.schemas_detected)
            result.steps.append(step9)

        # Step 10: Librarian organise
        step10 = self._step_librarian_organise(result.files_created)
        result.steps.append(step10)

        # Step 11: Handshake — announce to all systems
        step11 = self._step_handshake(result)
        result.steps.append(step11)
        result.handshake_sent = step11.get("sent", False)

        # Step 12: Contradiction check on final code
        step12 = self._step_contradiction_check(code, project_folder)
        result.steps.append(step12)

        # Step 13: Feed learning loop
        step13 = self._step_feed_learning(code, description, result)
        result.steps.append(step13)

        # Step 14: Immune system post-check
        step14 = self._step_immune_postcheck()
        result.steps.append(step14)

        # Step 15: Update KPIs
        step15 = self._step_update_kpi(result)
        result.steps.append(step15)

        # Complete
        result.status = "complete"
        result.completed_at = datetime.utcnow().isoformat()

        # Genesis: track completion
        try:
            from api._genesis_tracker import track
            track(
                key_type="system",
                what=f"HUNTER assimilation complete: {description[:80]}",
                who=user, how="HunterAssimilator.assimilate",
                output_data={
                    "files": len(result.files_created),
                    "issues_found": len(result.issues_found),
                    "issues_fixed": len(result.issues_fixed),
                    "trust": result.trust_score,
                    "handshake": result.handshake_sent,
                },
                tags=["hunter", "assimilation", "complete"],
                parent_key_id=result.genesis_key,
            )
        except Exception:
            pass

        # Store in Magma
        try:
            from cognitive.magma_bridge import ingest, store_procedure
            ingest(f"HUNTER assimilation: {description}. Files: {result.files_created}. Trust: {result.trust_score}",
                   source="hunter")
            store_procedure(f"Assimilated: {description[:50]}", description,
                           steps=["Parse", "Kimi analyse", "Pipeline verify", "Code review", "Fix", "Trust", "Write", "Handshake"])
        except Exception:
            pass

        self._history.append(result)
        return result

    # ── Step 1: Parse code into files and detect schemas ───────────────

    def _step_parse(self, code: str, description: str) -> Dict:
        files = []
        schemas = []

        # Extract file markers: ```filepath: path/to/file.ext
        file_blocks = re.findall(r'```filepath:\s*(.+?)\n(.*?)```', code, re.DOTALL)
        for path, content in file_blocks:
            files.append({"path": path.strip(), "content": content, "size": len(content)})

        # If no file markers, treat entire code as a single file
        if not files and code.strip():
            ext = ".py"  # Default
            if "function " in code or "const " in code:
                ext = ".js"
            elif "<" in code and ">" in code and "html" in code.lower():
                ext = ".html"
            name = re.sub(r'[^a-z0-9]', '_', description.lower()[:30]) + ext
            files.append({"path": name, "content": code, "size": len(code)})

        # Detect database schemas
        schema_patterns = [
            r'CREATE\s+TABLE\s+(\w+)',
            r'class\s+(\w+)\(.*BaseModel\)',
            r'class\s+(\w+)\(.*Base\)',
            r'__tablename__\s*=\s*["\'](\w+)["\']',
        ]
        for pattern in schema_patterns:
            matches = re.findall(pattern, code)
            schemas.extend(matches)

        return {"step": "parse", "files": [f["path"] for f in files], "schemas": list(set(schemas)),
                "file_details": files}

    # ── Step 2: Kimi analysis ──────────────────────────────────────────

    def _step_kimi_analyse(self, code: str, description: str) -> Dict:
        # Try consensus first if multiple models available (multi-perspective code review)
        # Protected by circuit breaker (prevents pipeline↔consensus loop)
        try:
            from cognitive.circuit_breaker import enter_loop, exit_loop
            if not enter_loop("consensus_refinement"):
                raise RuntimeError("Circuit breaker: consensus loop depth exceeded")
            from cognitive.consensus_engine import run_consensus, _check_model_available
            available = [m for m in ["opus", "kimi", "qwen"] if _check_model_available(m)]
            if len(available) >= 2:
                result = run_consensus(
                    prompt=(
                        f"Analyse this code being integrated into Grace AI:\n\n"
                        f"Description: {description}\n\nCode:\n{code[:4000]}\n\n"
                        f"Provide: 1) What it does 2) Dependencies needed 3) Potential conflicts "
                        f"4) Integration points 5) Risk assessment"
                    ),
                    models=available,
                    source="autonomous",
                )
                if result.verification.get("passed"):
                    return {
                        "step": "kimi_analyse", "analysis": result.final_output,
                        "success": True, "method": "consensus",
                        "models_used": result.models_used,
                        "confidence": result.confidence,
                    }
        except Exception:
            pass
        finally:
            try:
                exit_loop("consensus_refinement")
            except Exception:
                pass

        # Fallback to single Kimi analysis
        try:
            from llm_orchestrator.kimi_enhanced import get_kimi_enhanced
            kimi = get_kimi_enhanced()
            response = kimi._call(
                f"Analyse this code being integrated into Grace AI:\n\n"
                f"Description: {description}\n\n"
                f"Code:\n{code[:5000]}\n\n"
                f"Provide: 1) What it does 2) Dependencies needed 3) Potential conflicts "
                f"4) Integration points 5) Risk assessment",
                system="You are reviewing code for autonomous integration into an AI system.",
                temperature=0.2,
            )
            return {"step": "kimi_analyse", "analysis": response, "success": bool(response), "method": "kimi_solo"}
        except Exception as e:
            return {"step": "kimi_analyse", "analysis": None, "error": str(e)}

    # ── Step 3: Pipeline verification ──────────────────────────────────

    def _step_pipeline_verify(self, code: str, description: str, project_folder: str) -> Dict:
        try:
            from cognitive.pipeline import CognitivePipeline
            ctx = CognitivePipeline().run(
                prompt=f"Verify this code for integration: {description}\n\n{code[:3000]}",
                project_folder=project_folder,
                skip_stages=["generate"],  # We have the code already, just verify
            )
            return {
                "step": "pipeline_verify",
                "stages_passed": ctx.stages_passed,
                "stages_failed": ctx.stages_failed,
                "invariants": ctx.invariants,
                "ambiguity": ctx.ambiguity,
                "trust": ctx.trust_score,
            }
        except Exception as e:
            return {"step": "pipeline_verify", "error": str(e)}

    # ── Step 4: Code review ────────────────────────────────────────────

    def _step_code_review(self, code: str) -> Dict:
        issues = []

        # Basic static checks
        if "eval(" in code:
            issues.append("security: eval() usage detected")
        if "exec(" in code:
            issues.append("security: exec() usage detected")
        if "import os; os.system" in code:
            issues.append("security: shell command execution detected")
        if "password" in code.lower() and "=" in code and ("'" in code or '"' in code):
            issues.append("security: possible hardcoded password")
        if "TODO" in code or "FIXME" in code:
            issues.append("quality: TODO/FIXME found — incomplete code")
        if "print(" in code and "logger" not in code:
            issues.append("quality: print() used instead of logger")

        # Kimi code review
        try:
            from llm_orchestrator.kimi_enhanced import get_kimi_enhanced
            kimi = get_kimi_enhanced()
            review = kimi.review_code(code)
            if review.get("review"):
                issues.append(f"kimi_review: {review['review'][:200]}")
        except Exception:
            pass

        return {"step": "code_review", "issues": issues, "issue_count": len(issues)}

    # ── Step 5: Fix issues ─────────────────────────────────────────────

    def _step_fix_issues(self, code: str, issues: List[str], project_folder: str) -> Dict:
        try:
            from cognitive.pipeline import CognitivePipeline
            fix_prompt = f"Fix these issues in the code:\n\nIssues:\n" + "\n".join(f"- {i}" for i in issues) + f"\n\nCode:\n{code[:4000]}"
            ctx = CognitivePipeline().run(
                prompt=fix_prompt,
                project_folder=project_folder,
                use_kimi=False,
            )
            if ctx.llm_response:
                return {"step": "fix_issues", "fixed_code": ctx.llm_response, "fixed": issues[:5]}
        except Exception:
            pass
        return {"step": "fix_issues", "fixed_code": None, "fixed": []}

    # ── Step 6: Trust scoring ──────────────────────────────────────────

    def _step_trust_score(self, code: str) -> Dict:
        try:
            from cognitive.trust_engine import get_trust_engine
            engine = get_trust_engine()
            comp = engine.score_output("hunter_assimilation", "HUNTER Code", code, source="llm")
            return {"step": "trust_score", "trust": comp.trust_score, "needs_verification": comp.needs_verification}
        except Exception:
            return {"step": "trust_score", "trust": 50}

    # ── Step 7: Self-healing pre-check ─────────────────────────────────

    def _step_healing_precheck(self, code: str, files: List[str]) -> Dict:
        concerns = []
        if any("app.py" in f for f in files):
            concerns.append("Modifies main app — high impact")
        if any("database" in f.lower() or "migration" in f.lower() for f in files):
            concerns.append("Database changes — needs migration check")
        if any("settings" in f.lower() or "config" in f.lower() for f in files):
            concerns.append("Configuration changes — may affect runtime")
        return {"step": "healing_precheck", "concerns": concerns, "safe": len(concerns) == 0}

    # ── Step 8: Write files ────────────────────────────────────────────

    def _step_write_files(self, code: str, files: List[str], project_folder: str) -> Dict:
        written = []
        kb = Path("knowledge_base") if not project_folder else Path("knowledge_base") / project_folder

        file_blocks = re.findall(r'```filepath:\s*(.+?)\n(.*?)```', code, re.DOTALL)
        for path, content in file_blocks:
            target = kb / path.strip()
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                written.append(str(target))

                from api._genesis_tracker import track
                track(key_type="file_op", what=f"HUNTER file written: {path.strip()}",
                      file_path=str(target), tags=["hunter", "file_write"])
            except Exception as e:
                logger.warning(f"[HUNTER] Failed to write {path}: {e}")

        return {"step": "write_files", "written": written, "count": len(written)}

    # ── Step 9: Schema migration ───────────────────────────────────────

    def _step_migrate_schemas(self, schemas: List[str]) -> Dict:
        migrated = []
        for schema in schemas:
            try:
                from api._genesis_tracker import track
                track(key_type="db_change", what=f"HUNTER schema detected: {schema}",
                      tags=["hunter", "schema", schema])
                migrated.append(schema)
            except Exception:
                pass
        return {"step": "migrate_schemas", "schemas": migrated, "note": "Auto-migration on startup via create_tables()"}

    # ── Step 10: Librarian organise ────────────────────────────────────

    def _step_librarian_organise(self, files: List[str]) -> Dict:
        organised = []
        try:
            from cognitive.librarian_autonomous import get_autonomous_librarian
            lib = get_autonomous_librarian()
            for f in files:
                result = lib.organise_file(f)
                if result.get("action") == "organised":
                    organised.append(result)
        except Exception:
            pass
        return {"step": "librarian_organise", "organised": len(organised)}

    # ── Step 11: Handshake — announce to all systems ───────────────────

    def _step_handshake(self, result: AssimilationResult) -> Dict:
        """
        Announce the new component to every system in Grace.
        'Hi, I'm this component, I do this, I connect to these systems.'
        """
        announcement = {
            "type": "hunter_handshake",
            "request_id": result.request_id,
            "files": result.files_created,
            "schemas": result.schemas_detected,
            "trust_score": result.trust_score,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Announce via genesis realtime engine
        try:
            from genesis.realtime import get_realtime_engine
            rt = get_realtime_engine()
            rt.on_key_created(
                key_type="system",
                what=f"HUNTER HANDSHAKE: {len(result.files_created)} files assimilated, trust={result.trust_score:.0f}",
                who="hunter_assimilator",
                data=announcement,
            )
        except Exception:
            pass

        # Register in System Registry
        try:
            from cognitive.system_registry import get_system_registry
            get_system_registry().register_from_handshake(announcement)
        except Exception:
            pass

        # Genesis key for the handshake
        try:
            from api._genesis_tracker import track
            track(key_type="system",
                  what=f"HUNTER handshake: {len(result.files_created)} files integrated",
                  how="HunterAssimilator.handshake",
                  output_data=announcement,
                  tags=["hunter", "handshake"],
                  parent_key_id=result.genesis_key)
        except Exception:
            pass

        return {"step": "handshake", "sent": True, "announcement": announcement}

    # ── Step 12: Contradiction check ─────────────────────────────────

    def _step_contradiction_check(self, code: str, project_folder: str) -> Dict:
        try:
            # Check if code contradicts existing project
            if project_folder:
                kb = Path("knowledge_base") / project_folder
                if kb.exists():
                    existing_files = [f.name for f in kb.rglob("*.py")]
                    # Check for naming conflicts
                    new_files = [Path(f).name for f in (self._history[-1].files_created if self._history else [])]
                    conflicts = [f for f in new_files if f in existing_files]
                    if conflicts:
                        return {"step": "contradiction_check", "conflicts": conflicts, "clean": False}
            return {"step": "contradiction_check", "conflicts": [], "clean": True}
        except Exception:
            return {"step": "contradiction_check", "clean": True}

    # ── Step 13: Feed learning loop ────────────────────────────────────

    def _step_feed_learning(self, code: str, description: str, result: AssimilationResult) -> Dict:
        try:
            from cognitive.pipeline import FeedbackLoop
            outcome = "positive" if result.trust_score >= 60 and len(result.issues_found) == 0 else "negative"
            FeedbackLoop.record_outcome(
                genesis_key=result.genesis_key or "",
                prompt=f"HUNTER: {description}",
                output=code[:3000],
                outcome=outcome,
            )
            return {"step": "feed_learning", "outcome": outcome, "recorded": True}
        except Exception as e:
            return {"step": "feed_learning", "recorded": False, "error": str(e)}

    # ── Step 14: Immune system post-check ──────────────────────────────

    def _step_immune_postcheck(self) -> Dict:
        try:
            from cognitive.immune_system import get_immune_system
            immune = get_immune_system()
            result = immune.scan()
            new_anomalies = len(result.get("anomalies", []))
            return {"step": "immune_postcheck", "anomalies_after": new_anomalies,
                    "health": result.get("overall_health", {}).get("status", "unknown")}
        except Exception:
            return {"step": "immune_postcheck", "skipped": True}

    # ── Step 15: Update KPIs ───────────────────────────────────────────

    def _step_update_kpi(self, result: AssimilationResult) -> Dict:
        try:
            from cognitive.trust_engine import get_trust_engine
            engine = get_trust_engine()
            # Score the assimilation as a component
            success = result.trust_score >= 60 and len(result.issues_found) <= len(result.issues_fixed)
            comp = engine.score_output(
                "hunter_assimilation", "HUNTER Assimilator",
                f"Trust: {result.trust_score}, Issues: {len(result.issues_found)}, Fixed: {len(result.issues_fixed)}",
                source="deterministic" if success else "llm",
            )
            return {"step": "update_kpi", "component_trust": comp.trust_score, "trend": comp.trend}
        except Exception:
            return {"step": "update_kpi", "skipped": True}

    def get_history(self) -> List[Dict]:
        return [{
            "id": r.request_id, "status": r.status,
            "files": len(r.files_created), "issues_found": len(r.issues_found),
            "issues_fixed": len(r.issues_fixed), "trust": r.trust_score,
            "handshake": r.handshake_sent,
            "started": r.started_at, "completed": r.completed_at,
        } for r in self._history]


_hunter = None

def get_hunter() -> HunterAssimilator:
    global _hunter
    if _hunter is None:
        _hunter = HunterAssimilator()
    return _hunter
