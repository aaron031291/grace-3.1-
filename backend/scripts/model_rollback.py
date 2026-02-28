#!/usr/bin/env python3
"""
Model Rollback CLI — Revert to previous model versions.

Usage:
  python scripts/model_rollback.py --list           # Show version history
  python scripts/model_rollback.py --rollback -1    # Rollback to previous version
  python scripts/model_rollback.py --provider kimi  # Rollback specific provider
"""

import argparse
import json
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def list_versions():
    from cognitive.model_updater import get_version_history
    history = get_version_history()

    print("\n=== Current Models ===")
    for provider, model in history.get("current", {}).items():
        print(f"  {provider}: {model}")

    print("\n=== Version History ===")
    for entry in history.get("history", [])[-10:]:
        print(f"  [{entry.get('updated_at', '?')}] {entry.get('provider')}: "
              f"{entry.get('old_model')} → {entry.get('new_model')}")

    print(f"\n=== Last {len(history.get('checks', []))} Checks ===")
    for check in history.get("checks", [])[-5:]:
        print(f"  [{check.get('timestamp', '?')}] "
              f"Kimi: {check.get('kimi_count', 0)} models, "
              f"Opus: {check.get('opus_count', 0)} models, "
              f"Ollama: {check.get('ollama_count', 0)} models")


def rollback(version_offset: int, provider: str = None):
    from cognitive.model_updater import get_version_history, update_model

    history = get_version_history()
    changes = history.get("history", [])

    if not changes:
        print("No version history to rollback to.")
        return

    if provider:
        # Filter to specific provider
        changes = [c for c in changes if c.get("provider") == provider]

    if not changes:
        print(f"No history for provider: {provider}")
        return

    # Get the target version
    idx = max(0, len(changes) + version_offset)
    target = changes[idx] if idx < len(changes) else changes[0]

    old_model = target.get("old_model")
    prov = target.get("provider")

    if not old_model or not prov:
        print("Invalid rollback target.")
        return

    print(f"\nRolling back {prov}:")
    print(f"  Current: {history.get('current', {}).get(prov, '?')}")
    print(f"  Rolling back to: {old_model}")

    confirm = input("\nConfirm rollback? (y/n): ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return

    result = update_model(prov, old_model)
    if result.get("updated"):
        print(f"\n✅ Rolled back {prov} to {old_model}")
    else:
        print(f"\n❌ Rollback failed: {result.get('error', 'unknown')}")


def main():
    parser = argparse.ArgumentParser(description="Grace Model Rollback CLI")
    parser.add_argument("--list", action="store_true", help="List version history")
    parser.add_argument("--rollback", type=int, help="Rollback N versions (e.g. -1 for previous)")
    parser.add_argument("--provider", type=str, help="Specific provider to rollback (kimi/opus/ollama)")

    args = parser.parse_args()

    if args.list:
        list_versions()
    elif args.rollback is not None:
        rollback(args.rollback, args.provider)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
