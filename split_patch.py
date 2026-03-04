import re
import os

with open('commits_audit_utf8.patch', 'r', encoding='utf8') as f:
    content = f.read()

commits = re.split(r'^commit ', content, flags=re.MULTILINE)[1:]
hashes = [
    "948fcdfa", "08fd28bf", "c597df20", "c8cf6e95", "b8ccf1a3",
    "105cb302", "7c3793a1", "cc93e3ea", "cf03acf9", "23e30169",
    "450d4705", "4f547266", "2d1498ff", "0023f60b", "ebde4194"
]

audit_dir = "commits_audit_diffs"
if not os.path.exists(audit_dir):
    os.makedirs(audit_dir)

for i, c in enumerate(commits):
    lines = c.split('\n')
    full_hash = lines[0].strip()
    match = [h for h in hashes if full_hash.startswith(h)]
    if match:
        h = match[0]
        filename = f"{audit_dir}/commit_{h}.diff"
        with open(filename, 'w', encoding='utf8') as f:
            f.write("commit " + c)
    else:
        # Check if it matches any of our target range
        pass
