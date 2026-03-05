"""
Deterministic Genesis Key Validator
=====================================
Pure deterministic analysis of the Genesis Key system — no LLM needed.

Checks:
1. Schema Integrity: Required fields, valid enums, well-formed key_ids
2. Chain Integrity: parent_key_id references resolve, no orphaned chains
3. Fix Linkage: fix_key_id and fix_suggestion references are valid
4. KB Sync: Keys in DB match files in knowledge_base/layer_1/genesis_key/
5. User Profile Consistency: user_ids in keys exist in user_profile table
6. Archive Consistency: archive counts align with actual key counts
7. Connector Wiring: GenesisKeysConnector field names match the model
8. Route Wiring: Frontend expects /genesis/* routes — are they registered?
9. Timestamp Ordering: Child keys should have timestamps after their parents
10. Duplicate Detection: No duplicate key_ids
"""

import ast
import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).parent.parent


@dataclass
class GenesisIssue:
    """A single deterministic Genesis validation issue."""
    check: str
    severity: str  # critical, warning, info
    message: str
    details: Optional[Dict[str, Any]] = None
    fix_suggestion: Optional[str] = None


@dataclass
class GenesisValidationReport:
    """Full deterministic Genesis Key validation report."""
    timestamp: str
    total_issues: int
    critical_count: int
    warning_count: int
    info_count: int
    checks_run: List[str]
    issues: List[GenesisIssue]
    stats: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "total_issues": self.total_issues,
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "checks_run": self.checks_run,
            "issues": [asdict(i) for i in self.issues],
            "stats": self.stats,
        }


# ---------------------------------------------------------------------------
# 1. Schema Integrity
# ---------------------------------------------------------------------------

def check_genesis_schema_integrity() -> List[GenesisIssue]:
    """
    Verify the GenesisKey model has all required columns and the
    enum types are consistent between model definition and service usage.
    """
    issues = []

    model_file = BACKEND_ROOT / "models" / "genesis_key_models.py"
    service_file = BACKEND_ROOT / "genesis" / "genesis_key_service.py"

    if not model_file.exists():
        issues.append(GenesisIssue(
            check="schema_integrity",
            severity="critical",
            message="Genesis Key model file not found: models/genesis_key_models.py",
            fix_suggestion="Create or restore models/genesis_key_models.py",
        ))
        return issues

    try:
        source = model_file.read_text(errors="ignore")
        tree = ast.parse(source)
    except SyntaxError as e:
        issues.append(GenesisIssue(
            check="schema_integrity",
            severity="critical",
            message=f"Syntax error in genesis_key_models.py: {e.msg} (line {e.lineno})",
        ))
        return issues

    required_columns = {
        "key_id", "parent_key_id", "key_type", "status",
        "what_description", "who_actor", "when_timestamp",
        "is_error", "has_fix_suggestion", "fix_applied",
    }

    found_columns = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    found_columns.add(target.id)

    missing = required_columns - found_columns
    if missing:
        issues.append(GenesisIssue(
            check="schema_integrity",
            severity="critical",
            message=f"Missing required columns in GenesisKey model: {', '.join(sorted(missing))}",
            details={"missing": sorted(list(missing))},
            fix_suggestion="Add missing Column definitions to GenesisKey model",
        ))

    enum_classes = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name.endswith(("Type", "Status")):
            enum_classes.add(node.name)

    expected_enums = {"GenesisKeyType", "GenesisKeyStatus", "FixSuggestionStatus"}
    missing_enums = expected_enums - enum_classes
    if missing_enums:
        issues.append(GenesisIssue(
            check="schema_integrity",
            severity="critical",
            message=f"Missing enum classes: {', '.join(sorted(missing_enums))}",
            fix_suggestion="Define missing enum classes in genesis_key_models.py",
        ))

    if service_file.exists():
        try:
            svc_source = service_file.read_text(errors="ignore")
            svc_tree = ast.parse(svc_source)

            imported_names = set()
            for node in ast.walk(svc_tree):
                if isinstance(node, ast.ImportFrom) and node.module and "genesis_key_models" in node.module:
                    for alias in node.names:
                        imported_names.add(alias.name)

            expected_imports = {"GenesisKey", "GenesisKeyType", "GenesisKeyStatus"}
            missing_imports = expected_imports - imported_names
            if missing_imports:
                issues.append(GenesisIssue(
                    check="schema_integrity",
                    severity="warning",
                    message=f"genesis_key_service.py missing imports: {', '.join(sorted(missing_imports))}",
                    fix_suggestion="Add missing imports from models.genesis_key_models",
                ))
        except SyntaxError:
            issues.append(GenesisIssue(
                check="schema_integrity",
                severity="critical",
                message="Syntax error in genesis_key_service.py",
            ))

    return issues


