import os
import ast
from pathlib import Path

def get_imported_modules(base_dir):
    imported_names = set()
    for pf in Path(base_dir).rglob('*.py'):
        skip = False
        for p in pf.parts:
            if p in ('venv', '.venv', 'node_modules', '.git', '.gemini', '__pycache__'):
                skip = True
                break
        if skip: continue
        try:
            content = pf.read_text(encoding='utf-8')
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names: imported_names.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module: imported_names.add(node.module)
        except Exception:
            pass
    return imported_names

def find_cognitive_orphans():
    base_dir = Path(r"c:\Users\aaron\Desktop\grace-3.1--Aaron-new2\backend")
    cognitive_dir = base_dir / "cognitive"
    imported = get_imported_modules(base_dir)
    
    orphans = []
    
    for pf in cognitive_dir.rglob('*.py'):
        if pf.name == "__init__.py" or pf.stem.startswith("test_"): continue
        
        rel = pf.relative_to(base_dir)
        mod_rel = ".".join(list(rel.parts[:-1]) + [pf.stem])
        mod_abs = "backend." + mod_rel
        raw_name = pf.stem
        
        is_imported = False
        for im in imported:
            if mod_rel in im or mod_abs in im or raw_name in im:
                is_imported = True
                break
                
        if not is_imported:
            orphans.append(pf.name)
            
    print(f"--- COGNITIVE ORPHANS ({len(orphans)}) ---")
    for o in sorted(orphans):
        print(o)

if __name__ == "__main__":
    find_cognitive_orphans()
