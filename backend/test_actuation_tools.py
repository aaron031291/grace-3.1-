import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import asyncio
from grace_mcp.builtin_tools import _handle_execute_shell_command

async def run_hunt():
    res = await _handle_execute_shell_command({
        "command": "python ../backend/agent/test_agent.py" if os.path.exists("../backend/agent/test_agent.py") else "echo 'No test_agent.py found, please create an agent launcher'",
        "rationale": "Verify execution of shell command tool"
    })
    print("Test Execute Result:", res)

if __name__ == "__main__":
    asyncio.run(run_hunt())
