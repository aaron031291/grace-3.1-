"""
Project Container — each project is an isolated environment.

Manages: governance rules (3-tier), resource bridges, knowledge,
whitelist, and the full project lifecycle.

Rule hierarchy: GLOBAL (immutable) → PROJECT (per-project) → EXECUTION (per-task)
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
PROJECTS_DIR = DATA_DIR / "projects"

# ═══════════════════════════════════════════════════════════════════
#  GLOBAL RULES — immutable defaults, cannot be removed
# ═══════════════════════════════════════════════════════════════════

GLOBAL_RULES = [
    "All code must pass syntax validation before deployment",
    "All generated code must go through security scanning",
    "Every action must create a Genesis key for audit",
    "Trust score must be above 0.5 for autonomous execution",
    "Consensus mechanism must agree before deployment",
    "Anti-hallucination checks must pass at every pipeline layer",
    "Human approval required for destructive operations",
    "All data must be tracked with provenance",
]


# ═══════════════════════════════════════════════════════════════════
#  PROJECT CONTAINER
# ═══════════════════════════════════════════════════════════════════

class ProjectContainer:
    """An isolated environment for a project — everything self-contained."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.root = PROJECTS_DIR / project_id
        self._ensure_structure()

    def _ensure_structure(self):
        """Create the full project structure."""
        dirs = [
            "frontend", "backend", "docs", "tests",
            "governance", "knowledge", "whitelist",
            "reports", "data",
        ]
        for d in dirs:
            (self.root / d).mkdir(parents=True, exist_ok=True)

        # Write global rules if not present
        global_file = self.root / "governance" / "_global_rules.md"
        if not global_file.exists():
            global_file.write_text(
                "# Global Rules (Immutable)\n\n" +
                "\n".join(f"- {r}" for r in GLOBAL_RULES)
            )

    # ── Rule Management ────────────────────────────────────────

    def get_rules(self) -> dict:
        """Get all rules: global + project + execution."""
        gov_dir = self.root / "governance"
        project_rules = []
        for f in sorted(gov_dir.glob("*")):
            if f.name.startswith("_"):
                continue
            if f.is_file():
                project_rules.append({
                    "name": f.name,
                    "content": f.read_text(errors="ignore")[:500],
                    "size": f.stat().st_size,
                })

        return {
            "global_rules": GLOBAL_RULES,
            "project_rules": project_rules,
            "total": len(GLOBAL_RULES) + len(project_rules),
        }

    def add_rule(self, name: str, content: str) -> dict:
        """Add a project-level rule."""
        filepath = self.root / "governance" / name
        filepath.write_text(content, encoding="utf-8")
        return {"added": True, "name": name}

    # ── Knowledge Management ───────────────────────────────────

    def get_knowledge(self) -> dict:
        """Get project knowledge sources."""
        kb_dir = self.root / "knowledge"
        sources = []
        for f in sorted(kb_dir.rglob("*")):
            if f.is_file():
                sources.append({
                    "name": f.name,
                    "path": str(f.relative_to(self.root)),
                    "size": f.stat().st_size,
                    "type": f.suffix.lstrip("."),
                })
        return {"sources": sources, "total": len(sources)}

    def add_knowledge(self, name: str, content: str) -> dict:
        """Add a knowledge source."""
        filepath = self.root / "knowledge" / name
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding="utf-8")
        return {"added": True, "name": name, "path": str(filepath.relative_to(self.root))}

    # ── Whitelist Management ───────────────────────────────────

    def get_whitelist(self) -> dict:
        """Get project whitelist (approved sources)."""
        wl_file = self.root / "whitelist" / "sources.json"
        if wl_file.exists():
            try:
                return json.loads(wl_file.read_text())
            except Exception:
                pass
        return {"api_sources": [], "web_sources": [], "rules": ""}

    def update_whitelist(self, data: dict) -> dict:
        """Update project whitelist."""
        wl_file = self.root / "whitelist" / "sources.json"
        wl_file.parent.mkdir(parents=True, exist_ok=True)
        data["updated_at"] = datetime.utcnow().isoformat()
        wl_file.write_text(json.dumps(data, indent=2))
        return {"updated": True}

    # ── Context Bridge ─────────────────────────────────────────

    def get_context(self, max_chars: int = 10000) -> str:
        """Build full project context for LLM injection."""
        parts = [f"Project: {self.project_id}"]
        total = 0

        # Rules
        rules = self.get_rules()
        parts.append(f"\nRules: {rules['total']} active")

        # Knowledge
        knowledge = self.get_knowledge()
        parts.append(f"Knowledge sources: {knowledge['total']}")

        # Code files
        for f in self.root.rglob("*"):
            if f.is_file() and f.suffix in (".py", ".js", ".ts", ".md", ".json", ".txt"):
                if any(skip in str(f) for skip in ["__pycache__", ".git", "node_modules"]):
                    continue
                try:
                    content = f.read_text(errors="ignore")[:300]
                    rel = str(f.relative_to(self.root))
                    snippet = f"\n--- {rel} ---\n{content}"
                    if total + len(snippet) > max_chars:
                        break
                    parts.append(snippet)
                    total += len(snippet)
                except Exception:
                    pass

        return "\n".join(parts)

    # ── Stats ──────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Get project container stats."""
        file_count = sum(1 for _ in self.root.rglob("*") if _.is_file())
        size = sum(f.stat().st_size for f in self.root.rglob("*") if f.is_file())
        return {
            "project_id": self.project_id,
            "file_count": file_count,
            "size_mb": round(size / 1048576, 2),
            "rules": len(self.get_rules()["project_rules"]),
            "knowledge_sources": self.get_knowledge()["total"],
            "path": str(self.root),
        }