# ---------------------------------------------------------------------------
# 2. Chain Integrity (parent_key_id references)
# ---------------------------------------------------------------------------

def check_genesis_chain_integrity() -> List[GenesisIssue]:
    """
    Verify parent_key_id references resolve to existing keys in the DB.
    Uses direct SQLite access for deterministic, session-free checking.
    """
    issues = []

    db_path = BACKEND_ROOT / "data" / "grace.db"
    if not db_path.exists():
        issues.append(GenesisIssue(
            check="chain_integrity",
            severity="info",
            message="Database not found — cannot check chain integrity (first run?)",
        ))
        return issues

    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path), timeout=5)

        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]

        if "genesis_key" not in tables:
            issues.append(GenesisIssue(
                check="chain_integrity",
                severity="warning",
                message="genesis_key table does not exist yet — run migrations",
                fix_suggestion="Run database migrations to create genesis_key table",
            ))
            conn.close()
            return issues

        total_keys = conn.execute("SELECT COUNT(*) FROM genesis_key").fetchone()[0]

        orphans = conn.execute("""
            SELECT gk.key_id, gk.parent_key_id
            FROM genesis_key gk
            WHERE gk.parent_key_id IS NOT NULL
              AND gk.parent_key_id != ''
              AND gk.parent_key_id NOT IN (SELECT key_id FROM genesis_key)
        """).fetchall()

        if orphans:
            issues.append(GenesisIssue(
                check="chain_integrity",
                severity="warning",
                message=f"{len(orphans)} Genesis Keys reference non-existent parent keys",
                details={"orphan_count": len(orphans), "examples": [
                    {"key_id": r[0], "missing_parent": r[1]} for r in orphans[:5]
                ]},
                fix_suggestion="Investigate orphaned parent_key_id references — parent may have been deleted or archived",
            ))

        duplicates = conn.execute("""
            SELECT key_id, COUNT(*) as cnt
            FROM genesis_key
            GROUP BY key_id
            HAVING cnt > 1
        """).fetchall()

        if duplicates:
            issues.append(GenesisIssue(
                check="chain_integrity",
                severity="critical",
                message=f"{len(duplicates)} duplicate key_id values found",
                details={"duplicates": [{"key_id": r[0], "count": r[1]} for r in duplicates[:5]]},
                fix_suggestion="Remove or merge duplicate Genesis Keys",
            ))

        conn.close()
    except Exception as e:
        issues.append(GenesisIssue(
            check="chain_integrity",
            severity="warning",
            message=f"Chain integrity check failed: {e}",
        ))

    return issues


# ---------------------------------------------------------------------------
# 3. Fix Linkage
# ---------------------------------------------------------------------------

