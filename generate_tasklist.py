import os, glob, re

diffs_dir = r"C:\Users\jivot\.gemini\antigravity\brain\fc17d67c-6029-48a0-bd2d-3b130bbf0bf4\diffs"
out_file = r"C:\Users\jivot\.gemini\antigravity\brain\fc17d67c-6029-48a0-bd2d-3b130bbf0bf4\implementation_plan.md"

commits = []
for i in range(6, 26):
    patch_files = glob.glob(os.path.join(diffs_dir, f"{i:02d}_*.patch"))
    stat_files = glob.glob(os.path.join(diffs_dir, f"{i:02d}_*.stat"))
    if not patch_files or not stat_files: continue
    
    with open(patch_files[0], 'r', encoding='utf-8') as f:
        patch_text = f.read()
    with open(stat_files[0], 'r', encoding='utf-8') as f:
        stat_text = f.read()
        
    hash_full = re.search(r'^commit ([a-f0-9]+)', patch_text)
    hash_val = hash_full.group(1) if hash_full else patch_files[0].split('_')[1].split('.')[0]
    
    # Extract commit message
    msg_lines = []
    in_msg = False
    for line in patch_text.split('\n'):
        if line.startswith('Date:'):
            in_msg = True
            continue
        if in_msg and line.startswith('diff --git'):
            break
        if in_msg and line.strip():
            msg_lines.append(line.strip())
            
    msg = " ".join(msg_lines) if msg_lines else stat_text.split('\n')[0].split(' ', 1)[-1]
    
    # Extract files affected
    files = []
    for line in stat_text.split('\n'):
        if '|' in line:
            files.append(line.split('|')[0].strip())
            
    commits.append({
        'pos': i,
        'hash': hash_val,
        'msg': msg_lines[0] if msg_lines else msg,
        'desc': " ".join(msg_lines[1:]) if len(msg_lines) > 1 else "",
        'files': files
    })

md = [
    "# Implementation Plan: Commit Audit Checklist",
    "This plan contains the generated task list for commits 6 through 25.",
    ""
]

for c in commits:
    md.append(f"### Task {c['pos'] - 5} (Commit #{c['pos']} | Hash: `{c['hash'][:8]}`)")
    md.append(f"- **Stated goal**: {c['msg']}")
    if c['desc']: md.append(f"- **Description**: {c['desc']}")
    md.append(f"- **Actual changes**: See diff. Files changed: {len(c['files'])}")
    md.append(f"- **Files affected**:")
    for f in c['files']:
        md.append(f"  - `{f}`")
    md.append(f"- **Potentially superseded by**: N/A (will be evaluated)")
    md.append(f"- **Status**: [TO BE VERIFIED]")
    md.append("")
    
with open(out_file, "w", encoding='utf-8') as f:
    f.write("\n".join(md))

print(f"Generated {out_file}")
