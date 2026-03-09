import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_orchestrator.factory import get_qwen_coder, get_kimi_client

def main():
    try:
        system_prompt = (
            "You are a core cognitive engine inside the Grace AGI architecture. "
            "You have deep knowledge of Grace's autonomous loops, the memory mesh, and self-healing systems."
        )
        
        prompt = (
            "Based on your understanding of the Grace 3.1 architecture, what is missing from the system right now? "
            "What critical components are not wired up properly or remain unimplemented to get the system FULLY functional "
            "as an autonomous, self-healing, self-improving AGI? "
            "Please provide a concise but highly technical response detailing the specific gaps in integration or implementation. "
            "Mention specific subsystems (like the unified logic hub, ghost memory, consensus engine) if they are incomplete."
        )

        with open("architecture_gaps.md", "w", encoding="utf-8") as f:
            f.write("=== QWEN 3 (Local Reasoning & Coding Engine) ===\n")
            try:
                os.environ["OLLAMA_MODEL_CODE"] = "qwen3:32b"
                qwen = get_qwen_coder()
                response = qwen.generate(prompt=prompt, system_prompt=system_prompt)
                f.write(str(response) + "\n\n")
            except Exception as e:
                f.write(f"Qwen error: {e}\n\n")

            f.write("=== KIMI (Cloud Context Engine) ===\n")
            try:
                kimi = get_kimi_client()
                response = kimi.generate(prompt=prompt, system_prompt=system_prompt)
                f.write(str(response) + "\n")
            except Exception as e:
                f.write(f"Kimi error: {e}\n")
            
    except Exception as e:
        print(f"Fatal script error: {e}")

if __name__ == "__main__":
    main()

