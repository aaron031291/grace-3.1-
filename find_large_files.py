import subprocess
import shlex

# Get all objects in the commits we are trying to push
cmd = "git rev-list --objects c86a0ae0..HEAD"
res = subprocess.run(shlex.split(cmd), capture_output=True, text=True)

objects = []
for line in res.stdout.splitlines():
    parts = line.split(maxsplit=1)
    if not parts: continue
    obj_hash = parts[0]
    path = parts[1] if len(parts) > 1 else ""
    objects.append((obj_hash, path))

# Now check sizes for these blobs
for obj_hash, path in objects:
    cmd_size = f"git cat-file -s {obj_hash}"
    try:
        size = int(subprocess.check_output(shlex.split(cmd_size)).strip())
        if size > 50_000_000: # 50 MB
            print(f"{size / 1_000_000:.2f} MB - {path} ({obj_hash})")
    except:
        pass
