#!/usr/bin/env python3
"""
Clean Corrupted JSON Files
===========================
Finds and removes corrupted/empty JSON files from sandbox_lab directory.
"""

import json
import os
from pathlib import Path


def is_valid_json(file_path):
    """Check if a file contains valid JSON."""
    try:
        if os.path.getsize(file_path) == 0:
            return False
        with open(file_path, 'r', encoding='utf-8') as f:
            json.load(f)
        return True
    except (json.JSONDecodeError, ValueError, IOError):
        return False


def clean_corrupted_json(directory):
    """Find and remove corrupted JSON files."""
    directory = Path(directory)
    if not directory.exists():
        print(f"[INFO] Directory does not exist: {directory}")
        return
    
    print(f"[INFO] Checking JSON files in: {directory}")
    print()
    
    json_files = list(directory.glob("*.json"))
    if not json_files:
        print("[INFO] No JSON files found")
        return
    
    corrupted = []
    valid = []
    
    for json_file in json_files:
        if is_valid_json(json_file):
            valid.append(json_file)
        else:
            corrupted.append(json_file)
    
    print(f"[INFO] Found {len(valid)} valid JSON files")
    print(f"[INFO] Found {len(corrupted)} corrupted JSON files")
    print()
    
    if corrupted:
        print("[WARN] Corrupted files:")
        for file in corrupted:
            size = os.path.getsize(file)
            print(f"  - {file.name} ({size} bytes)")
        
        print()
        response = input("Delete corrupted files? (yes/no): ").strip().lower()
        if response in ['yes', 'y']:
            for file in corrupted:
                try:
                    file.unlink()
                    print(f"[OK] Deleted: {file.name}")
                except Exception as e:
                    print(f"[ERROR] Failed to delete {file.name}: {e}")
        else:
            print("[INFO] Skipped deletion")
    else:
        print("[OK] No corrupted files found")


if __name__ == "__main__":
    sandbox_dir = Path("backend/data/sandbox_lab")
    clean_corrupted_json(sandbox_dir)
