#!/usr/bin/env python3
"""
Spindle HITL Chat CLI

Provides an interactive operator terminal to manage Spindle Hand-Offs.
Listens to the HITL Dashboard API for handoff signals and provides a REPL
for consulting the consensus engine and submitting the procedural resolution.
"""

import sys
import time
import requests
import json
import logging
from typing import Dict, Any

# Suppress request logging
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

API_BASE = "http://localhost:8000/api"
SPINDLE_BASE = f"{API_BASE}/spindle/hitl"

def print_banner():
    print("=" * 60)
    print(" Spindle HITL Operator Terminal starting...")
    print(" Listening for GRACE-OP-012, GRACE-HO-004, etc.")
    print("=" * 60)

def poll_for_handoffs() -> list:
    """Poll the backend for pending handoffs."""
    try:
        res = requests.get(f"{SPINDLE_BASE}/active", timeout=2)
        if res.status_code == 200:
            data = res.json()
            return data.get("handoffs", [])
    except requests.exceptions.RequestException:
        pass
    return []

def resolve_handoff(handoff_id: str, decision: str, notes: str, fix_code: str = None):
    """Submit the resolution back to the Event Store."""
    payload = {
        "decision": decision,
        "notes": notes,
        "fix_code": fix_code
    }
    try:
        res = requests.post(f"{SPINDLE_BASE}/{handoff_id}/resolve", json=payload, timeout=10)
        if res.status_code == 200:
            print(f"\n[OK] Resolution ingested for {handoff_id}")
            print(f"[OK] Added to Event Store and Procedural Memory.")
        else:
            print(f"\n[ERROR] Failed to ingest resolution: {res.text}")
    except requests.exceptions.RequestException as e:
        print(f"\n[ERROR] Connection failed: {e}")

def chat_with_consensus(prompt: str) -> str:
    """Consult the AI brain before making a decision."""
    print("  [Consulting consensus engine...]")
    try:
        # Use brain v2 router
        res = requests.post(f"{API_BASE}/v2/ai/consensus", json={"prompt": prompt}, timeout=10)
        if res.status_code == 200:
            data = res.json()
            out = data.get("data", {}).get("final_output", "No response from consensus")
            return out
        return f"Error: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error: {e}"

def handle_handoff(handoff: Dict[str, Any]):
    print("\n" + "!" * 60)
    print(" 🚨 HITL HANDOFF TRIGGERED 🚨")
    print("!" * 60)
    print(f" ID:      {handoff.get('handoff_id')}")
    print(f" Signal:  {handoff.get('signal')}")
    print(f" Score:   {handoff.get('overall_score')}/10")
    print(f" Failed:  {[l['layer'] for l in handoff.get('failed_layers', [])]}")
    
    # Optional 5W1H Context
    context = handoff.get('clarity_context', {})
    if context:
        print(f"\n --- Context ---")
        print(f" {json.dumps(context, indent=2)}")
        
    print("-" * 60)
    print(" Operator REPL (Type commands, 'resolve' to finish)")
    
    fix_code = None
    notes = ""
    decision = ""
    
    while True:
        try:
            cmd = input("\n[spindle] > ")
            if not cmd.strip():
                continue
                
            if cmd.lower() == "resolve":
                print("\nInitiating Resolution...")
                decision = input("Decision [override/abort/fix]: ")
                notes = input("Operator Notes: ")
                has_code = input("Include fix code? [y/N]: ")
                if has_code.lower() == 'y':
                    print("Enter code (end with blank line):")
                    lines = []
                    while True:
                        line = input()
                        if not line:
                            break
                        lines.append(line)
                    fix_code = "\n".join(lines)
                
                resolve_handoff(handoff.get("handoff_id"), decision, notes, fix_code)
                break
                
            elif cmd.lower() in ["help", "?"]:
                print(" Commands:")
                print("   ask <msg>  - Consult AI consensus about this handoff")
                print("   !<cmd>     - Run a local shell command (e.g., !pytest tests/)")
                print("   resolve    - Submit your decision and clear the handoff")
                print("   ignore     - Keep it pending, check the next one")
                print("   help       - Show this menu")
                
            elif cmd.lower() == "ignore":
                print("Ignoring. Kept in queue.")
                break
                
            elif cmd.lower().startswith("ask "):
                msg = cmd[4:]
                response = chat_with_consensus(f"Regarding Spindle Handoff {handoff.get('signal')} (Score {handoff.get('overall_score')}): {msg}")
                print(f"\n[Consensus Engine]:\n{response}\n")
                
            elif cmd.startswith("!"):
                import subprocess
                shell_cmd = cmd[1:].strip()
                if shell_cmd:
                    try:
                        print(f"Running: {shell_cmd}")
                        result = subprocess.run(shell_cmd, shell=True, text=True, capture_output=True)
                        if result.stdout:
                            print(result.stdout)
                        if result.stderr:
                            print(result.stderr)
                        print(f"Exit code: {result.returncode}")
                    except Exception as e:
                        print(f"Shell execution failed: {e}")
                
            else:
                print("Unknown command. Type 'help' for options.")
                
        except (KeyboardInterrupt, EOFError):
            print("\nExiting REPL. Handoff remains pending.")
            break

def main():
    print_banner()
    try:
        while True:
            handoffs = poll_for_handoffs()
            if handoffs:
                for h in handoffs:
                    handle_handoff(h)
            time.sleep(2)
            sys.stdout.write('.')
            sys.stdout.flush()
    except KeyboardInterrupt:
        print("\nOperator terminal shut down.")

if __name__ == "__main__":
    main()
