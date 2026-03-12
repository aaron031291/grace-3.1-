"""
backend/self_healing/meta_healer.py
─────────────────────────────────────────────────────────────────────────────
Spindle Meta-Healing (Recursive Self-Improvement)

This module intercepts fatal backend exceptions (specifically those inside
Spindle's own generation/verification loops) and feeds the stack trace back
into an isolated instance of the Qwen Coder to generate a patch.

It autonomously applies the patch to the sandbox, allowing Spindle to fix
bugs in its own source code on-the-fly without crashing the entire system.
"""

import logging
import traceback
import sys
import threading
from typing import Callable, Any
from functools import wraps

logger = logging.getLogger(__name__)

# Prevent infinite recursion if the meta-healer itself crashes
_is_healing = threading.local()

def execute_meta_heal(exc_info) -> bool:
    """Take an active traceback, formulate a prompt, and ask Spindle to fix it."""
    exc_type, exc_val, exc_tb = exc_info
    if not exc_type or not exc_val:
        return False
        
    tb_lines = traceback.format_exception(exc_type, exc_val, exc_tb)
    tb_str = "".join(tb_lines)
    
    # Extract the target file where the crash originated (ideally our own codebase)
    target_file = None
    for line in reversed(tb_lines):
        if "File " in line and "backend" in line:
            import re
            m = re.search(r'File "([^"]+)"', line)
            if m:
                target_file = m.group(1)
                break
                
    if not target_file:
        logger.warning("[META-HEAL] Could not identify target backend file from traceback.")
        return False
        
    logger.error(f"[META-HEAL] Engaging Autonomous Meta-Healing for {target_file}...\n{tb_str[:500]}...")

    prompt = (
        f"CRITICAL SYSTEM CRASH in {target_file}.\n"
        f"You are the Grace Spindle Meta-Healer. You must fix your own source code.\n\n"
        f"TRACEBACK:\n{tb_str}\n\n"
        f"Analyze the traceback. Identify the exact line causing the '{exc_type.__name__}: {exc_val}'.\n"
        f"Write a Python script that reads {target_file}, patches exactly the broken lines, and writes the fix back to disk.\n"
        f"Do NOT generate the entire file, just a patch script.\n"
    )

    try:
        from cognitive.qwen_coding_net import generate_code
        # Force fast-path to prevent triggering full pipelines if they are the ones broken
        result = generate_code(prompt, use_pipeline=False)
        code = result.get("code", "")
        
        if not code or len(code) < 10:
            logger.error("[META-HEAL] Spindle failed to generate a meta-patch.")
            return False
            
        logger.info(f"[META-HEAL] Spindle generated patch script ({len(code)} bytes). Applying to Sandbox...")
        
        from ide.bridge.SpindleDriver import compile_spindle
        from validators.z3_geometric import geometric_verify
        from core.sandbox_modifier import modify_sandbox_node
        import uuid
        
        # We compile the patching script itself to ensure it's safe
        executable_ast = compile_spindle(code)
        is_safe = geometric_verify(executable_ast.to_dict())
        
        if not is_safe:
            logger.error("[META-HEAL] Meta-patch rejected by Z3 Geometric Proof.")
            return False
            
        patch_file = f"spindle_self_heal_patch_{uuid.uuid4().hex[:8]}.py"
        modify_sandbox_node(patch_file, code, reason="Meta-Healing Crash Override", actor="Spindle_Meta_LLM")
        
        # Execute the patch script to fix the underlying file
        ns = {}
        exec(code, ns, ns)
        
        logger.info(f"[META-HEAL] {target_file} successfully hot-patched!")
        return True
        
    except Exception as e:
        logger.error(f"[META-HEAL] Recursive Meta-Healing Failure: {e}")
        return False


def meta_heal(func: Callable) -> Callable:
    """Decorator to wrap critical Spindle or Core backend functions in self-healing."""
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if getattr(_is_healing, "active", False):
                # We are already inside a meta-heal loop, don't recurse
                raise e
                
            _is_healing.active = True
            try:
                success = execute_meta_heal(sys.exc_info())
                if success:
                    logger.info(f"[META-HEAL] Retrying {func.__name__} after successful patch...")
                    # Warning: Only safe if function is idempotent. 
                    return func(*args, **kwargs)
                else:
                    logger.error(f"[META-HEAL] Could not self-heal {func.__name__}. Crashing.")
                    raise e
            finally:
                _is_healing.active = False
    return wrapper
