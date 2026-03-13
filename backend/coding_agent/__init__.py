"""coding_agent package — Grace's autonomous coding agent."""
from backend.coding_agent.task_queue import submit, start_worker, get_status, register_handler
from backend.coding_agent.deterministic_gate import get_gate
from backend.coding_agent.verification_pass import get_verification_pass

__all__ = [
    "submit",
    "start_worker",
    "get_status",
    "register_handler",
    "get_gate",
    "get_verification_pass",
]
