"""
IDE Bridge for Grace
Connects the IDE to the Grace API endpoints. The IDE only sends text/events,
and Grace handles the internal Braille encoding, logic mappings, and code processing.
"""
import grace_client
from ide.bridge.SpindleDriver import compile_spindle
from validators.z3_geometric import geometric_verify
from core.sandbox_modifier import modify_sandbox_node

def on_save(file_path: str):
    """
    Triggered by the IDE when a file is saved.
    Passes context to Grace without requiring the IDE to understand the contents.
    """
    grace_client.send(f"File changed: {file_path}")
    print(f"Grace notified: Received. Analyzing {file_path}...")

def on_command(user_input: str, file_path: str = None, src: str = None) -> dict:
    """
    Triggered by the IDE when the user submits a natural language command or code change.
    Grace converts the src to deterministic Spindle Braille iteratively.
    """
    print(f"Sending to Grace: '{user_input}' (Building. Here is code.)")
    
    # 1. Spindle Compilation
    if src and file_path:
        executable_ast = compile_spindle(src)
        
        # 2. Z3 Geometric Verification
        is_safe = geometric_verify(executable_ast.to_dict())
        if not is_safe:
            return {"error": "Z3 Geometric Proof Failed. Entropy bounds exceeded. Change rejected."}
            
        # 3. Apply to Sandbox
        result = modify_sandbox_node(file_path, src, reason=user_input, actor="Spindle_Autonomy")
        return result
        
    # If no source is provided (natural language IDE prompt), route through
    # the autonomous Spindle Builder Pipeline (QwenCodingNet)
    from core.services.code_service import generate_code
    result = generate_code(prompt=user_input, use_pipeline=True)
    return result