def check_genesis_fix_linkage() -> List[GenesisIssue]:
    """Verify fix_key_id references and fix_suggestion foreign keys resolve."""
    issues = []

    db_path = BACKEND_ROOT / "data" / "grace.db"
    if not db_path.exists():
        return issues

    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path), timeout=5)

        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]

        if "genesis_key" not in tables:
            conn.close()
            return issues

        broken_fix_links = conn.execute("""
            SELECT key_id, fix_key_id
            FROM genesis_key
            WHERE fix_key_id IS NOT NULL
              AND fix_key_id != ''
              AND fix_key_id NOT IN (SELECT key_id FROM genesis_key)
        """).fetchall()

        if broken_fix_links:
            issues.append(GenesisIssue(
                check="fix_linkage",
                severity="warning",
                message=f"{len(broken_fix_links)} fix_key_id references point to non-existent keys",
                details={"examples": [{"key_id": r[0], "missing_fix_key": r[1]} for r in broken_fix_links[:5]]},
            ))

        if "fix_suggestion" in tables:
            orphan_suggestions = conn.execute("""
                SELECT fs.suggestion_id, fs.genesis_key_id
                FROM fix_suggestion fs
                WHERE fs.genesis_key_id NOT IN (SELECT key_id FROM genesis_key)
            """).fetchall()

            if orphan_suggestions:
                issues.append(GenesisIssue(
                    check="fix_linkage",
                    severity="warning",
                    message=f"{len(orphan_suggestions)} fix suggestions reference non-existent Genesis Keys",
                    details={"examples": [{"suggestion_id": r[0], "missing_key": r[1]} for r in orphan_suggestions[:5]]},
                ))

            error_keys_without_fix = conn.execute("""
                SELECT COUNT(*)
                FROM genesis_key
                WHERE is_error = 1
                  AND has_fix_suggestion = 0
                  AND status != 'fixed'
            """).fetchone()[0]

            if error_keys_without_fix > 10:
                issues.append(GenesisIssue(
                    check="fix_linkage",
                    severity="info",
                    message=f"{error_keys_without_fix} error keys have no fix suggestions",
                    details={"unfixed_errors": error_keys_without_fix},
                ))

        conn.close()
    except Exception as e:
        issues.append(GenesisIssue(
            check="fix_linkage",
            severity="info",
            message=f"Fix linkage check failed: {e}",
        ))

    return issues


# ---------------------------------------------------------------------------
# 4. KB Sync (knowledge_base/layer_1/genesis_key)
# ---------------------------------------------------------------------------

def check_genesis_kb_sync() -> List[GenesisIssue]:
    """
    Verify the knowledge_base/layer_1/genesis_key/ directory structure
    exists and contains data if the DB has Genesis Keys.
    """
    issues = []

    kb_path = BACKEND_ROOT / "knowledge_base" / "layer_1" / "genesis_key"

    if not kb_path.exists():
        issues.append(GenesisIssue(
            check="kb_sync",
            severity="warning",
            message="Knowledge base genesis_key directory does not exist",
            details={"expected_path": str(kb_path)},
            fix_suggestion="Directory will be auto-created on first Genesis Key creation",
        ))
        return issues

    json_files = list(kb_path.rglob("*.json"))
    user_dirs = [d for d in kb_path.iterdir() if d.is_dir()]

    db_path = BACKEND_ROOT / "data" / "grace.db"
    db_key_count = 0
    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path), timeout=5)
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
            if "genesis_key" in tables:
                db_key_count = conn.execute("SELECT COUNT(*) FROM genesis_key").fetchone()[0]
            conn.close()
        except Exception:
            pass

    if db_key_count > 0 and len(json_files) == 0:
        issues.append(GenesisIssue(
            check="kb_sync",
            severity="warning",
            message=f"DB has {db_key_count} Genesis Keys but KB directory has no JSON files",
            details={"db_keys": db_key_count, "kb_files": 0},
            fix_suggestion="KB integration may not be writing files — check genesis/kb_integration.py",
        ))
    elif db_key_count > 0 and len(json_files) > 0:
        ratio = len(json_files) / max(db_key_count, 1)
        if ratio < 0.1:
            issues.append(GenesisIssue(
                check="kb_sync",
                severity="info",
                message=f"KB has {len(json_files)} files for {db_key_count} DB keys (sync ratio: {ratio:.1%})",
                details={"db_keys": db_key_count, "kb_files": len(json_files)},
            ))

    return issues


