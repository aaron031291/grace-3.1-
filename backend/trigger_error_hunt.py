import asyncio
import os
import sys

# Completely suppress standard output to avoid UnicodeEncodeError in Windows 
if sys.platform == "win32":
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')

import logging

logging.basicConfig(level=logging.INFO, filename="hunt_agent.log", filemode="w", format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grace_mcp.orchestrator import get_mcp_orchestrator_sync
from grace_mcp.builtin_tools import get_builtin_tools

def log_output(msg):
    with open('hunt_log_final.txt', 'a', encoding='utf-8') as f:
        f.write(str(msg) + '\n')

async def run_hunt():
    with open('hunt_log_final.txt', 'w', encoding='utf-8') as f:
        f.write('--- Starting Autonomous Error Hunt ---\n')
        
    log_output('Initializing Orchestrator...')
    orchestrator = get_mcp_orchestrator_sync()
    orchestrator._initialized = True
    
    builtin_tools = get_builtin_tools(enable_rag=False, enable_web=False)
    for tool in builtin_tools:
        orchestrator._builtin_tools[tool.name] = tool
        if tool.to_openai_function() not in orchestrator._tools_openai_format:
             orchestrator._tools_openai_format.append(tool.to_openai_function())
        
    log_output(f'Loaded {len(orchestrator._tools_openai_format)} tools.')
    
    prompt = """
    You are Grace's autonomous self-healing agent. You have just been given access to 
    new actuation endpoints including `execute_shell_command`, `submit_coding_task`, 
    `restart_service`, and `update_knowledge_base`.

    Your task is to fix a specific bug in the backend. 
    There is a crash happening in `backend/genesis/file_version_tracker.py` and `backend/genesis/file_watcher.py`.
    The error is: `[Errno 13] Permission denied: 'C:\\Users\\aaron\\Desktop\\grace-3.1--Aaron-new2\\frontend\\dist\\assets'`
    This happens because the file watcher is intercepting a directory modify/create event, and passing it to the 
    symbiotic version tracker, which then tries to `open(file_path, "rb")` to compute a hash, but it crashes because
    it's a directory, not a file.

    Step 1: Use `execute_shell_command` with `cat` to read the affected files to understand the bug.
    
    Step 2: Fix the error using the `submit_coding_task` tool to queue a fix for the autonomous coding agent.
    CRITICAL: You must include the parameter `"dry_run": "false"` so that the fix is actually applied. 
    CRITICAL: You MUST include the `"target_file"` parameter with the exact path to the file (e.g. `backend/genesis/file_watcher.py` or `backend/genesis/file_version_tracker.py`).
    You need to either add `if os.path.isdir(file_path): return` in `file_watcher.py`'s event handlers, or skip directories in `file_version_tracker.py`'s `_compute_file_hash`.
    
    Step 3: Say "HUNT COMPLETE".
    """
    
    messages = [{'role': 'user', 'content': prompt}]
    
    for turn in range(5):
        log_output(f'\n--- Turn {turn+1} ---')
        response = await orchestrator.chat(
            messages=messages,
            model='qwen3:32b',
            temperature=0.2,
            max_tokens=2000
        )
        
        reply_content = response.get('content', '')
        log_output(f'\n=== SYSTEM RESPONSE ===\n{reply_content}')
        
        messages.append({'role': 'assistant', 'content': reply_content})
        
        tool_calls = response.get('tool_calls_made', [])
        if tool_calls:
            log_output('\n=== TOOL CALLS MADE ===')
            for call in tool_calls:
                 log_output(f"Tool: {call.get('tool')} | Success: {call.get('success')}")
                 log_output(f"Result Preview: {str(call.get('result_preview', ''))[:200]}")
                 
                 messages.append({
                     'role': 'system', 
                     'content': f"Tool '{call.get('tool')}' result: {call.get('result_preview', '')}"
                 })
        
        if 'HUNT COMPLETE' in reply_content:
             log_output('\nAgent finished the hunt.')
             break

    from coding_agent.task_queue import start_worker
    print("\n[Orchestrator] Starting task worker to process LLM coding tasks...")
    start_worker()
    import time
    time.sleep(60)

if __name__ == '__main__':
    asyncio.run(run_hunt())
