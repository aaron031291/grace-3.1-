import re

with open('commits_audit_utf8.patch', 'r', encoding='utf8') as f:
    content = f.read()

commits = re.split(r'^commit ', content, flags=re.MULTILINE)[1:]
output = []
for i, c in enumerate(commits):
    lines = c.split('\n')
    chash = lines[0].strip()
    
    msg_start = 0
    for j, l in enumerate(lines):
        if l.startswith('    '):
            msg_start = j
            break
            
    subject = lines[msg_start].strip() if msg_start > 0 else "No subject"
    
    diff_start = 0
    for j, l in enumerate(lines):
        if l.startswith('---'):
            diff_start = j
            break
            
    body = "\n".join(l.strip() for l in lines[msg_start+1:diff_start-1] if l.startswith('    '))
    
    files_affected = []
    in_stat = False
    for j in range(msg_start, len(lines)):
        if lines[j].startswith('---'):
            in_stat = True
        elif in_stat and lines[j].startswith(' '):
            if "|" in lines[j] and not "files changed" in lines[j] and not "file changed" in lines[j]:
                files_affected.append(lines[j].split('|')[0].strip())
        elif in_stat and lines[j].startswith('diff --git'):
            break
            
    pos = 14 + i
    
    output.append(f"Task #{pos} (Commit #{pos} | Hash: {chash[:8]})\n- Stated goal: {subject}\n- Actual changes: [...to review]\n- Files affected: {', '.join(files_affected)}\n- Potentially superseded by: N/A\n- Status: [TO BE VERIFIED]\n")

with open('commit_summary.txt', 'w', encoding='utf8') as f:
    f.write("\n".join(output))
