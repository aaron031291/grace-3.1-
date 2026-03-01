import os
import json
import shutil
from datetime import datetime

def fix_truncated_json(file_path):
    """
    Repair a truncated JSON file by adding missing closing characters.
    """
    print(f"Checking {file_path}...")
    
    if not os.path.exists(file_path):
        print(f"Error: {file_path} does not exist.")
        return False
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
        # Try to parse as is
        try:
            json.loads(content)
            print("File is already valid JSON.")
            return True
        except json.JSONDecodeError:
            pass
            
        print("File is invalid. Attempting repair...")
        
        # Backup first
        backup_path = f"{file_path}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(file_path, backup_path)
        print(f"Backup created: {backup_path}")
        
        # Heuristic repair for Grace Key JSON structure:
        # { "user_id": "...", "keys": [ {...}, ... ] }
        
        fixed_content = content
        
        # If it doesn't end with }, it's likely truncated
        if not fixed_content.endswith('}'):
            # Case 1: Truncated inside keys list
            if '"keys": [' in fixed_content:
                # Find the last complete object in the list
                last_brace = fixed_content.rfind('}')
                if last_brace != -1:
                    fixed_content = fixed_content[:last_brace+1]
                
                # Close the list and the root object
                fixed_content += '\n  ],\n  "last_updated": "' + datetime.utcnow().isoformat() + '",\n  "total_keys": 0,\n  "repaired": true\n}'
            else:
                # Case 2: Very early truncation
                fixed_content += '}'
        
        # Validate fixed content
        try:
            data = json.loads(fixed_content)
            # Re-calculate total keys
            if 'keys' in data:
                data['total_keys'] = len(data['keys'])
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            print(f"Successfully repaired {file_path}. Total keys: {data.get('total_keys', 0)}")
            return True
        except json.JSONDecodeError as e:
            print(f"Heuristic repair failed: {e}")
            return False
            
    except Exception as e:
        print(f"Error during repair: {e}")
        return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        for path in sys.argv[1:]:
            fix_truncated_json(path)
    else:
        # Default path from task
        corrupt_file = r"D:\grace-3.1-\backend\knowledge_base\layer_1\genesis_key\file_watcher\keys_2026-02-24.json"
        fix_truncated_json(corrupt_file)