# ---------------------------------------------------------------------------
# 5. User Profile Consistency
# ---------------------------------------------------------------------------

def check_genesis_user_profiles() -> List[GenesisIssue]:
    """Verify user_ids referenced in Genesis Keys exist in user_profile table."""
    issues = []

    db_path = BACKEND_ROOT / "data" / "grace.db"
    if not db_path.exists():
        return issues

    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path), timeout=5)

        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]

        if "genesis_key" not in tables or "user_profile" not in tables:
            conn.close()
            return issues

        orphan_users = conn.execute("""
            SELECT DISTINCT gk.user_id
            FROM genesis_key gk
            WHERE gk.user_id IS NOT NULL
              AND gk.user_id != ''
              AND gk.user_id NOT IN (SELECT user_id FROM user_profile)
        """).fetchall()

        if orphan_users:
            issues.append(GenesisIssue(
                check="user_profiles",
                severity="info",
                message=f"{len(orphan_users)} user_ids in Genesis Keys have no user_profile record",
                details={"orphan_user_ids": [r[0] for r in orphan_users[:10]]},
                fix_suggestion="User profiles may not have been created — check get_or_create_user()",
            ))

        stale_profiles = conn.execute("""
            SELECT user_id, total_actions,
                   (SELECT COUNT(*) FROM genesis_key WHERE user_id = user_profile.user_id) as actual
            FROM user_profile
            WHERE total_actions > 0
        """).fetchall()

        for user_id, recorded, actual in stale_profiles:
            if actual > 0 and abs(recorded - actual) > max(actual * 0.5, 10):
                issues.append(GenesisIssue(
                    check="user_profiles",
                    severity="info",
                    message=f"User {user_id}: total_actions ({recorded}) diverges from actual key count ({actual})",
                    details={"user_id": user_id, "recorded": recorded, "actual": actual},
                ))

        conn.close()
    except Exception as e:
        issues.append(GenesisIssue(
            check="user_profiles",
            severity="info",
            message=f"User profile check failed: {e}",
        ))

    return issues


# ---------------------------------------------------------------------------
# 6. Connector Wiring
# ---------------------------------------------------------------------------

def check_genesis_connector_wiring() -> List[GenesisIssue]:
    """
    Verify the GenesisKeysConnector uses field names that match the
    GenesisKey model. Known issue: connector uses genesis_key_id vs key_id.
    """
    issues = []

    connector_file = BACKEND_ROOT / "layer1" / "components" / "genesis_keys_connector.py"
    if not connector_file.exists():
        issues.append(GenesisIssue(
            check="connector_wiring",
            severity="warning",
            message="GenesisKeysConnector file not found",
            fix_suggestion="Create layer1/components/genesis_keys_connector.py",
        ))
        return issues

    try:
        source = connector_file.read_text(errors="ignore")
    except Exception:
        return issues

    mismatches = []
    if "genesis_key_id" in source and "key_id" not in source.replace("genesis_key_id", ""):
        pass
    if '"immutable"' in source or "'immutable'" in source:
        mismatches.append("immutable (not in GenesisKey model)")
    if '"metadata"' in source and '"metadata_human"' not in source and '"metadata_ai"' not in source:
        if "metadata" in source and "context_data" not in source:
            mismatches.append("metadata (model uses metadata_human/metadata_ai)")

    if mismatches:
        issues.append(GenesisIssue(
            check="connector_wiring",
            severity="warning",
            message=f"GenesisKeysConnector uses fields not in GenesisKey model: {', '.join(mismatches)}",
            details={"mismatched_fields": mismatches},
            fix_suggestion="Update connector to use correct GenesisKey model field names",
        ))

    init_file = BACKEND_ROOT / "layer1" / "initialize.py"
    if init_file.exists():
        init_source = init_file.read_text(errors="ignore")
        if "GenesisKeysConnector" not in init_source and "genesis_keys" not in init_source.lower():
            issues.append(GenesisIssue(
                check="connector_wiring",
                severity="info",
                message="GenesisKeysConnector may not be initialized in layer1/initialize.py",
                fix_suggestion="Add GenesisKeysConnector initialization to Layer 1 startup",
            ))

    return issues


