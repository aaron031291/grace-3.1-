import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from cognitive.braille_translator import BrailleTranslator

def run_self_ingestion():
    print("==================================================")
    print("🧠 INITIATING GRACE AST -> BRAILLE SELF-INGESTION 🧠")
    print("==================================================")
    
    backend_dir = Path(__file__).parent
    output_dir = backend_dir / "training_corpus" / "grace_self_code"
    
    # Create the output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    translator = BrailleTranslator()
    
    processed_count = 0
    error_count = 0
    
    # Walk through the backend directory
    for root, dirs, files in os.walk(backend_dir):
        # Skip certain directories to avoid infinite loops or parsing non-code/irrelevant code
        if "training_corpus" in root or "__pycache__" in root or ".pytest_cache" in root or "venv" in root:
            continue
            
        for file in files:
            if file.endswith(".py"):
                file_path = Path(root) / file
                
                # Create a relative name for the output file
                rel_path = file_path.relative_to(backend_dir)
                out_name = str(rel_path).replace("\\", "_").replace("/", "_").replace(".py", ".txt")
                out_path = output_dir / out_name
                
                try:
                    # Translate AST to Braille Sequence
                    braille_sequence = translator.translate_file(str(file_path))
                    
                    # Wrap in the expected training_ingest.py ## Section format
                    content = f"## {file_path.name}\n{braille_sequence}\n"
                    
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(content)
                        
                    processed_count += 1
                    print(f"✅ Translated: {rel_path} -> {out_name}")
                except Exception as e:
                    error_count += 1
                    print(f"❌ Error parsing {rel_path}: {e}")
                    
    print("\n==================================================")
    print(f"🎉 SELF-INGESTION COMPLETE 🎉")
    print(f"Files Translated: {processed_count}")
    print(f"Errors: {error_count}")
    print(f"Output Directory: {output_dir}")
    print("Grace will natively ingest these Braille files into Oracle/UM/FlashCache on her next boot.")
    print("==================================================")

if __name__ == "__main__":
    run_self_ingestion()
