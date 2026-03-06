import os
import subprocess

hashes = [
    "5bcb0e1377df11b40981cd5886f9eee4994c9635",
    "489b6ab387e9d0946874360b9cea8bba7fb74c06",
    "3950a710959d759bebb8cd593ad5c191254ddfd4",
    "c7c4da70650f02d4f36464a545609e981ca9f95a",
    "8cc292ed48cf122d737d889a9fc50ac2ba21d9cd",
    "b2e121dd523ea4ac462442454b8c64093e4717cf",
    "5f3fad75d7803d672e4d644bc7176e7ce4459668",
    "c528a8b8dbbbc956f971f89a6439e9a023ce67f8",
    "771e8890c0367db64592c1b607066d859c86c8ff",
    "e87951d0486e00d53b21b0c55c50b7c364c2860d",
    "43a8ccbf80a0dc3e6854d55bc2d35c85825c0ea5",
    "ab1f2a1a36d6b136656f74bf590e3bca98ae9cf1",
    "3051c0a874dd7db9b1f790af4f85e9d598339059",
    "7254cdc2093c67e7b876a28a9b20dbf8b1897fac",
    "3b6761ccf1e71b72daa4a2bfb57a85d187e4c108",
    "6757a03959f30708b738f9b7bb6c76294563adde",
    "feebcb503cf8c3e0ca4182c50e4d143cce2296cb",
    "cfad991309ef9ef8389f5b9131bfde201e36e9fa",
    "978571c95b70c26ff0f035bf3ab5b3a30761dfa6",
    "26f9777b581743bc17515952aa82492605e52210"
]

out_dir = r"C:\Users\jivot\.gemini\antigravity\brain\fc17d67c-6029-48a0-bd2d-3b130bbf0bf4\diffs"
os.makedirs(out_dir, exist_ok=True)

for i, h in enumerate(hashes):
    # Commit # from HEAD: #6 is index 0, #25 is index 19
    pos = i + 6
    diff = subprocess.check_output(['git', 'show', h]).decode('utf-8', 'replace')
    stat = subprocess.check_output(['git', 'show', '--stat', '--oneline', h]).decode('utf-8', 'replace')
    
    with open(os.path.join(out_dir, f"{pos:02d}_{h[:8]}.patch"), 'w', encoding='utf-8') as f:
        f.write(diff)
    with open(os.path.join(out_dir, f"{pos:02d}_{h[:8]}.stat"), 'w', encoding='utf-8') as f:
        f.write(stat)

# Also get 1-5
recent_hashes = [
    "db022ca2bc5f04090a1f41c90cc1f2ff98bd8a0b",
    "59855c4322af396537765746d1d853186d4dc9cc",
    "ff76011bfc67b8511253526e8cf0c6fed1cf3852",
    "90cc15369a4efb1e7955918365d509acdb8e4715",
    "59d8138b455038314ef0a8525d3262cd5931987c"
]

for i, h in enumerate(recent_hashes):
    pos = i + 1
    diff = subprocess.check_output(['git', 'show', h]).decode('utf-8', 'replace')
    with open(os.path.join(out_dir, f"recent_{pos:02d}_{h[:8]}.patch"), 'w', encoding='utf-8') as f:
        f.write(diff)

print(f"Exported {len(hashes) + len(recent_hashes)} patches to {out_dir}")
