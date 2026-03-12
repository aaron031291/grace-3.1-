import os
import re
from typing import Dict, Optional

class BrailleMapper:
    """
    Parses and translates between Python syntax, Braille Encodings, and Genesis Keys.
    Uses the configuration file `config/braille_python_mapping.txt` as its source of truth.
    """
    
    _instance = None
    
    def __new__(cls, mapping_file_path=None):
        if cls._instance is None:
            cls._instance = super(BrailleMapper, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, mapping_file_path=None):
        if self._initialized:
            return
            
        if mapping_file_path is None:
            # Assume it's in config/braille_python_mapping.txt relative to project root
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            mapping_file_path = os.path.join(base_dir, "config", "braille_python_mapping.txt")
        
        self.mapping_file_path = mapping_file_path
        self.python_to_braille_map: Dict[str, Dict[str, str]] = {}
        self.braille_to_python_map: Dict[str, list] = {}
        self.genesis_key_to_map: Dict[str, Dict[str, str]] = {}
        
        self._load_mapping()
        self._initialized = True

    def _load_mapping(self):
        if not os.path.exists(self.mapping_file_path):
            raise FileNotFoundError(f"Mapping file not found at {self.mapping_file_path}")
            
        with open(self.mapping_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        for line in lines:
            line = line.strip()
            # Identify lines with the mapping format
            # Example: def          | ●●●●●● 1mm □      | GRACE-PY-001 | DEFINITION
            if "|" in line and "GRACE-" in line:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 4:
                    keyword = parts[0]
                    braille = parts[1]
                    genesis_key = parts[2]
                    category = parts[3]
                    
                    mapping_entry = {
                        "keyword": keyword,
                        "braille": braille,
                        "genesis_key": genesis_key,
                        "category": category
                    }
                    
                    self.python_to_braille_map[keyword] = mapping_entry
                    if braille not in self.braille_to_python_map:
                        self.braille_to_python_map[braille] = []
                    self.braille_to_python_map[braille].append(mapping_entry)
                    self.genesis_key_to_map[genesis_key] = mapping_entry

    def python_to_braille(self, keyword: str) -> Optional[Dict[str, str]]:
        """Returns the mapping entry for a given Python keyword or function."""
        return self.python_to_braille_map.get(keyword)
        
    def braille_to_python(self, braille_symbol: str) -> list:
        """Returns a list of mapping entries for a given Braille symbol."""
        return self.braille_to_python_map.get(braille_symbol, [])
        
    def get_by_genesis_key(self, genesis_key: str) -> Optional[Dict[str, str]]:
        """Returns the mapping entry for a given Genesis Key."""
        return self.genesis_key_to_map.get(genesis_key)

# Provide a default singleton instance for easy import
mapper = BrailleMapper()
