"""
Repair script for .genesis_file_versions.json:
1. Fixes truncated/incomplete JSON at end of file
2. Rewrites all absolute Linux paths to be relative (os-agnostic)
3. Reports which referenced files are missing on this machine
4. Removes entries for non-existent files (optional)
"""
import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime

# ── Paths ────────────────────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).parent.resolve()
JSON_FILE   = BACKEND_DIR / ".genesis_file_versions.json"
BACKUP_FILE = BACKEND_DIR / ".genesis_file_versions.json.bak"

# The Linux prefix used in the JSON (from the original developer's machine)
# We'll strip this prefix and rebuild paths relative to the backend dir
OLD_PREFIX = "/home/zair/Documents/grace/test/grace-3.1-/backend/"

print(f"[FIX]  Source: {JSON_FILE}")
print(f"[FIX]  Backend dir: {BACKEND_DIR}")

# ── Step 1: Read raw bytes ────────────────────────────────────────────────────
raw = JSON_FILE.read_text(encoding="utf-8", errors="replace")
print(f"[FIX]  File size: {len(raw):,} chars, {raw.count(chr(10))+1:,} lines")

# ── Step 2: Fix truncated JSON ────────────────────────────────────────────────
# The file ends mid-entry.  We need to close open dicts/arrays cleanly.
# Strategy: parse as far as we can, then repair.

def fix_truncated_json(text: str):
    """Attempt to fix truncated JSON by trimming to the last valid complete entry."""
    # Remove trailing whitespace / NUL bytes
    text = text.rstrip("\x00 \t\r\n")

    # Count nesting depth to know how many brackets to add
    depth = 0
    in_string = False
    escape_next = False
    last_comma_at = -1

    for i, ch in enumerate(text):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in ('{', '['):
            depth += 1
        elif ch in ('}', ']'):
            depth -= 1
        elif ch == ',' and depth == 1:
            # top-level comma inside the "files" dict
            last_comma_at = i

    if depth == 0:
        print("[FIX]  JSON is already balanced — no truncation fix needed.")
        return text

    print(f"[FIX]  JSON is truncated (unclosed depth={depth}), trimming to last complete entry …")

    # Walk backwards from end to find the last ',' at depth 1 (between file entries)
    # and cut there, then close the remaining open structures.
    #
    # Simpler approach: strip back to last '}' that closes a versions array entry,
    # then add the closing brackets.

    # Find the last occurrence of a complete version entry closing pattern
    # We look for the last "}," or "}" that closes a file record
    # Safest: find the last "last_updated" field completed line
    cutpoints = [m.start() for m in re.finditer(r'"last_updated"\s*:\s*"[^"]+"\s*\n?\s*}', text)]
    if not cutpoints:
        # Fallback: find last completed versions array
        cutpoints = [m.start() for m in re.finditer(r'"version_count"\s*:\s*\d+', text)]

    if cutpoints:
        cut = cutpoints[-1]
        # Find the closing } of that entry
        end = text.find('}', cut)
        if end != -1:
            text = text[:end+1]
            # Now close the remaining open arrays/objects
            # Re-count depth
            depth2 = 0
            in_str2 = False
            esc2 = False
            for ch in text:
                if esc2: esc2 = False; continue
                if ch == '\\' and in_str2: esc2 = True; continue
                if ch == '"': in_str2 = not in_str2; continue
                if in_str2: continue
                if ch in ('{','['): depth2 += 1
                elif ch in ('}',']'): depth2 -= 1

            # Build closing sequence
            closing = ""
            # We need to close: versions array ], file entry }, files dict }, root object }
            # depth2 tells us how many opens are unclosed
            stack_chars = []
            d = 0
            in_s = False
            es = False
            for ch in text:
                if es: es = False; continue
                if ch == '\\' and in_s: es = True; continue
                if ch == '"': in_s = not in_s; continue
                if in_s: continue
                if ch == '{': stack_chars.append('}')
                elif ch == '[': stack_chars.append(']')
                elif ch in ('}',']'): stack_chars.pop() if stack_chars else None

            closing = "\n" + "".join(reversed(stack_chars))
            text = text + closing
            print(f"[FIX]  Appended closing: {closing.strip()!r}")

    return text

fixed_raw = fix_truncated_json(raw)

# ── Step 3: Parse JSON ────────────────────────────────────────────────────────
try:
    data = json.loads(fixed_raw)
    print(f"[FIX]  JSON parsed OK — {len(data.get('files', {}))} file entries")
except json.JSONDecodeError as e:
    print(f"[ERROR] JSON still invalid after fix attempt: {e}")
    print("        Manual inspection needed. Aborting.")
    sys.exit(1)

# ── Step 4: Fix paths + check file existence ──────────────────────────────────
missing = []
fixed_count = 0
removed_keys = []

files_dict = data.get("files", {})
new_files = {}

for key, entry in files_dict.items():
    # Fix file_path and absolute_path
    for field in ("file_path", "absolute_path"):
        val = entry.get(field, "")
        if not val:
            continue

        fixed_val = val
        # Strip the old Linux prefix and make relative to backend
        if OLD_PREFIX in fixed_val:
            rel = fixed_val[len(OLD_PREFIX):]          # e.g. "knowledge_base/scraped/..."
            fixed_val = str(BACKEND_DIR / rel)         # absolute Windows path
            fixed_count += 1
        elif val.startswith("/home/") or val.startswith("/root/"):
            # Unknown Linux prefix, strip up to /backend/ if present
            match = re.search(r'/backend/(.*)', val)
            if match:
                fixed_val = str(BACKEND_DIR / match.group(1))
                fixed_count += 1

        # Normalise separators for the current OS
        fixed_val = str(Path(fixed_val))
        entry[field] = fixed_val

    # Fix paths inside versions list
    for version in entry.get("versions", []):
        pass  # versions don't store paths currently

    # Check if the absolute file exists
    abs_path = entry.get("absolute_path") or entry.get("file_path", "")
    if abs_path and not Path(abs_path).exists():
        missing.append(abs_path)
        # Keep the entry anyway — just note it's missing

    new_files[key] = entry

data["files"] = new_files
data["last_path_fix"] = datetime.utcnow().isoformat()
data["path_fix_backend_dir"] = str(BACKEND_DIR)

# ── Step 5: Write backup + save ───────────────────────────────────────────────
print(f"[FIX]  Writing backup → {BACKUP_FILE.name}")
BACKUP_FILE.write_text(raw, encoding="utf-8")

print(f"[FIX]  Saving fixed JSON → {JSON_FILE.name}")
JSON_FILE.write_text(
    json.dumps(data, indent=2, ensure_ascii=False, default=str),
    encoding="utf-8"
)

# ── Step 6: Report ────────────────────────────────────────────────────────────
total = len(data["files"])
missing_count = len(missing)
present_count = total - missing_count

print()
print("=" * 60)
print(f"  Total entries   : {total}")
print(f"  Paths fixed     : {fixed_count}")
print(f"  Files present   : {present_count}")
print(f"  Files MISSING   : {missing_count}")
print("=" * 60)

if missing:
    print("\nMissing files (entries kept but file not found on disk):")
    for p in missing[:30]:
        print(f"  ✗  {p}")
    if len(missing) > 30:
        print(f"  … and {len(missing)-30} more")
else:
    print("\nAll referenced files exist on disk ✓")

print("\n[FIX]  Done. Restart the backend to pick up the repaired JSON.")
