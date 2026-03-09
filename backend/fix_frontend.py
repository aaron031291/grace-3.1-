import asyncio
import os
import sys

# Completely suppress standard output to avoid UnicodeEncodeError in Windows 
if sys.platform == "win32":
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grace_mcp.orchestrator import get_mcp_orchestrator_sync
from grace_mcp.builtin_tools import get_builtin_tools

def log_output(msg):
    with open('fix_frontend_log.txt', 'a', encoding='utf-8') as f:
        f.write(str(msg) + '\n')

async def run_hunt():
    with open('fix_frontend_log.txt', 'w', encoding='utf-8') as f:
        f.write('--- Starting Frontend Error Fix Run ---\n')
        
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
    You are Grace's autonomous self-healing agent and you have been explicitly tasked with fixing the RUNTIME error happening in the frontend of the Grace application. You have access to the actuation endpoints including `execute_shell_command`, `submit_coding_task`, `restart_service`, and `update_knowledge_base`.

    Step 1: Investigate the frontend folder (usually located next to the `backend` folder as `../frontend` or similar). Use `execute_shell_command` with commands like `npm run build`, `npm start`, or inspecting logs/terminal histories to determine the nature of the runtime error in the frontend.

    Step 2: Inspect the specific frontend code files that are crashing using your file reading tools or `execute_shell_command cat filename`.

    Step 3: Fix the frontend error. For simple fixes, edit the files directly. For complex fixes or to leverage a coding agent, use `submit_coding_task` detailing exactly what needs to be fixed.

    Step 4: Once you are confident the fix is deployed (e.g., you can compile the frontend successfully or restart the service and verify), emit the word "HUNT COMPLETE".

    Please begin your investigation into the frontend runtime error now. Keep using your tools repeatedly until the bug is squashed.
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
                 log_output(f"Result Preview: {str(call.get('result_preview', ''))[:400]}")
                 
                 messages.append({
                     'role': 'system', 
                     'content': f"Tool '{call.get('tool')}' result: {call.get('result_preview', '')}"
                 })
        
        if 'HUNT COMPLETE' in reply_content:
             log_output('\nAgent finished fixing the frontend.')
             break

if __name__ == '__main__':
    asyncio.run(run_hunt())
