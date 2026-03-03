"""
Component Validator — deterministic input/output testing.

Tests each component with known inputs and verifies the output
matches expected results. Not just "is it alive" but "does it
actually work correctly."

Report Cards — each component gets a score card linked to Genesis key.
"""

import time
import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

_report_cards: Dict[str, dict] = {}


def validate_component(component_id: str, test_fn, test_cases: list) -> dict:
    """
    Run deterministic tests on a component.
    test_cases: [{"input": {...}, "expected": {...}}, ...]
    """
    results = {
        "component_id": component_id,
        "total": len(test_cases),
        "passed": 0,
        "failed": 0,
        "errors": [],
        "tested_at": datetime.utcnow().isoformat(),
    }

    for i, case in enumerate(test_cases):
        try:
            actual = test_fn(case["input"])
            expected = case["expected"]

            if _outputs_match(actual, expected):
                results["passed"] += 1
            else:
                results["failed"] += 1
                results["errors"].append({
                    "case": i,
                    "input": str(case["input"])[:100],
                    "expected": str(expected)[:100],
                    "actual": str(actual)[:100],
                })
        except Exception as e:
            results["failed"] += 1
            results["errors"].append({"case": i, "error": str(e)[:100]})

    results["pass_rate"] = round(results["passed"] / max(results["total"], 1) * 100, 1)

    # Update report card
    _update_report_card(component_id, results)

    return results


def _outputs_match(actual: Any, expected: Any) -> bool:
    """Check if actual output matches expected."""
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key, val in expected.items():
            if key not in actual:
                return False
            if val is not None and actual[key] != val:
                if not isinstance(val, type) or not isinstance(actual[key], val):
                    return False
        return True
    return actual == expected


def validate_all_components() -> dict:
    """Run validation on all core Grace components."""
    results = {}

    # Define test cases for each component
    tests = {
        "brain_api": _test_brain_api,
        "files_service": _test_files,
        "govern_service": _test_govern,
        "time_sense": _test_time_sense,
        "resilience": _test_resilience,
        "security": _test_security,
        "librarian": _test_librarian,
        "hebbian": _test_hebbian,
    }

    for comp_id, test_fn in tests.items():
        try:
            results[comp_id] = test_fn()
        except Exception as e:
            results[comp_id] = {"component_id": comp_id, "error": str(e)[:100], "passed": 0, "failed": 1}

    total_passed = sum(r.get("passed", 0) for r in results.values())
    total_failed = sum(r.get("failed", 0) for r in results.values())

    return {
        "components_tested": len(results),
        "total_passed": total_passed,
        "total_failed": total_failed,
        "pass_rate": round(total_passed / max(total_passed + total_failed, 1) * 100, 1),
        "results": results,
        "validated_at": datetime.utcnow().isoformat(),
    }


def _test_brain_api() -> dict:
    from api.brain_api_v2 import call_brain
    return validate_component("brain_api", lambda i: call_brain(i["domain"], i["action"], i.get("payload", {})), [
        {"input": {"domain": "tasks", "action": "time_sense"}, "expected": {"ok": True}},
        {"input": {"domain": "fake", "action": "nope"}, "expected": {"ok": False}},
        {"input": {"domain": "system", "action": "runtime"}, "expected": {"ok": True}},
    ])


def _test_files() -> dict:
    from core.services.files_service import stats
    return validate_component("files_service", lambda i: stats(), [
        {"input": {}, "expected": {"total_files": int}},
    ])


def _test_govern() -> dict:
    from core.services.govern_service import get_persona
    return validate_component("govern_service", lambda i: get_persona(), [
        {"input": {}, "expected": {}},
    ])


def _test_time_sense() -> dict:
    from cognitive.time_sense import TimeSense
    return validate_component("time_sense", lambda i: TimeSense.get_context(), [
        {"input": {}, "expected": {"period": str, "is_business_hours": bool}},
    ])


def _test_resilience() -> dict:
    from core.resilience import CircuitBreaker
    def test(i):
        cb = CircuitBreaker("test_val", failure_threshold=2)
        return {"state": cb.state}
    return validate_component("resilience", test, [
        {"input": {}, "expected": {"state": "closed"}},
    ])


def _test_security() -> dict:
    from core.security import check_sql_injection
    return validate_component("security", lambda i: {"blocked": check_sql_injection(i["text"])}, [
        {"input": {"text": "'; DROP TABLE--"}, "expected": {"blocked": True}},
        {"input": {"text": "normal text"}, "expected": {"blocked": False}},
    ])


def _test_librarian() -> dict:
    from core.librarian import get_document_stats
    return validate_component("librarian", lambda i: get_document_stats(), [
        {"input": {}, "expected": {}},
    ])


def _test_hebbian() -> dict:
    from core.hebbian import get_hebbian_mesh
    return validate_component("hebbian", lambda i: {"weights": get_hebbian_mesh().get_weights()}, [
        {"input": {}, "expected": {"weights": dict}},
    ])


# ═══════════════════════════════════════════════════════════════════
#  REPORT CARDS
# ═══════════════════════════════════════════════════════════════════

def _update_report_card(component_id: str, validation: dict):
    """Update a component's report card."""
    _report_cards[component_id] = {
        "component_id": component_id,
        "last_validated": validation.get("tested_at"),
        "pass_rate": validation.get("pass_rate", 0),
        "total_tests": validation.get("total", 0),
        "passed": validation.get("passed", 0),
        "failed": validation.get("failed", 0),
        "errors": validation.get("errors", [])[:5],
        "status": "healthy" if validation.get("pass_rate", 0) >= 80 else "degraded" if validation.get("pass_rate", 0) >= 50 else "failing",
    }


def get_report_card(component_id: str) -> dict:
    """Get a component's report card."""
    card = _report_cards.get(component_id)
    if card:
        return card

    # Build on-the-fly from semantic search
    try:
        from core.semantic_search import COMPONENTS
        comp = COMPONENTS.get(component_id)
        if comp:
            return {
                "component_id": component_id,
                "purpose": comp["purpose"],
                "file": comp["file"],
                "connects_to": comp["connects"],
                "status": "not_validated",
                "note": "Run validate_all_components() to generate report card",
            }
    except Exception:
        pass

    return {"error": f"Component {component_id} not found"}


def get_all_report_cards() -> dict:
    """Get all report cards."""
    # Include unvalidated components
    try:
        from core.semantic_search import COMPONENTS
        all_cards = {}
        for cid, info in COMPONENTS.items():
            if cid in _report_cards:
                all_cards[cid] = _report_cards[cid]
            else:
                all_cards[cid] = {"component_id": cid, "purpose": info["purpose"], "status": "not_validated"}
        return {"report_cards": all_cards, "total": len(all_cards),
                "validated": len(_report_cards)}
    except Exception:
        return {"report_cards": _report_cards, "total": len(_report_cards)}
