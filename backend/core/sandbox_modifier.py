"""
Sandbox Modifier - Enforces strict governance and Ghost Shadow tracking
for any autonomous modifications Grace/Spindle makes to the Braille Sandbox.
"""
import difflib
import logging
from typing import Dict, Any

from database.session import session_scope
from database.models.braille_node import BrailleSandboxNode
from cognitive.ghost_memory import get_ghost_memory
from cognitive.corrigible_plan import get_corrigible_plan

logger = logging.getLogger(__name__)

def shadow_track_changes(old_ast: str, new_ast: str, ghost_mem) -> int:
    """
    Ghost Shadow tracking: performs line-by-line comparison between old and new ASTs
    and silently records the exact modifications into Ghost Memory.
    """
    old_lines = old_ast.splitlines() if old_ast else []
    new_lines = new_ast.splitlines() if new_ast else []
    
    diff = list(difflib.unified_diff(old_lines, new_lines, n=0))
    changes_tracked = 0
    
    for line in diff:
        if line.startswith('+++') or line.startswith('---') or line.startswith('@@'):
            continue
        if line.startswith('+'):
            ghost_mem.append(
                event_type="code_generated",
                content=f"Added: {line[1:].strip()}",
                metadata={"action": "add", "line_content": line[1:]}
            )
            changes_tracked += 1
        elif line.startswith('-'):
            ghost_mem.append(
                event_type="code_change",
                content=f"Removed: {line[1:].strip()}",
                metadata={"action": "remove", "line_content": line[1:]}
            )
            changes_tracked += 1

    return changes_tracked


def modify_sandbox_node(file_path: str, new_ast_content: str, reason: str, actor: str = "Spindle") -> Dict[str, Any]:
    """
    Safely modify a Braille Sandbox Node with full Genesis Key and Ghost Shadow tracking.
    """
    ghost = get_ghost_memory()
    ghost.start_task(f"Sandbox Modification: {file_path}")
    ghost.append("system_event", f"Initiating governed modification of {file_path} for reason: {reason}")
    
    try:
        # Import Genesis Tracker inside to avoid circular imports if any
        from api._genesis_tracker import track
    except ImportError:
        track = None
        logger.warning("Genesis Tracker not found, modifications will not generate Genesis Keys.")

    with session_scope() as session:
        node = session.query(BrailleSandboxNode).filter(BrailleSandboxNode.file_path == file_path).first()
        
        if not node:
            ghost.append("error", f"Node not found in Sandbox for {file_path}")
            return {"success": False, "error": "Node not found"}

        old_ast = node.ast_content
        
        
        # 0. Z3 Geometric Proof for Spindle Autonomy
        if actor == "Spindle_Autonomy":
            corrigible = get_corrigible_plan()
            is_provable = corrigible._prove_geometric_safety(new_ast_content)
            if not is_provable:
                ghost.append("error", f"Z3 Geometric Proof failed for AST modification on {file_path}")
                return {"success": False, "error": "Z3 Proof limit exceeded. Modification reverted."}
            else:
                ghost.append("success", "Z3 Geometric Proof passed. Entropy bounds verified.")

        # 1. Ghost Shadow line-by-line tracking
        changes_count = shadow_track_changes(old_ast, new_ast_content, ghost)
        ghost.append("system_event", f"Tracked {changes_count} AST modifications in Ghost Shadow.")
        
        # 2. Update the DB
        node.ast_content = new_ast_content
        session.commit()
        
        # 3. Genesis Key Batch Tracking
        genesis_key_id = None
        if track:
            genesis_key_id = track(
                key_type="code_change",
                what=f"Sandbox AST modification for {file_path}",
                where=file_path,
                why=reason,
                who=actor,
                how="sandbox_modifier.modify_sandbox_node",
                input_data={"old_ast_length": len(old_ast)},
                output_data={"new_ast_length": len(new_ast_content), "changes_count": changes_count},
                tags=["sandbox", "governance", "ghost_shadow"]
            )
            ghost.append("success", f"Genesis Key '{genesis_key_id}' generated for transaction.")
        
        reflection = ghost.is_task_done()  # Finalize and log to playbook
        
        return {
            "success": True,
            "file_path": file_path,
            "changes_count": changes_count,
            "genesis_key": genesis_key_id,
            "ghost_playbook_status": reflection
        }
