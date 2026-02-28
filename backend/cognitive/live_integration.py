"""
Live Integration Protocol (LIP) — Real-Time Component Integration

When a developer vibe-codes a new component via Grace IDE, it auto-integrates
into Grace's internal world in REAL TIME:

  File Created → Scan → Validate → Analyse → Trust Score → Compass Map →
  Register → Grant Citizenship → Go Live

Citizenship Levels:
  VISITOR   — just arrived, monitored, limited access
  RESIDENT  — basic integration, passed validation
  CITIZEN   — full integration, trusted, can be called by other systems
  ELDER     — core component, high trust, proven over time

The protocol ensures every new .py file becomes a "citizen" of Grace's
cognitive world — the Architecture Compass updates, the Pipeline knows about it,
Trust Engine scores it, and Grace can explain what it does.
"""

import ast
import hashlib
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).parent.parent


class IntegrationStage(str, Enum):
    DISCOVERED = "discovered"
    SYNTAX_OK = "syntax_ok"
    ANALYSED = "analysed"
    TRUST_SCORED = "trust_scored"
    COMPASS_MAPPED = "compass_mapped"
    REGISTERED = "registered"
    CITIZENSHIP_GRANTED = "citizenship_granted"
    LIVE = "live"
    FAILED = "failed"


class CitizenshipLevel(str, Enum):
    NONE = "none"
    VISITOR = "visitor"
    RESIDENT = "resident"
    CITIZEN = "citizen"
    ELDER = "elder"


@dataclass
class ComponentCandidate:
    file_path: str
    source_code: str
    file_hash: str
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    purpose: str = ""
    capabilities: List[str] = field(default_factory=list)
    stage: IntegrationStage = IntegrationStage.DISCOVERED
    trust_score: float = 0.0
    citizenship: CitizenshipLevel = CitizenshipLevel.NONE
    errors: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# Citizenship ledger — persisted to disk
_LEDGER_PATH = BACKEND_DIR / "data" / "citizenship_ledger.json"
_ledger: Dict[str, Dict[str, Any]] = {}
_ledger_lock = threading.Lock()


def _load_ledger():
    global _ledger
    if _LEDGER_PATH.exists():
        try:
            _ledger = json.loads(_LEDGER_PATH.read_text())
        except Exception:
            _ledger = {}


def _save_ledger():
    _LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _ledger_lock:
        _LEDGER_PATH.write_text(json.dumps(_ledger, indent=2, default=str))


_load_ledger()


def integrate_component(file_path: str, source_code: str = None) -> Dict[str, Any]:
    """
    Full integration pipeline for a new component.
    Takes a file from DISCOVERED to LIVE in one call.
    Returns the integration result with citizenship level.
    """
    path = Path(file_path)
    if not path.suffix == ".py":
        return {"error": "Only Python files can be integrated", "file": file_path}

    if source_code is None:
        full_path = BACKEND_DIR / file_path if not Path(file_path).is_absolute() else Path(file_path)
        if not full_path.exists():
            return {"error": f"File not found: {file_path}"}
        source_code = full_path.read_text(errors="ignore")

    candidate = ComponentCandidate(
        file_path=file_path,
        source_code=source_code,
        file_hash=hashlib.sha256(source_code.encode()).hexdigest(),
    )

    # Stage 1: Syntax validation
    candidate = _stage_syntax(candidate)
    if candidate.stage == IntegrationStage.FAILED:
        return _result(candidate)

    # Stage 2: Semantic analysis
    candidate = _stage_analyse(candidate)

    # Stage 3: Trust scoring
    candidate = _stage_trust(candidate)

    # Stage 4: Architecture Compass mapping
    candidate = _stage_compass(candidate)

    # Stage 5: Registration
    candidate = _stage_register(candidate)

    # Stage 6: Citizenship
    candidate = _stage_citizenship(candidate)

    # Stage 7: Go live
    candidate = _stage_live(candidate)

    return _result(candidate)


