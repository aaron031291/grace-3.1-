#!/usr/bin/env python3
"""
Check Layer 2 status and functionality.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.session import get_session
from pathlib import Path

def check_layer2():
    """Check Layer 2 status."""
    print("=" * 80)
    print("LAYER 2 STATUS CHECK")
    print("=" * 80)
    
    status = {
        "layer2_intelligence": False,
        "enterprise_wrapper": False,
        "cognitive_engine": False,
        "genesis_ide_integration": False,
        "issues": []
    }
    
    # 1. Check Layer2Intelligence import
    try:
        from genesis_ide.layer_intelligence import Layer2Intelligence
        print("✓ Layer2Intelligence class found")
        status["layer2_intelligence"] = True
    except Exception as e:
        print(f"X Layer2Intelligence import failed: {e}")
        status["issues"].append(f"Layer2Intelligence import: {e}")
    
    # 2. Check Enterprise wrapper imports
    try:
        from layer2.enterprise_intelligence import get_enterprise_layer2_intelligence
        from layer2.enterprise_cognitive_engine import get_enterprise_cognitive_engine
        print("✓ Enterprise Layer 2 wrappers found")
        status["enterprise_wrapper"] = True
    except Exception as e:
        print(f"X Enterprise wrapper import failed: {e}")
        status["issues"].append(f"Enterprise wrapper import: {e}")
    
    # 3. Check Cognitive Engine import
    try:
        from cognitive.engine import CognitiveEngine
        print("✓ CognitiveEngine class found")
        status["cognitive_engine"] = True
    except Exception as e:
        print(f"X CognitiveEngine import failed: {e}")
        status["issues"].append(f"CognitiveEngine import: {e}")
    
    # 4. Check Genesis IDE integration
    try:
        from genesis_ide.core_integration import GenesisIDECore
        print("✓ GenesisIDECore class found")
        status["genesis_ide_integration"] = True
    except Exception as e:
        print(f"X GenesisIDECore import failed: {e}")
        status["issues"].append(f"GenesisIDECore import: {e}")
    
    # 5. Try to initialize Layer 2 Intelligence
    print("\n" + "-" * 80)
    print("ATTEMPTING TO INITIALIZE LAYER 2")
    print("-" * 80)
    
    try:
        session = next(get_session())
        repo_path = Path(".")
        
        from genesis_ide.layer_intelligence import Layer2Intelligence
        layer2 = Layer2Intelligence(session=session, repo_path=repo_path)
        
        import asyncio
        initialized = asyncio.run(layer2.initialize())
        
        if initialized:
            print("✓ Layer 2 Intelligence initialized successfully")
            print(f"  - Metrics: {layer2.metrics}")
            print(f"  - Reasoner: {layer2._reasoner is not None}")
            print(f"  - LLM Orchestrator: {layer2._llm_orchestrator is not None}")
            print(f"  - Genesis Service: {layer2._genesis_service is not None}")
        else:
            print("⚠ Layer 2 Intelligence initialization returned False")
            status["issues"].append("Layer 2 initialization returned False")
            
    except Exception as e:
        print(f"X Layer 2 initialization failed: {e}")
        import traceback
        traceback.print_exc()
        status["issues"].append(f"Layer 2 initialization: {e}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    all_working = all([
        status["layer2_intelligence"],
        status["enterprise_wrapper"],
        status["cognitive_engine"],
        status["genesis_ide_integration"]
    ])
    
    if all_working and len(status["issues"]) == 0:
        print("✓ Layer 2 is WORKING - All components available")
    elif all_working:
        print("⚠ Layer 2 is PARTIALLY WORKING - Some issues detected")
        for issue in status["issues"]:
            print(f"  - {issue}")
    else:
        print("X Layer 2 is NOT WORKING - Critical components missing")
        for issue in status["issues"]:
            print(f"  - {issue}")
    
    return status

if __name__ == "__main__":
    check_layer2()
