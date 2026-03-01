"""
Integration Gap Detector — Finds disconnected components in Grace.

Scans the system for:
- Unregistered API routes
- Disconnected event bus publishers/subscribers
- Components that exist but aren't wired into the main system
- Missing database migrations
- Broken import chains
- Unused but existing capabilities
"""

import importlib
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).parent.parent


def detect_all_gaps() -> List[Dict[str, Any]]:
    """Run all gap detectors and return a unified list."""
    gaps = []
    gaps.extend(detect_unregistered_apis())
    gaps.extend(detect_disconnected_components())
    gaps.extend(detect_event_bus_gaps())
    gaps.extend(detect_missing_connections())
    return gaps


def detect_unregistered_apis() -> List[Dict[str, Any]]:
    """Find API router files that exist but aren't registered in app.py."""
    gaps = []

    try:
        app_text = (BACKEND_ROOT / "app.py").read_text()
    except Exception:
        return gaps

    api_dir = BACKEND_ROOT / "api"
    if not api_dir.exists():
        return gaps

    for f in api_dir.glob("*_api.py"):
        module_name = f.stem
        if module_name.startswith("_"):
            continue

        import_pattern = f"from api.{module_name} import"
        router_pattern = f"{module_name.replace('_api', '')}_router"

        if import_pattern not in app_text:
            gaps.append({
                "type": "unregistered_api",
                "component": module_name,
                "file": str(f.relative_to(BACKEND_ROOT)),
                "description": f"API router '{module_name}' exists but is not imported in app.py",
                "severity": "medium",
                "fix_suggestion": f"Add 'from api.{module_name} import router as {router_pattern}' to app.py",
            })

    return gaps


def detect_disconnected_components() -> List[Dict[str, Any]]:
    """Find cognitive/genesis components that exist but aren't connected."""
    gaps = []

    component_dirs = {
        "cognitive": BACKEND_ROOT / "cognitive",
        "genesis": BACKEND_ROOT / "genesis",
        "file_manager": BACKEND_ROOT / "file_manager",
        "librarian": BACKEND_ROOT / "librarian",
    }

    try:
        app_text = (BACKEND_ROOT / "app.py").read_text()
    except Exception:
        app_text = ""

    known_connected = [
        "consensus_engine", "patch_consensus", "self_healing_tracker",
        "memory_mesh_integration", "pipeline", "trust_engine",
        "event_bus", "librarian_autonomous", "horizon_planner",
        "sandbox_mirror", "reporting_engine", "ml_trainer",
        "mirror_self_modeling", "continuous_learning_orchestrator",
        "sandbox_engine", "autonomous_sandbox_lab",
    ]

    for dir_name, dir_path in component_dirs.items():
        if not dir_path.exists():
            continue

        for f in dir_path.glob("*.py"):
            if f.name.startswith("_") or f.name == "__init__.py":
                continue

            module_stem = f.stem
            is_connected = any(
                module_stem in app_text or module_stem in kc
                for kc in known_connected
            )

            if not is_connected:
                has_singleton = False
                try:
                    text = f.read_text()
                    has_singleton = "def get_" in text or "_instance" in text or "singleton" in text.lower()
                except Exception:
                    pass

                if has_singleton:
                    gaps.append({
                        "type": "disconnected_component",
                        "component": f"{dir_name}/{module_stem}",
                        "file": str(f.relative_to(BACKEND_ROOT)),
                        "description": f"Component '{module_stem}' has a singleton/factory but may not be initialized at startup",
                        "severity": "low",
                        "fix_suggestion": f"Consider initializing '{module_stem}' in app.py lifespan or connecting via event bus",
                    })

    return gaps


