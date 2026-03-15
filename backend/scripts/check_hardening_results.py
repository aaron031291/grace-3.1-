"""Check hardening results from Spindle fallback DB and Genesis ledger."""
import sqlite3
import json
from pathlib import Path

# Check Spindle fallback DB
fb = Path(__file__).parent.parent / "data" / "spindle_events_fallback.db"
if fb.exists():
    conn = sqlite3.connect(str(fb))
    count = conn.execute("SELECT COUNT(*) FROM spindle_fallback").fetchone()[0]
    print(f"=== Spindle Fallback Events: {count} ===")
    rows = conn.execute(
        "SELECT sequence_id, timestamp, topic, source_type, payload_json "
        "FROM spindle_fallback ORDER BY sequence_id DESC LIMIT 40"
    ).fetchall()
    
    hardening_events = []
    agent_events = []
    for seq, ts, topic, src, payload_json in rows:
        ts_short = ts[:19] if ts else "?"
        if "hardening" in (topic or "") or "hardening" in (src or ""):
            hardening_events.append((seq, ts_short, topic, src, payload_json))
        if "coding_agent" in (topic or ""):
            agent_events.append((seq, ts_short, topic, src, payload_json))
        print(f"  seq={seq:4d} | {ts_short} | {src or '?':20s} | {topic}")
    
    print(f"\n=== Hardening-specific events: {len(hardening_events)} ===")
    for seq, ts, topic, src, pj in hardening_events[:10]:
        data = json.loads(pj) if pj else {}
        phase = data.get("phase", "?")
        task_id = data.get("task_id", "")
        status = data.get("status", "")
        conf = data.get("confidence", "")
        print(f"  {phase:12s} | {task_id:12s} | status={status} | confidence={conf}")
    
    print(f"\n=== Coding Agent events: {len(agent_events)} ===")
    for seq, ts, topic, src, pj in agent_events[:10]:
        data = json.loads(pj) if pj else {}
        agents = data.get("agents", data.get("agent", ""))
        task_id = data.get("task_id", "")
        print(f"  {topic:40s} | {task_id:12s} | agents={agents}")
    
    conn.close()
else:
    print("No Spindle fallback DB found")
    print(f"Checked: {fb}")

# Check Genesis ledger JSON
gf = Path(__file__).parent.parent.parent / ".genesis_file_versions.json"
if gf.exists():
    data = json.loads(gf.read_text(encoding="utf-8"))
    print(f"\n=== Genesis File Versions: {len(data)} tracked files ===")
else:
    print("\nNo Genesis file versions JSON found")

# Check the coding agent pool ledger via import
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from cognitive.coding_agents import get_coding_agent_pool
    pool = get_coding_agent_pool()
    summary = pool.ledger.get_summary()
    print(f"\n=== Agent Pool Ledger ===")
    print(f"  Sessions: {summary.get('total_sessions', 0)}")
    print(f"  Actions:  {summary.get('total_actions', 0)}")
    print(f"  Status:   {summary}")
except Exception as e:
    print(f"\nAgent pool ledger: {e}")
