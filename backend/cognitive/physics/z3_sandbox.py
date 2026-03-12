import os
import subprocess
import tempfile
import logging

logger = logging.getLogger(__name__)

class Z3Sandbox:
    """
    Provides an isolated execution environment for testing LLM-generated Z3 constraints.
    Crucial for safety: NEVER execute raw LLM Python code directly in the live process.
    """
    
    def __init__(self):
        # We assume the environment running Grace has z3 available
        self.exec_timeout = 5.0 # Seconds before killing infinite loops
        
    def test_generated_constraint(self, z3_code_snippet: str) -> tuple[bool, str]:
        """
        Wraps the LLM-generated constraint in a minimal Z3 python harness.
        Executes it in a disjoint process. Returns True if valid Python/Z3 code.
        """
        
        sandbox_harness = f"""
from z3 import *

def run_verify():
    solver = Solver()
    
    # Mock BitVecs
    domain_mask = BitVec('domain_mask', 64)
    intent_mask = BitVec('intent_mask', 64)
    state_mask  = BitVec('state_mask', 64)
    ctx_mask    = BitVec('ctx_mask', 64)
    
    # Mock Constants
    DOMAIN_DATABASE = 1 << 0
    DOMAIN_API = 1 << 1
    DOMAIN_MEMORY = 1 << 2
    DOMAIN_NETWORK = 1 << 3
    DOMAIN_SYS_CONF = 1 << 4
    
    INTENT_START = 1 << 8
    INTENT_STOP = 1 << 9
    INTENT_DELETE = 1 << 10
    INTENT_QUERY = 1 << 11
    INTENT_GRANT = 1 << 12
    INTENT_REPAIR = 1 << 13
    
    STATE_FAILED = 1 << 16
    STATE_IMMUTABLE = 1 << 17
    STATE_ACTIVE = 1 << 18
    STATE_UNKNOWN = 1 << 19
    STATE_STOPPED = 1 << 20
    
    PRIV_ADMIN = 1 << 24
    PRIV_USER = 1 << 25
    PRIV_SYSTEM = 1 << 26
    PRIV_GUEST = 1 << 27
    CTX_MAINTENANCE = 1 << 32
    CTX_EMERGENCY = 1 << 33
    CTX_ELEVATED = 1 << 34

    # --- INJECTED LLM CODE ---
    class MockPhysics:
        def __init__(self):
            self.solver = solver
            self.domain_mask = domain_mask
            self.intent_mask = intent_mask
            self.state_mask = state_mask
            self.ctx_mask = ctx_mask
            
        def inject_rules(self):
            # The LLM wrote code assuming `self.solver.add(...)`
            {z3_code_snippet.replace(chr(10), chr(10) + '            ')}
            
    mock = MockPhysics()
    mock.inject_rules()
    
    # Check if the rules are fundamentally unsatisfiable (i.e. contradiction)
    res = solver.check()
    if res == unsat:
        print("ERROR: Injected rules create immediate logical contradiction (UNSAT).")
        exit(1)
        
    print("SUCCESS: Rule parses and compiles cleanly.")
    
if __name__ == '__main__':
    run_verify()
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tf:
            tf.write(sandbox_harness)
            temp_path = tf.name
            
        try:
            # Run the file via python interpreter
            result = subprocess.run(
                ['python', temp_path],
                capture_output=True,
                text=True,
                timeout=self.exec_timeout
            )
            
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, result.stderr.strip() or result.stdout.strip()
                
        except subprocess.TimeoutExpired:
            return False, "TIMEOUT: Evaluation exceeded safety limits."
        except Exception as e:
            return False, f"SANDBOX_ERROR: {e}"
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
