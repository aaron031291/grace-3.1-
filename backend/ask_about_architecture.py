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
            "Based on your understanding of the Grace architecture, what is missing from the system right now? "
            "What critical components are not wired up properly or remain unimplemented to get the system FULLY functional "
            "as an autonomous, self-healing, self-improving AGI? "
            "Please provide a concise but highly technical response detailing the specific gaps in integration or implementation."
        )

        print("\n\n=== 🧠 QWEN 3.5 (Local Reasoning & Coding Engine) ===")
        print("Initializing Qwen 3.5...\n")
        try:
            qwen = get_qwen_coder()
            response = qwen.generate(prompt=prompt, system_prompt=system_prompt)
            print(response)
        except Exception as e:
            print(f"Qwen error: {e}")

        print("\n\n=== 🌐 KIMI (Cloud Context & Document Engine) ===")
        print("Initializing Kimi...\n")
        try:
            kimi = get_kimi_client()
            response = kimi.generate(prompt=prompt, system_prompt=system_prompt)
            print(response)
        except Exception as e:
            print(f"Kimi error: {e}")
            
    except Exception as e:
        print(f"Fatal script error: {e}")

if __name__ == "__main__":
    main()
