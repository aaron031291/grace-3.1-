"""
List learning patterns and learning examples from the learning memory database.

Run from backend dir (with venv active):
  python scripts/list_learning_memory.py
  python scripts/list_learning_memory.py --examples
  python scripts/list_learning_memory.py --patterns --limit 20

Uses backend/.env for database connection (SQLite or PostgreSQL).
"""
import argparse
import json
import sys
from pathlib import Path

# Ensure backend root is on path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


def _from_json_str(val):
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            return parsed if isinstance(parsed, (dict, list)) else {"raw": val}
        except Exception:
            return {"raw": val}
    return {"raw": str(val)}


def main():
    parser = argparse.ArgumentParser(description="List learning patterns and/or examples from learning memory DB")
    parser.add_argument("--patterns", action="store_true", help="List learning patterns (default: True if nothing else)")
    parser.add_argument("--examples", action="store_true", help="List learning examples")
    parser.add_argument("--limit", type=int, default=50, help="Max rows (default 50)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON only")
    args = parser.parse_args()

    if not args.patterns and not args.examples:
        args.patterns = True

    from dotenv import load_dotenv
    load_dotenv(backend_dir / ".env")

    from database.config import DatabaseConfig
    from database.connection import DatabaseConnection
    from database.session import initialize_session_factory, get_session_factory

    config = DatabaseConfig.from_env()
    DatabaseConnection.initialize(config)
    initialize_session_factory()
    session_factory = get_session_factory()
    session = session_factory()

    try:
        if args.patterns:
            from cognitive.learning_memory import LearningPattern
            rows = session.query(LearningPattern).order_by(LearningPattern.updated_at.desc()).limit(args.limit).all()
            data = []
            for p in rows:
                data.append({
                    "id": str(p.id) if hasattr(p, "id") else None,
                    "created_at": p.created_at.isoformat() if getattr(p, "created_at", None) else None,
                    "updated_at": p.updated_at.isoformat() if getattr(p, "updated_at", None) else None,
                    "pattern_name": getattr(p, "pattern_name", None),
                    "pattern_type": getattr(p, "pattern_type", None),
                    "preconditions": _from_json_str(getattr(p, "preconditions", None)),
                    "actions": _from_json_str(getattr(p, "actions", None)),
                    "expected_outcomes": _from_json_str(getattr(p, "expected_outcomes", None)),
                    "trust_score": getattr(p, "trust_score", None),
                    "success_rate": getattr(p, "success_rate", None),
                    "sample_size": getattr(p, "sample_size", None),
                    "supporting_examples": _from_json_str(getattr(p, "supporting_examples", "[]")),
                    "times_applied": getattr(p, "times_applied", None),
                    "times_succeeded": getattr(p, "times_succeeded", None),
                    "times_failed": getattr(p, "times_failed", None),
                })
            result = {"patterns": data, "count": len(data)}
            if args.json:
                print(json.dumps(result, indent=2, default=str))
            else:
                print(f"\n--- Learning patterns (count={len(data)}) ---\n")
                for i, p in enumerate(data, 1):
                    print(f"  [{i}] {p.get('pattern_name') or '(unnamed)'}  type={p.get('pattern_type')}  trust={p.get('trust_score')}  success_rate={p.get('success_rate')}")
                    prec = p.get("preconditions") or {}
                    act = p.get("actions") or {}
                    if prec or act:
                        print(f"      preconditions: {json.dumps(prec)[:120]}...")
                        print(f"      actions: {json.dumps(act)[:120]}...")
                    print()

        if args.examples:
            from cognitive.learning_memory import LearningExample
            rows = session.query(LearningExample).order_by(LearningExample.updated_at.desc()).limit(args.limit).all()
            data = []
            for e in rows:
                data.append({
                    "id": str(e.id) if hasattr(e, "id") else None,
                    "created_at": e.created_at.isoformat() if getattr(e, "created_at", None) else None,
                    "updated_at": e.updated_at.isoformat() if getattr(e, "updated_at", None) else None,
                    "example_type": getattr(e, "example_type", None),
                    "input_context": _from_json_str(getattr(e, "input_context", None)),
                    "expected_output": _from_json_str(getattr(e, "expected_output", None)),
                    "actual_output": _from_json_str(getattr(e, "actual_output", None)),
                    "trust_score": getattr(e, "trust_score", None),
                    "source": getattr(e, "source", None),
                    "times_referenced": getattr(e, "times_referenced", None),
                    "times_validated": getattr(e, "times_validated", None),
                    "times_invalidated": getattr(e, "times_invalidated", None),
                })
            result = {"examples": data, "count": len(data)}
            if args.json:
                print(json.dumps(result, indent=2, default=str))
            else:
                print(f"\n--- Learning examples (count={len(data)}) ---\n")
                for i, e in enumerate(data, 1):
                    print(f"  [{i}] type={e.get('example_type')}  source={e.get('source')}  trust={e.get('trust_score')}")
                    ctx = e.get("input_context") or {}
                    exp = e.get("expected_output") or {}
                    if ctx or exp:
                        print(f"      context: {json.dumps(ctx)[:100]}...")
                        print(f"      expected: {json.dumps(exp)[:100]}...")
                    print()
    finally:
        session.close()


if __name__ == "__main__":
    main()