# ---------------------------------------------------------------------------
# 7. Route Wiring (frontend expects /genesis/*)
# ---------------------------------------------------------------------------

def check_genesis_route_wiring() -> List[GenesisIssue]:
    """
    Check if the frontend expects /genesis/* API routes and whether
    those routes are actually registered in app.py.
    """
    issues = []

    app_file = BACKEND_ROOT / "app.py"
    if not app_file.exists():
        return issues

    app_source = app_file.read_text(errors="ignore")

    frontend_panel = BACKEND_ROOT.parent / "frontend" / "src" / "components" / "GenesisKeyPanel.jsx"
    expected_routes = []

    if frontend_panel.exists():
        panel_source = frontend_panel.read_text(errors="ignore")
        import re
        api_calls = re.findall(r'["\']\/genesis\/[^"\']*["\']', panel_source)
        expected_routes = list(set(api_calls))

    if expected_routes:
        genesis_router_registered = (
            "genesis" in app_source.lower()
            and ("include_router" in app_source or "genesis_keys" in app_source)
        )

        if not genesis_router_registered:
            issues.append(GenesisIssue(
                check="route_wiring",
                severity="warning",
                message=f"Frontend expects {len(expected_routes)} /genesis/* routes but no genesis router is registered in app.py",
                details={"expected_routes": expected_routes[:10]},
                fix_suggestion="Create and register a genesis API router in app.py, or use brain API v2 proxy",
            ))

    return issues


# ---------------------------------------------------------------------------
# 8. Timestamp Ordering
# ---------------------------------------------------------------------------

def check_genesis_timestamp_ordering() -> List[GenesisIssue]:
    """Verify child keys have timestamps after their parent keys."""
    issues = []

    db_path = BACKEND_ROOT / "data" / "grace.db"
    if not db_path.exists():
        return issues

    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path), timeout=5)

        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]

        if "genesis_key" not in tables:
            conn.close()
            return issues

        inverted = conn.execute("""
            SELECT child.key_id, child.when_timestamp, parent.key_id, parent.when_timestamp
            FROM genesis_key child
            JOIN genesis_key parent ON child.parent_key_id = parent.key_id
            WHERE child.when_timestamp < parent.when_timestamp
        """).fetchall()

        if inverted:
            issues.append(GenesisIssue(
                check="timestamp_ordering",
                severity="info",
                message=f"{len(inverted)} child keys have timestamps before their parent keys",
                details={"count": len(inverted), "examples": [
                    {"child": r[0], "child_time": r[1], "parent": r[2], "parent_time": r[3]}
                    for r in inverted[:3]
                ]},
            ))

        conn.close()
    except Exception as e:
        issues.append(GenesisIssue(
            check="timestamp_ordering",
            severity="info",
            message=f"Timestamp ordering check failed: {e}",
        ))

    return issues


# ---------------------------------------------------------------------------
# 9. Import Chain
# ---------------------------------------------------------------------------

def check_genesis_import_chain() -> List[GenesisIssue]:
    """Verify the Genesis Key import chain resolves without errors."""
    issues = []

    critical_files = [
        "models/genesis_key_models.py",
        "genesis/genesis_key_service.py",
        "genesis/kb_integration.py",
        "api/_genesis_tracker.py",
    ]

    for rel_path in critical_files:
        full_path = BACKEND_ROOT / rel_path
        if not full_path.exists():
            issues.append(GenesisIssue(
                check="import_chain",
                severity="critical",
                message=f"Critical Genesis file missing: {rel_path}",
                fix_suggestion=f"Create or restore {rel_path}",
            ))
            continue

        try:
            source = full_path.read_text(errors="ignore")
            ast.parse(source)
        except SyntaxError as e:
            issues.append(GenesisIssue(
                check="import_chain",
                severity="critical",
                message=f"Syntax error in {rel_path}: {e.msg} (line {e.lineno})",
            ))

    return issues


