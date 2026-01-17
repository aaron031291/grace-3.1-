import os
import shutil

# Paths
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_dir = os.path.join(base_dir, "backend")
data_dir = os.path.join(backend_dir, "data")
cognitive_dir = os.path.join(backend_dir, "cognitive")

def fix_imports():
    files_to_fix = [
        os.path.join(cognitive_dir, "episodic_memory.py"),
        os.path.join(cognitive_dir, "procedural_memory.py")
    ]
    
    import_line = "from pydantic import BaseModel\n"
    
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if "from pydantic import BaseModel" not in content:
                print(f"[FIX] Adding Pydantic import to {os.path.basename(file_path)}...")
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(import_line + content)
            else:
                print(f"[OK] {os.path.basename(file_path)} already has the import.")
        else:
            print(f"[SKIP] {os.path.basename(file_path)} does not exist.")

def rename_conflicting_config():
    old_config = os.path.join(backend_dir, "config.py")
    new_config = os.path.join(backend_dir, "backend_root_config.py")
    
    if os.path.exists(old_config):
        print("[FIX] Renaming conflicting config.py to backend_root_config.py...")
        try:
            shutil.move(old_config, new_config)
            print("      Note: If you had custom settings there, you may need to update imports.")
        except Exception as e:
            print(f"[ERROR] Could not rename config: {e}")
    else:
        print("[SKIP] config.py does not exist at backend/config.py")

def clear_db():
    db_path = os.path.join(data_dir, "grace.db")
    if os.path.exists(db_path):
        print("[FIX] Deleting potentially corrupted database (datatype mismatch)...")
        try:
            os.remove(db_path)
            print("      Grace will recreate a fresh database on startup.")
        except Exception as e:
            print(f"[ERROR] Could not delete DB (is Grace still running?): {e}")
    else:
        print("[SKIP] grace.db does not exist at backend/data/grace.db")

if __name__ == "__main__":
    print("=== GRACE 3.1 RESCUE SYSTEM ===")
    fix_imports()
    rename_conflicting_config()
    clear_db()
    print("===============================")
    print("\nAttempting manual boot test...")
    print("Run this command next:")
    print(f"cd backend && python -m uvicorn app:app --host 0.0.0.0 --port 8000")
