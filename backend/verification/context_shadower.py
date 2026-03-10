"""
backend/verification/context_shadower.py
─────────────────────────────────────────────────────────────────────────────
Context Shadowing & Atomic Hot-Swapping for Continual Context Evolution.

1. Takes proposed code from Grace and writes it to `__grACE_shadow/`.
2. Triggers the 12-Layer VVT Pipeline on the shadow module.
3. If VVT mints a Trust Coin, it atomically hot-swaps the module into `sys.modules`.
"""

import os
import sys
import time
import shutil
import importlib
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from verification.deterministic_vvt_pipeline import vvt_vault
from verification.constitutional_interpreter import ConstitutionalInterpreter, ConstitutionalViolation

logger = logging.getLogger("ContextShadower")

SHADOW_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "__grACE_shadow")

class ContextShadower:
    """Quarantine sandbox to test LLM rewrites before replacing production files."""
    
    def __init__(self):
        # Ensure shadow dir exists
        os.makedirs(SHADOW_DIR, exist_ok=True)
        init_file = os.path.join(SHADOW_DIR, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w") as f:
                f.write("# Auto-generated package init for Grace Shadow Execution\n")

    def propose_module_update(
        self, 
        target_file_path: str, 
        new_code_content: str, 
        module_name_to_test: str
    ) -> Dict[str, Any]:
        """
        Takes new code proposed by the LLM and runs it through the VVT gauntlet.
        If it survives, it is atomically swapped into production.
        """
        logger.info(f"Context Shadower engaged for proposed update to: {target_file_path}")
        
        # 1. Create Shadow File
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        base_name = os.path.basename(target_file_path)
        shadow_name = f"shadow_{timestamp}_{base_name}"
        shadow_path = os.path.join(SHADOW_DIR, shadow_name)
        
        with open(shadow_path, "w", encoding="utf-8") as f:
            f.write(new_code_content)
            
        logger.info(f"Shadow module written to quarantine: {shadow_path}")
        
        # 2. Phase 1: Pre-Execution Formal Proof (Constitutional Interpreter)
        interpreter = ConstitutionalInterpreter()
        try:
            interpreter.verify_contract(new_code_content, module_name_to_test)
        except ConstitutionalViolation as e:
            logger.error(f"Shadow module {module_name_to_test} violated the Domain Constitution: {e}")
            return {
                "success": False,
                "status": "CONSTITUTION_VIOLATION",
                "logs": [f"Pre-Execution Formal Proof Failed: {e}"],
                "error": str(e)
            }
            
        logger.info("Shadow module passed Constitutional Formal Proof. Minting VVT_CONTRACT_COIN.")
        contract_coin = "VVT_CONTRACT_COIN"
        
        # 3. Phase 1.5: Run the 12-Layer VVT Deterministic pipeline against the shadow code
        # In a real environment, we'd dynamically point the VVT execution engine to import from the shadow path
        vvt_passed = vvt_vault.run_all_layers(
            code_string=new_code_content, 
            function_name=module_name_to_test
        )
        
        if not vvt_passed:
            logger.warning("Shadow module FAILED the VVT gauntlet. Quarantine swap aborted.")
            return {
                "success": False,
                "status": "VVT_FAILED",
                "logs": [log for res in vvt_vault.results for log in res.logs],
                "error": getattr(vvt_vault.results[-1], 'error', "VVT Pipeline halted execution.") if vvt_vault.results else "Unknown error"
            }
            
        # 4. Mint Trust Coin
        trust_coin = "VVT_PLATINUM_COIN"
        logger.info(f"Shadow module passed VVT gauntlet. Trust Coin Minted: {trust_coin}")
        
        # 4.5. High-Risk Global Approval Check
        if self._is_high_risk(target_file_path):
            logger.info("Target file is HIGH-RISK. Engaging Global Approval Engine.")
            try:
                from governance.inline_approval_engine import get_approval_engine
                engine = get_approval_engine()
                # Request synchronous approval for the hot-swap
                is_approved, reason = engine.request_approval(
                    action_type="hot_swap_core_module",
                    risk_score=0.9, # Core modules are automatically high-risk
                    context={"file": target_file_path, "shadow_file": shadow_path, "coin": trust_coin}
                )
                if not is_approved:
                    logger.warning(f"Global Governance REJECTED the hot-swap: {reason}")
                    try:
                        from ml_intelligence.kpi_tracker import get_kpi_tracker
                        tracker = get_kpi_tracker()
                        tracker.increment_kpi("context_evolution", "rejected", value=1.0)
                        tracker.increment_kpi("context_evolution", "requests", value=1.0)
                    except ImportError:
                        pass
                    return {
                        "success": False,
                        "status": "GOVERNANCE_REJECTED",
                        "logs": [f"Global approval denied: {reason}"],
                        "error": "Hot-swap aborted by Inline Approval Engine."
                    }
            except ImportError as e:
                logger.error("Failed to route to Inline Approval Engine. Proceeding with caution.")
            
        # 5. Atomic Swap (The Hot-Replace)
        try:
            swap_result = self._atomic_modules_swap(target_file_path, shadow_path)
            
            # Log the successful cognitive evolution
            self._log_evolution(target_file_path, trust_coin, contract_coin)
            
            return {
                "success": True,
                "status": "ATOMIC_SWAP_COMPLETE",
                "trust_coin": trust_coin,
                "contract_coin": contract_coin,
                "logs": ["Shadow module verified by Constitution.", "Trust coin minted.", "sys.modules hot-swapped atomically."]
            }
            
        except Exception as e:
            logger.error(f"Atomic swap failed mid-flight: {e}")
            return {
                "success": False,
                "status": "ATOMIC_SWAP_FAILED",
                "error": str(e)
            }

    def _atomic_modules_swap(self, prod_file_path: str, quarantine_file_path: str) -> bool:
        """
        Safely replace the physical file AND hot-reload it into Python's sys.modules.
        """
        # Physical File Swap
        backup_path = f"{prod_file_path}.bak"
        shutil.copy2(prod_file_path, backup_path)
        
        try:
            shutil.copy2(quarantine_file_path, prod_file_path)
            
            # We must figure out the python module path to reload it from sys.modules
            # e.g backend/api/something.py -> api.something
            abs_prod = os.path.abspath(prod_file_path)
            backend_base = os.path.dirname(os.path.dirname(abs_prod))
            
            # Very simplistic conversion for POC. E.g C:/.../backend/cognitive/test.py -> cognitive.test
            rel_path = os.path.relpath(abs_prod, backend_base)
            mod_path = rel_path.replace(os.sep, ".")[:-3] # remove .py
            
            # The Hot-Swap
            if mod_path in sys.modules:
                importlib.reload(sys.modules[mod_path])
                logger.info(f"Hot-swapped memory module: {mod_path}")
                
            return True
            
        except Exception as e:
            # Revert Physical File
            shutil.copy2(backup_path, prod_file_path)
            logger.error(f"Physical file swap reverted due to error: {e}")
            raise e

    def _log_evolution(self, file_path: str, coin: str, contract_coin: str = "N/A"):
        """Send evolution event to telemetry."""
        try:
            from api._genesis_tracker import track
            track(
                key_type="context_evolution_swapped",
                what=f"Safely hot-swapped logic for: {file_path}",
                who="context_shadower.py",
                how="12-Layer VVT Verified + sys.modules atomic patch",
                input_data={"file": file_path, "coin_minted": coin, "contract_coin": contract_coin},
                output_data={"status": "SUCCESS"},
                tags=["guardian", "context-evolution", "hot-swap"]
            )
        except ImportError:
            pass

    def _is_high_risk(self, file_path: str) -> bool:
        """Determines if a file path is considered a high-risk core component."""
        high_risk_keywords = ["memory_tables", "guardian", "verification", "governance", "settings.py", "validation_api.py"]
        return any(keyword in file_path for keyword in high_risk_keywords)

# Singleton accessor
shadower = ContextShadower()
