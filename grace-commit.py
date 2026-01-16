#!/usr/bin/env python3
"""
Grace Commit Script - Automatically commits to develop, then can merge to main
Environment ID: aaron
"""
import subprocess
import sys
import os
from pathlib import Path

# Read environment config
CONFIG_FILE = Path(__file__).parent / ".git" / "grace-env-config"
ENV_ID = "aaron"
DEVELOPER_NAME = "aaron"

if CONFIG_FILE.exists():
    with open(CONFIG_FILE, 'r') as f:
        for line in f:
            if line.startswith('ENV_ID='):
                ENV_ID = line.split('=', 1)[1].strip()
            elif line.startswith('DEVELOPER_NAME='):
                DEVELOPER_NAME = line.split('=', 1)[1].strip()

def get_current_branch():
    """Get current git branch"""
    result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], 
                          capture_output=True, text=True)
    return result.stdout.strip()

def commit_to_develop(message):
    """Commit changes to develop branch"""
    current_branch = get_current_branch()
    
    # Stage all changes
    subprocess.run(['git', 'add', '-A'], check=True)
    
    # If not on develop, switch to develop
    if current_branch != 'develop':
        print(f"Switching from {current_branch} to develop...")
        subprocess.run(['git', 'checkout', 'develop'], check=True)
        # Merge current branch into develop if it's not main
        if current_branch not in ['main', 'develop']:
            subprocess.run(['git', 'merge', current_branch, '--no-edit'], 
                         capture_output=True)
    
    # Commit with message
    subprocess.run(['git', 'commit', '-m', message], check=True)
    print(f"✓ Committed to develop: {message}")
    
    # Push to remote
    subprocess.run(['git', 'push', 'origin', 'develop'], check=True)
    print(f"✓ Pushed to origin/develop")

def merge_to_main():
    """Merge develop into main"""
    current_branch = get_current_branch()
    
    # Switch to main
    if current_branch != 'main':
        subprocess.run(['git', 'checkout', 'main'], check=True)
    
    # Merge develop into main
    subprocess.run(['git', 'merge', 'develop', '--no-ff', '-m', 
                   f'Merge develop into main (ENV_ID: {ENV_ID})'], check=True)
    print(f"✓ Merged develop into main")
    
    # Push to remote
    subprocess.run(['git', 'push', 'origin', 'main'], check=True)
    print(f"✓ Pushed to origin/main")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python grace-commit.py commit 'Your commit message'")
        print("  python grace-commit.py merge")
        print(f"\nEnvironment ID: {ENV_ID}")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'commit':
        if len(sys.argv) < 3:
            print("Error: Commit message required")
            sys.exit(1)
        message = sys.argv[2]
        commit_to_develop(message)
    elif command == 'merge':
        merge_to_main()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