# ═══════════════════════════════════════════════════════════════════
#  CONTAINER MANAGER
# ═══════════════════════════════════════════════════════════════════

_containers: Dict[str, ProjectContainer] = {}


def get_container(project_id: str) -> ProjectContainer:
    """Get or create a project container."""
    if project_id not in _containers:
        _containers[project_id] = ProjectContainer(project_id)
    return _containers[project_id]


def list_containers() -> list:
    """List all project containers."""
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    containers = []
    for d in sorted(PROJECTS_DIR.iterdir()):
        if d.is_dir() and not d.name.startswith("."):
            c = get_container(d.name)
            containers.append(c.get_stats())
    return containers


def clone_grace_environment(target_project: str) -> dict:
    """
    Clone Grace's own infrastructure into a new project.
    This lets Grace build OTHER AI systems using her own architecture.
    """
    source = Path(__file__).parent.parent
    target = PROJECTS_DIR / target_project

    if target.exists():
        return {"error": f"Project {target_project} already exists"}

    # Copy core architecture (read-only template)
    dirs_to_copy = ["core", "api", "database", "models"]
    target.mkdir(parents=True)

    for d in dirs_to_copy:
        src = source / d
        dst = target / "backend" / d
        if src.exists():
            shutil.copytree(str(src), str(dst), ignore=shutil.ignore_patterns(
                "__pycache__", "*.pyc", "*.db", "*.log"))

    # Create frontend scaffold
    (target / "frontend" / "src").mkdir(parents=True)
    (target / "docs").mkdir(exist_ok=True)
    (target / "tests").mkdir(exist_ok=True)
    (target / "governance").mkdir(exist_ok=True)

    # Track via Genesis
    try:
        from api._genesis_tracker import track
        track(key_type="system_event",
              what=f"Grace environment cloned to {target_project}",
              who="project_container",
              tags=["clone", "environment", target_project])
    except Exception:
        pass

    return {"cloned": True, "project": target_project,
            "dirs_copied": dirs_to_copy,
            "path": str(target)}
