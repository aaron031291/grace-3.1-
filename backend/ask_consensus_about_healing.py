import os
import sys

# Suppress standard output to avoid Windows console Unicode encode errors
if sys.platform == "win32":
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cognitive.consensus_engine import run_consensus

def log_output(msg):
    with open('consensus_interview.txt', 'a', encoding='utf-8') as f:
        f.write(str(msg) + '\n')

def run_interview():
    with open('consensus_interview.txt', 'w', encoding='utf-8') as f:
        f.write('--- Consensus Self-Healing Diagnostic Interview ---\n')
        
    log_output('Initializing Consensus Engine...')
    
    prompt = """
    We are trying to debug the autonomous self-healing pipeline in Grace. 
    The operator has the following questions for you (the consensus mechanism):

    1. What exactly do you need to successfully self-heal the system autonomously?
    2. Why can't you execute on errors safely right now? 
    3. Are you actually getting the error messages?
    4. Where in the system architecture does the self-healing process break down or get stuck?

    Please analyze the current Grace architecture, your available tools, the event bus pipeline, and the guardian governance rules. Provide a detailed, technical response answering these four questions.
    """
    
    try:
        result = run_consensus(
            prompt=prompt,
            source="system_admin",
            user_context="Operator debugging self-healing"
        )
        log_output(f'\n=== CONSENSUS RESPONSE ===\n{result.final_output}')
        log_output(f'\n=== MODELS USED ===\n{result.models_used}')
        log_output(f'\n=== CONFIDENCE ===\n{result.confidence}')
    except Exception as e:
        log_output(f'\n=== EXCEPTION ===\n{str(e)}')

if __name__ == '__main__':
    run_interview()
