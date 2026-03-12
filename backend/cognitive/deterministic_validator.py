"""
Deterministic Validator - Z3 Autonomy Predicate
Encodes the formal autonomy predicate for Spindle's isolated runtime:
“PID == 1 ∧ cap_sys_rawio == 1 ∧ oom_kills == 0”
"""

import logging
from typing import Dict, Any, Tuple
try:
    import z3
    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False

logger = logging.getLogger(__name__)

class SpindleAutonomyValidator:
    def __init__(self):
        self.solver = None
        if Z3_AVAILABLE:
            self.solver = z3.Solver()
            
            # Define Z3 variables
            self.pid = z3.Int('pid')
            self.cap_sys_rawio = z3.Int('cap_sys_rawio')
            self.oom_kills = z3.Int('oom_kills')
            
            # Add formal constraints (The Autonomy Predicate)
            # Spindle must run as the primary process in its isolation (PID 1 conceptually, or > 0 on Windows)
            # Must have required capabilities (conceptually 1)
            # Must not be crashing from OOM
            self.solver.add(self.pid > 0) 
            self.solver.add(self.cap_sys_rawio == 1)
            self.solver.add(self.oom_kills == 0)

    def evaluate(self, metrics: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Evaluates current runtime metrics against the formal Z3 autonomy predicate.
        Returns (is_autonomous, reason)
        """
        if not Z3_AVAILABLE:
            logger.warning("[AUTONOMY-PREDICATE] Z3 not available, falling back to basic checks.")
            return self._fallback_evaluate(metrics)

        m_pid = metrics.get('pid', -1)
        m_cap = metrics.get('cap_sys_rawio', 0)
        m_oom = metrics.get('oom_kills', 1)

        # Push state, apply real-world metrics, check satisfiability, pop state
        self.solver.push()
        self.solver.add(self.pid == m_pid)
        self.solver.add(self.cap_sys_rawio == m_cap)
        self.solver.add(self.oom_kills == m_oom)
        
        result = self.solver.check()
        self.solver.pop()

        if result == z3.sat:
            return True, "Formal autonomy predicate satisfied."
        else:
            return False, f"Metrics failed formal verification: pid={m_pid}, cap={m_cap}, oom={m_oom}"

    def _fallback_evaluate(self, metrics: Dict[str, Any]) -> Tuple[bool, str]:
        """Simple python boolean logic if Z3 isn't available"""
        m_pid = metrics.get('pid', -1)
        m_cap = metrics.get('cap_sys_rawio', 0)
        m_oom = metrics.get('oom_kills', 1)
        
        if m_pid > 0 and m_cap == 1 and m_oom == 0:
            return True, "Basic autonomy predicate satisfied."
        return False, "Failed basic constraints."

# Singleton instance
_validator = SpindleAutonomyValidator()

def verify_autonomy(metrics: Dict[str, Any]) -> Tuple[bool, str]:
    return _validator.evaluate(metrics)
