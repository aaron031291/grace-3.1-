import os
import ast
from pathlib import Path

def find_orphans(base_dir_str):
    base_dir = Path(base_dir_str)
    all_py = list(base_dir.rglob("*.py"))
    
    # Files to ignore (scripts, entry points, tests)
    ignore_stems = {"app", "main", "test_", "conftest"}
    
    imported_names = set()
    
    # 1. Gather all imported module parts
    for pf in all_py:
        try:
            content = pf.read_text(encoding="utf-8")
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported_names.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imported_names.add(node.module)
        except Exception:
            pass

    orphaned = []
    
    # 2. Check each file
    for pf in all_py:
        if pf.stem.startswith("test_") or pf.stem in ignore_stems:
            continue
        if pf.name == "__init__.py":
            continue
            
        try:
            rel = pf.relative_to(base_dir)
            
            # Reconstruct module names it could be imported as
            parts = list(rel.parts[:-1]) + [rel.stem]
            relative_mod = ".".join(parts)
            absolute_mod = "backend." + relative_mod
            
            # E.g. bitmask_geometry -> cognitive.physics.bitmask_geometry
            raw_name = pf.stem
            
            is_imported = False
            for im in imported_names:
                if relative_mod in im or raw_name in im or absolute_mod in im:
                    is_imported = True
                    break
                    
            if not is_imported:
                orphaned.append(str(rel))
        except ValueError:
            pass

    return orphaned

if __name__ == "__main__":
    b_dir = r"c:\Users\aaron\Desktop\grace-3.1--Aaron-new2\backend"
    o_files = find_orphans(b_dir)
    print(f"--- POTENTIAL ORPHANS ({len(o_files)}) ---")
    for f in sorted(o_files):
        print(f)
