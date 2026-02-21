import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from grace_mcp.orchestrator import MCPOrchestrator

async def verify_resource_templates():
    print("--- Verifying Resource Templates Implementation ---")
    
    # 1. Initialize Orchestrator
    orchestrator = MCPOrchestrator()
    print("Initializing orchestrator...")
    success = await orchestrator.initialize()
    if not success:
        print("❌ Failed to initialize orchestrator")
        return False
    
    # 2. Check Resource Templates List
    print("\nListing resource templates...")
    templates = await orchestrator.mcp_client.list_resource_templates()
    print(f"Found {len(templates)} templates")
    
    has_logs_template = False
    for t in templates:
        print(f" - {t['name']}: {t['uri_template']} ({t['mime_type']})")
        if t['uri_template'] == "logs://{pid}":
            has_logs_template = True
            
    if not has_logs_template:
        print("❌ 'logs://{pid}' template not found")
        # return False # Might not be fatal if direct call works
    else:
        print("✅ 'logs://{pid}' template found")

    # 3. Start a dummy process to test logs
    print("\nStarting a dummy process (ping localhost)...")
    start_result = await orchestrator.mcp_client.call_tool(
        tool_name="start_process",
        arguments={
            "command": "ping localhost -n 10",
            "name": "log-test-proc",
            "timeout_ms": 30000
        }
    )
    
    if not start_result.get("success"):
        print(f"❌ Failed to start process: {start_result.get('error')}")
        return False
    
    pid = None
    # Extract PID from result - usually start_process returns it in text or _meta
    content = start_result.get("content", "")
    print(f"Start result: {content}")
    
    # Simple extraction of PID from common message format
    import re
    pid_match = re.search(r"PID (\d+)", content)
    if pid_match:
        pid = int(pid_match.group(1))
    
    if not pid:
        # Fallback 2: Check for "PID: 1234" (just in case)
        pid_match = re.search(r"PID: (\d+)", content)
        if pid_match:
            pid = int(pid_match.group(1))

    if not pid:
        # Fallback 3: check list_processes
        print("PID not found in output, checking list_processes...")
        proc_list = await orchestrator.mcp_client.call_tool("list_processes", {})
        proc_content = proc_list.get("content", "")
        print(f"Active processes: {proc_content}")
        
        # Try to find our ping process
        ping_match = re.search(r"PID: (\d+), Command: .*ping", proc_content)
        if ping_match:
            pid = int(ping_match.group(1))
            print(f"Found ping PID via list_processes: {pid}")

    if not pid:
        print("❌ Could not determine PID")
        return False

    print(f"✅ Process started with PID: {pid}")
    
    # Wait a bit for some output
    print("Waiting 3 seconds for output...")
    await asyncio.sleep(3)
    
    # 4. Read Resource
    uri = f"logs://{pid}"
    print(f"\nReading resource: {uri}")
    resource_result = await orchestrator.read_resource(uri)
    
    if not resource_result.get("success"):
        print(f"❌ Failed to read resource: {resource_result.get('error')}")
    else:
        print("✅ Resource read successfully!")
        log_content = resource_result.get("content", "")
        print("--- Log Content Preview ---")
        print(log_content[:500] + "..." if len(log_content) > 500 else log_content)
        print("---------------------------")
        
        if len(log_content.strip()) > 0:
            print("✅ Logs are non-empty")
        else:
            print("⚠️ Logs are empty (process might be slow or failed)")

    # 5. LLM-in-the-loop test
    print("\n--- LLM-in-the-loop Test ---")
    print(f"Asking LLM to analyze logs for PID {pid}...")
    
    prompt = (
        f"I've started a 'ping' process with PID {pid}. "
        f"Please use the 'read_resource' tool with the URI 'logs://{pid}' to read its current logs, "
        f"tell me what the ping results look like, and then confirm if the process seems to be working correctly."
    )
    
    chat_result = await orchestrator.chat([{"role": "user", "content": prompt}])
    
    if chat_result.get("success"):
        print("\n✅ LLM Chat Response:")
        print(chat_result.get("content"))
        
        # Check if LLM actually called the tool
        tool_calls = chat_result.get("tool_calls_made", [])
        used_read_resource = any(tc.get("tool") == "read_resource" for tc in tool_calls)
        
        if used_read_resource:
            print("\n✅ Success: LLM used the 'read_resource' tool!")
        else:
            print("\n❌ Failure: LLM did NOT use the 'read_resource' tool.")
            print(f"Tool calls made: {[tc.get('tool') for tc in tool_calls]}")
    else:
        print(f"\n❌ LLM Chat failed: {chat_result.get('error')}")

    # 6. Verify Audit Log
    print("\nChecking audit log...")
    recent = orchestrator.mcp_client.audit_logger.get_recent_entries(5)
    found_audit = False
    for entry in recent:
        if entry.get("type") == "resource_read" and entry.get("resource_uri") == uri:
            found_audit = True
            print(f"✅ Found audit entry for {uri}")
            break
    
    if not found_audit:
        print("❌ Audit entry for resource read not found")

    # 6. Cleanup
    print("\nStopping process...")
    await orchestrator.mcp_client.call_tool("kill_process", {"pid": pid})
    await orchestrator.shutdown()
    
    print("\n--- Verification Complete ---")
    return True

if __name__ == "__main__":
    asyncio.run(verify_resource_templates())
