#!/usr/bin/env python3
"""
ingest_healing_playbooks.py
Reads all YAML playbooks in backend/self_healing/playbooks and uploads them
into Grace's Unified Memory and Magma Cognitive Bridge as structured knowledge.
"""

import os
import sys
import glob
import yaml
import json

# Setup paths so we can import backend packages
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cognitive import magma_bridge
from cognitive.unified_memory import get_unified_memory

def ingest_all_playbooks():
    playbooks_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "self_healing", "playbooks")
    yaml_files = glob.glob(os.path.join(playbooks_dir, "*.yaml"))
    
    if not yaml_files:
        print("No yaml playbooks found.")
        return

    print(f"Found {len(yaml_files)} playbooks. Ensuring Memory connections...")
    
    unified_mem = get_unified_memory()
    
    success_count = 0
    
    for yaml_path in yaml_files:
        filename = os.path.basename(yaml_path)
        playbook_name = filename.replace(".yaml", "")
        
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                playbook_data = yaml.safe_load(f)
                
            trigger = playbook_data.get("trigger", "unknown")
            description = playbook_data.get("description", "").strip()
            remediation = playbook_data.get("remediation", [])
            conditions = playbook_data.get("conditions", [])
            
            # Formulate steps string list
            steps = []
            for step in remediation:
                steps.append(f"[{step.get('module', 'sys')}.{step.get('function', 'func')}] {step.get('description', '')}")
                
            print(f"Ingesting playbook: {playbook_name} (Trigger: {trigger})")
            
            # 1. Ingest as a Magma procedure
            magma_bridge.store_procedure(
                name=f"heal_{playbook_name}",
                description=f"Self-healing playbook for {trigger}. {description}",
                steps=steps
            )
            
            # 2. Ingest as a Magma pattern
            magma_bridge.store_pattern(
                pattern_type="healing_playbook",
                description=f"Playbook definition for {playbook_name}",
                data={"trigger": trigger, "conditions": conditions, "remediation": steps}
            )
            
            # 3. Raw semantic ingestion
            raw_text = f"Self-Healing Playbook '{playbook_name}' triggered by '{trigger}'. Description: {description}. Steps to resolve: {json.dumps(steps)}"
            magma_bridge.ingest(
                content=raw_text,
                source="ingest_playbooks",
                metadata={"type": "playbook", "playbook_name": playbook_name}
            )
            
            # 4. Push to unified memory as a high-trust learning example
            unified_mem.store_learning(
                input_ctx=f"How to heal {trigger}? Conditions: {json.dumps(conditions)}",
                expected=f"Execute playbook {playbook_name}:\n" + "\n".join(steps),
                actual=f"Execute playbook {playbook_name}:\n" + "\n".join(steps),
                trust=1.0,
                source="ingest_playbooks",
                example_type="playbook_definition"
            )
            
            success_count += 1
            print(f" → Successfully ingested '{playbook_name}'.")
        except Exception as e:
            print(f" ❌ Failed to ingest '{playbook_name}': {e}")
            
    print(f"\nCompleted! Successfully uploaded {success_count}/{len(yaml_files)} playbooks to Grace's memory mesh.")

if __name__ == "__main__":
    # Ensure offline test environments are skipped if using live DBs
    os.environ.setdefault("SKIP_EMBEDDING_LOAD", "false")
    os.environ.setdefault("SKIP_QDRANT_CHECK", "false")
    os.environ.setdefault("DISABLE_CONTINUOUS_LEARNING", "true")
    
    ingest_all_playbooks()
