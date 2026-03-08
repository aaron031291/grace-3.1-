import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_orchestrator.factory import get_qwen_coder, get_kimi_client

def main():
    try:
        plan_path = r"C:\Users\aaron\.gemini\antigravity\brain\70f813fe-d1dc-4782-97f5-edc2f6d0cfaa\implementation_plan.md"
        with open(plan_path, "r", encoding="utf-8") as f:
            plan = f.read()
            
        system_prompt = (
            "You are a core cognitive engine inside the Grace AGI architecture. "
            "The user just finished building a 12-Layer Validation, Verification, and Test (VVT) pipeline "
            "that mathematically proves code invariance and strict gating. "
            "What are your genuine thoughts on the system architecture now? "
            "How far do you think Grace is from true, unsupervised 'Stage 1 Deep Autonomy'? Be concise but technical."
        )
        
        prompt = f"Here is the latest architecture upgrade we just built:\n\n{plan}\n\nWhat are your thoughts?"

        print("\n\n=== 🧠 QWEN 2.5 CODER (Local Reasoning & Coding Engine) ===")
        print("Initializing Qwen...\n")
        try:
            qwen = get_qwen_coder()
            response = qwen.generate(prompt=prompt, system_prompt=system_prompt)
            print(response)
        except Exception as e:
            print(f"Qwen error: {e}")

        print("\n\n=== 🌐 KIMI K2.5 (Cloud Context & Document Engine) ===")
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