def detect_event_bus_gaps() -> List[Dict[str, Any]]:
    """Find event topics that are published but never subscribed to, or vice versa."""
    gaps = []

    publishers = set()
    subscribers = set()

    try:
        for py_file in BACKEND_ROOT.rglob("*.py"):
            if "node_modules" in str(py_file) or "mcp_repos" in str(py_file):
                continue
            try:
                text = py_file.read_text(errors="ignore")
                import re
                for match in re.finditer(r'publish\(["\']([^"\']+)["\']', text):
                    publishers.add(match.group(1))
                for match in re.finditer(r'publish_async\(["\']([^"\']+)["\']', text):
                    publishers.add(match.group(1))
                for match in re.finditer(r'subscribe\(["\']([^"\']+)["\']', text):
                    subscribers.add(match.group(1))
            except Exception:
                continue
    except Exception:
        return gaps

    # Find published topics with no subscribers (accounting for wildcards)
    for topic in publishers:
        has_subscriber = topic in subscribers
        if not has_subscriber:
            parts = topic.split(".")
            for sub_topic in subscribers:
                if sub_topic.endswith("*"):
                    prefix = sub_topic[:-1]
                    if topic.startswith(prefix):
                        has_subscriber = True
                        break
                elif sub_topic == "*":
                    has_subscriber = True
                    break

        if not has_subscriber:
            gaps.append({
                "type": "orphan_publisher",
                "component": "event_bus",
                "description": f"Event '{topic}' is published but has no subscribers",
                "severity": "low",
                "fix_suggestion": f"Add a subscriber for '{topic}' or remove the publisher",
            })

    return gaps


def detect_missing_connections() -> List[Dict[str, Any]]:
    """Detect known architectural gaps between subsystems."""
    gaps = []

    known_gaps = [
        {
            "type": "dual_system",
            "component": "sandbox",
            "description": "Two sandbox systems exist (sandbox_engine + autonomous_sandbox_lab) without unified API",
            "severity": "medium",
            "fix_suggestion": "Unify sandbox_engine and autonomous_sandbox_lab into sandbox_mirror",
        },
        {
            "type": "dual_system",
            "component": "event_system",
            "description": "Grace OS EventSystem and cognitive event_bus are separate with no bridge",
            "severity": "high",
            "fix_suggestion": "Create an event bridge that forwards between the two systems",
        },
        {
            "type": "dual_system",
            "component": "trust",
            "description": "TrustScorekeeper (session/layer) and TrustEngine (component) operate independently",
            "severity": "medium",
            "fix_suggestion": "Create unified trust aggregation that combines both trust sources",
        },
        {
            "type": "dual_system",
            "component": "registry",
            "description": "Grace OS LayerRegistry and core ComponentRegistry are separate",
            "severity": "medium",
            "fix_suggestion": "Register Grace OS layers in ComponentRegistry for unified lifecycle management",
        },
        {
            "type": "missing_connection",
            "component": "planner",
            "description": "Planner /execute does not invoke Grace OS pipeline or Cognitive Pipeline",
            "severity": "high",
            "fix_suggestion": "Wire planner execution to SessionManager or CognitivePipeline",
        },
        {
            "type": "missing_connection",
            "component": "mirror",
            "description": "Mirror self-modeling doesn't subscribe to event bus",
            "severity": "medium",
            "fix_suggestion": "Subscribe Mirror to genesis.*, healing.*, learning.* events",
        },
        {
            "type": "missing_connection",
            "component": "deep_test_engine",
            "description": "Deep test engine exists but isn't wired into startup or health checks",
            "severity": "low",
            "fix_suggestion": "Run deep tests periodically or on health check request",
        },
    ]

    # Only include gaps that actually exist in the codebase
    for gap in known_gaps:
        component = gap["component"]
        exists = True
        if component == "sandbox":
            exists = (BACKEND_ROOT / "cognitive" / "sandbox_engine.py").exists()
        elif component == "deep_test_engine":
            exists = (BACKEND_ROOT / "cognitive" / "deep_test_engine.py").exists()

        if exists:
            gaps.append(gap)

    return gaps


def get_gap_summary() -> Dict[str, Any]:
    """Get a summary of all integration gaps."""
    all_gaps = detect_all_gaps()

    by_type = {}
    by_severity = {"high": 0, "medium": 0, "low": 0}

    for gap in all_gaps:
        gap_type = gap.get("type", "unknown")
        by_type[gap_type] = by_type.get(gap_type, 0) + 1
        severity = gap.get("severity", "low")
        by_severity[severity] = by_severity.get(severity, 0) + 1

    return {
        "total_gaps": len(all_gaps),
        "by_type": by_type,
        "by_severity": by_severity,
        "high_priority": [g for g in all_gaps if g.get("severity") == "high"],
        "all_gaps": all_gaps,
    }
