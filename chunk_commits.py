import subprocess
import math
import sys

# 1. Get all currently changed/untracked files that differ from HEAD (we just soft-reset)
# To be safe, let's just use `git diff --name-only`
print("Unstaging all files...")
subprocess.run(['git', 'reset', 'HEAD'], check=True)

print("Getting unstaged/untracked files...")
# Get modified/deleted files
diff_output = subprocess.check_output(['git', 'diff', '--name-only'], text=True)
files = diff_output.splitlines()

# Get untracked files
untracked_output = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], text=True)
files.extend(untracked_output.splitlines())

# Remove duplicates empty strings
files = list(set([f.strip() for f in files if f.strip()]))

total_files = len(files)
chunks = 15
chunk_size = math.ceil(total_files / chunks)

print(f"Total files: {total_files}")
print(f"Chunk size: {chunk_size} files per commit")

for i in range(chunks):
    start = i * chunk_size
    end = min((i + 1) * chunk_size, total_files)
    chunk_files = files[start:end]
    
    if not chunk_files:
        continue
    
    print(f"Commit {i+1}/{chunks}: Staging {len(chunk_files)} files...")
    
    # We add them in batches to avoid command line length limits
    batch_size = 500
    for j in range(0, len(chunk_files), batch_size):
        batch = chunk_files[j:j+batch_size]
        subprocess.run(['git', 'add'] + batch, check=True)
        
    subprocess.run(['git', 'commit', '-m', f'Chunk {i+1}/{chunks}: Spindle HITL and Architecture Updates'], check=True)

print("Finished splitting into 15 commits!")
