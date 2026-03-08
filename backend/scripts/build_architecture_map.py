#!/usr/bin/env python3
"""
Build the Architecture Compass and export the full map to JSON.
Run from backend/:  python scripts/build_architecture_map.py
Output: backend/architecture_map.json
"""
import json
import sys
from pathlib import Path

# backend/ root
BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

def main():
    from cognitive.architecture_compass import get_compass
    c = get_compass()
    c.build()
    m = c.get_full_map()
    out = BACKEND / "architecture_map.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(m, f, indent=2, ensure_ascii=False)
    print(f"Built architecture map: {len(m['components'])} components -> {out}")
    chat_nlp = [
        p for p, i in m["components"].items()
        if ("chat_response" in (i.get("capabilities") or [])) or ("full_nlp" in (i.get("capabilities") or []))
    ]
    print(f"Components with chat_response or full_nlp: {len(chat_nlp)}")
    for p in sorted(chat_nlp):
        print(f"  - {p}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
