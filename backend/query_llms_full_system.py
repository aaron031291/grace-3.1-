import sys
import os
import glob

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_orchestrator.factory import get_qwen_coder, get_kimi_client, get_qwen_reasoner

def get_system_context():
    """Gather core architectural files to provide full system context."""
    context_files = [
        "backend/self_healing/error_pipeline.py",
        "backend/cognitive/unified_memory.py",
        "backend/cognitive/continuous_learning_orchestrator.py",
        "backend/verification/deterministic_vvt_pipeline.py",
        "backend/api/autonomous_loop_api.py",
    ]
    
    context = "=== GRACE CORE ARCHITECTURE ===\n\n"
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    for rel_path in context_files:
        full_path = os.path.join(base_dir, rel_path.replace("/", os.sep))
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
                context += f"--- File: {rel_path} ---\n{content[:3000]}...\n\n"
        else:
            context += f"--- File: {rel_path} (Not Found) ---\n\n"
            
    return context

def main():
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "query_output.txt")
    with open(output_path, "w", encoding="utf-8") as out_f:
        try:
            system_context = get_system_context()
            
            system_prompt = (
                "You are a core cognitive engine inside the Grace AGI architecture. "
                "You have been granted access to Grace's core system source code, memory systems, self-healing pipelines, and self-learning orchestrator. "
                "Analyze the architecture provided. Be concise, technical, and highly analytical."
            )
            
            prompt = (
                f"{system_context}\n\n"
                "QUESTION FROM THE CREATOR:\n"
                "Based on your understanding of the whole system (Memory, Self-Healing, Self-Learning, and the VVT pipeline), "
                "what are your thoughts on the system as a whole? "
                "Specifically, how do we safely give Grace 'continual context evolution' without destabilizing her?"
            )

            out_f.write("\n\n" + "="*60 + "\n")
            out_f.write("QWEN 2.5 CODER (Reasoning Engine)...\n")
            out_f.write("="*60 + "\n\n")
            out_f.flush()
            
            try:
                qwen = get_qwen_coder()
                response = qwen.generate(prompt=prompt, system_prompt=system_prompt)
                out_f.write(response + "\n")
            except Exception as e:
                out_f.write(f"Qwen error: {e}\n")
            out_f.flush()

            out_f.write("\n\n" + "="*60 + "\n")
            out_f.write("KIMI K2.5 (Cloud Context Engine)...\n")
            out_f.write("="*60 + "\n\n")
            out_f.flush()
            
            try:
                kimi = get_kimi_client()
                response = kimi.generate(prompt=prompt, system_prompt=system_prompt)
                out_f.write(response + "\n")
            except Exception as e:
                out_f.write(f"Kimi error: {e}\n")
                
        except Exception as e:
            out_f.write(f"Fatal script error: {e}\n")

if __name__ == "__main__":
    main()
