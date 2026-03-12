import subprocess
import sys

def run(cmd):
    print(f"Running: {cmd}")
    res = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if res.returncode != 0:
        print(f"Error ({res.returncode}):\n{res.stderr}")
        sys.exit(1)
    print(res.stdout)

commits = [
    "7b465a09", "793071e8", "1cab2cd1", "56c90dbb", 
    "084a53ba", "d96d36f2", "758df3dc", "22266a1d", 
    "0097a934", "a3824739", "b0f648ed", "bb067e42"
]

for c in commits:
    print(f"================ PUSHING {c} ================")
    run(f"git push origin {c}:master")
    
print("All chunks pushed successfully!")