def _stage_syntax(c: ComponentCandidate) -> ComponentCandidate:
    """Validate Python syntax."""
    try:
        tree = ast.parse(c.source_code)
        c.classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        c.functions = [n.name for n in ast.walk(tree)
                       if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")]

        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        c.imports = list(set(imports))

        c.stage = IntegrationStage.SYNTAX_OK
    except SyntaxError as e:
        c.stage = IntegrationStage.FAILED
        c.errors.append(f"Syntax error: {e}")
    return c


def _stage_analyse(c: ComponentCandidate) -> ComponentCandidate:
    """Analyse what the component does — extract purpose and capabilities."""
    # Extract docstring
    try:
        tree = ast.parse(c.source_code)
        docstring = ast.get_docstring(tree) or ""
    except Exception:
        docstring = ""

    # Determine purpose from docstring and structure
    if docstring:
        c.purpose = docstring.split("\n")[0][:200]
    else:
        c.purpose = f"Module with {len(c.classes)} classes and {len(c.functions)} functions"

    # Extract capabilities from function names and docstrings
    capabilities = set()
    for func in c.functions:
        if "search" in func.lower() or "query" in func.lower():
            capabilities.add("search")
        if "generate" in func.lower() or "create" in func.lower():
            capabilities.add("generation")
        if "heal" in func.lower() or "fix" in func.lower():
            capabilities.add("healing")
        if "learn" in func.lower() or "train" in func.lower():
            capabilities.add("learning")
        if "score" in func.lower() or "trust" in func.lower():
            capabilities.add("scoring")
        if "upload" in func.lower() or "ingest" in func.lower():
            capabilities.add("ingestion")
        if "analyse" in func.lower() or "analyze" in func.lower():
            capabilities.add("analysis")
        if "route" in func.lower() or "dispatch" in func.lower():
            capabilities.add("routing")

    c.capabilities = list(capabilities)
    c.stage = IntegrationStage.ANALYSED
    return c


def _stage_trust(c: ComponentCandidate) -> ComponentCandidate:
    """Calculate initial trust score."""
    score = 0.3  # Base for new component

    # Bonus for having docstrings
    if c.purpose and len(c.purpose) > 20:
        score += 0.1

    # Bonus for connecting to existing Grace systems
    grace_imports = [i for i in c.imports
                     if any(i.startswith(p) for p in ["cognitive.", "api.", "llm_orchestrator.", "genesis."])]
    score += min(0.2, len(grace_imports) * 0.05)

    # Bonus for having tests-like patterns
    if any("test" in f.lower() for f in c.functions):
        score += 0.05

    # Penalty for being too large (complexity)
    line_count = c.source_code.count("\n")
    if line_count > 500:
        score -= 0.05
    if line_count > 1000:
        score -= 0.1

    # Penalty for no functions (likely dead code)
    if not c.functions and not c.classes:
        score -= 0.15

    c.trust_score = max(0.1, min(1.0, score))

    try:
        from cognitive.trust_engine import get_trust_engine
        te = get_trust_engine()
        comp_name = Path(c.file_path).stem
        te.score_output(f"component_{comp_name}", f"New: {comp_name}", c.purpose, source="internal")
    except Exception:
        pass

    c.stage = IntegrationStage.TRUST_SCORED
    return c


def _stage_compass(c: ComponentCandidate) -> ComponentCandidate:
    """Update Architecture Compass with new component."""
    try:
        from cognitive.architecture_compass import get_compass, COMPONENT_KNOWLEDGE

        # Add to the knowledge base
        rel_path = c.file_path
        COMPONENT_KNOWLEDGE[rel_path] = {
            "purpose": c.purpose,
            "capabilities": c.capabilities,
            "key_apis": c.functions[:5],
        }

        # Rebuild compass to include new component
        compass = get_compass()
        compass._built = False  # Force rebuild
        compass.build()

        c.stage = IntegrationStage.COMPASS_MAPPED
    except Exception as e:
        c.errors.append(f"Compass mapping: {e}")
        c.stage = IntegrationStage.COMPASS_MAPPED  # Non-fatal

    return c


def _stage_register(c: ComponentCandidate) -> ComponentCandidate:
    """Register in the citizenship ledger and event bus."""
    with _ledger_lock:
        _ledger[c.file_path] = {
            "file_hash": c.file_hash,
            "classes": c.classes,
            "functions": c.functions,
            "purpose": c.purpose,
            "capabilities": c.capabilities,
            "trust_score": c.trust_score,
            "citizenship": c.citizenship.value,
            "integrated_at": c.timestamp,
            "stage": c.stage.value,
        }

    _save_ledger()

    # Fire event
    try:
        from cognitive.event_bus import publish
        publish("component.registered", {
            "file": c.file_path,
            "classes": c.classes,
            "functions": c.functions[:5],
            "trust": c.trust_score,
        }, source="live_integration")
    except Exception:
        pass

    # Genesis Key
    try:
        from api._genesis_tracker import track
        track(
            key_type="system",
            what=f"Component registered: {c.file_path} ({len(c.classes)} classes, {len(c.functions)} funcs)",
            where=c.file_path,
            how="live_integration.integrate_component",
            output_data={
                "purpose": c.purpose,
                "capabilities": c.capabilities,
                "trust": c.trust_score,
            },
            tags=["live_integration", "component_registered"],
        )
    except Exception:
        pass

    c.stage = IntegrationStage.REGISTERED
    return c


def _stage_citizenship(c: ComponentCandidate) -> ComponentCandidate:
    """Grant citizenship level based on trust and validation."""
    if c.trust_score >= 0.7 and not c.errors:
        c.citizenship = CitizenshipLevel.CITIZEN
    elif c.trust_score >= 0.5:
        c.citizenship = CitizenshipLevel.RESIDENT
    elif c.trust_score >= 0.3:
        c.citizenship = CitizenshipLevel.VISITOR
    else:
        c.citizenship = CitizenshipLevel.NONE

    # Update ledger
    with _ledger_lock:
        if c.file_path in _ledger:
            _ledger[c.file_path]["citizenship"] = c.citizenship.value

    _save_ledger()

    c.stage = IntegrationStage.CITIZENSHIP_GRANTED
    return c


def _stage_live(c: ComponentCandidate) -> ComponentCandidate:
    """Mark component as live — fully integrated into Grace's world."""
    # Store in unified memory
    try:
        from cognitive.unified_memory import get_unified_memory
        mem = get_unified_memory()
        mem.store_learning(
            input_ctx=f"New component: {c.file_path}",
            expected=c.purpose,
            actual=f"Classes: {c.classes}, Functions: {c.functions[:10]}",
            trust=c.trust_score,
            source="live_integration",
            example_type="component_knowledge",
        )
    except Exception:
        pass

    # Store in FlashCache for keyword discovery
    try:
        from cognitive.flash_cache import get_flash_cache
        fc = get_flash_cache()
        kw = fc.extract_keywords(f"{c.purpose} {' '.join(c.functions)}")
        fc.register(
            source_uri=f"internal://component/{c.file_path}",
            source_type="internal",
            source_name=Path(c.file_path).stem,
            keywords=kw + c.capabilities,
            summary=c.purpose,
            trust_score=c.trust_score,
            ttl_hours=8760,
        )
    except Exception:
        pass

    c.stage = IntegrationStage.LIVE
    return c


def _result(c: ComponentCandidate) -> Dict[str, Any]:
    return {
        "file_path": c.file_path,
        "stage": c.stage.value,
        "trust_score": c.trust_score,
        "citizenship": c.citizenship.value,
        "purpose": c.purpose,
        "capabilities": c.capabilities,
        "classes": c.classes,
        "functions": c.functions[:20],
        "imports": c.imports[:20],
        "errors": c.errors,
        "success": c.stage == IntegrationStage.LIVE,
    }


# ── Bulk Integration ─────────────────────────────────────────────────

def integrate_directory(dir_path: str) -> Dict[str, Any]:
    """Integrate all Python files in a directory."""
    path = BACKEND_DIR / dir_path if not Path(dir_path).is_absolute() else Path(dir_path)
    if not path.exists() or not path.is_dir():
        return {"error": f"Directory not found: {dir_path}"}

    results = []
    for f in sorted(path.rglob("*.py")):
        if f.name == "__init__.py":
            continue
        rel = str(f.relative_to(BACKEND_DIR))
        result = integrate_component(rel)
        results.append(result)

    successful = sum(1 for r in results if r.get("success"))
    return {
        "directory": dir_path,
        "total": len(results),
        "successful": successful,
        "failed": len(results) - successful,
        "results": results,
    }


def get_citizenship_ledger() -> Dict[str, Any]:
    """Get the full citizenship ledger."""
    _load_ledger()
    with _ledger_lock:
        citizens = {k: v for k, v in _ledger.items() if v.get("citizenship") in ("citizen", "elder")}
        residents = {k: v for k, v in _ledger.items() if v.get("citizenship") == "resident"}
        visitors = {k: v for k, v in _ledger.items() if v.get("citizenship") == "visitor"}

    return {
        "total": len(_ledger),
        "citizens": len(citizens),
        "residents": len(residents),
        "visitors": len(visitors),
        "ledger": _ledger,
    }


def promote_component(file_path: str, level: str) -> Dict[str, Any]:
    """Manually promote a component's citizenship level."""
    with _ledger_lock:
        if file_path not in _ledger:
            return {"error": f"Component not found: {file_path}"}
        _ledger[file_path]["citizenship"] = level
        _ledger[file_path]["promoted_at"] = datetime.utcnow().isoformat()

    _save_ledger()
    return {"promoted": True, "file": file_path, "level": level}