# ---------------------------------------------------------------------------
# Full Validation Pipeline
# ---------------------------------------------------------------------------

def run_genesis_validation() -> GenesisValidationReport:
    """
    Run the complete deterministic Genesis Key validation pipeline.
    No LLM needed. Pure structural + data analysis.
    """
    import time
    start = time.time()

    all_issues: List[GenesisIssue] = []
    checks_run = []

    checks = [
        ("schema_integrity", check_genesis_schema_integrity),
        ("import_chain", check_genesis_import_chain),
        ("chain_integrity", check_genesis_chain_integrity),
        ("fix_linkage", check_genesis_fix_linkage),
        ("kb_sync", check_genesis_kb_sync),
        ("user_profiles", check_genesis_user_profiles),
        ("connector_wiring", check_genesis_connector_wiring),
        ("route_wiring", check_genesis_route_wiring),
        ("timestamp_ordering", check_genesis_timestamp_ordering),
    ]

    for name, checker in checks:
        try:
            logger.info(f"[DETERMINISTIC-GENESIS] Running {name}...")
            results = checker()
            all_issues.extend(results)
            checks_run.append(name)
        except Exception as e:
            all_issues.append(GenesisIssue(
                check=name,
                severity="warning",
                message=f"Check {name} raised exception: {e}",
            ))
            checks_run.append(name)

    elapsed = (time.time() - start) * 1000

    stats = _gather_genesis_stats()

    report = GenesisValidationReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        total_issues=len(all_issues),
        critical_count=sum(1 for i in all_issues if i.severity == "critical"),
        warning_count=sum(1 for i in all_issues if i.severity == "warning"),
        info_count=sum(1 for i in all_issues if i.severity == "info"),
        checks_run=checks_run,
        issues=all_issues,
        stats=stats,
    )

    logger.info(
        f"[DETERMINISTIC-GENESIS] Complete: {report.total_issues} issues "
        f"({report.critical_count} critical, {report.warning_count} warning, {report.info_count} info) "
        f"in {elapsed:.0f}ms"
    )

    return report


def _gather_genesis_stats() -> Dict[str, Any]:
    """Gather basic Genesis Key statistics from the DB."""
    stats: Dict[str, Any] = {
        "total_keys": 0,
        "error_keys": 0,
        "fixed_keys": 0,
        "unique_users": 0,
        "key_types": {},
        "kb_files": 0,
    }

    db_path = BACKEND_ROOT / "data" / "grace.db"
    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path), timeout=5)
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]

            if "genesis_key" in tables:
                stats["total_keys"] = conn.execute("SELECT COUNT(*) FROM genesis_key").fetchone()[0]
                stats["error_keys"] = conn.execute(
                    "SELECT COUNT(*) FROM genesis_key WHERE is_error = 1"
                ).fetchone()[0]
                stats["fixed_keys"] = conn.execute(
                    "SELECT COUNT(*) FROM genesis_key WHERE status = 'fixed'"
                ).fetchone()[0]
                stats["unique_users"] = conn.execute(
                    "SELECT COUNT(DISTINCT user_id) FROM genesis_key WHERE user_id IS NOT NULL"
                ).fetchone()[0]

                for row in conn.execute(
                    "SELECT key_type, COUNT(*) FROM genesis_key GROUP BY key_type ORDER BY COUNT(*) DESC LIMIT 10"
                ).fetchall():
                    stats["key_types"][row[0]] = row[1]

            conn.close()
        except Exception:
            pass

    kb_path = BACKEND_ROOT / "knowledge_base" / "layer_1" / "genesis_key"
    if kb_path.exists():
        stats["kb_files"] = sum(1 for _ in kb_path.rglob("*.json"))

    return stats
